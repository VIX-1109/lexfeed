from app.config import MAX_POSTS_PER_TOPIC, FEED_SIZE


def diversify(ranked_posts: list, max_size: int = FEED_SIZE) -> list:
    """
    Stage 3 — Ensure the feed isn't monotonous.

    Rules:
    - Max 3 posts per topic/category
    - No same author back to back
    - No more than 2 of same post type in last 3 posts
    - Mix Help Requests with other content
    """
    final_feed = []
    topic_count = {}

    for post in ranked_posts:
        if len(final_feed) >= max_size:
            break

        topic = post.get("primary_category") or post.get("category", "General")
        author_id = post.get("author_id") or post.get("user_id", "")
        post_type = post.get("type", "Short Update")

        # Rule 1: Max posts per topic
        if topic_count.get(topic, 0) >= MAX_POSTS_PER_TOPIC:
            continue

        # Rule 2: No same author back to back
        if final_feed and (final_feed[-1].get("author_id") == author_id or
                           final_feed[-1].get("user_id") == author_id):
            continue

        # Rule 3: No more than 2 of same post type in last 3
        recent_types = [p.get("type") for p in final_feed[-3:]]
        if recent_types.count(post_type) >= 2:
            continue

        final_feed.append(post)
        topic_count[topic] = topic_count.get(topic, 0) + 1

    return final_feed
