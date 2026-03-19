"""
Short-term memory — sliding window conversation history (in-memory).
"""
from collections import deque
from typing import List, Dict
import os

MAX_MESSAGES = int(os.getenv("MAX_MEMORY_MESSAGES", "20"))


class ShortTermMemory:
    def __init__(self, max_messages: int = MAX_MESSAGES):
        self._messages: deque = deque(maxlen=max_messages)

    def add(self, role: str, content: str) -> None:
        """Add a message (role: 'user' | 'assistant' | 'system')."""
        self._messages.append({"role": role, "content": content})

    def get_history(self) -> List[Dict[str, str]]:
        """Return all messages in the current window."""
        return list(self._messages)

    def get_context_string(self) -> str:
        """Return conversation as plain text for injection into prompts."""
        lines = []
        for msg in self._messages:
            prefix = "User" if msg["role"] == "user" else "AI"
            lines.append(f"{prefix}: {msg['content']}")
        return "\n".join(lines)

    def clear(self) -> None:
        """Clear the conversation window."""
        self._messages.clear()

    def __len__(self) -> int:
        return len(self._messages)
