"""One-off: enrich + embed any published posts that don't have an embedding yet.

Same logic as the /enrich endpoint, applied in bulk. Safe to re-run — it only
touches posts missing from post_embeddings.

    python scripts/backfill_embeddings.py
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from dotenv import load_dotenv  # noqa: E402
load_dotenv(os.path.join(ROOT, ".env"))

from app.database import get_supabase  # noqa: E402
from app.core.enrichment import enrich_and_store_post  # noqa: E402


def main():
    db = get_supabase()
    posts = db.table("posts").select("id, content").eq("status", "published").execute().data or []
    have = {r["post_id"] for r in (db.table("post_embeddings").select("post_id").execute().data or [])}
    todo = [p for p in posts if p["id"] not in have and (p.get("content") or "").strip()]

    print(f"[backfill] {len(todo)} post(s) to enrich")
    for i, p in enumerate(todo, 1):
        try:
            tags = enrich_and_store_post(p["id"], p["content"])
            print(f"  [{i}/{len(todo)}] ok  {tags.get('primary_category')}  {p['id']}")
        except Exception as e:
            print(f"  [{i}/{len(todo)}] FAILED {p['id']}: {e}")

    print("[backfill] done")


if __name__ == "__main__":
    main()
