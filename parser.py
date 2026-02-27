"""
Парсер трендов и конкурентов.
Находит актуальные темы для статей через:
  - RSS/HTML страниц конкурентов
  - Google News RSS по ключевым словам
  - Яндекс.Новости RSS
"""

import re
import time
import logging
import urllib.parse
from dataclasses import dataclass
from typing import Optional

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


@dataclass
class Topic:
    title: str
    description: str
    source_url: str
    source: str  # "competitor" | "google_news" | "yandex_news"


# ──────────────────────────────────────────────────────────────────────────────
# Парсинг RSS/страниц конкурентов
# ──────────────────────────────────────────────────────────────────────────────

def _fetch(url: str, timeout: int = 15) -> Optional[str]:
    try:
        resp = requests.get(
            url,
            headers=HEADERS,
            timeout=timeout,
            proxies={"http": None, "https": None},
        )
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding
        return resp.text
    except Exception as e:
        logger.warning(f"Fetch error {url}: {e}")
        return None


def _parse_rss(xml_text: str, source_label: str) -> list[Topic]:
    topics = []
    try:
        soup = BeautifulSoup(xml_text, "xml")
        items = soup.find_all("item")[:20]
        for item in items:
            title_tag = item.find("title")
            desc_tag = item.find("description") or item.find("summary")
            link_tag = item.find("link")
            if not title_tag:
                continue
            title = title_tag.get_text(strip=True)
            desc = BeautifulSoup(
                (desc_tag.get_text(strip=True) if desc_tag else ""), "html.parser"
            ).get_text()[:300]
            link = link_tag.get_text(strip=True) if link_tag else ""
            topics.append(Topic(title=title, description=desc, source_url=link, source=source_label))
    except Exception as e:
        logger.warning(f"RSS parse error: {e}")
    return topics


def parse_competitor_site(url: str) -> list[Topic]:
    """Парсит страницу конкурента: ищет RSS или извлекает заголовки статей."""
    html = _fetch(url)
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")

    # 1. Попробовать найти RSS
    rss_link = soup.find("link", {"type": "application/rss+xml"})
    if rss_link and rss_link.get("href"):
        rss_url = urllib.parse.urljoin(url, rss_link["href"])
        rss_text = _fetch(rss_url)
        if rss_text:
            topics = _parse_rss(rss_text, "competitor")
            if topics:
                logger.info(f"Competitor RSS {rss_url}: {len(topics)} topics")
                return topics

    # 2. Fallback — ищем статьи по тегам h2/h3 с ссылками
    topics = []
    for tag in soup.find_all(["h2", "h3"], limit=30):
        a = tag.find("a", href=True)
        if not a:
            a = tag.find_parent("a", href=True) or tag.find_next("a", href=True)
        title = tag.get_text(strip=True)
        link = urllib.parse.urljoin(url, a["href"]) if a else url
        if len(title) > 20:
            topics.append(Topic(title=title, description="", source_url=link, source="competitor"))

    logger.info(f"Competitor HTML {url}: {len(topics)} topics")
    return topics[:15]


# ──────────────────────────────────────────────────────────────────────────────
# Google News по ключевым словам
# ──────────────────────────────────────────────────────────────────────────────

def fetch_google_news(keyword: str, lang: str = "ru", country: str = "RU") -> list[Topic]:
    """Получает топ новостей из Google News RSS."""
    q = urllib.parse.quote(keyword)
    url = f"https://news.google.com/rss/search?q={q}&hl={lang}&gl={country}&ceid={country}:{lang}"
    xml = _fetch(url)
    if not xml:
        return []
    topics = _parse_rss(xml, "google_news")
    logger.info(f"Google News '{keyword}': {len(topics)} topics")
    return topics


# ──────────────────────────────────────────────────────────────────────────────
# Яндекс.Новости
# ──────────────────────────────────────────────────────────────────────────────

def fetch_yandex_news(keyword: str) -> list[Topic]:
    """Получает новости Яндекса по ключевому слову."""
    q = urllib.parse.quote(keyword)
    url = f"https://news.yandex.ru/search.rss?text={q}&grhow=clutster"
    xml = _fetch(url)
    if not xml:
        return []
    topics = _parse_rss(xml, "yandex_news")
    logger.info(f"Yandex News '{keyword}': {len(topics)} topics")
    return topics


# ──────────────────────────────────────────────────────────────────────────────
# Публичный API
# ──────────────────────────────────────────────────────────────────────────────

def deduplicate(topics: list[Topic], seen_titles: set[str] | None = None) -> list[Topic]:
    """Убирает дубликаты по нормализованному заголовку."""
    if seen_titles is None:
        seen_titles = set()
    unique = []
    for t in topics:
        key = re.sub(r"\W+", "", t.title.lower())[:60]
        if key and key not in seen_titles:
            seen_titles.add(key)
            unique.append(t)
    return unique


def collect_topics(
    competitor_urls: list[str],
    niche_keywords: list[str],
    limit: int = 20,
) -> list[Topic]:
    """
    Собирает темы из всех источников и возвращает дедуплицированный список.
    """
    all_topics: list[Topic] = []

    for url in competitor_urls:
        all_topics.extend(parse_competitor_site(url))
        time.sleep(1)

    for kw in niche_keywords:
        all_topics.extend(fetch_google_news(kw))
        all_topics.extend(fetch_yandex_news(kw))
        time.sleep(0.5)

    unique = deduplicate(all_topics)
    logger.info(f"Total unique topics collected: {len(unique)}")
    return unique[:limit]
