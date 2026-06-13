"""
Generate embeddings for all existing posts in the database.
Run this once after setup to populate the post_embeddings table.

Usage:
    python scripts/generate_embeddings.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import get_supabase, upsert_post_embedding, upsert_post_tags
from app.core.embeddings import embed_text
from app.core.enrichment import enrich_post


def generate_all_embeddings(batch_size: int = 50):
    db = get_supabase()

    print("Fetching all published posts...")
    res = db.table("posts").select("id, content").eq("status", "published").execute()
    posts = res.data or []
    print(f"Found {len(posts)} posts to process.")

    for i, post in enumerate(posts):
        post_id = post["id"]
        content = post.get("content", "")

        if not content.strip():
            print(f"  [{i+1}/{len(posts)}] Skipping empty post {post_id}")
            continue

        # Check if embedding already exists
        existing = db.table("post_embeddings").select("post_id").eq("post_id", post_id).maybe_single().execute()
        if existing.data:
            print(f"  [{i+1}/{len(posts)}] Already embedded: {post_id}")
            continue

        try:
            # Generate embedding
            embedding = embed_text(content)

            # LLM enrichment
            tags = enrich_post(content)

            # Store embedding
            upsert_post_embedding(
                post_id=post_id,
                embedding=embedding,
                enriched_tags=tags.get("enriched_tags", []),
                legal_topics=[tags.get("primary_category")] + tags.get("secondary_categories", []),
                urgency_score={"low": 1, "medium": 2, "high": 3, "critical": 4}.get(tags.get("urgency", "low"), 1),
            )

            # Store tags
            upsert_post_tags(post_id, {
                "primary_topic": tags.get("primary_category"),
                "secondary_topics": tags.get("secondary_categories", []),
                "legal_acts": tags.get("legal_acts", []),
                "urgency": tags.get("urgency", "low"),
                "target_audience": tags.get("target_audience", []),
            })

            print(f"  [{i+1}/{len(posts)}] ✓ {post_id} → {tags.get('primary_category')}")

        except Exception as e:
            print(f"  [{i+1}/{len(posts)}] ✗ Error processing {post_id}: {e}")

    print("\nDone! All posts embedded.")


if __name__ == "__main__":
    generate_all_embeddings()
