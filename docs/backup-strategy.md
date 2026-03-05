# Estratégia de Backup e Disaster Recovery

## Scripts disponíveis

| Script | Descrição |
|--------|-----------|
| `scripts/backup.sh` | Executa `mongodump` e salva em `backups/YYYY-MM-DD_HH-MM-SS/` |
| `scripts/restore.sh <dir>` | Restaura um backup com `mongorestore --drop` |
| `scripts/backup-cleanup.sh [dias]` | Remove backups mais antigos que N dias (padrão: 7) |

## Executar backup manualmente

```bash
# Certifique-se que o container está rodando
docker compose ps

# Backup com timestamp automático
./scripts/backup.sh

# Verificar backup criado
ls -lh backups/
```

## Restaurar um backup

```bash
# CUIDADO: --drop apaga os dados atuais antes de restaurar
./scripts/restore.sh ./backups/2026-03-04_02-00-00
```

## Automatizar com cron (no host)

Adicione ao crontab do usuário que tem acesso ao Docker:

```bash
crontab -e
```

```cron
# Backup diário às 02:00
0 2 * * * /caminho/absoluto/lista-compras/scripts/backup.sh >> /var/log/lista-compras-backup.log 2>&1

# Limpeza semanal (mantém 30 dias)
0 3 * * 0 /caminho/absoluto/lista-compras/scripts/backup-cleanup.sh 30 >> /var/log/lista-compras-backup.log 2>&1
```

## Política de retenção recomendada

| Tipo | Frequência | Retenção |
|------|-----------|---------|
| Diário | 02:00 todo dia | 7 dias |
| Semanal (domingo) | 03:00 todo domingo | 4 semanas |
| Mensal (dia 1) | 04:00 todo dia 1 | 3 meses |

Para retenção diferenciada, ajuste o argumento de `backup-cleanup.sh` em cada entrada do cron.

## Verificação de integridade

Após cada backup, valide o número de documentos:

```bash
# Conta documentos no backup (requer mongosh ou mongodump --dryRun)
ls -la backups/$(ls backups/ | tail -1)/shopping_lists/
```

## Armazenamento externo (recomendado para produção)

Copie os backups para um storage externo (S3, Google Cloud Storage, etc.):

```bash
# Exemplo com rclone
rclone copy ./backups/ remote:meu-bucket/lista-compras-backups/
```
