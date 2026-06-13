from fastapi import APIRouter, HTTPException
from app.database import (
    fetch_posts,
    fetch_user_interests,
    fetch_post_embedding,
)
from app.core.candidates import get_candidates
from app.core.ranking import rank_candidates
from app.core.diversify import diversify
from app.core.filter import final_filter

router = APIRouter()


@router.get("/feed/{user_id}")
async def get_feed(user_id: str, limit: int = 20, tab: str = "foryou"):
    """
    Get personalized feed for a user.
    tab: foryou (personalized) | recent (chronological)
    """
    try:
        # Tab: recent — just return latest posts, no personalization
        if tab == "recent":
            return {"posts": fetch_posts(limit), "tab": "recent", "personalized": False}

        # Tab: foryou — full 4-stage pipeline
        user_interests = fetch_user_interests(user_id) or {}
        user_vector = user_interests.get("interest_vector")

        # Stage 1 — Candidate generation
        candidates = get_candidates(user_id, user_vector, limit=200)

        if not candidates:
            return {"posts": [], "tab": "foryou", "personalized": False}

        # Build embeddings map for ranking
        embeddings_map = {}
        for post in candidates:
            post_id = post.get("id")
            emb_data = fetch_post_embedding(post_id)
            if emb_data and emb_data.get("embedding"):
                embeddings_map[post_id] = emb_data["embedding"]
            # Also attach enriched tags to post
            if emb_data:
                post["enriched_tags"] = emb_data.get("enriched_tags") or []
                post["primary_category"] = (emb_data.get("legal_topics") or [None])[0]

        # Stage 2 — Ranking
        ranked = rank_candidates(candidates, user_interests, embeddings_map)

        # Stage 3 — Diversification
        diversified = diversify(ranked, max_size=limit * 2)

        # Stage 4 — Final filter
        filtered = final_filter(diversified, user_id)

        return {
            "posts": filtered[:limit],
            "tab": "foryou",
            "personalized": bool(user_vector),
            "total_candidates": len(candidates),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
