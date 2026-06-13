# Product Requirements Document
## LexFeed — Legal Content Recommendation Engine

**Author:** Vighnesh Vikas Sonawane
**Version:** 2.0
**Date:** June 2026
**Status:** In Development
**Target Integration:** NyayaSetu Justice Feed

---

## 1. Problem

NyayaSetu's Justice Feed shows posts in reverse chronological order. This means:

- A citizen with a tenant dispute sees criminal law posts that are irrelevant to them
- A high quality post from a verified advocate gets buried after 2 hours
- New users see random content with no reason to keep scrolling
- Users have to manually pick a category when posting — most don't know legal terminology

Legal platforms need to optimize for **relevance and trust**, not just engagement time.

---

## 2. Solution

LexFeed is a Python recommendation service that:

- **Auto-detects post categories** using an LLM — no manual dropdown needed
- **Learns what each user cares about** by watching their behavior silently
- **Ranks posts** using a 6-signal scoring model
- **Gets smarter** the more the user interacts

Zero cost. Runs entirely on free tools.

---

## 3. Goals

- Users see relevant legal content without configuring anything
- Verified advocate posts reach the right people within 2 hours of publishing
- New users have a useful feed from their first session
- Feed improves automatically with use — no manual tuning needed

---

## 4. Users

**Citizen (Client)**
Has a specific legal problem. Doesn't know legal terminology. Loses interest fast if the feed is irrelevant.

**Advocate**
Posts legal awareness content. Wants posts seen by people who actually need that expertise.

**Platform Admin**
Monitors feed quality. Needs visibility into what the algorithm promotes.

---

## 5. Features

### 5.1 Auto Category Detection
When a user publishes a post, the text is sent to an LLM which returns:
- Primary legal topic (Tenant Rights, Consumer Rights, Family Law, etc.)
- Urgency level (low / medium / high / critical)
- Enriched tags (5 keywords)
- Target audience

The user never sees a category dropdown. It happens silently in 1-2 seconds after posting.

If the LLM is unavailable, a keyword-based fallback classifies the post locally — no API needed.

### 5.2 Personalized Feed
The feed has 3 tabs:
- **For You** — personalized using the 4-stage pipeline
- **Recent** — standard reverse chronological
- **Trending** — highest engagement in last 48 hours

### 5.3 Interest Learning (No Onboarding Form)
The system watches user behavior silently:
- Scrolling past quickly → weak negative signal
- Reading slowly (5+ seconds) → weak positive signal
- Expanding a post → medium positive signal
- Liking or commenting → strong positive signal
- Reporting → strong negative signal

These signals continuously update the user's interest vector.

**Cold start for new users:** One simple question on first visit — "What brought you to NyayaSetu?" with 4 buttons. No dropdowns, no topic lists. Answer maps to a starting interest vector internally.

### 5.4 Score Transparency (Admin)
Admin dashboard can view score breakdown for any post for any user — recency, engagement, semantic similarity, etc. Useful for debugging and trust.

---

## 6. Success Metrics

| Metric | Target |
|--------|--------|
| Posts clicked per session | 2.5+ (vs 1.2 baseline) |
| Feed session duration | 4 min+ (vs 1.8 min baseline) |
| Irrelevant post reports | Less than 5% of feed impressions |
| Verified post reach time | Under 2 hours |
| Users with personalized feed | 80%+ after 5 interactions |

---

## 7. What's Out of Scope (for now)

- Video recommendations
- Push notifications based on feed
- A/B testing infrastructure
- Paid content promotion
- Collaborative filtering (needs more users — add later)

---

## 8. Timeline

| Phase | What | When |
|-------|------|------|
| Phase 1 | Embeddings + pgvector + basic similarity feed | Week 1 |
| Phase 2 | 6-signal ranking + diversification + filter | Week 2 |
| Phase 3 | LLM enrichment + feedback loop + cold start | Week 3 |
| Phase 4 | Evaluation + demo + NyayaSetu integration | Week 4 |
