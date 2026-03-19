"""
Memory Tool — Allows agent to query and store long-term memory facts.
"""
from .base import BaseTool
from typing import Any


class MemoryTool(BaseTool):
    name = "memory_tool"
    description = (
        "Menyimpan dan mengingat fakta, preferensi, atau informasi penting tentang user. "
        "Bisa menyimpan ('store') atau mengingat kembali ('recall') informasi."
    )
    parameters = {
        "action": "recall | store | list | search",
        "key": "(opsional) kunci/nama fakta",
        "value": "(opsional) nilai untuk disimpan (wajib saat store)",
        "query": "(opsional) kata kunci untuk pencMadura Ain",
    }

    def __init__(self, memory_manager: Any = None):
        self.memory = memory_manager

    def run(
        self,
        action: str = "recall",
        key: str = "",
        value: str = "",
        query: str = "",
        **kwargs,
    ) -> str:
        if not self.memory:
            return "❌ Memory manager tidak tersedia."

        action = action.lower().strip()

        if action == "store":
            return self._store(key, value)
        elif action == "recall":
            return self._recall(key, query)
        elif action == "list":
            return self._list_all()
        elif action == "search":
            return self._search(query or key)
        else:
            return f"❌ Action tidak dikenal: '{action}'. Pilih: recall, store, list, search"

    def _store(self, key: str, value: str) -> str:
        if not key or not value:
            return "❌ 'key' dan 'value' diperlukan untuk menyimpan fakta."
        self.memory.remember_fact(key, value)
        return f"✅ Tersimpan: **{key}** = {value}"

    def _recall(self, key: str, query: str) -> str:
        if key:
            val = self.memory.recall_fact(key)
            if val:
                return f"🧠 Ingatan tentang '{key}': {val}"
            return f"❓ Tidak ada ingatan untuk '{key}'."
        if query:
            return self._search(query)
        # Recall recent conversations
        history = self.memory.get_recent_history(limit=10)
        if not history:
            return "🧠 Belum ada percakapan yang tersimpan."
        lines = ["🧠 **Percakapan terakhir:**\n"]
        for msg in history[-5:]:
            role = "Kamu" if msg["role"] == "user" else "Madura Ai"
            ts = msg.get("timestamp", "")[:16]
            lines.append(f"[{ts}] **{role}**: {msg['content'][:120]}")
        return "\n".join(lines)

    def _list_all(self) -> str:
        facts = self.memory.get_all_facts()
        if not facts:
            return "🧠 Belum ada fakta yang tersimpan."
        lines = ["🧠 **Fakta yang diingat:**\n"]
        for f in facts:
            lines.append(f"• **{f['key']}**: {f['value']} _(disimpan: {f['timestamp'][:10]})_")
        return "\n".join(lines)

    def _search(self, query: str) -> str:
        if not query:
            return "❌ Query pencMadura Ain diperlukan."
        results = self.memory.search_memory(query)
        lines = [f"🔍 **Hasil pencMadura Ain memori: '{query}'**\n"]
        facts = results.get("facts", [])
        convos = results.get("conversations", [])
        if facts:
            lines.append("**Fakta:**")
            for f in facts:
                lines.append(f"• {f['key']}: {f['value']}")
        if convos:
            lines.append("\n**Percakapan:**")
            for c in convos[:3]:
                role = "Kamu" if c["role"] == "user" else "AI"
                lines.append(f"• [{c['timestamp'][:10]}] {role}: {c['content'][:100]}")
        if not facts and not convos:
            return f"❓ Tidak ada ingatan tentang '{query}'."
        return "\n".join(lines)
