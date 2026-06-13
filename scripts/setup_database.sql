-- LexFeed Database Setup
-- Run this in your Supabase SQL Editor

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Store semantic embeddings for each post
CREATE TABLE IF NOT EXISTS post_embeddings (
  post_id UUID PRIMARY KEY REFERENCES posts(id) ON DELETE CASCADE,
  embedding vector(384),
  enriched_tags TEXT[] DEFAULT '{}',
  primary_topic TEXT DEFAULT 'General',
  legal_topics TEXT[] DEFAULT '{}',
  urgency_score INT DEFAULT 2,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Store user interest vectors
CREATE TABLE IF NOT EXISTS user_interests (
  user_id UUID PRIMARY KEY REFERENCES profiles(id) ON DELETE CASCADE,
  interest_vector vector(384),
  explicit_interests TEXT[] DEFAULT '{}',
  implicit_interests TEXT[] DEFAULT '{}',
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Store pre-computed feed scores per user per post
CREATE TABLE IF NOT EXISTS feed_scores (
  user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
  post_id UUID REFERENCES posts(id) ON DELETE CASCADE,
  score FLOAT DEFAULT 0,
  score_breakdown JSONB DEFAULT '{}',
  computed_at TIMESTAMPTZ DEFAULT NOW(),
  PRIMARY KEY (user_id, post_id)
);

-- Track all user interactions for feedback loop
CREATE TABLE IF NOT EXISTS interaction_logs (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
  post_id UUID REFERENCES posts(id) ON DELETE CASCADE,
  action TEXT NOT NULL,
  duration_ms INT DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Store LLM-enriched post metadata
CREATE TABLE IF NOT EXISTS post_tags (
  post_id UUID PRIMARY KEY REFERENCES posts(id) ON DELETE CASCADE,
  primary_topic TEXT DEFAULT 'General',
  secondary_topics TEXT[] DEFAULT '{}',
  legal_acts TEXT[] DEFAULT '{}',
  urgency TEXT DEFAULT 'medium',
  target_audience TEXT[] DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for fast similarity search
CREATE INDEX IF NOT EXISTS post_embeddings_embedding_idx
  ON post_embeddings USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);

CREATE INDEX IF NOT EXISTS user_interests_vector_idx
  ON user_interests USING ivfflat (interest_vector vector_cosine_ops)
  WITH (lists = 100);

-- Indexes for fast filtering
CREATE INDEX IF NOT EXISTS interaction_logs_user_id_idx ON interaction_logs(user_id);
CREATE INDEX IF NOT EXISTS interaction_logs_post_id_idx ON interaction_logs(post_id);
CREATE INDEX IF NOT EXISTS interaction_logs_created_at_idx ON interaction_logs(created_at);
CREATE INDEX IF NOT EXISTS feed_scores_user_id_idx ON feed_scores(user_id);

-- ── Helper Functions ──────────────────────────────────────────────

-- Find posts similar to a user's interest vector
CREATE OR REPLACE FUNCTION get_similar_posts(
  query_embedding vector(384),
  exclude_ids UUID[],
  match_count INT DEFAULT 100
)
RETURNS TABLE (
  id UUID,
  content TEXT,
  author_id UUID,
  author_verified BOOLEAN,
  type TEXT,
  category TEXT,
  reactions_count INT,
  comments_count INT,
  created_at TIMESTAMPTZ,
  embedding vector(384),
  enriched_tags TEXT[],
  primary_topic TEXT,
  similarity FLOAT
)
LANGUAGE sql STABLE
AS $$
  SELECT
    p.id,
    p.content,
    p.author_id,
    COALESCE(adv.verification_status = 'verified', FALSE) as author_verified,
    p.type,
    p.category,
    COALESCE(p.reactions_count, 0) as reactions_count,
    COALESCE(p.comments_count, 0) as comments_count,
    p.created_at,
    pe.embedding,
    pe.enriched_tags,
    pe.primary_topic,
    1 - (pe.embedding <=> query_embedding) as similarity
  FROM posts p
  JOIN post_embeddings pe ON p.id = pe.post_id
  LEFT JOIN advocates adv ON p.author_id = adv.id
  WHERE p.status = 'published'
    AND p.id != ALL(exclude_ids)
  ORDER BY pe.embedding <=> query_embedding
  LIMIT match_count;
$$;

-- Get posts liked by people the user has interacted with
CREATE OR REPLACE FUNCTION get_social_graph_posts(
  p_user_id UUID,
  p_exclude_ids UUID[],
  p_limit INT DEFAULT 100
)
RETURNS TABLE (
  id UUID,
  content TEXT,
  author_id UUID,
  author_verified BOOLEAN,
  type TEXT,
  category TEXT,
  reactions_count INT,
  comments_count INT,
  created_at TIMESTAMPTZ,
  primary_topic TEXT
)
LANGUAGE sql STABLE
AS $$
  SELECT DISTINCT
    p.id,
    p.content,
    p.author_id,
    COALESCE(adv.verification_status = 'verified', FALSE) as author_verified,
    p.type,
    p.category,
    COALESCE(p.reactions_count, 0) as reactions_count,
    COALESCE(p.comments_count, 0) as comments_count,
    p.created_at,
    COALESCE(pt.primary_topic, p.category, 'General') as primary_topic
  FROM posts p
  JOIN interaction_logs il ON p.id = il.post_id
  LEFT JOIN advocates adv ON p.author_id = adv.id
  LEFT JOIN post_tags pt ON p.id = pt.post_id
  WHERE il.user_id IN (
    SELECT DISTINCT receiver_id FROM messages WHERE sender_id = p_user_id
    UNION
    SELECT DISTINCT sender_id FROM messages WHERE receiver_id = p_user_id
  )
  AND il.action = 'like'
  AND p.status = 'published'
  AND p.id != ALL(p_exclude_ids)
  LIMIT p_limit;
$$;

-- Get post IDs the user has already seen
CREATE OR REPLACE FUNCTION get_seen_post_ids(
  p_user_id UUID,
  p_within_hours INT DEFAULT 24
)
RETURNS TABLE (post_id UUID)
LANGUAGE sql STABLE
AS $$
  SELECT DISTINCT post_id
  FROM interaction_logs
  WHERE user_id = p_user_id
    AND created_at > NOW() - (p_within_hours || ' hours')::INTERVAL;
$$;

-- Get topic counts from recent interactions
CREATE OR REPLACE FUNCTION get_recent_topic_counts(
  p_user_id UUID,
  p_within_hours INT DEFAULT 2
)
RETURNS TABLE (primary_topic TEXT, count BIGINT)
LANGUAGE sql STABLE
AS $$
  SELECT
    COALESCE(pt.primary_topic, 'General') as primary_topic,
    COUNT(*) as count
  FROM interaction_logs il
  JOIN post_tags pt ON il.post_id = pt.post_id
  WHERE il.user_id = p_user_id
    AND il.created_at > NOW() - (p_within_hours || ' hours')::INTERVAL
  GROUP BY pt.primary_topic;
$$;

-- Get trending posts by engagement in last 48 hours
CREATE OR REPLACE FUNCTION get_trending_posts(
  p_limit INT DEFAULT 20,
  p_offset INT DEFAULT 0
)
RETURNS TABLE (
  id UUID,
  content TEXT,
  author_id UUID,
  type TEXT,
  category TEXT,
  reactions_count INT,
  comments_count INT,
  created_at TIMESTAMPTZ,
  trend_score FLOAT
)
LANGUAGE sql STABLE
AS $$
  SELECT
    p.id,
    p.content,
    p.author_id,
    p.type,
    p.category,
    COALESCE(p.reactions_count, 0) as reactions_count,
    COALESCE(p.comments_count, 0) as comments_count,
    p.created_at,
    (COALESCE(p.reactions_count, 0) * 2.0 + COALESCE(p.comments_count, 0) * 4.0) as trend_score
  FROM posts p
  WHERE p.status = 'published'
    AND p.created_at > NOW() - INTERVAL '48 hours'
  ORDER BY trend_score DESC
  LIMIT p_limit
  OFFSET p_offset;
$$;
