CREATE TABLE IF NOT EXISTS execution (
  run_id text PRIMARY KEY,
  status text NOT NULL,
  created_at double precision DEFAULT EXTRACT(EPOCH FROM now()),
  updated_at double precision DEFAULT EXTRACT(EPOCH FROM now()),
  result text
);
