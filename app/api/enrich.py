from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.core.enrichment import enrich_post
from app.core.embeddings import embed_text
from app.database import upsert_post_embedding, upsert_post_tags

router = APIRouter()


class EnrichPayload(BaseModel):
    post_id: str
    content: str


@router.post("/enrich")
async def enrich_new_post(payload: EnrichPayload):
    """
    Auto-classify a new post and generate its embedding.
    Called automatically when a post is created in NyayaSetu.
    No manual category selection needed.
    """
    try:
        # Step 1 — LLM auto-classification (Groq, free tier)
        tags = enrich_post(payload.content)

        # Step 2 — Generate semantic embedding (local, free)
        embedding = embed_text(payload.content)

        # Step 3 — Store embedding
        upsert_post_embedding(
            post_id=payload.post_id,
            embedding=embedding,
            enriched_tags=tags.get("enriched_tags", []),
            legal_topics=[tags.get("primary_category")] + tags.get("secondary_categories", []),
            urgency_score={"low": 1, "medium": 2, "high": 3, "critical": 4}.get(tags.get("urgency", "low"), 1),
        )

        # Step 4 — Store enriched tags
        upsert_post_tags(payload.post_id, {
            "primary_topic": tags.get("primary_category"),
            "secondary_topics": tags.get("secondary_categories", []),
            "legal_acts": tags.get("legal_acts", []),
            "urgency": tags.get("urgency", "low"),
            "target_audience": tags.get("target_audience", []),
        })

        return {
            "success": True,
            "post_id": payload.post_id,
            "detected_category": tags.get("primary_category"),
            "tags": tags,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
