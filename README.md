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

A standalone ML-powered content recommendation engine for legal platforms.
Built to integrate with NyayaSetu's Justice Feed.

## What it does

- Auto-detects post categories using a free LLM (no manual tagging)
- Builds a personalized interest profile for each user from their behavior
- Ranks posts using a 6-signal scoring model
- Diversifies the feed so it doesn't feel repetitive
- Gets smarter the more you use it

## Tech Stack

| Component | Tool | Cost |
|-----------|------|------|
| Embeddings | sentence-transformers (local) | Free |
| Vector DB | pgvector on Supabase | Free |
| LLM Classification | Groq free tier | Free |
| API Service | FastAPI | Free |
| Hosting | Railway free tier | Free |
| Scheduler | n8n (Docker) | Free |
| Database | Supabase PostgreSQL | Free |

**Total cost: ₹0**

## Project Structure

```
lexfeed/
  app/
    main.py           ← FastAPI server entry point
    config.py         ← environment variables
    database.py       ← Supabase connection
    core/
      embeddings.py   ← sentence-transformers logic
      enrichment.py   ← Groq LLM auto-classification
      ranking.py      ← 6-signal scoring function
      candidates.py   ← candidate generation (Stage 1)
      diversify.py    ← diversification rules (Stage 3)
      filter.py       ← final filter (Stage 4)
      feedback.py     ← interest vector update on interaction
    api/
      feed.py         ← GET /feed/{user_id}
      interact.py     ← POST /interact
      enrich.py       ← POST /enrich
      health.py       ← GET /health
  scripts/
    setup_db.sql      ← SQL to create all required tables
    generate_embeddings.py  ← one-time script for existing posts
    seed_demo.py      ← seed demo data for testing
  notebooks/
    demo.ipynb        ← interactive demo notebook
  tests/
    test_ranking.py
    test_enrichment.py
  requirements.txt
  .env.example
  README.md
```

## Setup

### 1. Clone and install

```bash
git clone https://github.com/VIX-1109/lexfeed
cd lexfeed
pip install -r requirements.txt
```

### 2. Set up environment variables

```bash
cp .env.example .env
# Fill in your Supabase URL, anon key, and Groq API key
```

### 3. Set up database

```bash
# Run in your Supabase SQL Editor
# Copy contents of scripts/setup_db.sql and run
```

### 4. Generate embeddings for existing posts

```bash
python scripts/generate_embeddings.py
```

### 5. Run the API server

```bash
uvicorn app.main:app --reload
```

API will be available at `http://localhost:8000`
Interactive docs at `http://localhost:8000/docs`

## Local demo mode

If `.env` is not configured, LexFeed automatically uses built-in demo data.
This lets you test the recommendation engine before connecting Supabase.

```bash
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Try these URLs:

| URL | What it shows |
|-----|---------------|
| `http://localhost:8000/health` | Confirms demo mode is active |
| `http://localhost:8000/demo/users` | Lists fake users you can test with |
| `http://localhost:8000/demo/posts` | Lists fake legal posts |
| `http://localhost:8000/feed/demo-tenant` | Personalized feed for a tenant-rights user |
| `http://localhost:8000/feed/demo-consumer` | Personalized feed for a consumer-rights user |
| `http://localhost:8000/feed/demo-family` | Personalized feed for a family-law user |
| `http://localhost:8000/feed/demo-tenant?tab=recent` | Chronological feed |

### 6. Run the demo notebook

```bash
jupyter notebook notebooks/demo.ipynb
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/feed/{user_id}` | Get personalized feed |
| POST | `/interact` | Log user interaction |
| POST | `/enrich` | Auto-classify a new post |
| GET | `/health` | Service health check |

## Integration with NyayaSetu

```javascript
// In NyayaSetu's useJusticeFeed.js
const fetchPersonalizedFeed = async (userId) => {
  const res = await fetch(`${LEXFEED_URL}/feed/${userId}`);
  const data = await res.json();
  return data.posts;
};
```

## Author

Vighnesh Vikas Sonawane — github.com/VIX-1109
