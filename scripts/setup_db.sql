-- LexFeed Database Setup
-- Run this in your Supabase SQL Editor

-- Step 1: Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Step 2: Post embeddings table
CREATE TABLE IF NOT EXISTS post_embeddings (
  post_id UUID PRIMARY KEY REFERENCES posts(id) ON DELETE CASCADE,
  embedding vector(384),
  enriched_tags TEXT[] DEFAULT '{}',
  legal_topics TEXT[] DEFAULT '{}',
  urgency_score INT DEFAULT 1,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Step 3: User interests table
CREATE TABLE IF NOT EXISTS user_interests (
  user_id UUID PRIMARY KEY REFERENCES profiles(id) ON DELETE CASCADE,
  interest_vector vector(384),
  explicit_interests TEXT[] DEFAULT '{}',
  implicit_interests TEXT[] DEFAULT '{}',
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Step 4: Interaction logs table
CREATE TABLE IF NOT EXISTS interaction_logs (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
  post_id UUID REFERENCES posts(id) ON DELETE CASCADE,
  action TEXT NOT NULL,
  duration_ms INT DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Step 5: Post tags table (LLM enrichment results)
CREATE TABLE IF NOT EXISTS post_tags (
  post_id UUID PRIMARY KEY REFERENCES posts(id) ON DELETE CASCADE,
  primary_topic TEXT,
  secondary_topics TEXT[] DEFAULT '{}',
  legal_acts TEXT[] DEFAULT '{}',
  urgency TEXT DEFAULT 'low',
  target_audience TEXT[] DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Step 6: Indexes for fast queries
CREATE INDEX IF NOT EXISTS idx_post_embeddings_vector
  ON post_embeddings USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);

CREATE INDEX IF NOT EXISTS idx_user_interests_vector
  ON user_interests USING ivfflat (interest_vector vector_cosine_ops)
  WITH (lists = 100);

CREATE INDEX IF NOT EXISTS idx_interaction_logs_user_id
  ON interaction_logs(user_id);

CREATE INDEX IF NOT EXISTS idx_interaction_logs_post_id
  ON interaction_logs(post_id);

CREATE INDEX IF NOT EXISTS idx_interaction_logs_created_at
  ON interaction_logs(created_at);

-- Step 7: pgvector similarity search function
-- Used by LexFeed candidate generation (Stage 1)
CREATE OR REPLACE FUNCTION match_posts_by_embedding(
  query_embedding vector(384),
  match_count INT DEFAULT 100,
  excluded_ids UUID[] DEFAULT '{}'
)
RETURNS TABLE (
  id UUID,
  content TEXT,
  author_id UUID,
  author_verified BOOLEAN,
  type TEXT,
  category TEXT,
  status TEXT,
  reactions_count INT,
  comments_count INT,
  created_at TIMESTAMPTZ,
  similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    p.id,
    p.content,
    p.author_id,
    p.author_verified,
    p.type,
    p.category,
    p.status,
    p.reactions_count,
    p.comments_count,
    p.created_at,
    1 - (pe.embedding <=> query_embedding) AS similarity
  FROM posts p
  JOIN post_embeddings pe ON p.id = pe.post_id
  WHERE p.status = 'published'
    AND (array_length(excluded_ids, 1) IS NULL OR p.id != ALL(excluded_ids))
  ORDER BY pe.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

-- Step 8: Add existing indexes to NyayaSetu tables for performance
CREATE INDEX IF NOT EXISTS idx_advocates_verification_status
  ON advocates(verification_status);

CREATE INDEX IF NOT EXISTS idx_advocates_location
  ON advocates(location);

CREATE INDEX IF NOT EXISTS idx_posts_created_at
  ON posts(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_messages_sender_id
  ON messages(sender_id);

CREATE INDEX IF NOT EXISTS idx_messages_receiver_id
  ON messages(receiver_id);

CREATE INDEX IF NOT EXISTS idx_appointments_client_id
  ON appointments(client_id);

CREATE INDEX IF NOT EXISTS idx_appointments_advocate_id
  ON appointments(advocate_id);
