"""
seed_with_ai.py
────────────────────────────────────────────────────────────────────────────────
Generates realistic Indian legal posts using Groq AI and seeds them into
NyayaSetu's Supabase posts table. Also enriches each post via LexFeed's
/enrich endpoint to generate ML embeddings.

Usage:
    python scripts/seed_with_ai.py

Requirements:
    - .env with SUPABASE_URL, SUPABASE_ANON_KEY, GROQ_API_KEY, SEED_AUTHOR_ID
    - LexFeed backend running on localhost:8000
"""

import os
import sys
import time
import uuid
import json
import requests
from datetime import datetime, timezone, timedelta
from collections import Counter
from dotenv import load_dotenv
import random

load_dotenv()

SUPABASE_URL      = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
GROQ_API_KEY      = os.getenv("GROQ_API_KEY")
LEXFEED_API       = os.getenv("LEXFEED_API", "http://localhost:8000")
SEED_AUTHOR_ID    = os.getenv("SEED_AUTHOR_ID")

GROQ_URL   = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

# 10 batches of 10 posts = 100 total posts across all categories
BATCHES = [
    ("Tenant Rights",    "Help Request",  10),
    ("Criminal Law",     "Help Request",  10),
    ("Consumer Rights",  "Help Request",  10),
    ("Property Law",     "Help Request",  8),
    ("Family Law",       "Help Request",  8),
    ("Employment",       "Help Request",  8),
    ("Women Safety",     "Help Request",  8),
    ("RTI",              "Short Update",  8),
    ("General Legal",    "Legal News",    10),
    ("Civil Litigation", "Article",       10),
]

def generate_posts_with_groq(category: str, post_type: str, count: int) -> list:
    """Use Groq to generate realistic Indian legal posts for a category."""

    type_instructions = {
        "Help Request": "Write as a real Indian person asking for help with a legal problem they are facing right now. Use first person. Be specific about location (Indian cities), amounts in rupees, and realistic Indian names/situations. Sound worried and genuine.",
        "Short Update": "Write as a citizen sharing a legal awareness tip or update about their rights. Short and informative. Mention specific Indian laws by name (IPC sections, Consumer Protection Act, RTI Act etc).",
        "Legal News":   "Write as a brief news update about a recent court ruling or legal development in India. Mention High Court or Supreme Court. Be factual and concise.",
        "Article":      "Write as an informative article explaining legal rights or procedures for Indians. Include specific law names, sections, and practical steps.",
    }

    prompt = f"""Generate exactly {count} realistic Indian legal social media posts about "{category}".

Post type: {post_type}
Instructions: {type_instructions.get(post_type, '')}

Rules:
- Each post must be between 100-400 words
- Use realistic Indian context (cities, rupee amounts, Indian laws)
- Each post must be unique with different scenarios
- Do NOT include post numbers or labels
- Return ONLY a JSON array of strings, each string is one post
- No markdown, no backticks, just raw JSON array

Example format:
["Post 1 content here...", "Post 2 content here...", ...]"""

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    body = {
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.85,
        "max_tokens": 4000,
    }

    try:
        res = requests.post(GROQ_URL, headers=headers, json=body, timeout=30)
        if res.status_code != 200:
            print(f"  ❌ Groq error {res.status_code}: {res.text[:100]}")
            return []

        content = res.json()["choices"][0]["message"]["content"].strip()

        # Strip markdown code fences if present
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        content = content.strip()

        posts = json.loads(content)
        if isinstance(posts, list):
            return [str(p).strip() for p in posts if len(str(p).strip()) > 80]
        return []

    except json.JSONDecodeError as e:
        print(f"  ⚠️  JSON parse error: {e}")
        return []
    except Exception as e:
        print(f"  ❌ Groq request failed: {e}")
        return []

def enrich_post(post_id: str, content: str) -> bool:
    """Call LexFeed /enrich to generate ML embedding for the post."""
    try:
        res = requests.post(
            f"{LEXFEED_API}/enrich",
            json={"post_id": post_id, "content": content},
            timeout=30,
        )
        return res.status_code == 200
    except:
        return False

def check_lexfeed_running() -> bool:
    try:
        res = requests.get(f"{LEXFEED_API}/health", timeout=3)
        return res.status_code == 200
    except:
        return False

def random_past_date(days_back: int = 180) -> str:
    """Generate a random date within the past N days."""
    delta = random.randint(0, days_back)
    dt = datetime.now(timezone.utc) - timedelta(days=delta)
    return dt.isoformat()

def insert_posts_to_supabase(posts: list) -> int:
    from supabase import create_client
    db = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    inserted = 0
    failed = 0

    print(f"\n💾 Inserting {len(posts)} posts into Supabase...")

    for i, post in enumerate(posts):
        post_id = str(uuid.uuid4())

        row = {
            "id":              post_id,
            "author_id":       SEED_AUTHOR_ID,
            "type":            post["type"],
            "category":        post["category"],
            "content":         post["content"][:2000],
            "status":          "published",
            "is_anonymous":    random.choice([True, False, False]),
            "author_verified": False,
            "reactions_count": random.randint(0, 120),
            "comments_count":  random.randint(0, 30),
            "reports_count":   0,
            "created_at":      post["created_at"],
        }

        try:
            db.table("posts").insert(row).execute()
            inserted += 1

            enriched = enrich_post(post_id, post["content"])
            status = "✓ enriched" if enriched else "⚠ enrich skipped"

            print(f"  [{i+1}/{len(posts)}] {post['type']:<14} {post['category']:<20} {status}")
            time.sleep(0.3)

        except Exception as e:
            failed += 1
            print(f"  ❌ Insert failed: {str(e)[:80]}")

    print(f"\n✅ Done: {inserted} inserted, {failed} failed")
    return inserted

def main():
    print("=" * 60)
    print("  NyayaSetu AI Seed Script")
    print("  Powered by Groq + LLaMA 3")
    print("=" * 60)

    # Validate
    for key, name in [(SUPABASE_URL, "SUPABASE_URL"), (SUPABASE_ANON_KEY, "SUPABASE_ANON_KEY"),
                      (GROQ_API_KEY, "GROQ_API_KEY"), (SEED_AUTHOR_ID, "SEED_AUTHOR_ID")]:
        if not key or "your_" in str(key):
            print(f"\n❌ {name} not set in .env")
            sys.exit(1)

    if check_lexfeed_running():
        print("\n✅ LexFeed backend running — ML embeddings will be generated")
    else:
        print("\n⚠️  LexFeed backend not running — posts inserted without embeddings")
        ans = input("   Continue anyway? (y/n): ")
        if ans.lower() != "y":
            sys.exit(0)

    # Generate posts
    all_posts = []
    total_to_generate = sum(count for _, _, count in BATCHES)
    print(f"\n🤖 Generating {total_to_generate} posts using Groq AI...\n")

    for category, post_type, count in BATCHES:
        print(f"  Generating {count} × {category} ({post_type})...")
        contents = generate_posts_with_groq(category, post_type, count)

        for content in contents:
            all_posts.append({
                "content":    content,
                "category":   category,
                "type":       post_type,
                "created_at": random_past_date(180),
            })

        print(f"  ✓ Got {len(contents)} posts")
        time.sleep(1)  # Groq rate limit

    print(f"\n📊 Generated {len(all_posts)} posts total")
    print(f"\n📊 Category breakdown:")
    cats = Counter(p["category"] for p in all_posts)
    for cat, count in cats.most_common():
        print(f"   {cat:<25} {count} posts")

    print(f"\n🚀 Ready to insert {len(all_posts)} AI-generated Indian legal posts")
    ans = input("   Proceed? (y/n): ")
    if ans.lower() != "y":
        print("Aborted.")
        sys.exit(0)

    inserted = insert_posts_to_supabase(all_posts)

    print(f"\n🎉 Done! {inserted} posts now in your database.")
    print(f"   Open NyayaSetu or LexFeed frontend to see the feed.")

if __name__ == "__main__":
    main()
