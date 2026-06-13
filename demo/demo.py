"""
LexFeed Demo Script
===================
Run this to demonstrate the recommendation engine working.
No Jupyter needed — plain Python script.

Usage:
  python demo/demo.py

What it shows:
  1. Auto category detection from post text
  2. Embedding generation
  3. Similarity between posts
  4. Feed scoring breakdown
  5. Cold start vector generation
"""

import sys
import os
import asyncio

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.embeddings import EmbeddingService
from app.enrichment import EnrichmentService
from app.ranking import RankingEngine


def separator(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


async def demo_category_detection():
    separator("DEMO 1: Auto Category Detection")

    enricher = EnrichmentService()

    test_posts = [
        "My landlord is refusing to return my security deposit of Rs 50,000 even after 3 months of vacating the property.",
        "My employer has not paid salary for the last 2 months and is threatening to terminate me if I complain.",
        "I received a defective product from an online store and they are refusing to give a refund.",
        "My husband is threatening me and I need to know about legal protection available to me.",
        "I want to file an RTI application to know why my passport application is delayed.",
    ]

    for i, post in enumerate(test_posts, 1):
        print(f"\nPost {i}: {post[:80]}...")
        tags = await enricher.classify_post(post)
        print(f"  → Primary Topic:  {tags['primary_topic']}")
        print(f"  → Urgency:        {tags['urgency']}")
        print(f"  → Tags:           {', '.join(tags['enriched_tags'][:3])}")
        print(f"  → Target:         {', '.join(tags['target_audience'])}")


async def demo_embeddings():
    separator("DEMO 2: Semantic Similarity")

    embedder = EmbeddingService()

    print("\nGenerating embeddings for 3 posts...")

    posts = {
        "Tenant post":    "My landlord hasn't returned my deposit after I vacated the flat 3 months ago.",
        "Consumer post":  "The product I bought online was defective. The company refuses to give a refund.",
        "Similar tenant": "Landlord is refusing to give back security deposit even after leaving the house.",
    }

    embeddings = {}
    for name, text in posts.items():
        emb = embedder.generate_embedding(text)
        embeddings[name] = emb
        print(f"  ✓ {name} — vector length: {len(emb)}")

    print("\nSimilarity scores:")
    names = list(embeddings.keys())
    for i in range(len(names)):
        for j in range(i+1, len(names)):
            sim = embedder.cosine_similarity(embeddings[names[i]], embeddings[names[j]])
            bar = "█" * int(sim * 20)
            print(f"  {names[i]} ↔ {names[j]}")
            print(f"  Similarity: {sim:.3f} {bar}")

    print("\n→ 'Tenant post' and 'Similar tenant' should score highest (same meaning, different words)")
    print("→ 'Consumer post' should score lower (different legal topic)")


async def demo_scoring():
    separator("DEMO 3: Post Scoring Breakdown")

    embedder = EmbeddingService()

    # Simulate a user interested in tenant rights
    user_text = "I am a tenant looking for help with rent and deposit issues"
    user_vector = embedder.generate_embedding(user_text)

    # Simulate posts with different characteristics
    test_posts = [
        {
            "id": "post-1",
            "content": "Landlord refusing to return deposit — know your rights as a tenant in India.",
            "created_at": "2026-05-31T10:00:00+00:00",
            "reactions_count": 45,
            "comments_count": 12,
            "author_verified": True,
            "primary_topic": "Tenant Rights",
            "enriched_tags": ["tenant", "deposit", "landlord", "rights"],
            "type": "Legal News"
        },
        {
            "id": "post-2",
            "content": "Criminal procedure for filing FIR in India.",
            "created_at": "2026-04-01T10:00:00+00:00",  # Old post
            "reactions_count": 5,
            "comments_count": 1,
            "author_verified": False,
            "primary_topic": "Criminal Law",
            "enriched_tags": ["fir", "police", "criminal"],
            "type": "Short Update"
        },
        {
            "id": "post-3",
            "content": "How to recover your security deposit legally — step by step guide.",
            "created_at": "2026-05-30T15:00:00+00:00",
            "reactions_count": 30,
            "comments_count": 8,
            "author_verified": True,
            "primary_topic": "Tenant Rights",
            "enriched_tags": ["deposit", "tenant", "recovery", "legal"],
            "type": "Article"
        },
    ]

    # Generate embeddings for posts
    for post in test_posts:
        post["embedding"] = embedder.generate_embedding(post["content"])

    # Score each post
    from app.database import DatabaseService
    db = DatabaseService.__new__(DatabaseService)  # Create without connecting
    ranker = RankingEngine(db, embedder)

    user_interests = ["Tenant Rights", "Property Law"]
    recent_topic_counts = {}

    print(f"\nUser interest: '{user_text[:50]}...'\n")

    results = []
    for post in test_posts:
        score, breakdown = ranker.score_post(
            post=post,
            user_interests=user_interests,
            user_vector=user_vector,
            recent_topic_counts=recent_topic_counts
        )
        results.append((post["id"], post["content"][:60], score, breakdown))

    results.sort(key=lambda x: x[2], reverse=True)

    for rank, (post_id, content, score, breakdown) in enumerate(results, 1):
        print(f"Rank {rank}: {content}...")
        print(f"  Total Score: {score:.1f}")
        for signal, value in breakdown.items():
            bar = "█" * max(0, int(abs(value) / 5))
            print(f"  {signal:20s}: {value:6.1f}  {bar}")
        print()


async def demo_cold_start():
    separator("DEMO 4: Cold Start — New User Onboarding")

    embedder = EmbeddingService()

    answers = [
        "I need help with a legal issue",
        "I want to learn about my rights",
        "I am a legal professional",
        "Just exploring",
    ]

    print("\nGenerating starting interest vectors for different onboarding answers...\n")

    vectors = {}
    for answer in answers:
        vector = await embedder.generate_cold_start_vector(
            user_id="demo-user",
            onboarding_answer=answer
        )
        vectors[answer] = vector
        print(f"  ✓ '{answer}'")
        print(f"    Vector length: {len(vector)}, First 3 values: {[round(v, 4) for v in vector[:3]]}")

    print("\nSimilarity between different user types:")
    answer_list = list(vectors.keys())
    for i in range(len(answer_list)):
        for j in range(i+1, len(answer_list)):
            sim = embedder.cosine_similarity(vectors[answer_list[i]], vectors[answer_list[j]])
            print(f"  '{answer_list[i][:30]}' ↔ '{answer_list[j][:30]}'")
            print(f"  Similarity: {sim:.3f}")


async def main():
    print("\n" + "="*60)
    print("  LEXFEED — Legal Content Recommendation Engine")
    print("  Demo Script")
    print("="*60)
    print("\nThis demo runs entirely locally — no database connection needed.")
    print("Embedding model will download on first run (~90MB, one time only).\n")

    try:
        await demo_category_detection()
        await demo_embeddings()
        await demo_scoring()
        await demo_cold_start()

        separator("DEMO COMPLETE")
        print("\n✓ Auto category detection — working")
        print("✓ Semantic embeddings — working")
        print("✓ Post scoring with 6 signals — working")
        print("✓ Cold start vector generation — working")
        print("\nNext step: Connect to Supabase and run the full API server.")
        print("  1. Copy .env.example to .env and fill in your keys")
        print("  2. Run: python -m app.main")
        print("  3. Open: http://localhost:8000/docs")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("Make sure you've installed requirements: pip install -r requirements.txt")


if __name__ == "__main__":
    asyncio.run(main())
