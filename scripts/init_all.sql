CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS rebot_vector_memory (
  id bigserial PRIMARY KEY,
  content text NOT NULL,
  metadata jsonb DEFAULT '{}'::jsonb,
  embedding vector(256)
);

CREATE TABLE IF NOT EXISTS execution (
  run_id text PRIMARY KEY,
  status text NOT NULL,
  created_at double precision DEFAULT EXTRACT(EPOCH FROM now()),
  updated_at double precision DEFAULT EXTRACT(EPOCH FROM now()),
  result text
);
