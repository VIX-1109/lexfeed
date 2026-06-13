import os
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus
import xml.etree.ElementTree as ET
from typing import Optional

import httpx
from fastapi import APIRouter

from app.config import GOOGLE_API_KEY, GOOGLE_CSE_ID

router = APIRouter(prefix="/news", tags=["news"])

# ── CACHE ─────────────────────────────────────────────────────────────────────
_cache: dict = {"items": [], "fetched_at": None, "source": None}
CACHE_TTL_SECONDS = 7200  # 2 hours


def _cache_valid() -> bool:
    if not _cache["fetched_at"] or not _cache["items"]:
        return False
    age = (datetime.now(timezone.utc) - _cache["fetched_at"]).total_seconds()
    return age < CACHE_TTL_SECONDS


def _set_cache(items: list, source: str):
    _cache["items"] = items
    _cache["source"] = source
    _cache["fetched_at"] = datetime.now(timezone.utc)


# ── HELPERS ───────────────────────────────────────────────────────────────────
def _time_ago(published_at: Optional[str]) -> str:
    if not published_at:
        return "Live"
    try:
        dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        diff = datetime.now(timezone.utc) - dt
        seconds = max(0, int(diff.total_seconds()))
        if seconds < 3600:
            return f"{max(1, seconds // 60)}m ago"
        if seconds < 86400:
            return f"{seconds // 3600}h ago"
        return f"{seconds // 86400}d ago"
    except Exception:
        return "Live"


def _tag_from_title(title: str) -> str:
    t = title.lower()
    if "supreme court" in t:
        return "Supreme Court"
    if "high court" in t:
        return "High Court"
    if "consumer" in t:
        return "Consumer Rights"
    if "tenant" in t or "rent" in t or "landlord" in t:
        return "Tenant Rights"
    if "criminal" in t or "bail" in t or "fir" in t or "arrest" in t:
        return "Criminal Law"
    if "family" in t or "divorce" in t or "marriage" in t:
        return "Family Law"
    if "property" in t or "rera" in t:
        return "Property Law"
    if "employment" in t or "salary" in t or "labour" in t:
        return "Employment"
    if "women" in t or "dowry" in t or "harassment" in t:
        return "Women Safety"
    if "rti" in t or "right to information" in t:
        return "RTI"
    return "Legal News"


# ── SOURCES ───────────────────────────────────────────────────────────────────

async def _fetch_gnews(limit: int) -> list[dict]:
    """Fetch from GNews API."""
    key = os.getenv("GNEWS_API_KEY")
    if not key:
        print("[GNews] No API key found")
        return []
    url = (
        "https://gnews.io/api/v4/search"
        f"?q=india+legal+law+supreme+court+rights+consumer"
        f"&lang=en&country=in&max={limit}&token={key}"
        f"&sortby=publishedAt"
    )
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.get(url)
            print(f"[GNews] status: {res.status_code}")
            data = res.json()
            print(f"[GNews] response keys: {list(data.keys())}")

        # GNews free plan wraps articles differently — try both keys
        articles = data.get("articles") or data.get("data") or []
        print(f"[GNews] got {len(articles)} articles")

        # If still empty, log the full response for debugging
        if not articles:
            print(f"[GNews] full response: {str(data)[:300]}")
            return []

        items = []
        for a in articles[:limit]:
            published_at = a.get("publishedAt") or a.get("published_at")
            items.append({
                "tag": _tag_from_title(a.get("title", "")),
                "title": a.get("title", "Legal news update"),
                "summary": a.get("description", "") or a.get("content", "")[:200],
                "source": a.get("source", {}).get("name", "GNews") if isinstance(a.get("source"), dict) else str(a.get("source", "GNews")),
                "url": a.get("url"),
                "image": a.get("image"),
                "time": _time_ago(published_at),
            })
        print(f"[GNews] returning {len(items)} items")
        return items
    except Exception as e:
        print(f"[GNews] fetch failed: {e}")
        return []


async def _fetch_barandbench_rss(limit: int) -> list[dict]:
    """Fetch from Bar & Bench RSS."""
    url = "https://www.barandbench.com/feed"
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (compatible; LexFeed/1.0)"}) as client:
            res = await client.get(url)
            print(f"[Bar & Bench RSS] status: {res.status_code}")
            res.raise_for_status()

        # Try parsing — handle both RSS and Atom formats
        root = ET.fromstring(res.text)
        ns = root.tag.split('}')[0].strip('{') if '}' in root.tag else ''

        items = []
        # Try RSS format
        entries = root.findall("./channel/item")
        # Try Atom format if RSS empty
        if not entries:
            entries = root.findall(f".//{{{ns}}}entry") if ns else root.findall(".//entry")

        print(f"[Bar & Bench RSS] found {len(entries)} entries")

        for item in entries[:limit]:
            title = item.findtext("title") or item.findtext(f"{{{ns}}}title") or "Legal news update"
            link  = item.findtext("link") or item.findtext(f"{{{ns}}}link") or ""
            pub   = item.findtext("pubDate") or item.findtext("published") or item.findtext(f"{{{ns}}}published") or ""
            published_at = None
            if pub:
                try:
                    published_at = parsedate_to_datetime(pub).astimezone(timezone.utc).isoformat()
                except Exception:
                    try:
                        published_at = datetime.fromisoformat(pub.replace("Z", "+00:00")).isoformat()
                    except Exception:
                        published_at = None
            items.append({
                "tag":     _tag_from_title(title),
                "title":   title.strip(),
                "summary": item.findtext("description") or "",
                "source":  "Bar & Bench",
                "url":     link,
                "image":   None,
                "time":    _time_ago(published_at),
            })
        print(f"[Bar & Bench RSS] returning {len(items)} items")
        return items
    except Exception as e:
        print(f"[Bar & Bench RSS] fetch failed: {e}")
        return []


async def _fetch_google_news_rss(limit: int) -> list[dict]:
    """Fetch from Google News RSS — reliable fallback."""
    query = quote_plus("India legal news Supreme Court High Court consumer rights tenant")
    url = f"https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            res = await client.get(url)
            print(f"[Google News RSS] status: {res.status_code}")
            res.raise_for_status()
        root = ET.fromstring(res.text)
        items = []
        for item in root.findall("./channel/item")[:limit * 2]:
            title = item.findtext("title") or "Legal news update"
            link  = item.findtext("link")
            pub_date = item.findtext("pubDate")
            published_at = None
            if pub_date:
                try:
                    published_at = parsedate_to_datetime(pub_date).astimezone(timezone.utc).isoformat()
                except Exception:
                    published_at = None
            items.append({
                "tag":     _tag_from_title(title),
                "title":   title,
                "summary": "",
                "source":  "Google News",
                "url":     link,
                "image":   None,
                "time":    _time_ago(published_at),
            })
            if len(items) >= limit:
                break
        print(f"[Google News RSS] returning {len(items)} items")
        return items
    except Exception as e:
        print(f"[Google News RSS] fetch failed: {e}")
        return []


async def _fetch_google_custom_search(limit: int) -> list[dict]:
    if not GOOGLE_API_KEY or not GOOGLE_CSE_ID:
        return []
    params = {
        "key": GOOGLE_API_KEY, "cx": GOOGLE_CSE_ID,
        "q": "India legal news Supreme Court High Court consumer rights",
        "num": min(limit, 10), "dateRestrict": "d7", "sort": "date",
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.get("https://www.googleapis.com/customsearch/v1", params=params)
            res.raise_for_status()
            data = res.json()
        items = []
        for item in data.get("items", [])[:limit]:
            title = item.get("title", "Legal news update")
            items.append({
                "tag": _tag_from_title(title), "title": title,
                "summary": item.get("snippet", ""),
                "source": item.get("displayLink", "Google"),
                "url": item.get("link"), "image": None, "time": "Live",
            })
        return items
    except Exception as e:
        print(f"[Google CSE] fetch failed: {e}")
        return []


# ── ENDPOINT ──────────────────────────────────────────────────────────────────

@router.get("/live")
async def get_live_news(limit: int = 6, refresh: bool = False):
    limit = max(1, min(limit, 10))

    if _cache_valid() and not refresh:
        return {
            "source": _cache["source"], "cached": True,
            "fetched_at": _cache["fetched_at"].isoformat(),
            "gnews_configured": bool(os.getenv("GNEWS_API_KEY")),
            "items": _cache["items"][:limit],
        }

    source = "static_fallback"
    items = []

    # 1. GNews API
    items = await _fetch_gnews(limit)
    if items:
        source = "gnews_api"

    # 2. Bar & Bench RSS
    if not items:
        items = await _fetch_barandbench_rss(limit)
        if items:
            source = "barandbench_rss"

    # 3. Google Custom Search
    if not items:
        items = await _fetch_google_custom_search(limit)
        if items:
            source = "google_custom_search"

    # 4. Google News RSS
    if not items:
        items = await _fetch_google_news_rss(limit)
        if items:
            source = "google_news_rss"

    # Static fallback
    if not items:
        items = [{
            "tag": "Legal News",
            "title": "Live legal news is temporarily unavailable.",
            "summary": "Please check back shortly.",
            "source": "LexFeed", "url": None, "image": None, "time": "Retry later",
        }]
        source = "static_fallback"

    _set_cache(items, source)

    return {
        "source": source, "cached": False,
        "fetched_at": _cache["fetched_at"].isoformat(),
        "gnews_configured": bool(os.getenv("GNEWS_API_KEY")),
        "items": items,
    }


@router.get("/cache/clear")
async def clear_news_cache():
    _cache["items"] = []
    _cache["fetched_at"] = None
    _cache["source"] = None
    return {"message": "News cache cleared. Next request will fetch fresh news."}
