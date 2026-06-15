import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from app.api.feed import router as feed_router
from app.api.interact import router as interact_router
from app.api.enrich import router as enrich_router
from app.api.health import router as health_router
from app.api.demo import router as demo_router
from app.api.news import router as news_router

app = FastAPI(
    title="LexFeed",
    description="Legal Content Recommendation Engine for NyayaSetu",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "null",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        # Vercel deployments (lexfeed frontend)
        "https://lexfeed.vercel.app",
        "https://lexfeed-*.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(feed_router)
app.include_router(interact_router)
app.include_router(enrich_router)
app.include_router(health_router)
app.include_router(demo_router)
app.include_router(news_router)


@app.get("/")
async def root():
    frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "index.html")
    if os.path.exists(frontend_path):
        return FileResponse(frontend_path)
    return {
        "service": "LexFeed",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": ["/feed/{user_id}", "/interact", "/enrich", "/health", "/demo/users", "/news/live"],
    }

