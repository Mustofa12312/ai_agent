"""
Agent — Core ReAct (Reason → Act → Observe) loop.
Orchestrates LLM, Router, Tools, and Memory.
"""
import os
import re
import json
from typing import Optional
from core.llm import LLMWrapper
from core.router import Router
from memory.memory_manager import MemoryManager
from tools.registry import ToolRegistry, build_registry
from config.config_manager import load_config, get_system_prompt
from utils.logger import logger, log_tool_call, log_tool_result

MAX_ITERATIONS = int(os.getenv("MAX_TOOL_ITERATIONS", "5"))

# Deletion requires confirmation — guarded at agent level
DANGEROUS_ACTIONS = {"delete"}


class Agent:
    def __init__(self):
        self.config = load_config()
        self.memory = MemoryManager()
        self.llm = LLMWrapper()
        self.router = Router()
        self.registry: ToolRegistry = build_registry(
            memory_manager=self.memory,
            config=self.config,
        )
        self._system_prompt = get_system_prompt(self.config)

    # ------------------------------------------------------------------ #
    #  Main entry point
    # ------------------------------------------------------------------ #

    def chat(self, user_input: str, confirm_delete: bool = False) -> str:
        """Process user input and return agent response."""
        self.memory.add_message("user", user_input)
        intent, primary_tool = self.router.route(user_input)
        logger.debug(f"[router] intent={intent}, tool={primary_tool}")

        if intent == "direct_chat":
            response = self._direct_chat(user_input)
        elif intent in ("tool_call", "multi_step"):
            response = self._tool_call_loop(user_input, primary_tool, confirm_delete)
        else:
            response = self._direct_chat(user_input)

        self.memory.add_message("assistant", response)
        return response

    # ------------------------------------------------------------------ #
    #  Direct chat (no tools)
    # ------------------------------------------------------------------ #

    def _direct_chat(self, user_input: str) -> str:
        messages = self.memory.get_context()
        return self.llm.chat(messages, system_prompt=self._system_prompt)

    # ------------------------------------------------------------------ #
    #  Single tool call with ReAct loop
    # ------------------------------------------------------------------ #

    def _tool_call_loop(
        self, user_input: str, tool_name: Optional[str], confirm_delete: bool
    ) -> str:
        context = self.memory.get_context()
        tool_schemas = self.registry.schemas()

        # Ask LLM how to call the tool
        planning_prompt = self._build_planning_prompt(user_input, tool_name)
        plan_messages = context + [{"role": "user", "content": planning_prompt}]
        plan = self.llm.chat(plan_messages, system_prompt=self._system_prompt, tool_schemas=tool_schemas)

        # Parse tool call from LLM response
        tool_calls = self._parse_tool_calls(plan)
        if not tool_calls and tool_name:
            tool_calls = [{"tool": tool_name, "params": self._infer_params(user_input, tool_name)}]

        if not tool_calls:
            return self._direct_chat(user_input)

        observations = []
        for tc in tool_calls[:MAX_ITERATIONS]:
            t_name = tc.get("tool", "")
            t_params = tc.get("params", {})

            # Safety check for dangerous actions
            if t_name == "file_tool" and t_params.get("action") in DANGEROUS_ACTIONS:
                if not confirm_delete:
                    return self._ask_confirmation(t_params.get("path", "file"))

            log_tool_call(t_name, t_params)
            result = self.registry.run_tool(t_name, **t_params)
            log_tool_result(t_name, result)
            observations.append(f"[Hasil {t_name}]: {result}")

        # Let LLM synthesize final response
        synth_messages = context + [
            {"role": "user", "content": user_input},
            {"role": "assistant", "content": "\n".join(observations)},
            {"role": "user", "content": "Berikan respons final berdasarkan hasil tools di atas."},
        ]
        return self.llm.chat(synth_messages, system_prompt=self._system_prompt)

    # ------------------------------------------------------------------ #
    #  Multi-step task
    # ------------------------------------------------------------------ #

    def _multi_step(self, user_input: str, confirm_delete: bool) -> str:
        required_tools = self.router.get_required_tools(user_input)
        all_results = []

        for tool_name in required_tools[:4]:  # Max 4 tools in chain
            params = self._infer_params(user_input, tool_name)
            if tool_name == "file_tool" and params.get("action") in DANGEROUS_ACTIONS:
                if not confirm_delete:
                    return self._ask_confirmation(params.get("path", "file"))
            log_tool_call(tool_name, params)
            result = self.registry.run_tool(tool_name, **params)
            log_tool_result(tool_name, result)
            all_results.append(f"[{tool_name}]:\n{result}")

        combined = "\n\n".join(all_results)
        context = self.memory.get_context()
        synth_messages = context + [
            {"role": "user", "content": user_input},
            {"role": "assistant", "content": combined},
            {
                "role": "user",
                "content": "Berikan ringkasan komprehensif dari semua hasil di atas.",
            },
        ]
        return self.llm.chat(synth_messages, system_prompt=self._system_prompt)

    # ------------------------------------------------------------------ #
    #  Helpers
    # ------------------------------------------------------------------ #

    def _build_planning_prompt(self, user_input: str, tool_name: Optional[str]) -> str:
        tools_info = "\n".join(
            f"- {t.name}: {t.description} | params: {t.parameters}"
            for t in self.registry.all_tools()
        )
        hint = f"Tool yang kemungkinan diperlukan: {tool_name}" if tool_name else ""
        return (
            f"User berkata: '{user_input}'\n\n"
            f"Tools tersedia:\n{tools_info}\n\n"
            f"{hint}\n\n"
            "Tentukan tool mana yang tepat dan parameter apa yang dibutuhkan. "
            "Jawab dalam format JSON: "
            '[{"tool": "nama_tool", "params": {"param1": "value1"}}]'
        )

    def _parse_tool_calls(self, text: str) -> list:
        """Extract JSON tool call array from LLM response."""
        patterns = [
            r"\[.*?\]",
            r"```json\s*(\[.*?\])\s*```",
            r"```\s*(\[.*?\])\s*```",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                try:
                    raw = match.group(1) if match.lastindex else match.group(0)
                    calls = json.loads(raw)
                    if isinstance(calls, list):
                        return calls
                except json.JSONDecodeError:
                    continue
        return []

    def _infer_params(self, user_input: str, tool_name: str) -> dict:
        """Simple heuristic parameter extraction from user input."""
        text = user_input.lower()
        params: dict = {}

        if tool_name == "file_tool":
            # Detect action
            if any(kw in text for kw in ["buat file", "tulis", "create", "write"]):
                params["action"] = "write"
            elif any(kw in text for kw in ["baca", "read", "tampilkan isi", "buka"]):
                params["action"] = "read"
            elif any(kw in text for kw in ["hapus", "delete", "rm"]):
                params["action"] = "delete"
            elif any(kw in text for kw in ["tambahkan", "append"]):
                params["action"] = "append"
            elif any(kw in text for kw in ["buat folder", "mkdir"]):
                params["action"] = "mkdir"
            else:
                params["action"] = "list"

            # Extract filename
            filename_match = re.search(
                r'[\w\-. ]+\.(txt|json|csv|md|log|py)', user_input, re.IGNORECASE
            )
            if filename_match:
                params["path"] = filename_match.group(0).strip()

            # Extract content
            content_match = re.search(
                r'(?:dengan isi|content|isi:|berisi|konten)["\s:]+(.+?)(?:\"|$)',
                user_input,
                re.IGNORECASE | re.DOTALL
            )
            if content_match:
                params["content"] = content_match.group(1).strip().strip('"\'')

        elif tool_name == "weather_tool":
            city_match = re.search(
                r'(?:di|cuaca|weather)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
                user_input,
                re.IGNORECASE
            )
            params["city"] = city_match.group(1).strip() if city_match else "Jakarta"

        elif tool_name == "web_search_tool":
            # Remove trigger words
            query = re.sub(
                r'^(cari|search|googling|browsing|cari tahu|temukan|carikan)\s*',
                '', text, flags=re.IGNORECASE
            ).strip()
            params["query"] = query or user_input

        elif tool_name == "news_tool":
            topic = "umum"
            for t_key in ["ai", "teknologi", "indonesia", "ekonomi", "kesehatan", "olahraga"]:
                if t_key in text:
                    topic = t_key
                    break
            params["topic"] = topic

        elif tool_name == "time_tool":
            tz = ""
            for tz_kw in ["wib", "wita", "wit", "jakarta", "bali", "makassar"]:
                if tz_kw in text:
                    tz = tz_kw
                    break
            params["timezone"] = tz

        elif tool_name == "memory_tool":
            if any(kw in text for kw in ["ingat bahwa", "simpan", "catat", "remember", "suka", "aku suka", "aku tidak"]):
                params["action"] = "store"
                # Try to extract key=value
                kv_match = re.search(
                    r'(?:ingat bahwa|bahwa|bahwa saya|saya)\s+(.+)', text
                )
                if kv_match:
                    params["key"] = "preferensi_user"
                    params["value"] = kv_match.group(1).strip()
            elif any(kw in text for kw in ["kemarin", "dulu", "terakhir", "ingat tidak", "apa yang"]):
                params["action"] = "recall"
            elif any(kw in text for kw in ["daftar", "semua"]):
                params["action"] = "list"
            else:
                params["action"] = "recall"
                params["query"] = user_input

        elif tool_name == "scheduler_tool":
            params["task"] = user_input

        return params

    def _ask_confirmation(self, filename: str) -> str:
        return (
            f"⚠️ Kamu mau hapus **{filename}**? "
            "Ketik `ya hapus {filename}` untuk konfirmasi."
        )

    # ------------------------------------------------------------------ #
    #  Utility methods for CLI
    # ------------------------------------------------------------------ #

    def clear_session(self) -> None:
        self.memory.clear_session()

    def get_history(self, limit: int = 20) -> list:
        return self.memory.get_recent_history(limit=limit)

    def get_facts(self) -> list:
        return self.memory.get_all_facts()
