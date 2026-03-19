"""
Config Manager — Load and save agent identity/personality settings.
"""
import json
import os
from pathlib import Path
from typing import Any

CONFIG_PATH = Path(__file__).parent.parent / "config.json"


def load_config() -> dict:
    """Load config from config.json."""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return _default_config()


def save_config(cfg: dict) -> None:
    """Persist config changes to config.json."""
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


def get_system_prompt(cfg: dict) -> str:
    """Build the system prompt from personality config."""
    persona_key = cfg.get("personality", "santai")
    personalities = cfg.get("personalities", {})
    base = personalities.get(persona_key, "Kamu adalah AI assistant yang helpful.")
    ai_name = cfg.get("ai_name", "Madura Ai")
    user_name = cfg.get("user_name", "Boss")
    prompt = base.replace("{user_name}", user_name)
    prompt = f"Namamu adalah {ai_name}. " + prompt
    return prompt


def _default_config() -> dict:
    return {
        "ai_name": "Madura Ai",
        "user_name": "Boss",
        "personality": "santai",
        "language": "id",
        "workspace_dir": "workspace",
        "personalities": {
            "santai": "Kamu adalah AI assistant yang ramah, santai, dan suka bercanda. Panggil user dengan '{user_name}'. Gunakan bahasa informal dan sesekali pakai emoji. Tetap cerdas dan helpful.",
            "formal": "Kamu adalah AI assistant profesional dan formal. Panggil user dengan 'Bapak/Ibu {user_name}'. Gunakan bahasa Indonesia baku dan sopan.",
            "hacker": "Kamu adalah AI dengan gaya hacker/programmer. Panggil user dengan '{user_name}'. Suka pakai istilah teknis, efisien, langsung ke poin, no nonsense.",
        },
    }
