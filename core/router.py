"""
Smart Router — Classifies user intent and dispatches to tools or chat.
"""
import re
from typing import Tuple, Optional


# --- Keyword maps for fast tool detection ---
TOOL_KEYWORDS: dict = {
    "time_tool": [
        "jam", "waktu", "pukul", "hari apa", "tanggal", "sekarang jam",
        "what time", "hari ini tanggal", "timezone", "zona waktu",
    ],
    "weather_tool": [
        "cuaca", "hujan", "suhu", "panas", "dingin", "angin", "kelembaban",
        "weather", "temperature", "forecast", "prakiraan",
    ],
    "file_tool": [
        "buat file", "tulis file", "baca file", "hapus file", "edit file",
        "create file", "read file", "delete file", "write file",
        "buat folder", "tampilkan isi", "list file", "daftar file",
        "simpan ke file", "buka file", "rename file",
    ],
    "web_search_tool": [
        "cari", "search", "googling", "bing", "temukan informasi",
        "cari tahu", "carikan", "cari di internet", "browse",
    ],
    "news_tool": [
        "berita", "news", "headlines", "terkini", "hari ini berita",
        "update terbaru", "breaking news", "berita terbaru",
    ],
    "memory_tool": [
        "ingat", "remember", "catat", "simpan info", "apa yang kamu ingat",
        "kemarin saya bilang", "kamu ingat tidak", "preferensi saya",
        "suka", "tidak suka", "aku suka", "aku tidak suka",
    ],
    "scheduler_tool": [
        "ingatkan", "remind", "jadwalkan", "scheduler", "jam berapa nanti",
        "set reminder", "alarm", "tiap hari", "setiap pagi",
        "automatically", "otomatis cek",
    ],
}

MULTI_STEP_PATTERNS = [
    r"cari.*lalu.*ringkas",
    r"search.*then.*summarize",
    r"temukan.*dan.*buat",
    r"cari.*kemudian",
    r"kumpulkan.*dan.*tampilkan",
    r"ambil.*lalu",
]


class Router:
    """Classifies user input and returns (intent, tool_name_or_none)."""

    def route(self, user_input: str) -> Tuple[str, Optional[str]]:
        """
        Returns:
            (intent, tool_name)
            intent  : 'tool_call' | 'multi_step' | 'direct_chat'
            tool_name: tool name or None
        """
        text = user_input.lower().strip()

        # Check multi-step first
        if self._is_multi_step(text):
            return ("multi_step", self._detect_primary_tool(text))

        # Check single tool
        tool = self._detect_tool(text)
        if tool:
            return ("tool_call", tool)

        return ("direct_chat", None)

    def _detect_tool(self, text: str) -> Optional[str]:
        """Return the first matched tool name."""
        for tool_name, keywords in TOOL_KEYWORDS.items():
            for kw in keywords:
                if kw in text:
                    return tool_name
        return None

    def _detect_primary_tool(self, text: str) -> Optional[str]:
        """Detect the primary tool in a multi-step task."""
        # Priority order
        for priority_tool in ["news_tool", "web_search_tool", "file_tool", "weather_tool"]:
            keywords = TOOL_KEYWORDS.get(priority_tool, [])
            for kw in keywords:
                if kw in text:
                    return priority_tool
        return self._detect_tool(text)

    def _is_multi_step(self, text: str) -> bool:
        for pattern in MULTI_STEP_PATTERNS:
            if re.search(pattern, text):
                return True
        # Detect "and then" style chaining  
        if " dan " in text and any(kw in text for kw in ["lalu", "kemudian", "setelah itu", "then"]):
            return True
        return False

    def get_required_tools(self, user_input: str) -> list:
        """Get all tools mentioned in a multi-step input."""
        text = user_input.lower()
        found = []
        for tool_name, keywords in TOOL_KEYWORDS.items():
            for kw in keywords:
                if kw in text and tool_name not in found:
                    found.append(tool_name)
        return found
