from fastapi import APIRouter
from app.database import get_supabase, use_demo_store

router = APIRouter()


@router.get("/health")
async def health_check():
    """Service health check."""
    if use_demo_store():
        db_status = "demo store"
    else:
        try:
            db = get_supabase()
            db.table("posts").select("id").limit(1).execute()
            db_status = "connected"
        except Exception as e:
            db_status = f"error: {str(e)}"

    return {
        "status": "ok",
        "service": "LexFeed",
        "version": "1.0.0",
        "database": db_status,
        "demo_mode": use_demo_store(),
    }
