from datetime import datetime, timezone
from app.core.embeddings import cosine_similarity


# Interaction weights for feedback loop
INTERACTION_WEIGHTS = {
    "like": 1.0,
    "comment": 1.5,
    "expand": 0.5,     # user clicked "read more"
    "share": 2.0,
    "report": -2.0,
    "skip": -0.3,
    "read": 0.2,       # user spent 5+ seconds on post
}


def score_post(post: dict, user_interests: dict, post_embedding: list) -> tuple:
    """
    Score a post for a specific user using 6 signals.
    Returns (score, breakdown_dict).
    """
    score = 0.0
    breakdown = {}

    # ── Signal 1: Recency ──────────────────────────────────────────
    # Max 100 points, decays linearly over 48 hours
    try:
        created_at = datetime.fromisoformat(post["created_at"].replace("Z", "+00:00"))
        hours_old = (datetime.now(timezone.utc) - created_at).total_seconds() / 3600
        recency = max(0.0, 100.0 - (hours_old * 2.08))
    except Exception:
        recency = 50.0
    score += recency
    breakdown["recency"] = round(recency, 1)

    # ── Signal 2: Engagement ───────────────────────────────────────
    # reactions worth 2 pts each, comments worth 4 pts, capped at 60
    reactions = post.get("reactions_count", 0) or 0
    comments = post.get("comments_count", 0) or 0
    engagement = min(60.0, reactions * 2 + comments * 4)
    score += engagement
    breakdown["engagement"] = round(engagement, 1)

    # ── Signal 3: Author credibility ──────────────────────────────
    is_verified = post.get("author_verified", False)
    is_admin = post.get("author_role") == "admin"
    credibility = 20.0 if is_verified else (10.0 if is_admin else 3.0)
    score += credibility
    breakdown["credibility"] = credibility

    # ── Signal 4: Explicit interest match ─────────────────────────
    explicit_interests = user_interests.get("explicit_interests") or []
    enriched_tags = post.get("enriched_tags") or []
    primary_cat = post.get("primary_category", "")
    interest_match = 30.0 if (
        primary_cat in explicit_interests or
        any(tag in explicit_interests for tag in enriched_tags)
    ) else 0.0
    score += interest_match
    breakdown["interest_match"] = interest_match

    # ── Signal 5: Semantic similarity ─────────────────────────────
    user_vector = user_interests.get("interest_vector")
    if user_vector and post_embedding:
        similarity = cosine_similarity(post_embedding, user_vector)
        semantic_score = similarity * 50.0
    else:
        semantic_score = 0.0
    score += semantic_score
    breakdown["semantic"] = round(semantic_score, 2)

    # ── Signal 6: Novelty penalty ─────────────────────────────────
    # Reduce score if user has seen 3+ posts on same topic in last 2h
    recent_topics = user_interests.get("_recent_topics", [])
    novelty_penalty = 25.0 if recent_topics.count(primary_cat) >= 3 else 0.0
    score -= novelty_penalty
    breakdown["novelty_penalty"] = -novelty_penalty

    return round(score, 2), breakdown


def rank_candidates(candidates: list, user_interests: dict, embeddings_map: dict) -> list:
    """
    Score and rank a list of candidate posts for a user.
    candidates: list of post dicts
    embeddings_map: {post_id: embedding_vector}
    Returns sorted list with scores attached.
    """
    scored = []
    for post in candidates:
        post_id = post.get("id")
        embedding = embeddings_map.get(post_id)
        score, breakdown = score_post(post, user_interests, embedding)
        scored.append({**post, "_score": score, "_breakdown": breakdown})

    return sorted(scored, key=lambda p: p["_score"], reverse=True)
