import json
from groq import Groq
from app.config import GROQ_API_KEY, GROQ_MODEL, LEGAL_CATEGORIES, POST_TYPES, URGENCY_LEVELS

client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

URGENCY_SCORES = {"low": 1, "medium": 2, "high": 3, "critical": 4}


def enrich_post(content: str) -> dict:
    """
    Auto-classify a post using Groq LLM (free tier).
    Returns structured tags without any manual input from the user.
    """
    categories_str = ", ".join(LEGAL_CATEGORIES)
    types_str = ", ".join(POST_TYPES)
    urgency_str = ", ".join(URGENCY_LEVELS)

    prompt = f"""You are a legal content classifier for an Indian legal platform.
Analyze the following post and return ONLY a JSON object. No explanation, no preamble, no markdown.

Post: "{content}"

Return this exact JSON structure:
{{
    "primary_category": "one of: {categories_str}",
    "secondary_categories": ["up to 2 more relevant categories"],
    "post_type": "one of: {types_str}",
    "urgency": "one of: {urgency_str}",
    "target_audience": ["e.g. tenant, employee, consumer, citizen, woman, farmer"],
    "legal_acts": ["Indian laws or acts referenced, empty array if none"],
    "enriched_tags": ["5 specific keyword tags from the post content"],
    "summary": "one sentence summary under 20 words"
}}"""

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,  # current free, fast Groq model (configurable)
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=400,
        )
        raw = response.choices[0].message.content.strip()

        # Clean up any accidental markdown
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        return json.loads(raw)

    except Exception as e:
        print(f"Enrichment error: {e}")
        # Fallback — return generic tags so the post still gets stored
        return {
            "primary_category": "General Legal",
            "secondary_categories": [],
            "post_type": "Short Update",
            "urgency": "low",
            "target_audience": ["citizen"],
            "legal_acts": [],
            "enriched_tags": [],
            "summary": content[:80],
        }


def detect_cold_start_interests(answer: str) -> list:
    """
    Map a user's onboarding answer to initial interest categories.
    Used for new users with no interaction history.
    """
    mapping = {
        "legal_help": ["Property Law", "Family Law", "Consumer Rights", "Tenant Rights"],
        "know_rights": ["Consumer Rights", "Women Safety", "RTI", "Employment"],
        "professional": ["Corporate Law", "Tax Law", "Civil Litigation", "Criminal Law"],
        "exploring": ["General Legal", "Consumer Rights", "Property Law"],
    }
    return mapping.get(answer, ["General Legal"])


def enrich_and_store_post(post_id: str, content: str) -> dict:
    """
    Single source of truth for "enrich one post": classify with the LLM,
    embed, and persist both. Used by the /enrich endpoint AND the offline
    backfill script — keeping this logic in one place instead of duplicated.
    """
    from app.core.embeddings import embed_text
    from app.database import upsert_post_embedding, upsert_post_tags

    tags = enrich_post(content)
    embedding = embed_text(content)

    upsert_post_embedding(
        post_id=post_id,
        embedding=embedding,
        enriched_tags=tags.get("enriched_tags", []),
        legal_topics=[tags.get("primary_category")] + tags.get("secondary_categories", []),
        urgency_score=URGENCY_SCORES.get(tags.get("urgency", "low"), 1),
    )
    upsert_post_tags(post_id, {
        "primary_topic": tags.get("primary_category"),
        "secondary_topics": tags.get("secondary_categories", []),
        "legal_acts": tags.get("legal_acts", []),
        "urgency": tags.get("urgency", "low"),
        "target_audience": tags.get("target_audience", []),
    })
    return tags
