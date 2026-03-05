#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# restore.sh — Restaura backup do MongoDB via mongorestore
#
# Uso:
#   ./scripts/restore.sh ./backups/2026-03-04_02-00-00
#
# ATENÇÃO: sobrescreve o banco atual. Use com cuidado em produção.
# ──────────────────────────────────────────────────────────────────────────────
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Uso: $0 <caminho-do-backup>"
  echo "Exemplo: $0 ./backups/2026-03-04_02-00-00"
  exit 1
fi

BACKUP_PATH="$(realpath "$1")"
CONTAINER_NAME="lista-compras-mongodb-1"
DB_NAME="${MONGO_DB:-shopping_lists}"
TEMP_DIR="/tmp/mongorestore_$$"

if [[ ! -d "$BACKUP_PATH" ]]; then
  echo "[restore] Erro: diretório não encontrado: ${BACKUP_PATH}"
  exit 1
fi

echo "[restore] Copiando backup para o container..."
docker exec "$CONTAINER_NAME" mkdir -p "$TEMP_DIR"
docker cp "${BACKUP_PATH}/." "${CONTAINER_NAME}:${TEMP_DIR}"

echo "[restore] Executando mongorestore..."
docker exec "$CONTAINER_NAME" mongorestore \
  --db "$DB_NAME" \
  --drop \
  "${TEMP_DIR}/${DB_NAME}"

docker exec "$CONTAINER_NAME" rm -rf "$TEMP_DIR"

echo "[restore] Restauração concluída do backup: ${BACKUP_PATH}"
