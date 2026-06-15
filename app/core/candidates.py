from app import demo_store
from app.database import get_supabase, use_demo_store


def get_candidates(user_id: str, user_vector: list, limit: int = 200) -> list:
    """
    Stage 1 — Generate ~200 candidate posts from two pools.
    Pool A: Semantic similarity to user interest vector (pgvector)
    Pool B: Posts liked by people the user has interacted with (social graph)
    """
    if use_demo_store():
        return demo_store.get_candidates(user_id, user_vector, limit)

    db = get_supabase()
    seen_post_ids = _get_seen_post_ids(user_id)
    reported_post_ids = _get_reported_post_ids(user_id)
    excluded_ids = list(set(seen_post_ids + reported_post_ids))

    pool_a = _get_semantic_candidates(db, user_vector, excluded_ids, limit=100)
    pool_b = _get_social_graph_candidates(db, user_id, excluded_ids, limit=100)

    # Merge and deduplicate
    combined = {p["id"]: p for p in pool_a + pool_b}
    return list(combined.values())[:limit]


def _get_semantic_candidates(db, user_vector: list, excluded_ids: list, limit: int = 100) -> list:
    """Find posts whose embeddings are closest to the user's interest vector."""
    if not user_vector:
        # Cold start — return recent posts
        res = db.table("posts").select("*").eq("status", "published").order("created_at", desc=True).limit(limit).execute()
        return res.data or []

    try:
        # pgvector cosine similarity search
        vector_str = f"[{','.join(str(v) for v in user_vector)}]"
        res = db.rpc("match_posts_by_embedding", {
            "query_embedding": vector_str,
            "match_count": limit,
            "excluded_ids": excluded_ids or [],
        }).execute()
        return res.data or []
    except Exception as e:
        print(f"pgvector search failed, falling back to recent posts: {e}")
        res = db.table("posts").select("*").eq("status", "published").order("created_at", desc=True).limit(limit).execute()
        return res.data or []


def _get_social_graph_candidates(db, user_id: str, excluded_ids: list, limit: int = 100) -> list:
    """Find posts liked by advocates the user has messaged."""
    try:
        # Get users this person has messaged
        sent = db.table("messages").select("receiver_id").eq("sender_id", user_id).execute()
        received = db.table("messages").select("sender_id").eq("receiver_id", user_id).execute()

        peer_ids = list(set(
            [r["receiver_id"] for r in (sent.data or [])] +
            [r["sender_id"] for r in (received.data or [])]
        ))

        if not peer_ids:
            return []

        # Get posts those peers liked
        liked = db.table("interaction_logs").select("post_id").in_("user_id", peer_ids).eq("action", "like").execute()
        post_ids = list(set(r["post_id"] for r in (liked.data or []) if r["post_id"] not in excluded_ids))

        if not post_ids:
            return []

        res = db.table("posts").select("*").in_("id", post_ids[:limit]).execute()
        return res.data or []
    except Exception as e:
        print(f"Social graph candidates error: {e}")
        return []


def _get_seen_post_ids(user_id: str) -> list:
    """Get post IDs the user saw recently — only if the seen-filter is enabled."""
    from app.config import SEEN_FILTER_HOURS
    if SEEN_FILTER_HOURS <= 0:
        return []
    from app.database import fetch_seen_posts
    return fetch_seen_posts(user_id, within_hours=SEEN_FILTER_HOURS)


def _get_reported_post_ids(user_id: str) -> list:
    """Get post IDs the user has reported."""
    from app.database import fetch_reported_posts
    return fetch_reported_posts(user_id)
