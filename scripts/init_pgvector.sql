CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS rebot_vector_memory (
  id bigserial PRIMARY KEY,
  content text NOT NULL,
  metadata jsonb DEFAULT '{}'::jsonb,
  embedding vector(256)
);
