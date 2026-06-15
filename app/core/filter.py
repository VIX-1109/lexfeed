from app.config import SEEN_FILTER_HOURS
from app.database import fetch_reported_posts, fetch_seen_posts


def final_filter(posts: list, user_id: str) -> list:
    """
    Stage 4 — Remove posts the user shouldn't see.
    - Posts the user reported
    - Posts already seen recently (only if SEEN_FILTER_HOURS > 0)
    - Posts with no content
    """
    blocked_post_ids = set(fetch_reported_posts(user_id))
    seen_recent = (
        set(fetch_seen_posts(user_id, within_hours=SEEN_FILTER_HOURS))
        if SEEN_FILTER_HOURS > 0 else set()
    )

    return [
        p for p in posts
        if p.get("id") not in blocked_post_ids
        and p.get("id") not in seen_recent
        and p.get("content")
        and len(p.get("content", "").strip()) > 0
    ]
