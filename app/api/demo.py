from fastapi import APIRouter

from app import demo_store
from app.database import use_demo_store

router = APIRouter(prefix="/demo", tags=["demo"])


@router.get("/users")
async def get_demo_users():
    return {
        "demo_mode": use_demo_store(),
        "users": demo_store.get_demo_users(),
        "try_feeds": [f"/feed/{user['user_id']}" for user in demo_store.get_demo_users()],
    }


@router.get("/posts")
async def get_demo_posts():
    return {
        "demo_mode": use_demo_store(),
        "posts": demo_store.fetch_posts(),
    }
