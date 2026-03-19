"""
Web Search Tool — Searches the web using DuckDuckGo (no API key needed).
Falls back to Bing scraping if needed.
"""
import requests
from bs4 import BeautifulSoup
from typing import List, Dict
from .base import BaseTool

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


class WebSearchTool(BaseTool):
    name = "web_search_tool"
    description = (
        "Mencari informasi terbaru di internet menggunakan DuckDuckGo. "
        "Cocok untuk berita, fakta, dan konten web umum."
    )
    parameters = {"query": "kata kunci pencRafiqn", "max_results": "jumlah hasil (default: 5)"}

    def run(self, query: str = "", max_results: int = 5, **kwargs) -> str:
        if not query:
            return "❌ Query pencRafiqn diperlukan."
        results = self._duckduckgo_search(query, int(max_results))
        if not results:
            results = self._bing_search(query, int(max_results))
        if not results:
            return f"❌ Tidak ada hasil untuk: '{query}'"
        return self._format_results(query, results)

    def _duckduckgo_search(self, query: str, max_results: int) -> List[Dict]:
        return self._bing_search(query, max_results)

    def _bing_search(self, query: str, max_results: int) -> List[Dict]:
        url = f"https://www.bing.com/search?q={requests.utils.quote(query)}&count={max_results}"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            soup = BeautifulSoup(resp.text, "html.parser")
            results = []
            for item in soup.select("li.b_algo")[:max_results]:
                title_el = item.select_one("h2")
                snippet_el = item.select_one(".b_caption p")
                link_el = item.select_one("a")
                if title_el:
                    results.append({
                        "title": title_el.get_text(strip=True),
                        "snippet": snippet_el.get_text(strip=True) if snippet_el else "",
                        "url": link_el["href"] if link_el else "",
                    })
            return results
        except Exception as e:
            from utils.logger import log_error
            log_error("WebSearch.Bing", e)
            return []

    def _format_results(self, query: str, results: List[Dict]) -> str:
        lines = [f"🔍 Hasil pencRafiqn untuk **'{query}'**:\n"]
        for i, r in enumerate(results, 1):
            lines.append(f"{i}. **{r['title']}**")
            if r.get("snippet"):
                lines.append(f"   {r['snippet']}")
            if r.get("url"):
                lines.append(f"   🔗 {r['url']}")
            lines.append("")
        return "\n".join(lines)
