"""
LLM Wrapper — Gemini (primary) with OpenAI fallback.
Supports tool/function calling schema injection.
"""
import os
import asyncio
from typing import List, Dict, Optional, Any
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")


class LLMWrapper:
    """Wraps Gemini API with OpenAI fallback."""

    def __init__(self):
        self._gemini_model = None
        self._openai_client = None
        self._init_gemini()
        self._init_openai()

    def _init_gemini(self) -> None:
        if not GEMINI_API_KEY:
            return
        try:
            import google.generativeai as genai
            genai.configure(api_key=GEMINI_API_KEY)
            self._gemini_model = genai.GenerativeModel(
                model_name="gemini-2.5-flash",
                generation_config={
                    "temperature": 0.7,
                    "top_p": 0.95,
                    "max_output_tokens": 2048,
                },
            )
        except Exception as e:
            from utils.logger import log_error
            log_error("LLM._init_gemini", e)

    def _init_openai(self) -> None:
        if not OPENAI_API_KEY:
            return
        try:
            from openai import OpenAI
            self._openai_client = OpenAI(api_key=OPENAI_API_KEY)
        except Exception as e:
            from utils.logger import log_error
            log_error("LLM._init_openai", e)

    def chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str = "",
        tool_schemas: Optional[List[Dict]] = None,
    ) -> str:
        """Synchronous chat. Returns the assistant's text response."""
        try:
            return self._gemini_chat(messages, system_prompt, tool_schemas)
        except Exception as gemini_err:
            from utils.logger import log_error, logger
            log_error("Gemini", gemini_err)
            if self._openai_client:
                logger.warning("⚠️ Gemini gagal, mencoba OpenAI fallback...")
            try:
                return self._openai_chat(messages, system_prompt)
            except Exception as openai_err:
                if str(openai_err) == "OPENAI_API_KEY tidak dikonfigurasi. Abaikan fallback.":
                    return "❌ Maaf, saya sedang sangat lelah (Batas penggunaan Gemini habis sementara waktu 429). Mohon tunggu sekitar 1-2 menit lalu coba sapa lagi ya! 🥺"
                log_error("OpenAI", openai_err)
                return "❌ Maaf, terjadi kesalahan pada sistem AI. Coba lagi sebentar."

    def _gemini_chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
        tool_schemas: Optional[List[Dict]],
    ) -> str:
        import google.generativeai as genai

        # Build history in Gemini format
        history = []
        system_parts = [system_prompt] if system_prompt else []

        for msg in messages[:-1]:  # All except the last user message
            role = "user" if msg["role"] == "user" else "model"
            history.append({"role": role, "parts": [msg["content"]]})

        last_user_msg = messages[-1]["content"] if messages else ""

        # Include tool context in system
        if tool_schemas:
            tool_desc = "\n\nAva tools yang bisa kamu panggil:\n"
            for t in tool_schemas:
                tool_desc += f"- **{t['name']}**: {t['description']}\n"
                if t.get("parameters"):
                    tool_desc += f"  Params: {t['parameters']}\n"
            system_parts.append(tool_desc)

        full_system = "\n\n".join(system_parts)

        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction=full_system if full_system else None,
            generation_config={"temperature": 0.7, "max_output_tokens": 2048},
        )

        chat = model.start_chat(history=history)
        response = chat.send_message(last_user_msg)
        return response.text.strip()

    def _openai_chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
    ) -> str:
        if not self._openai_client:
            raise ValueError("OPENAI_API_KEY tidak dikonfigurasi. Abaikan fallback.")
        all_messages = []
        if system_prompt:
            all_messages.append({"role": "system", "content": system_prompt})
        all_messages.extend(messages)

        response = self._openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=all_messages,
            max_tokens=1024,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()

    async def async_chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str = "",
        tool_schemas: Optional[List[Dict]] = None,
    ) -> str:
        """Async wrapper around the synchronous chat."""
        return await asyncio.to_thread(self.chat, messages, system_prompt, tool_schemas)

    def is_available(self) -> bool:
        return self._gemini_model is not None or self._openai_client is not None
