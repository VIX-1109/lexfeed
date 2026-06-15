from supabase import create_client, Client
from app.config import LEXFEED_ENV, SUPABASE_URL, SUPABASE_ANON_KEY
from app import demo_store

_client: Client = None


def use_demo_store() -> bool:
    return (
        LEXFEED_ENV == "demo"
        or not SUPABASE_URL
        or not SUPABASE_ANON_KEY
        or "your_supabase" in SUPABASE_URL
        or "your_supabase" in SUPABASE_ANON_KEY
    )


def get_supabase() -> Client:
    global _client
    if _client is None:
        if use_demo_store():
            raise ValueError("Supabase URL and Anon Key must be configured in .env file.")
        _client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    return _client


def fetch_posts(limit: int = 1000):
    """Fetch all published posts from Supabase."""
    if use_demo_store():
        return demo_store.fetch_posts(limit)
    db = get_supabase()
    res = db.table("posts").select("*").eq("status", "published").order("created_at", desc=True).limit(limit).execute()
    return res.data or []


def fetch_post_by_id(post_id: str):
    if use_demo_store():
        return demo_store.fetch_post_by_id(post_id)
    db = get_supabase()
    res = db.table("posts").select("*").eq("id", post_id).single().execute()
    return res.data


def fetch_user_interactions(user_id: str, limit: int = 200):
    """Fetch recent interactions for a user."""
    if use_demo_store():
        return [row for row in demo_store.INTERACTIONS if row["user_id"] == user_id][-limit:]
    db = get_supabase()
    res = db.table("interaction_logs").select("*").eq("user_id", user_id).order("created_at", desc=True).limit(limit).execute()
    return res.data or []


def fetch_user_interests(user_id: str):
    """Fetch stored interest vector and explicit interests for a user."""
    if use_demo_store():
        return demo_store.fetch_user_interests(user_id)
    db = get_supabase()
    res = db.table("user_interests").select("*").eq("user_id", user_id).maybe_single().execute()
    return res.data


def upsert_user_interests(user_id: str, interest_vector: list, explicit_interests: list = None, implicit_interests: list = None):
    if use_demo_store():
        demo_store.upsert_user_interests(user_id, interest_vector, explicit_interests, implicit_interests)
        return
    db = get_supabase()
    payload = {
        "user_id": user_id,
        "interest_vector": interest_vector,
        "updated_at": "now()",
    }
    if explicit_interests is not None:
        payload["explicit_interests"] = explicit_interests
    if implicit_interests is not None:
        payload["implicit_interests"] = implicit_interests
    db.table("user_interests").upsert(payload).execute()


def fetch_post_embedding(post_id: str):
    if use_demo_store():
        return demo_store.fetch_post_embedding(post_id)
    db = get_supabase()
    res = db.table("post_embeddings").select("*").eq("post_id", post_id).maybe_single().execute()
    return res.data


def fetch_post_embeddings_batch(post_ids: list) -> dict:
    """Fetch embeddings for multiple posts in a single query. Returns {post_id: row}."""
    if not post_ids:
        return {}
    if use_demo_store():
        return {pid: demo_store.fetch_post_embedding(pid) for pid in post_ids if demo_store.fetch_post_embedding(pid)}
    db = get_supabase()
    res = db.table("post_embeddings").select("*").in_("post_id", post_ids).execute()
    return {r["post_id"]: r for r in (res.data or [])}


def upsert_post_embedding(post_id: str, embedding: list, enriched_tags: list = None, legal_topics: list = None, urgency_score: int = 1):
    if use_demo_store():
        demo_store.upsert_post_embedding(post_id, embedding, enriched_tags, legal_topics, urgency_score)
        return
    db = get_supabase()
    db.table("post_embeddings").upsert({
        "post_id": post_id,
        "embedding": embedding,
        "enriched_tags": enriched_tags or [],
        "legal_topics": legal_topics or [],
        "urgency_score": urgency_score,
    }).execute()


def upsert_post_tags(post_id: str, tags: dict):
    if use_demo_store():
        demo_store.upsert_post_tags(post_id, tags)
        return
    db = get_supabase()
    db.table("post_tags").upsert({"post_id": post_id, **tags}).execute()


def log_interaction(user_id: str, post_id: str, action: str, duration_ms: int = 0):
    if use_demo_store():
        demo_store.log_interaction(user_id, post_id, action, duration_ms)
        return
    db = get_supabase()
    db.table("interaction_logs").insert({
        "user_id": user_id,
        "post_id": post_id,
        "action": action,
        "duration_ms": duration_ms,
    }).execute()


def fetch_reported_posts(user_id: str):
    if use_demo_store():
        return demo_store.fetch_reported_posts(user_id)
    db = get_supabase()
    res = db.table("interaction_logs").select("post_id").eq("user_id", user_id).eq("action", "report").execute()
    return [r["post_id"] for r in (res.data or [])]


def fetch_seen_posts(user_id: str, within_hours: int = 24):
    if use_demo_store():
        return demo_store.fetch_seen_posts(user_id, within_hours)
    db = get_supabase()
    from datetime import datetime, timezone, timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=within_hours)).isoformat()
    res = db.table("interaction_logs").select("post_id").eq("user_id", user_id).gte("created_at", cutoff).execute()
    return list(set(r["post_id"] for r in (res.data or [])))


class DatabaseService:
    def __init__(self):
        try:
            self.supabase = get_supabase()
        except Exception:
            self.supabase = None

    async def get_post_embedding(self, post_id: str):
        if not self.supabase:
            return None
        try:
            return fetch_post_embedding(post_id)
        except Exception:
            return None

    async def get_user_interest_vector(self, user_id: str):
        if not self.supabase:
            return None
        try:
            data = fetch_user_interests(user_id)
            return data.get("interest_vector") if data else None
        except Exception:
            return None

    async def update_user_interest_vector(self, user_id: str, interest_vector: list):
        if not self.supabase:
            return None
        try:
            upsert_user_interests(user_id, interest_vector=interest_vector)
        except Exception:
            pass

    async def get_seen_post_ids(self, user_id: str, within_hours: int = 24):
        if not self.supabase:
            return []
        try:
            return fetch_seen_posts(user_id, within_hours)
        except Exception:
            return []

    async def get_reported_post_ids(self, user_id: str):
        if not self.supabase:
            return []
        try:
            return fetch_reported_posts(user_id)
        except Exception:
            return []

    async def get_similar_posts(self, user_vector: list, exclude_ids: list, limit: int = 100):
        if not self.supabase:
            return []
        try:
            res = self.supabase.rpc("match_posts", {
                "query_embedding": user_vector,
                "match_threshold": 0.0,
                "match_count": limit,
                "exclude_ids": exclude_ids
            }).execute()
            return res.data or []
        except Exception:
            return []

    async def get_recent_posts(self, limit: int = 100):
        if not self.supabase:
            return []
        try:
            return fetch_posts(limit)
        except Exception:
            return []

    async def get_social_graph_posts(self, user_id: str, exclude_ids: list, limit: int = 100):
        return []

    async def get_blocked_author_ids(self, user_id: str):
        return []

    async def get_user_explicit_interests(self, user_id: str):
        if not self.supabase:
            return []
        try:
            data = fetch_user_interests(user_id)
            return data.get("explicit_interests") if data else []
        except Exception:
            return []

    async def get_recent_topic_counts(self, user_id: str, within_hours: int = 2):
        return {}

    async def store_feed_score(self, user_id: str, post_id: str, score: float, breakdown: dict):
        pass

    async def get_post_by_id(self, post_id: str):
        if not self.supabase:
            return None
        try:
            return fetch_post_by_id(post_id)
        except Exception:
            return None
