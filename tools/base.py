"""
Base Tool — Abstract class for all tools in the agent.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseTool(ABC):
    name: str = "base_tool"
    description: str = "Base tool description."
    parameters: Dict = {}

    @abstractmethod
    def run(self, **kwargs) -> str:
        """Execute the tool and return a string result."""
        ...

    def schema(self) -> Dict:
        """Return OpenAI-style function schema for this tool."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }

    def safe_run(self, **kwargs) -> str:
        """Run with error handling."""
        try:
            return self.run(**kwargs)
        except Exception as e:
            from utils.logger import log_error
            log_error(f"Tool.{self.name}", e)
            return f"❌ Error di tool '{self.name}': {str(e)}"
