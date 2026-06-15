from fastapi import APIRouter, HTTPException
from app.database import (
    fetch_posts,
    fetch_user_interests,
    fetch_post_embeddings_batch,
)
from app.core.candidates import get_candidates
from app.core.ranking import rank_candidates
from app.core.diversify import diversify
from app.core.filter import final_filter

router = APIRouter()


def _engagement(post: dict) -> float:
    return (post.get("reactions_count") or 0) * 2 + (post.get("comments_count") or 0) * 4


@router.get("/feed/{user_id}")
async def get_feed(user_id: str, limit: int = 20, tab: str = "foryou"):
    """
    Get feed for a user.
    tab: foryou (personalized) | recent (chronological) | trending (most engagement) | urgent (help requests / high urgency)
    """
    try:
        if tab == "recent":
            return {"posts": fetch_posts(limit), "tab": "recent", "personalized": False}

        if tab == "trending":
            posts = fetch_posts(500)
            posts.sort(key=_engagement, reverse=True)
            return {"posts": posts[:limit], "tab": "trending", "personalized": False}

        if tab == "urgent":
            posts = fetch_posts(500)
            post_ids = [p["id"] for p in posts]
            emb_map = fetch_post_embeddings_batch(post_ids)
            urgent = []
            for p in posts:
                emb = emb_map.get(p["id"]) or {}
                urgency = emb.get("urgency_score", 1) or 1
                if urgency >= 3:
                    p["urgency_score"] = urgency
                    urgent.append(p)
            if not urgent:
                # Fallback: return Help Requests sorted by recency
                urgent = [p for p in posts if (p.get("type") or "").lower() in ("help request", "help_request")]
            return {"posts": urgent[:limit], "tab": "urgent", "personalized": False}

        # foryou — full 4-stage pipeline
        user_interests = fetch_user_interests(user_id) or {}
        user_vector = user_interests.get("interest_vector")

        candidates = get_candidates(user_id, user_vector, limit=200)

        if not candidates:
            return {"posts": [], "tab": "foryou", "personalized": False}

        # Batch-fetch all embeddings in one query (fixes N+1)
        post_ids = [p.get("id") for p in candidates]
        emb_map = fetch_post_embeddings_batch(post_ids)

        embeddings_map = {}
        for post in candidates:
            post_id = post.get("id")
            emb_data = emb_map.get(post_id)
            if emb_data and emb_data.get("embedding"):
                embeddings_map[post_id] = emb_data["embedding"]
            if emb_data:
                post["enriched_tags"] = emb_data.get("enriched_tags") or []
                post["primary_category"] = (emb_data.get("legal_topics") or [None])[0]

        ranked = rank_candidates(candidates, user_interests, embeddings_map)
        diversified = diversify(ranked, max_size=limit * 2)
        filtered = final_filter(diversified, user_id)

        return {
            "posts": filtered[:limit],
            "tab": "foryou",
            "personalized": bool(user_vector),
            "total_candidates": len(candidates),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
