"""
Memory Manager — Unified interface for short-term + long-term memory.
"""
from .short_term import ShortTermMemory
from .long_term import LongTermMemory
from typing import List, Dict, Optional
import uuid


class MemoryManager:
    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or str(uuid.uuid4())
        self.short_term = ShortTermMemory()
        self.long_term = LongTermMemory()

    def add_message(self, role: str, content: str) -> None:
        """Add to both short-term and long-term memory."""
        self.short_term.add(role, content)
        self.long_term.save_message(role, content, self.session_id)

    def get_context(self) -> List[Dict]:
        """Get short-term history for LLM context injection."""
        return self.short_term.get_history()

    def get_context_string(self) -> str:
        return self.short_term.get_context_string()

    def remember_fact(self, key: str, value: str) -> None:
        """Store a named fact in long-term memory."""
        self.long_term.save_fact(key, value)

    def recall_fact(self, key: str) -> Optional[str]:
        return self.long_term.get_fact(key)

    def search_memory(self, query: str) -> Dict:
        """Search both conversations and facts."""
        conversations = self.long_term.search_conversations(query, limit=5)
        facts = self.long_term.search_facts(query)
        return {"conversations": conversations, "facts": facts}

    def get_recent_history(self, limit: int = 20) -> List[Dict]:
        return self.long_term.get_recent_conversations(limit=limit)

    def save_preference(self, key: str, value: str) -> None:
        self.long_term.save_preference(key, value)

    def get_preference(self, key: str) -> Optional[str]:
        return self.long_term.get_preference(key)

    def clear_session(self) -> None:
        """Clear only short-term memory."""
        self.short_term.clear()

    def get_all_facts(self) -> List[Dict]:
        return self.long_term.get_all_facts()
