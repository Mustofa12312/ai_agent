"""
News Tool — Aggregates and summarizes news from multiple sources.
Uses RSS feeds (no API key needed) and scraping.
"""
import requests
from bs4 import BeautifulSoup
from typing import List, Dict
from .base import BaseTool

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; AIAgent/1.0)"
    )
}

RSS_SOURCES = {
    "teknologi": [
        ("TechCrunch", "https://techcrunch.com/feed/"),
        ("The Verge", "https://www.theverge.com/rss/index.xml"),
    ],
    "ai": [
        ("AI News", "https://techcrunch.com/tag/artificial-intelligence/feed/"),
        ("MIT Tech", "https://news.mit.edu/rss/topic/artificial-intelligence2"),
    ],
    "indonesia": [
        ("Kompas", "https://rss.kompas.com/nationalfeed.xml"),
        ("CNN Indonesia", "https://www.cnnindonesia.com/teknologi/rss"),
    ],
    "umum": [
        ("BBC", "https://feeds.bbci.co.uk/news/rss.xml"),
        ("Reuters", "https://feeds.reuters.com/reuters/topNews"),
    ],
}

CATEGORY_KEYWORDS = {
    "ai": ["artificial intelligence", "machine learning", "ai ", "llm", "chatgpt", "gemini", "openai"],
    "teknologi": ["technology", "tech", "software", "hardware", "startup"],
    "indonesia": ["indonesia", "jakarta", "jokowi", "prabowo"],
    "ekonomi": ["economy", "economic", "market", "saham", "rupiah"],
    "kesehatan": ["health", "medical", "covid", "vaccine", "kesehatan"],
}


class NewsTool(BaseTool):
    name = "news_tool"
    description = (
        "Mengambil berita terbaru dari berbagai sumber (RSS), "
        "meringkasnya menjadi bullet points, dan memberikan confidence level."
    )
    parameters = {
        "topic": "topik berita: ai, teknologi, indonesia, umum (default: umum)",
        "max_items": "jumlah berita (default: 8)",
    }

    def run(self, topic: str = "umum", max_items: int = 8, **kwargs) -> str:
        topic_key = topic.lower().strip()
        sources = RSS_SOURCES.get(topic_key, RSS_SOURCES["umum"])
        all_articles = []

        for source_name, rss_url in sources:
            articles = self._parse_rss(source_name, rss_url)
            all_articles.extend(articles)

        # Also try keyword-matched sources
        if topic_key not in RSS_SOURCES:
            for src_name, rss_url in RSS_SOURCES["umum"]:
                arts = self._parse_rss(src_name, rss_url)
                # Filter by topic keyword
                keyword_art = [
                    a for a in arts
                    if topic_key in a.get("title", "").lower()
                    or topic_key in a.get("summary", "").lower()
                ]
                all_articles.extend(keyword_art)

        if not all_articles:
            return f"❌ Tidak ada berita untuk topik '{topic}' saat ini."

        # Deduplicate by title
        seen = set()
        unique = []
        for art in all_articles:
            if art["title"] not in seen:
                seen.add(art["title"])
                unique.append(art)

        unique = unique[:int(max_items)]
        return self._format_news(topic, unique)

    def _parse_rss(self, source_name: str, url: str) -> List[Dict]:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=8)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.content, "xml")
            items = soup.find_all("item") or soup.find_all("entry")
            articles = []
            for item in items[:10]:
                title = item.find("title")
                desc = item.find("description") or item.find("summary")
                link = item.find("link")
                pub_date = item.find("pubDate") or item.find("published")
                articles.append({
                    "title": title.get_text(strip=True) if title else "Tanpa judul",
                    "summary": self._clean_text(desc.get_text(strip=True) if desc else ""),
                    "url": (link.get_text(strip=True) if link else ""),
                    "date": pub_date.get_text(strip=True)[:16] if pub_date else "?",
                    "source": source_name,
                    "confidence": self._confidence_score(title, desc),
                })
            return articles
        except Exception as e:
            from utils.logger import log_error
            log_error(f"News.RSS.{source_name}", e)
            return []

    def _clean_text(self, text: str) -> str:
        """Strip HTML tags."""
        soup = BeautifulSoup(text, "html.parser")
        clean = soup.get_text(separator=" ", strip=True)
        return clean[:200] + "..." if len(clean) > 200 else clean

    def _confidence_score(self, title, desc) -> str:
        score = 50
        if title and len(title.get_text(strip=True)) > 20:
            score += 20
        if desc and len(desc.get_text(strip=True)) > 50:
            score += 30
        if score >= 90:
            return "🟢 Tinggi"
        elif score >= 70:
            return "🟡 Sedang"
        return "🔴 Rendah"

    def _format_news(self, topic: str, articles: List[Dict]) -> str:
        lines = [f"📰 **Berita Terbaru — {topic.upper()}** ({len(articles)} berita)\n"]
        for i, a in enumerate(articles, 1):
            lines.append(f"{i}. **{a['title']}**")
            lines.append(f"   📅 {a['date']} | 📡 {a['source']} | {a['confidence']}")
            if a.get("summary"):
                lines.append(f"   ↳ {a['summary']}")
            if a.get("url"):
                lines.append(f"   🔗 {a['url']}")
            lines.append("")
        return "\n".join(lines)
