"""
Time Tool — Returns current local time, date, day in specified timezone.
"""
import pytz
from datetime import datetime
from .base import BaseTool

# Common Indonesian timezone aliases
TZ_ALIASES = {
    "wib": "Asia/Jakarta",
    "wita": "Asia/Makassar",
    "wit": "Asia/Jayapura",
    "jakarta": "Asia/Jakarta",
    "bali": "Asia/Makassar",
    "makassar": "Asia/Makassar",
    "local": "Asia/Jakarta",
    "": "Asia/Jakarta",
}

DAYS_ID = {
    "Monday": "Senin", "Tuesday": "Selasa", "Wednesday": "Rabu",
    "Thursday": "Kamis", "Friday": "Jumat", "Saturday": "Sabtu", "Sunday": "Minggu",
}
MONTHS_ID = {
    "January": "Januari", "February": "Februari", "March": "Maret",
    "April": "April", "May": "Mei", "June": "Juni",
    "July": "Juli", "August": "Agustus", "September": "September",
    "October": "Oktober", "November": "November", "December": "Desember",
}


class TimeTool(BaseTool):
    name = "time_tool"
    description = (
        "Memberikan waktu dan tanggal saat ini. "
        "Mendukung berbagai timezone (WIB, WITA, WIT, atau nama kota)."
    )
    parameters = {"timezone": "(opsional) timezone: wib, wita, wit, atau nama kota"}

    def run(self, timezone: str = "", **kwargs) -> str:
        tz_key = timezone.lower().strip()
        tz_name = TZ_ALIASES.get(tz_key, tz_key or "Asia/Jakarta")

        try:
            tz = pytz.timezone(tz_name)
        except pytz.exceptions.UnknownTimeZoneError:
            tz = pytz.timezone("Asia/Jakarta")
            tz_name = "Asia/Jakarta"

        now = datetime.now(tz)
        day_en = now.strftime("%A")
        month_en = now.strftime("%B")
        day_id = DAYS_ID.get(day_en, day_en)
        month_id = MONTHS_ID.get(month_en, month_en)

        utc_offset = now.strftime("%z")
        offset_fmt = f"UTC{utc_offset[:3]}:{utc_offset[3:]}"

        return (
            f"🕐 **Waktu Sekarang:**\n"
            f"  Waktu  : {now.strftime('%H:%M:%S')}\n"
            f"  Hari   : {day_id}\n"
            f"  Tanggal: {now.day} {month_id} {now.year}\n"
            f"  Zona   : {tz_name} ({offset_fmt})"
        )
