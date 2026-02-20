#!/usr/bin/env bash
set -euo pipefail

DB_USER="rebot"
DB_PASS="Rebot@2026!"
DB_NAME="rebot"

dnf -y install dnf-plugins-core curl
dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
dnf -y install docker-ce docker-ce-cli containerd.io docker-compose-plugin
systemctl enable --now docker

mkdir -p /opt/rebot-stack
cd /opt/rebot-stack

cat > docker-compose.yml <<'EOF'
version: "3.9"
services:
  db:
    image: pgvector/pgvector:pg16
    container_name: rebot_db
    environment:
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASS}
      POSTGRES_DB: ${DB_NAME}
    ports:
      - "5432:5432"
    volumes:
      - db_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql:ro

  redis:
    image: redis:7
    container_name: rebot_redis
    ports:
      - "6379:6379"

  rabbitmq:
    image: rabbitmq:3-management
    container_name: rebot_rabbitmq
    ports:
      - "5672:5672"
      - "15672:15672"

volumes:
  db_data:
EOF

cat > .env <<EOF
DB_USER=${DB_USER}
DB_PASS=${DB_PASS}
DB_NAME=${DB_NAME}
EOF

cat > init.sql <<'EOF'
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS execution (
  run_id TEXT PRIMARY KEY,
  status TEXT NOT NULL DEFAULT 'pending',
  created_at DOUBLE PRECISION NOT NULL,
  updated_at DOUBLE PRECISION NOT NULL,
  result TEXT
);
EOF

docker compose up -d

firewall-cmd --permanent --add-port=5432/tcp
firewall-cmd --permanent --add-port=6379/tcp
firewall-cmd --permanent --add-port=5672/tcp
firewall-cmd --permanent --add-port=15672/tcp
firewall-cmd --reload

echo "Done. DB=${DB_NAME} USER=${DB_USER} PASS=${DB_PASS}"
