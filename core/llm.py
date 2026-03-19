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
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")


class LLMWrapper:
    """Wraps Gemini API with Groq/OpenAI fallback."""

    def __init__(self):
        self._gemini_model = None
        self._fallback_client = None
        self._fallback_model = None
        self._fallback_name = None
        self._init_gemini()
        self._init_fallback()

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

    def _init_fallback(self) -> None:
        try:
            from openai import OpenAI
            if GROQ_API_KEY:
                self._fallback_client = OpenAI(
                    api_key=GROQ_API_KEY, 
                    base_url="https://api.groq.com/openai/v1"
                )
                self._fallback_model = "llama-3.3-70b-versatile"
                self._fallback_name = "Groq (Llama 3)"
            elif OPENAI_API_KEY:
                self._fallback_client = OpenAI(api_key=OPENAI_API_KEY)
                self._fallback_model = "gpt-3.5-turbo"
                self._fallback_name = "OpenAI"
        except Exception as e:
            from utils.logger import log_error
            log_error("LLM._init_fallback", e)

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
            if self._fallback_client:
                logger.warning(f"⚠️ Gemini gagal (Limit 429), otomatis memakai {self._fallback_name}...")
            try:
                return self._fallback_chat(messages, system_prompt)
            except Exception as fallback_err:
                if str(fallback_err) == "NO_FALLBACK_KEY":
                    return "❌ Maaf, saya sedang sangat lelah (Batas penggunaan harian Gemini habis). **Saran:** Tambahkan `GROQ_API_KEY` di file `.env` supaya saya bisa otomatis memakai Llama-3 gratis saat ini terjadi!"
                log_error("Fallback", fallback_err)
                return "❌ Maaf, terjadi kesalahan pada sistem AI. Coba lagi sebentar."

    def _gemini_chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
        tool_schemas: Optional[List[Dict]],
    ) -> str:
        import google.generativeai as genai

        history = []
        system_parts = [system_prompt] if system_prompt else []

        for msg in messages[:-1]:
            role = "user" if msg["role"] == "user" else "model"
            history.append({"role": role, "parts": [msg["content"]]})

        last_user_msg = messages[-1]["content"] if messages else ""

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

    def _fallback_chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
    ) -> str:
        if not self._fallback_client:
            raise ValueError("NO_FALLBACK_KEY")
        all_messages = []
        if system_prompt:
            all_messages.append({"role": "system", "content": system_prompt})
        all_messages.extend(messages)

        response = self._fallback_client.chat.completions.create(
            model=self._fallback_model,
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
        return await asyncio.to_thread(self.chat, messages, system_prompt, tool_schemas)

    def is_available(self) -> bool:
        return self._gemini_model is not None or self._fallback_client is not None

