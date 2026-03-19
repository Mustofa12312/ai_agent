"""
Utils — Structured logger using Rich.
"""
import logging
import os
from pathlib import Path
from rich.logging import RichHandler
from rich.console import Console

console = Console()

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_DIR = Path.home() / ".ai_agent" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(message)s",
    datefmt="[%X]",
    handlers=[
        RichHandler(console=console, rich_tracebacks=True, show_path=False),
        logging.FileHandler(LOG_DIR / "agent.log", encoding="utf-8"),
    ],
)

logger = logging.getLogger("ai_agent")


def log_tool_call(tool_name: str, params: dict) -> None:
    logger.debug(f"[tool] {tool_name} | params={params}")


def log_tool_result(tool_name: str, result: str) -> None:
    logger.debug(f"[result] {tool_name} | {result[:200]}")


def log_error(context: str, error: Exception) -> None:
    logger.error(f"[error] {context}: {error}")
