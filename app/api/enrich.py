from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.core.enrichment import enrich_and_store_post

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
        tags = enrich_and_store_post(payload.post_id, payload.content)
        return {
            "success": True,
            "post_id": payload.post_id,
            "detected_category": tags.get("primary_category"),
            "tags": tags,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
