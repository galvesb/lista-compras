#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# backup-cleanup.sh — Remove backups mais antigos que N dias
#
# Uso:
#   ./scripts/backup-cleanup.sh 7    # mantém últimos 7 dias (padrão)
#   ./scripts/backup-cleanup.sh 30   # mantém últimos 30 dias
# ──────────────────────────────────────────────────────────────────────────────
set -euo pipefail

RETENTION_DAYS="${1:-7}"
BACKUP_DIR="$(cd "$(dirname "$0")/.." && pwd)/backups"

if [[ ! -d "$BACKUP_DIR" ]]; then
  echo "[cleanup] Diretório de backups não encontrado: ${BACKUP_DIR}"
  exit 0
fi

echo "[cleanup] Removendo backups com mais de ${RETENTION_DAYS} dias em ${BACKUP_DIR}"
find "$BACKUP_DIR" -maxdepth 1 -mindepth 1 -type d -mtime "+${RETENTION_DAYS}" -print -exec rm -rf {} +
echo "[cleanup] Concluído."
