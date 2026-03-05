#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# backup.sh — Backup diário do MongoDB via mongodump dentro do container
#
# Uso:
#   ./scripts/backup.sh                    # backup com timestamp automático
#   ./scripts/backup.sh mybackup-label     # nome customizado
#
# Requer: docker, docker compose up (container mongodb rodando)
# Destino: ./backups/YYYY-MM-DD_HH-MM-SS/
# ──────────────────────────────────────────────────────────────────────────────
set -euo pipefail

BACKUP_DIR="$(cd "$(dirname "$0")/.." && pwd)/backups"
TIMESTAMP="${1:-$(date +%Y-%m-%d_%H-%M-%S)}"
DEST="${BACKUP_DIR}/${TIMESTAMP}"

COMPOSE_FILE="$(cd "$(dirname "$0")/.." && pwd)/docker-compose.yml"
CONTAINER_NAME="lista-compras-mongodb-1"  # ajuste ao nome real do container
DB_NAME="${MONGO_DB:-shopping_lists}"

mkdir -p "$DEST"

echo "[backup] Iniciando mongodump → ${DEST}"

docker exec "$CONTAINER_NAME" mongodump \
  --db "$DB_NAME" \
  --out "/tmp/mongodump_${TIMESTAMP}"

docker cp "${CONTAINER_NAME}:/tmp/mongodump_${TIMESTAMP}/." "$DEST"

# Limpa dump temporário no container
docker exec "$CONTAINER_NAME" rm -rf "/tmp/mongodump_${TIMESTAMP}"

echo "[backup] Concluído: ${DEST}"
echo "[backup] Tamanho: $(du -sh "$DEST" | cut -f1)"
