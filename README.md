---
title: LexFeed
emoji: ⚖️
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# LexFeed — Legal Content Recommendation Engine

[![Live API](https://img.shields.io/badge/Live%20API-Hugging%20Face%20Spaces-yellow?style=for-the-badge)](https://vix1109-lexfeed.hf.space)
[![FastAPI](https://img.shields.io/badge/FastAPI-Python-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com)
[![Hugging Face Spaces](https://img.shields.io/badge/Hosted%20on-HF%20Spaces-orange?style=flat-square&logo=huggingface)](https://huggingface.co/spaces/vix1109/lexfeed)

> An ML-powered recommendation engine built for NyayaSetu — India's legal awareness platform. Ranks legal content using a 6-signal scoring model, auto-classifies posts with an LLM, and learns from user behavior over time.

**[→ Live API: vix1109-lexfeed.hf.space](https://vix1109-lexfeed.hf.space)**  
**[→ Interactive docs: vix1109-lexfeed.hf.space/docs](https://vix1109-lexfeed.hf.space/docs)**

---

## What it does

- **Auto-tags posts** using a free LLM (Groq + LLaMA 3.1) — no manual categorization needed
- **Builds a personalized interest profile** for each user from their scroll, read, and retweet behavior
- **Ranks posts** using 6 signals: semantic similarity, recency, engagement, urgency, category match, diversity
- **Serves legal news** from Bar & Bench RSS, cached in Supabase so it survives server restarts
- **Gets smarter over time** — more interactions = better personalization
- **Graceful fallback** — NyayaSetu falls back to newest-first if LexFeed is unavailable

---

## Tech Stack

| Component | Tool | Cost |
|-----------|------|------|
| Embeddings | sentence-transformers (all-MiniLM-L6-v2, local) | Free |
| Vector DB | pgvector on Supabase | Free |
| LLM Classification | Groq free tier (llama-3.1-8b-instant) | Free |
| API Service | FastAPI + Uvicorn | Free |
| Hosting | Hugging Face Spaces (Docker, ~16GB RAM) | Free |
| Database | Supabase PostgreSQL | Free |

**Total infrastructure cost: ₹0**

---

## Project Structure

```
lexfeed/
  app/
    main.py           ← FastAPI server, CORS, router registration
    config.py         ← environment variables
    database.py       ← Supabase client, batch fetch helpers
    core/
      embeddings.py   ← sentence-transformers (lazy-loaded to save RAM)
      enrichment.py   ← Groq LLM auto-classification + shared enrich_and_store_post()
      ranking.py      ← 6-signal scoring function
      candidates.py   ← Stage 1: candidate generation
      diversify.py    ← Stage 3: diversification rules
      filter.py       ← Stage 4: final seen/quality filter
      feedback.py     ← interest vector update on user interaction
    api/
      feed.py         ← GET /feed/{user_id}?tab=foryou|recent|trending|urgent
      interact.py     ← POST /interact
      enrich.py       ← POST /enrich
      news.py         ← GET /news/live
      health.py       ← GET /health
  scripts/
    legal_news.sql    ← SQL to create legal_news table + replace_legal_news() function
    backfill_embeddings.py  ← embed existing posts in bulk
    populate_news.py  ← one-time news seeder
  requirements.txt
  requirements-dev.txt
  Dockerfile
  .env.example
```

---

## 4-Stage Pipeline

```
All posts in DB
      ↓
[Stage 1] Candidate Generation   — filter by seen history, recency window
      ↓
[Stage 2] Ranking                — 6-signal score per post
      ↓
[Stage 3] Diversification        — cap per-category, inject variety
      ↓
[Stage 4] Final Filter           — urgency boost, quality threshold
      ↓
Ranked feed returned to NyayaSetu
```

### 6 Ranking Signals

| Signal | Weight | Description |
|--------|--------|-------------|
| Semantic similarity | High | Cosine distance between post embedding and user interest vector |
| Recency | Medium | Exponential decay — newer posts score higher |
| Engagement | Medium | Likes + comments + retweet count |
| Urgency | High | LLM-assigned urgency score (low/medium/high/critical) |
| Category match | Medium | User's top interest categories get a boost |
| Diversity | Modifier | Penalizes over-representation of one category |

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/feed/{user_id}` | Personalized ranked feed (tab: foryou/recent/trending/urgent) |
| POST | `/interact` | Log user interaction (read, retweet, scroll) |
| POST | `/enrich` | Auto-classify and embed a new post |
| GET | `/news/live` | Live Indian legal news from Bar & Bench RSS |
| GET | `/health` | Service health check |

---

## Integration with NyayaSetu

```javascript
// frontend/src/services/lexfeedService.js
const BASE = process.env.NEXT_PUBLIC_LEXFEED_API_URL; // https://vix1109-lexfeed.hf.space

export const getRankedPostIds = async (userId, tab = 'foryou', limit = 50) => {
  const res = await fetch(`${BASE}/feed/${userId}?tab=${tab}&limit=${limit}`, {
    signal: AbortSignal.timeout(4000),  // 4s graceful timeout
  });
  const data = await res.json();
  return data.posts.map(p => p.id);
};
```

NyayaSetu re-orders its Supabase posts by the IDs returned here. If LexFeed is down or slow, it silently falls back to chronological order.

---

## Run Locally

```bash
git clone https://github.com/VIX-1109/lexfeed
cd lexfeed
pip install -r requirements.txt

# Set up .env (copy from .env.example and fill in values)
cp .env.example .env

# Run the API server
uvicorn app.main:app --reload
```

API at `http://localhost:8000` — interactive docs at `http://localhost:8000/docs`.

### Environment Variables

```env
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=   # required for writing embeddings/interactions
GROQ_API_KEY=
GROQ_MODEL=llama-3.1-8b-instant
```

---

## Deployment (Hugging Face Spaces)

LexFeed runs as a Docker container on Hugging Face Spaces (free, ~16GB RAM). Render's 512MB free tier was too small for sentence-transformers + torch.

The `Dockerfile` installs dependencies and runs uvicorn on port 7860 (HF Spaces default). Secrets are set via the HF Space settings panel, never committed to the repo.

---

## Author

**Vighnesh Vikas Sonawane** — [@VIX-1109](https://github.com/VIX-1109)

Part of the [NyayaSetu](https://github.com/VIX-1109/NyayaSetu) project — legal awareness for India.
