from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.database import log_interaction
from app.core.feedback import update_on_interaction

router = APIRouter()


class InteractionPayload(BaseModel):
    user_id: str
    post_id: str
    action: str  # like, comment, expand, share, report, skip, read
    duration_ms: int = 0


@router.post("/interact")
async def log_user_interaction(payload: InteractionPayload):
    """
    Log a user interaction and update their interest vector.
    Called from the frontend on every meaningful interaction.
    """
    valid_actions = {"like", "comment", "expand", "share", "report", "skip", "read"}
    if payload.action not in valid_actions:
        raise HTTPException(status_code=400, detail=f"Invalid action. Must be one of: {valid_actions}")

    try:
        # Log to interaction_logs table
        log_interaction(
            user_id=payload.user_id,
            post_id=payload.post_id,
            action=payload.action,
            duration_ms=payload.duration_ms,
        )

        # Update user interest vector (feedback loop)
        update_on_interaction(
            user_id=payload.user_id,
            post_id=payload.post_id,
            action=payload.action,
        )

        return {"success": True, "action": payload.action}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
