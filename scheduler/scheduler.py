"""
Scheduler — APScheduler-based background job management.
Supports one-off reminders and recurring cron jobs.
"""
import re
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor

JOBS_DB = Path.home() / ".ai_agent" / "jobs.db"
JOBS_DB.parent.mkdir(parents=True, exist_ok=True)

jobstores = {
    "default": SQLAlchemyJobStore(url=f"sqlite:///{JOBS_DB}")
}
executors = {"default": ThreadPoolExecutor(max_workers=2)}


class Scheduler:
    def __init__(self, notify_callback: Optional[Callable] = None):
        self._scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults={"coalesce": True, "max_instances": 1},
        )
        self._notify = notify_callback or self._default_notify
        self._scheduler.start()

    def parse_and_schedule(self, user_input: str) -> str:
        """Parse natural language reminder and schedule it."""
        result = self._parse_time(user_input)
        if not result:
            return "❌ Tidak bisa memahami waktu dari permintaan tersebut."

        run_time, task_desc = result

        # Check if it's a recurring task
        if any(kw in user_input.lower() for kw in ["tiap", "setiap", "every", "daily"]):
            return self._schedule_recurring(user_input, task_desc)

        job_id = f"reminder_{int(run_time.timestamp())}"
        msg = f"⏰ Pengingat: {task_desc}"

        self._scheduler.add_job(
            self._notify,
            trigger="date",
            run_date=run_time,
            args=[msg],
            id=job_id,
            replace_existing=True,
        )

        return (
            f"✅ Pengingat diset!\n"
            f"  📅 Waktu: {run_time.strftime('%H:%M, %d %B %Y')}\n"
            f"  📝 Tugas: {task_desc}"
        )

    def _parse_time(self, text: str):
        """Extract time from text like 'jam 5 sore', 'pukul 17:00'."""
        now = datetime.now()
        text_lower = text.lower()

        # Match "jam X" or "pukul X"
        pattern = r'(?:jam|pukul|at)\s*(\d{1,2})(?::(\d{2}))?\s*(pagi|siang|sore|malam|am|pm)?'
        match = re.search(pattern, text_lower)
        if match:
            hour = int(match.group(1))
            minute = int(match.group(2) or 0)
            meridiem = match.group(3) or ""
            if meridiem in ("sore", "malam", "pm") and hour < 12:
                hour += 12
            elif meridiem in ("pagi", "am") and hour == 12:
                hour = 0
            run_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if run_time <= now:
                run_time += timedelta(days=1)

            # Extract task description
            task = re.sub(pattern, "", text, flags=re.IGNORECASE)
            task = re.sub(r'(?:ingatkan|remind)\s*(?:saya|me)?\s*', '', task, flags=re.IGNORECASE).strip()
            task = task or "Pengingat"
            return run_time, task

        # Match "X menit lagi"
        min_match = re.search(r'(\d+)\s*menit\s*(?:lagi|kemudian)?', text_lower)
        if min_match:
            minutes = int(min_match.group(1))
            run_time = now + timedelta(minutes=minutes)
            task = re.sub(r'\d+\s*menit.*', '', text, flags=re.IGNORECASE).strip() or "Pengingat"
            return run_time, task

        return None

    def _schedule_recurring(self, text: str, task_desc: str) -> str:
        """Schedule a recurring task."""
        text_lower = text.lower()
        hour = 8  # default 8 AM

        time_match = re.search(r'(?:jam|pukul)\s*(\d{1,2})', text_lower)
        if time_match:
            hour = int(time_match.group(1))

        job_id = f"cron_{task_desc[:20].replace(' ', '_')}"
        self._scheduler.add_job(
            self._notify,
            trigger="cron",
            hour=hour,
            minute=0,
            args=[f"🔄 Tugas otomatis: {task_desc}"],
            id=job_id,
            replace_existing=True,
        )
        return f"✅ Tugas rutin dijadwalkan setiap hari jam {hour:02d}:00\n  📝 {task_desc}"

    def list_jobs(self) -> str:
        jobs = self._scheduler.get_jobs()
        if not jobs:
            return "📅 Tidak ada jadwal aktif."
        lines = ["📅 **Jadwal aktif:**\n"]
        for job in jobs:
            next_run = job.next_run_time
            lines.append(f"• {job.id}: next run {next_run}")
        return "\n".join(lines)

    def cancel_job(self, job_id: str) -> str:
        try:
            self._scheduler.remove_job(job_id)
            return f"✅ Job '{job_id}' dibatalkan."
        except Exception:
            return f"❌ Job '{job_id}' tidak ditemukan."

    def shutdown(self) -> None:
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)

    @staticmethod
    def _default_notify(message: str) -> None:
        from rich.console import Console
        Console().print(f"\n[bold yellow]{message}[/bold yellow]\n")
