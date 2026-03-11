"""
NewsService
-----------
Handles news site preferences per user, article scraping, 24-hour cache,
and LLM-based translation of regional-language content.
"""

import asyncio
import json
import os
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin, urlparse

import requests
import trafilatura
from bs4 import BeautifulSoup

ROOT = Path(__file__).parent.parent
NEWS_CACHE_DIR = ROOT / "news_cache"
USER_STORE_DIR = ROOT / "user_store" / "profiles"
NEWS_CACHE_DIR.mkdir(parents=True, exist_ok=True)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
}

DEFAULT_SOURCES = [
    {
        "id": "tamil_oneindia",
        "state": "Tamilnadu",
        "name": "Tamil OneIndia",
        "url": "https://tamil.oneindia.com/rss/feeds/tamil-news-fb.xml",
    },
    {
        "id": "kannadaprabha",
        "state": "Karnataka",
        "name": "Kannada Prabha",
        "url": "https://www.kannadaprabha.com/politics",
    },
    {
        "id": "swetchadaily",
        "state": "Telangana",
        "name": "Swetcha Daily",
        "url": "https://swetchadaily.com/politics",
    },
]

_DEFAULT_IDS = {d["id"] for d in DEFAULT_SOURCES}


# ── User preference helpers ────────────────────────────────────────────────

def _user_news_path(user_id: str) -> Path:
    return USER_STORE_DIR / f"{user_id}_news.json"


def _load_user_sites(user_id: str) -> list:
    path = _user_news_path(user_id)
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("sites", [])
    except Exception:
        return []


def _save_user_sites(user_id: str, sites: list):
    _user_news_path(user_id).write_text(
        json.dumps({"sites": sites}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def get_user_sites(user_id: str) -> dict:
    sites = _load_user_sites(user_id)
    existing_ids = {s["id"] for s in sites}
    available_defaults = [d for d in DEFAULT_SOURCES if d["id"] not in existing_ids]
    return {
        "sites": sites,
        "defaults": DEFAULT_SOURCES,
        "available_defaults": available_defaults,
    }


def add_site(user_id: str, state: str, name: str, url: str, site_id: Optional[str] = None) -> dict:
    sites = _load_user_sites(user_id)
    resolved_id = site_id or f"custom_{int(time.time())}"
    if any(s["id"] == resolved_id for s in sites):
        raise ValueError(f"Site '{resolved_id}' is already in your list.")
    new_site = {
        "id": resolved_id,
        "state": state.strip(),
        "name": name.strip(),
        "url": url.strip(),
        "is_default": resolved_id in _DEFAULT_IDS,
    }
    sites.append(new_site)
    _save_user_sites(user_id, sites)
    return new_site


def delete_site(user_id: str, site_id: str) -> dict:
    sites = _load_user_sites(user_id)
    new_sites = [s for s in sites if s["id"] != site_id]
    if len(new_sites) == len(sites):
        raise ValueError(f"Site '{site_id}' not found in your list.")
    _save_user_sites(user_id, new_sites)
    return {"deleted": site_id}


# ── Cache helpers ──────────────────────────────────────────────────────────

def _cache_path(site_id: str) -> Path:
    return NEWS_CACHE_DIR / f"{site_id}.json"


def _load_cache(site_id: str) -> Optional[dict]:
    p = _cache_path(site_id)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _is_fresh(cache: dict) -> bool:
    last = cache.get("last_polled")
    if not last:
        return False
    try:
        return datetime.now() - datetime.fromisoformat(last) < timedelta(hours=24)
    except Exception:
        return False


# ── RSS detection & parsing ────────────────────────────────────────────────

def _is_rss_url(url: str) -> bool:
    """Return True if the URL looks like an RSS/Atom feed."""
    lower = url.lower()
    return (
        lower.endswith(".xml")
        or lower.endswith(".rss")
        or lower.endswith(".atom")
        or "/rss" in lower
        or "/feed" in lower
        or "/feeds/" in lower
    )


def _parse_rss(xml_text: str) -> list[dict]:
    """Parse RSS/Atom XML and return list of {title, url, content} dicts."""
    articles = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        # Strip byte-order mark or encoding declaration and retry
        cleaned = re.sub(r"^<\?xml[^?]*\?>", "", xml_text.lstrip("\ufeff")).strip()
        root = ET.fromstring(cleaned)

    # Namespace map for Atom and common RSS extensions
    ns = {
        "content": "http://purl.org/rss/1.0/modules/content/",
        "media":   "http://search.yahoo.com/mrss/",
        "atom":    "http://www.w3.org/2005/Atom",
    }

    # RSS 2.0 — items inside <channel>
    items = root.findall(".//item")
    # Atom — entries
    if not items:
        items = root.findall(".//atom:entry", ns) or root.findall(".//{http://www.w3.org/2005/Atom}entry")

    for item in items[:50]:
        def _text(tag, fallback=""):
            el = item.find(tag)
            return (el.text or "").strip() if el is not None else fallback

        title = _text("title") or _text("{http://www.w3.org/2005/Atom}title")
        # Link: try <link>, then <atom:link href>, then <guid>
        link_el = item.find("link")
        if link_el is not None and link_el.text:
            link = link_el.text.strip()
        else:
            atom_link = item.find("{http://www.w3.org/2005/Atom}link")
            link = (atom_link.get("href", "") if atom_link is not None else "") or _text("guid")

        # Content: prefer content:encoded, then description
        content_el = item.find("content:encoded", ns)
        if content_el is None:
            content_el = item.find("{http://purl.org/rss/1.0/modules/content/}encoded")
        raw_content = (content_el.text if content_el is not None else None) or _text("description")

        # Strip HTML tags from content
        if raw_content:
            raw_content = BeautifulSoup(raw_content, "html.parser").get_text(separator=" ", strip=True)

        if title and link:
            articles.append({"title": title, "url": link, "content": raw_content or ""})

    return articles


def _fetch_rss_sync(feed_url: str) -> list[dict]:
    """Fetch and parse an RSS feed using urllib with a crawler UA (bypasses Cloudflare)."""
    import urllib.request
    req = urllib.request.Request(
        feed_url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"},
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        body = resp.read().decode("utf-8", errors="replace")
    return _parse_rss(body)


# ── Scraping ───────────────────────────────────────────────────────────────

def _extract_links_from_html(html: str, listing_url: str) -> list[dict]:
    """Parse article links from HTML string."""
    soup = BeautifulSoup(html, "html.parser")
    parsed = urlparse(listing_url)
    base_netloc = parsed.netloc
    base = f"{parsed.scheme}://{base_netloc}"

    articles = []
    seen = set()

    candidate_selectors = [
        "article a", "h1 a", "h2 a", "h3 a", "h4 a",
        ".headline a", ".article-title a", ".news-title a",
        "[class*='title'] a", "[class*='headline'] a",
        "[class*='story'] a", ".entry-title a",
    ]
    candidates = []
    for sel in candidate_selectors:
        candidates.extend(soup.select(sel))
    if len(candidates) < 5:
        candidates = soup.find_all("a", href=True)

    skip_kw = {"/tag/", "/category/", "/author/", "/page/", "/feed", "/rss", "/amp/"}
    for a in candidates:
        href = a.get("href", "")
        if not href or href.startswith(("#", "javascript", "mailto")):
            continue
        full = urljoin(base, href)
        if urlparse(full).netloc != base_netloc:
            continue
        if full in seen or full == listing_url:
            continue
        if any(kw in full for kw in skip_kw):
            continue
        segments = [s for s in urlparse(full).path.rstrip("/").split("/") if s]
        if len(segments) < 1:
            continue
        title = a.get_text(separator=" ", strip=True)
        if len(title) < 8 or len(title) > 400:
            continue
        seen.add(full)
        articles.append({"title": title, "url": full})
        if len(articles) >= 50:
            break

    return articles


def _fetch_html_with_session(listing_url: str) -> str:
    """Fetch page HTML using a session — visits homepage first to acquire cookies."""
    parsed = urlparse(listing_url)
    homepage = f"{parsed.scheme}://{parsed.netloc}"
    session = requests.Session()
    session.headers.update(_HEADERS)
    # Warm up cookies via homepage visit
    try:
        session.get(homepage, timeout=15, allow_redirects=True)
    except Exception:
        pass
    resp = session.get(
        listing_url,
        timeout=20,
        allow_redirects=True,
        headers={**_HEADERS, "Referer": homepage},
    )
    resp.raise_for_status()
    return resp.text


def _scrape_article_links_sync(listing_url: str) -> list[dict]:
    """
    Fetch article stubs from a URL.
    - RSS/Atom feeds  → parsed directly (reliable, no bot issues).
    - HTML pages      → Strategy 1: trafilatura; Strategy 2: session + cookies.
    Returns list of {title, url, content(optional)}.
    """
    if _is_rss_url(listing_url):
        return _fetch_rss_sync(listing_url)

    last_error = None

    # Strategy 1 — trafilatura (handles many anti-bot measures)
    try:
        raw = trafilatura.fetch_url(listing_url)
        if raw and len(raw) > 500:
            links = _extract_links_from_html(raw, listing_url)
            if links:
                return links
    except Exception as e:
        last_error = e

    # Strategy 2 — requests session with cookie warm-up
    try:
        html = _fetch_html_with_session(listing_url)
        links = _extract_links_from_html(html, listing_url)
        if links:
            return links
    except Exception as e:
        last_error = e

    raise RuntimeError(
        f"Could not fetch articles from {listing_url}. "
        f"The site may be blocking automated access. Last error: {last_error}"
    )


def _fetch_article_content_sync(url: str) -> str:
    try:
        raw = trafilatura.fetch_url(url)
        if raw:
            return trafilatura.extract(raw, include_comments=False, include_tables=False) or ""
    except Exception:
        pass
    return ""


# ── Translation ────────────────────────────────────────────────────────────


_news_filter_agent = None

def _get_news_filter_agent():
    global _news_filter_agent
    if _news_filter_agent is None:
        from agents.news_filter_agent import NewsFilterAgent
        _news_filter_agent = NewsFilterAgent()
    return _news_filter_agent


# ── Main article fetch ─────────────────────────────────────────────────────

async def get_articles(site_id: str, site_url: str, site_name: str) -> dict:
    """
    Return top-10 political articles for a site (LLM-filtered + translated).
    Uses 24-hour cache.
    """
    cache = _load_cache(site_id)
    if cache and _is_fresh(cache):
        return {**cache, "from_cache": True}

    # Step 1: fetch up to 50 article stubs (RSS or HTML scrape)
    raw_links = await asyncio.to_thread(_scrape_article_links_sync, site_url)

    # Step 2: enrich with content (RSS already has it; HTML sites need per-article fetch)
    is_rss = _is_rss_url(site_url)
    raw_articles = []
    for link in raw_links[:50]:
        if is_rss and link.get("content") and len(link["content"]) > 80:
            content = link["content"]
        else:
            fetched = await asyncio.to_thread(_fetch_article_content_sync, link["url"])
            content = fetched if len(fetched) > 80 else link.get("content") or link["title"]
        raw_articles.append({"title": link["title"], "url": link["url"], "content": content})

    # Step 3: NewsFilterAgent filters for political news and translates to English (returns ≤10)
    agent = _get_news_filter_agent()
    articles = await agent.filter_and_translate(site_name, raw_articles)
    print(f"[NewsService] {len(raw_articles)} raw → {len(articles)} political articles after filtering")

    result = {
        "site_id": site_id,
        "site_name": site_name,
        "url": site_url,
        "last_polled": datetime.now().isoformat(),
        "articles": articles,
        "from_cache": False,
    }
    _cache_path(site_id).write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return result
