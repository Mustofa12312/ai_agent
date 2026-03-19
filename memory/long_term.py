"""
Long-term memory — SQLite-based persistent storage.
Stores: conversation history, user preferences, named facts.
"""
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

DB_DIR = Path.home() / ".ai_agent"
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DB_DIR / "memory.db"


class LongTermMemory:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS facts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    source TEXT DEFAULT 'user',
                    timestamp TEXT NOT NULL,
                    UNIQUE(key)
                );

                CREATE TABLE IF NOT EXISTS preferences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pref_key TEXT NOT NULL UNIQUE,
                    pref_value TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_conversations_session
                    ON conversations(session_id);
                CREATE INDEX IF NOT EXISTS idx_conversations_timestamp
                    ON conversations(timestamp);
            """)

    # --- Conversations ---

    def save_message(self, role: str, content: str, session_id: str) -> None:
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO conversations (role, content, session_id, timestamp) VALUES (?,?,?,?)",
                (role, content, session_id, datetime.now().isoformat()),
            )

    def get_recent_conversations(self, limit: int = 50) -> List[Dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT role, content, timestamp FROM conversations ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in reversed(rows)]

    def get_session_history(self, session_id: str) -> List[Dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT role, content, timestamp FROM conversations WHERE session_id=? ORDER BY timestamp",
                (session_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def search_conversations(self, query: str, limit: int = 10) -> List[Dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT role, content, timestamp FROM conversations WHERE content LIKE ? ORDER BY timestamp DESC LIMIT ?",
                (f"%{query}%", limit),
            ).fetchall()
        return [dict(r) for r in rows]

    # --- Facts ---

    def save_fact(self, key: str, value: str, source: str = "user") -> None:
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO facts (key, value, source, timestamp) VALUES (?,?,?,?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value, timestamp=excluded.timestamp",
                (key, value, source, datetime.now().isoformat()),
            )

    def get_fact(self, key: str) -> Optional[str]:
        with self._get_conn() as conn:
            row = conn.execute("SELECT value FROM facts WHERE key=?", (key,)).fetchone()
        return row["value"] if row else None

    def get_all_facts(self) -> List[Dict]:
        with self._get_conn() as conn:
            rows = conn.execute("SELECT key, value, source, timestamp FROM facts ORDER BY timestamp DESC").fetchall()
        return [dict(r) for r in rows]

    def search_facts(self, query: str) -> List[Dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT key, value, timestamp FROM facts WHERE key LIKE ? OR value LIKE ?",
                (f"%{query}%", f"%{query}%"),
            ).fetchall()
        return [dict(r) for r in rows]

    # --- Preferences ---

    def save_preference(self, key: str, value: str) -> None:
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO preferences (pref_key, pref_value, timestamp) VALUES (?,?,?) "
                "ON CONFLICT(pref_key) DO UPDATE SET pref_value=excluded.pref_value, timestamp=excluded.timestamp",
                (key, value, datetime.now().isoformat()),
            )

    def get_preference(self, key: str) -> Optional[str]:
        with self._get_conn() as conn:
            row = conn.execute("SELECT pref_value FROM preferences WHERE pref_key=?", (key,)).fetchone()
        return row["pref_value"] if row else None

    def get_all_preferences(self) -> Dict:
        with self._get_conn() as conn:
            rows = conn.execute("SELECT pref_key, pref_value FROM preferences").fetchall()
        return {r["pref_key"]: r["pref_value"] for r in rows}

    def clear_all(self) -> None:
        with self._get_conn() as conn:
            conn.execute("DELETE FROM conversations")
            conn.execute("DELETE FROM facts")
            conn.execute("DELETE FROM preferences")
