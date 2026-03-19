"""
File Tool — Sandboxed file operations (read, write, append, delete, list).
All operations are restricted to the workspace directory.
"""
import os
import csv
import json
from pathlib import Path
from typing import Optional
from .base import BaseTool


class FileTool(BaseTool):
    name = "file_tool"
    description = (
        "Membaca, menulis, mengedit, menghapus file dan folder, serta membuat folder. "
        "Hanya bisa akses folder workspace. "
        "Dukung: .txt, .json, .csv, .md."
    )
    parameters = {
        "action": "read | write | append | delete | list | mkdir",
        "path": "nama file atau folder (relatif dari workspace)",
        "content": "(opsional) konten untuk write/append",
    }

    def __init__(self, workspace_dir: str = "workspace"):
        self.workspace = Path(workspace_dir).resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)

    def run(self, action: str = "list", path: str = "", content: str = "", **kwargs) -> str:
        action = action.lower().strip()
        safe_path = self._safe_path(path) if path else None

        if action == "list":
            return self._list(safe_path or self.workspace)
        elif action == "read":
            return self._read(safe_path)
        elif action == "write":
            return self._write(safe_path, content)
        elif action == "append":
            return self._append(safe_path, content)
        elif action == "delete":
            return self._delete(safe_path)
        elif action == "mkdir":
            return self._mkdir(safe_path)
        else:
            return f"❌ Action tidak dikenal: '{action}'. Pilih: read, write, append, delete, list, mkdir"

    def _safe_path(self, rel_path: str) -> Path:
        """Resolve path and ensure it's inside workspace."""
        target = (self.workspace / rel_path).resolve()
        if not str(target).startswith(str(self.workspace)):
            raise PermissionError(f"⛔ Akses ditolak: '{rel_path}' berada di luar workspace.")
        return target

    def _list(self, dir_path: Path) -> str:
        if not dir_path.exists():
            return f"❌ Folder '{dir_path.name}' tidak ditemukan."
        items = list(dir_path.iterdir())
        if not items:
            return "📂 Workspace kosong."
        lines = [f"📂 Isi workspace ({dir_path}):"]
        for item in sorted(items):
            icon = "📁" if item.is_dir() else "📄"
            size = f" ({item.stat().st_size} bytes)" if item.is_file() else ""
            lines.append(f"  {icon} {item.name}{size}")
        return "\n".join(lines)

    def _read(self, path: Path) -> str:
        if path is None:
            return "❌ Nama file diperlukan untuk membaca."
        if not path.exists():
            return f"❌ File '{path.name}' tidak ditemukan di workspace."
        suffix = path.suffix.lower()
        try:
            if suffix == ".json":
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                return f"📄 {path.name}:\n```json\n{json.dumps(data, indent=2, ensure_ascii=False)}\n```"
            elif suffix == ".csv":
                with open(path, newline="", encoding="utf-8") as f:
                    reader = csv.reader(f)
                    rows = list(reader)
                lines = [" | ".join(r) for r in rows[:50]]
                return f"📄 {path.name} (CSV, {len(rows)} baris):\n" + "\n".join(lines)
            else:
                content = path.read_text(encoding="utf-8")
                return f"📄 {path.name}:\n{content}"
        except Exception as e:
            return f"❌ Gagal membaca '{path.name}': {e}"

    def _write(self, path: Path, content: str) -> str:
        if path is None:
            return "❌ Nama file diperlukan."
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return f"✅ File '{path.name}' berhasil ditulis ({len(content)} karakter)."

    def _append(self, path: Path, content: str) -> str:
        if path is None:
            return "❌ Nama file diperlukan."
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(content + "\n")
        return f"✅ Konten ditambahkan ke '{path.name}'."

    def _delete(self, path: Path) -> str:
        if path is None:
            return "❌ Nama file/folder diperlukan."
        if not path.exists():
            return f"❌ '{path.name}' tidak ditemukan."
        if path.is_file():
            path.unlink()
            return f"🗑️ File '{path.name}' berhasil dihapus."
        elif path.is_dir():
            import shutil
            shutil.rmtree(path)
            return f"🗑️ Folder '{path.name}' beserta isinya berhasil dihapus."
        return "❌ Gagal menghapus."

    def _mkdir(self, path: Path) -> str:
        if path is None:
            return "❌ Nama folder diperlukan."
        path.mkdir(parents=True, exist_ok=True)
        return f"✅ Folder '{path.name}' berhasil dibuat."
