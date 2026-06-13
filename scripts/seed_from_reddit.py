"""
seed_from_reddit.py
────────────────────────────────────────────────────────────────────────────────
Pulls real posts from r/LegalAdviceIndia (no API key needed),
maps them to NyayaSetu's posts table schema, and inserts them into Supabase.

Also calls LexFeed's /enrich endpoint to auto-classify each post and generate
its ML embedding so the recommendation pipeline works immediately.

Usage:
    python scripts/seed_from_reddit.py

Requirements:
    - .env file with SUPABASE_URL, SUPABASE_ANON_KEY, SEED_AUTHOR_ID
    - LexFeed backend running on localhost:8000 (for /enrich)
"""

import os
import sys
import time
import uuid
import requests
from datetime import datetime, timezone
from collections import Counter
from dotenv import load_dotenv

load_dotenv()

# ── CONFIG ────────────────────────────────────────────────────────────────────

SUPABASE_URL      = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
LEXFEED_API       = os.getenv("LEXFEED_API", "http://localhost:8000")
SEED_AUTHOR_ID    = os.getenv("SEED_AUTHOR_ID")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
}
POST_LIMIT  = 100
MIN_SCORE   = 2
MIN_LENGTH  = 80

FLAIR_TO_TYPE = {
    "advice needed":  "Help Request",
    "help":           "Help Request",
    "question":       "Help Request",
    "news":           "Legal News",
    "article":        "Article",
    "discussion":     "Article",
    "information":    "Short Update",
}

KEYWORD_CATEGORY_MAP = [
    (["domestic violence", "dowry", "498a", "cruelty", "harassment wife",
      "women safety", "stalking", "sexual harassment", "pocso"], "Women Safety"),
    (["fir", "police", "arrest", "bail", "ipc", "crpc", "criminal",
      "custody", "chargesheet", "accused", "complaint police"], "Criminal Law"),
    (["tenant", "landlord", "rent", "deposit", "eviction", "lease",
      "rental", "pg ", "paying guest", "notice to vacate"], "Tenant Rights"),
    (["property", "plot", "flat", "builder", "registry", "sale deed",
      "possession", "real estate", "rera", "land", "construction"], "Property Law"),
    (["consumer", "refund", "product", "amazon", "flipkart", "ecommerce",
      "defective", "warranty", "service", "complaint forum"], "Consumer Rights"),
    (["divorce", "alimony", "maintenance", "custody", "marriage",
      "family court", "child", "adoption", "hindu marriage", "muslim"], "Family Law"),
    (["salary", "job", "employer", "fired", "terminate", "pf", "epf",
      "labour", "gratuity", "notice period", "workplace"], "Employment"),
    (["rti", "right to information", "government", "public authority",
      "pio", "central information"], "RTI"),
    (["income tax", "gst", "tds", "itr", "tax notice",
      "tax return", "80c", "capital gains"], "Tax Law"),
    (["company", "startup", "contract", "agreement", "mou", "nda",
      "partnership", "incorporation", "shareholder"], "Corporate Law"),
    (["court", "case", "lawsuit", "legal notice", "summons", "hearing",
      "judge", "advocate", "lawyer", "civil suit", "injunction"], "Civil Litigation"),
]

def detect_category(title: str, body: str) -> str:
    text = (title + " " + body).lower()
    for keywords, category in KEYWORD_CATEGORY_MAP:
        if any(kw in text for kw in keywords):
            return category
    return "General Legal"

def detect_type(flair: str, title: str) -> str:
    if flair:
        flair_lower = flair.lower()
        for key, post_type in FLAIR_TO_TYPE.items():
            if key in flair_lower:
                return post_type
    title_lower = title.lower()
    if any(w in title_lower for w in ["help", "advice", "what should", "can i", "is it legal", "my landlord", "my employer", "my husband", "my wife"]):
        return "Help Request"
    if any(w in title_lower for w in ["news", "court rules", "sc ", "hc ", "supreme court", "high court", "judgment"]):
        return "Legal News"
    if any(w in title_lower for w in ["guide", "how to", "explain", "everything about", "all you need"]):
        return "Article"
    return "Short Update"

def clean_content(title: str, body: str) -> str:
    body = body.strip()
    for artifact in ["[deleted]", "[removed]", "&#x200B;", "&amp;", "&gt;", "&lt;"]:
        body = body.replace(artifact, "")
    body = body.strip()
    if body and len(body) > 20:
        return f"{title.strip()}\n\n{body}"
    return title.strip()

def fetch_reddit_posts(subreddit: str, limit: int = 100) -> list:
    posts = []

    print(f"\n📡 Fetching posts from r/{subreddit} via Arctic Shift archive...")

    try:
        url = f"https://arctic-shift.photon-reddit.com/api/posts/search?subreddit={subreddit}&limit={limit}&sort=top"
        res = requests.get(url, headers=HEADERS, timeout=15)

        if res.status_code == 200:
            data = res.json()
            posts = data.get("data", [])
            print(f"  ✓ Fetched {len(posts)} posts via Arctic Shift")
        else:
            print(f"  ⚠️  Arctic Shift returned {res.status_code}, trying Pushshift...")
            url2 = f"https://api.pushshift.io/reddit/search/submission/?subreddit={subreddit}&size={limit}&sort=score&sort_type=score"
            res2 = requests.get(url2, headers=HEADERS, timeout=15)
            if res2.status_code == 200:
                data2 = res2.json()
                posts = data2.get("data", [])
                print(f"  ✓ Fetched {len(posts)} posts via Pushshift")
            else:
                print(f"  ❌ Pushshift also failed: {res2.status_code}")

    except Exception as e:
        print(f"  ❌ Error fetching posts: {e}")

    print(f"  ✓ Total fetched: {len(posts)} raw posts")
    return posts

def filter_and_clean(raw_posts: list) -> list:
    cleaned = []
    skipped = 0

    for p in raw_posts:
        if p.get("removed_by_category") or p.get("author") == "[deleted]":
            skipped += 1
            continue

        title = p.get("title", "").strip()
        body  = p.get("selftext", "").strip()
        score = p.get("score", 0)

        if score < MIN_SCORE:
            skipped += 1
            continue

        content = clean_content(title, body)
        if len(content) < MIN_LENGTH:
            skipped += 1
            continue

        flair     = p.get("link_flair_text") or ""
        category  = detect_category(title, body)
        post_type = detect_type(flair, title)

        created_utc = p.get("created_utc", time.time())
        created_at  = datetime.fromtimestamp(created_utc, tz=timezone.utc).isoformat()

        cleaned.append({
            "reddit_id":    p.get("id"),
            "content":      content,
            "category":     category,
            "type":         post_type,
            "created_at":   created_at,
            "reddit_score": score,
            "comments":     p.get("num_comments", 0),
        })

    print(f"  ✓ After filtering: {len(cleaned)} usable posts ({skipped} skipped)")
    return cleaned

def enrich_post(post_id: str, content: str) -> dict | None:
    try:
        res = requests.post(
            f"{LEXFEED_API}/enrich",
            json={"post_id": post_id, "content": content},
            timeout=30,
        )
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        print(f"    ⚠️  Enrich failed: {e}")
    return None

def insert_posts_to_supabase(posts: list, author_id: str) -> int:
    from supabase import create_client

    db = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    inserted = 0
    failed   = 0

    print(f"\n💾 Inserting {len(posts)} posts into Supabase...")

    for i, post in enumerate(posts):
        post_id = str(uuid.uuid4())

        row = {
            "id":              post_id,
            "author_id":       author_id,
            "type":            post["type"],
            "category":        post["category"],
            "content":         post["content"][:2000],
            "status":          "published",
            "is_anonymous":    False,
            "author_verified": False,
            "reactions_count": min(post["reddit_score"], 999),
            "comments_count":  min(post["comments"], 99),
            "reports_count":   0,
            "created_at":      post["created_at"],
        }

        try:
            db.table("posts").insert(row).execute()
            inserted += 1

            enrich_result = enrich_post(post_id, post["content"])
            enriched = "✓ enriched" if enrich_result else "⚠ enrich skipped"

            print(f"  [{i+1}/{len(posts)}] {post['type']:<14} {post['category']:<20} {enriched}")
            time.sleep(0.5)

        except Exception as e:
            failed += 1
            err = str(e)
            if "posts_content_not_blank" not in err:
                print(f"  ❌ Insert failed: {err[:80]}")

    print(f"\n✅ Done: {inserted} inserted, {failed} failed")
    return inserted

def check_lexfeed_running() -> bool:
    try:
        res = requests.get(f"{LEXFEED_API}/health", timeout=3)
        return res.status_code == 200
    except:
        return False

def main():
    print("=" * 60)
    print("  NyayaSetu Reddit Seed Script")
    print("  Source: r/LegalAdviceIndia")
    print("=" * 60)

    if not SUPABASE_URL or "your_supabase" in SUPABASE_URL:
        print("\n❌ SUPABASE_URL not set in .env")
        sys.exit(1)

    if not SUPABASE_ANON_KEY or "your_supabase" in SUPABASE_ANON_KEY:
        print("\n❌ SUPABASE_ANON_KEY not set in .env")
        sys.exit(1)

    if not SEED_AUTHOR_ID:
        print("\n❌ SEED_AUTHOR_ID not set in .env")
        print("   Add a real profile UUID from your Supabase profiles table:")
        print("   SEED_AUTHOR_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx")
        sys.exit(1)

    if check_lexfeed_running():
        print("\n✅ LexFeed backend is running — posts will be enriched with ML embeddings")
    else:
        print("\n⚠️  LexFeed backend not running — posts will be inserted without ML embeddings")
        print("   Start it with: uvicorn app.main:app --reload")
        ans = input("   Continue anyway? (y/n): ")
        if ans.lower() != "y":
            sys.exit(0)

    raw   = fetch_reddit_posts("LegalAdviceIndia", limit=POST_LIMIT)
    posts = filter_and_clean(raw)

    if not posts:
        print("\n❌ No usable posts found")
        sys.exit(1)

    print(f"\n📊 Category breakdown:")
    cats  = Counter(p["category"] for p in posts)
    types = Counter(p["type"]     for p in posts)
    for cat, count in cats.most_common():
        print(f"   {cat:<25} {count} posts")
    print(f"\n📊 Type breakdown:")
    for t, count in types.most_common():
        print(f"   {t:<25} {count} posts")

    print(f"\n🚀 Ready to insert {len(posts)} posts as author: {SEED_AUTHOR_ID}")
    ans = input("   Proceed? (y/n): ")
    if ans.lower() != "y":
        print("Aborted.")
        sys.exit(0)

    inserted = insert_posts_to_supabase(posts, SEED_AUTHOR_ID)

    print(f"\n🎉 Seeding complete! {inserted} real Indian legal posts now in your database.")
    print(f"   Open NyayaSetu Justice Feed or LexFeed frontend to see them.")

if __name__ == "__main__":
    main()
