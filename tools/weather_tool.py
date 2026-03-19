"""
Weather Tool — Real-time weather using wttr.in (no API key needed).
"""
import requests
from .base import BaseTool


class WeatherTool(BaseTool):
    name = "weather_tool"
    description = (
        "Mendapatkan data cuaca real-time: suhu, kelembaban, kondisi, "
        "dan persentase hujan untuk kota tertentu."
    )
    parameters = {"city": "nama kota (contoh: Jakarta, Surabaya, Bandung)"}

    def run(self, city: str = "Jakarta", **kwargs) -> str:
        if not city:
            city = "Jakarta"
        city_enc = city.strip().replace(" ", "+")
        return self._get_wttr(city, city_enc)

    def _get_wttr(self, city: str, city_enc: str) -> str:
        # wttr.in JSON API — no key required
        url = f"https://wttr.in/{city_enc}?format=j1"
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            current = data["current_condition"][0]
            weather_desc = current["weatherDesc"][0]["value"]
            temp_c = current["temp_C"]
            feels_like = current["FeelsLikeC"]
            humidity = current["humidity"]
            wind_kph = current["windspeedKmph"]
            vis_km = current["visibility"]
            cloud = current["cloudcover"]

            # Rain probability from hourly forecast
            today = data.get("weather", [{}])[0]
            hourly = today.get("hourly", [])
            rain_pcts = [int(h.get("chanceofrain", 0)) for h in hourly]
            avg_rain = round(sum(rain_pcts) / len(rain_pcts)) if rain_pcts else 0
            rain_emoji = "🌧️" if avg_rain > 50 else ("🌦️" if avg_rain > 20 else "☀️")

            max_temp = today.get("maxtempC", "?")
            min_temp = today.get("mintempC", "?")

            return (
                f"🌤️ **Cuaca {city.title()} sekarang:**\n"
                f"  Kondisi   : {weather_desc}\n"
                f"  Suhu      : {temp_c}°C (terasa {feels_like}°C)\n"
                f"  Max/Min   : {max_temp}°C / {min_temp}°C\n"
                f"  Kelembaban: {humidity}%\n"
                f"  Angin     : {wind_kph} km/h\n"
                f"  Visibilitas: {vis_km} km\n"
                f"  Awan      : {cloud}%\n"
                f"  {rain_emoji} Hujan hari ini: ~{avg_rain}%"
            )
        except requests.exceptions.Timeout:
            return f"⏱️ Koneksi timeout untuk kota '{city}'. Coba lagi."
        except Exception as e:
            from utils.logger import log_error
            log_error("WeatherTool", e)
            return f"❌ Gagal mengambil data cuaca untuk '{city}': {e}"
