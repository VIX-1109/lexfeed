from app.database import (
    fetch_user_interests,
    upsert_user_interests,
    fetch_post_embedding,
)
from app.core.embeddings import weighted_update

# How much each action shifts the interest vector
INTERACTION_WEIGHTS = {
    "like": 1.0,
    "comment": 1.5,
    "expand": 0.5,
    "share": 2.0,
    "report": -2.0,
    "skip": -0.3,
    "read": 0.2,
}


def update_on_interaction(user_id: str, post_id: str, action: str) -> None:
    """
    Update the user's interest vector based on an interaction.
    This is the feedback loop — the more a user interacts, the smarter the feed gets.
    """
    weight = INTERACTION_WEIGHTS.get(action, 0)
    if weight == 0:
        return

    # Get the post's embedding
    post_emb_data = fetch_post_embedding(post_id)
    if not post_emb_data or not post_emb_data.get("embedding"):
        return

    post_vector = post_emb_data["embedding"]

    # Get current user interests
    user_interests = fetch_user_interests(user_id)
    if not user_interests or not user_interests.get("interest_vector"):
        # Cold start — use post vector as initial interest vector
        upsert_user_interests(user_id, interest_vector=post_vector)
        return

    current_vector = user_interests["interest_vector"]

    # Weighted moving average update
    new_vector = weighted_update(current_vector, post_vector, weight=abs(weight))

    # Update implicit interests list
    implicit = user_interests.get("implicit_interests") or []
    post_tags = post_emb_data.get("legal_topics") or []
    if weight > 0:
        for tag in post_tags:
            if tag not in implicit:
                implicit.append(tag)
    elif weight < 0:
        implicit = [t for t in implicit if t not in post_tags]

    upsert_user_interests(
        user_id=user_id,
        interest_vector=new_vector,
        implicit_interests=implicit[:20],  # Keep top 20
    )


def initialize_user_interests(user_id: str, onboarding_answer: str) -> None:
    """
    Cold start — initialize user interests from onboarding answer.
    Called when a new user answers 'What brought you to NyayaSetu?'
    """
    from app.core.enrichment import detect_cold_start_interests
    from app.database import get_supabase
    from app.core.embeddings import average_vectors, embed_text

    explicit_interests = detect_cold_start_interests(onboarding_answer)

    # Build initial vector by averaging embeddings of category names
    category_vectors = [embed_text(cat) for cat in explicit_interests]
    initial_vector = average_vectors(category_vectors)

    upsert_user_interests(
        user_id=user_id,
        interest_vector=initial_vector,
        explicit_interests=explicit_interests,
        implicit_interests=[],
    )
