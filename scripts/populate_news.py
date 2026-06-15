"""One-off: fetch live legal news and write it to the Supabase legal_news table.

Useful to populate / refresh the news without deploying the full service.
Run from anywhere:  python scripts/populate_news.py
"""
import os
import sys
import asyncio

# Load this project's .env and make `app` importable regardless of cwd
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from dotenv import load_dotenv  # noqa: E402
load_dotenv(os.path.join(ROOT, ".env"))

from app.api.news import get_live_news  # noqa: E402


async def main():
    res = await get_live_news(limit=10, refresh=True)
    items = res.get("items", [])
    print(f"[populate_news] source={res.get('source')}  items={len(items)}")
    for it in items[:5]:
        print(f"   - [{it.get('tag')}] {(it.get('title') or '')[:72]}")
    if res.get("source") == "static_fallback":
        print("[populate_news] WARNING: no live source returned data; nothing was stored.")


if __name__ == "__main__":
    asyncio.run(main())
