"""
Crypto Plugin — Example plugin: fetch crypto prices from CoinGecko (free, no API key).
"""
import requests
from tools.base import BaseTool


class CryptoPlugin(BaseTool):
    name = "crypto_tool"
    description = "Mendapatkan harga cryptocurrency real-time. Contoh: Bitcoin, Ethereum, BNB."
    parameters = {"coin": "nama koin: bitcoin, ethereum, bnb, solana, dll.", "currency": "IDR atau USD (default: USD)"}

    def run(self, coin: str = "bitcoin", currency: str = "usd", **kwargs) -> str:
        coin = coin.lower().strip()
        currency = currency.lower().strip()
        url = f"https://api.coingecko.com/api/v3/simple/price"
        try:
            resp = requests.get(
                url,
                params={"ids": coin, "vs_currencies": currency, "include_24hr_change": "true"},
                timeout=8,
            )
            resp.raise_for_status()
            data = resp.json()
            if coin not in data:
                return f"❌ Koin '{coin}' tidak ditemukan. Coba: bitcoin, ethereum, bnb, solana"
            price = data[coin][currency]
            change = data[coin].get(f"{currency}_24h_change", 0)
            arrow = "📈" if change >= 0 else "📉"
            currency_symbol = "Rp" if currency == "idr" else "$"
            price_fmt = f"{price:,.0f}" if currency == "idr" else f"{price:,.2f}"
            return (
                f"💰 **{coin.title()}** ({currency.upper()})\n"
                f"  Harga  : {currency_symbol}{price_fmt}\n"
                f"  24h    : {arrow} {change:+.2f}%"
            )
        except Exception as e:
            return f"❌ Gagal mengambil harga {coin}: {e}"
