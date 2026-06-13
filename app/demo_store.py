from __future__ import annotations

from datetime import datetime, timedelta, timezone
from math import sqrt


DIMENSIONS = 384


def _topic_vector(topic: str) -> list[float]:
    """Create a deterministic lightweight vector for local demos."""
    vector = [0.0] * DIMENSIONS
    seed = sum(ord(ch) for ch in topic)
    for offset, weight in enumerate((1.0, 0.65, 0.35)):
        vector[(seed + offset * 37) % DIMENSIONS] = weight
    norm = sqrt(sum(value * value for value in vector))
    return [value / norm for value in vector]


def _average_vectors(vectors: list[list[float]]) -> list[float]:
    if not vectors:
        return [0.0] * DIMENSIONS
    averaged = [sum(values) / len(vectors) for values in zip(*vectors)]
    norm = sqrt(sum(value * value for value in averaged))
    return [value / norm for value in averaged] if norm else averaged


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right:
        return 0.0
    return sum(a * b for a, b in zip(left, right))


def _created(hours_ago: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=hours_ago)).isoformat()


USERS = {
    "demo-tenant": {
        "user_id": "demo-tenant",
        "name": "Tenant issue user",
        "explicit_interests": ["Tenant Rights", "Property Law"],
        "implicit_interests": ["deposit", "landlord", "rent"],
        "interest_vector": _average_vectors([_topic_vector("Tenant Rights"), _topic_vector("Property Law")]),
    },
    "demo-consumer": {
        "user_id": "demo-consumer",
        "name": "Consumer complaint user",
        "explicit_interests": ["Consumer Rights"],
        "implicit_interests": ["refund", "defective product"],
        "interest_vector": _topic_vector("Consumer Rights"),
    },
    "demo-family": {
        "user_id": "demo-family",
        "name": "Family law user",
        "explicit_interests": ["Family Law", "Women Safety"],
        "implicit_interests": ["maintenance", "protection"],
        "interest_vector": _average_vectors([_topic_vector("Family Law"), _topic_vector("Women Safety")]),
    },
}


POSTS = [
    {
        "id": "post-tenant-deposit",
        "content": "My landlord is refusing to return my security deposit after I vacated the flat.",
        "author_id": "adv-tenant-1",
        "author_verified": True,
        "author_role": "advocate",
        "type": "Help Request",
        "category": "Tenant Rights",
        "primary_category": "Tenant Rights",
        "reactions_count": 42,
        "comments_count": 11,
        "status": "published",
        "created_at": _created(2),
    },
    {
        "id": "post-rent-agreement",
        "content": "Before signing a rent agreement, check lock-in period, deposit clause, and notice terms.",
        "author_id": "adv-tenant-2",
        "author_verified": True,
        "author_role": "advocate",
        "type": "Article",
        "category": "Tenant Rights",
        "primary_category": "Tenant Rights",
        "reactions_count": 26,
        "comments_count": 6,
        "status": "published",
        "created_at": _created(8),
    },
    {
        "id": "post-property-registration",
        "content": "Property buyers should verify title deed, encumbrance certificate, and registration records.",
        "author_id": "adv-property-1",
        "author_verified": True,
        "author_role": "advocate",
        "type": "Article",
        "category": "Property Law",
        "primary_category": "Property Law",
        "reactions_count": 30,
        "comments_count": 5,
        "status": "published",
        "created_at": _created(18),
    },
    {
        "id": "post-consumer-refund",
        "content": "An online seller sent me a defective phone and is refusing refund or replacement.",
        "author_id": "user-consumer-1",
        "author_verified": False,
        "author_role": "citizen",
        "type": "Help Request",
        "category": "Consumer Rights",
        "primary_category": "Consumer Rights",
        "reactions_count": 55,
        "comments_count": 17,
        "status": "published",
        "created_at": _created(4),
    },
    {
        "id": "post-consumer-forum",
        "content": "Consumer forum complaints can be filed online when companies ignore refund requests.",
        "author_id": "adv-consumer-1",
        "author_verified": True,
        "author_role": "advocate",
        "type": "Short Update",
        "category": "Consumer Rights",
        "primary_category": "Consumer Rights",
        "reactions_count": 18,
        "comments_count": 3,
        "status": "published",
        "created_at": _created(16),
    },
    {
        "id": "post-maintenance",
        "content": "A spouse can claim maintenance when they cannot support themselves after separation.",
        "author_id": "adv-family-1",
        "author_verified": True,
        "author_role": "advocate",
        "type": "Article",
        "category": "Family Law",
        "primary_category": "Family Law",
        "reactions_count": 37,
        "comments_count": 9,
        "status": "published",
        "created_at": _created(6),
    },
    {
        "id": "post-domestic-violence",
        "content": "Domestic violence victims can seek protection orders, residence orders, and emergency help.",
        "author_id": "adv-women-1",
        "author_verified": True,
        "author_role": "advocate",
        "type": "Legal News",
        "category": "Women Safety",
        "primary_category": "Women Safety",
        "reactions_count": 60,
        "comments_count": 20,
        "status": "published",
        "created_at": _created(1),
    },
    {
        "id": "post-rti-passport",
        "content": "You can file an RTI application to ask why a passport or government request is delayed.",
        "author_id": "adv-rti-1",
        "author_verified": False,
        "author_role": "advocate",
        "type": "Short Update",
        "category": "RTI",
        "primary_category": "RTI",
        "reactions_count": 14,
        "comments_count": 4,
        "status": "published",
        "created_at": _created(10),
    },
    {
        "id": "post-fir",
        "content": "If police refuse to register an FIR, you can approach senior officers or the magistrate.",
        "author_id": "adv-criminal-1",
        "author_verified": True,
        "author_role": "advocate",
        "type": "Short Update",
        "category": "Criminal Law",
        "primary_category": "Criminal Law",
        "reactions_count": 44,
        "comments_count": 13,
        "status": "published",
        "created_at": _created(12),
    },
    {
        "id": "post-salary",
        "content": "Employees can complain if salary is delayed repeatedly or termination threats are used.",
        "author_id": "adv-employment-1",
        "author_verified": False,
        "author_role": "advocate",
        "type": "Help Request",
        "category": "Employment",
        "primary_category": "Employment",
        "reactions_count": 21,
        "comments_count": 7,
        "status": "published",
        "created_at": _created(20),
    },
]


POST_EMBEDDINGS = {
    post["id"]: {
        "post_id": post["id"],
        "embedding": _topic_vector(post["primary_category"]),
        "enriched_tags": post["content"].lower().replace(".", "").split()[:5],
        "legal_topics": [post["primary_category"]],
        "urgency_score": 2,
    }
    for post in POSTS
}

INTERACTIONS: list[dict] = []


def get_demo_users() -> list[dict]:
    return [
        {
            "user_id": user["user_id"],
            "name": user["name"],
            "explicit_interests": user["explicit_interests"],
            "implicit_interests": user["implicit_interests"],
        }
        for user in USERS.values()
    ]


def fetch_posts(limit: int = 1000) -> list[dict]:
    return [post.copy() for post in POSTS[:limit]]


def fetch_post_by_id(post_id: str) -> dict | None:
    for post in POSTS:
        if post["id"] == post_id:
            return post.copy()
    return None


def fetch_user_interests(user_id: str) -> dict | None:
    user = USERS.get(user_id)
    return user.copy() if user else None


def upsert_user_interests(
    user_id: str,
    interest_vector: list[float],
    explicit_interests: list[str] | None = None,
    implicit_interests: list[str] | None = None,
) -> None:
    user = USERS.setdefault(
        user_id,
        {
            "user_id": user_id,
            "name": "Ad-hoc demo user",
            "explicit_interests": [],
            "implicit_interests": [],
            "interest_vector": [0.0] * DIMENSIONS,
        },
    )
    user["interest_vector"] = interest_vector
    if explicit_interests is not None:
        user["explicit_interests"] = explicit_interests
    if implicit_interests is not None:
        user["implicit_interests"] = implicit_interests


def fetch_post_embedding(post_id: str) -> dict | None:
    data = POST_EMBEDDINGS.get(post_id)
    return data.copy() if data else None


def upsert_post_embedding(
    post_id: str,
    embedding: list[float],
    enriched_tags: list[str] | None = None,
    legal_topics: list[str] | None = None,
    urgency_score: int = 1,
) -> None:
    POST_EMBEDDINGS[post_id] = {
        "post_id": post_id,
        "embedding": embedding,
        "enriched_tags": enriched_tags or [],
        "legal_topics": legal_topics or [],
        "urgency_score": urgency_score,
    }


def upsert_post_tags(post_id: str, tags: dict) -> None:
    post = fetch_post_by_id(post_id)
    if not post:
        return
    post["primary_category"] = tags.get("primary_topic") or post.get("primary_category")


def log_interaction(user_id: str, post_id: str, action: str, duration_ms: int = 0) -> None:
    INTERACTIONS.append(
        {
            "user_id": user_id,
            "post_id": post_id,
            "action": action,
            "duration_ms": duration_ms,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    )


def fetch_reported_posts(user_id: str) -> list[str]:
    return [row["post_id"] for row in INTERACTIONS if row["user_id"] == user_id and row["action"] == "report"]


def fetch_seen_posts(user_id: str, within_hours: int = 24) -> list[str]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=within_hours)
    seen = []
    for row in INTERACTIONS:
        created_at = datetime.fromisoformat(row["created_at"])
        if row["user_id"] == user_id and created_at >= cutoff:
            seen.append(row["post_id"])
    return list(set(seen))


def get_candidates(user_id: str, user_vector: list[float] | None, limit: int = 200) -> list[dict]:
    excluded = set(fetch_seen_posts(user_id) + fetch_reported_posts(user_id))
    candidates = [post.copy() for post in POSTS if post["id"] not in excluded and post["status"] == "published"]
    if user_vector:
        candidates.sort(
            key=lambda post: _cosine_similarity(POST_EMBEDDINGS[post["id"]]["embedding"], user_vector),
            reverse=True,
        )
    else:
        candidates.sort(key=lambda post: post["created_at"], reverse=True)
    return candidates[:limit]
