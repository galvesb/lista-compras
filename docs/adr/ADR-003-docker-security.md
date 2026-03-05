# ADR-003 — Estratégia de Segurança nos Containers Docker

**Status:** Aceito
**Data:** 2026-03-04

## Contexto

Containers rodando como `root` ampliam o raio de impacto em caso de exploração de vulnerabilidade: um processo comprometido dentro do container teria privilégios de root no host (em configurações padrão sem user namespaces). Além disso, imagens gordas com ferramentas de build incluídas no runtime aumentam a superfície de ataque.

## Decisão

Aplicar as seguintes práticas em todos os Dockerfiles:

### 1. Multi-stage build

Separar estágio de **build** (com ferramentas de compilação) do estágio de **runtime** (apenas artefatos necessários). Reduz tamanho final e elimina compiladores/gerenciadores de pacote do container em produção.

```dockerfile
# Backend: python:3.12-slim no builder, python:3.12-slim no runtime
FROM python:3.12-slim AS builder
# ... instala dependências
FROM python:3.12-slim AS runtime
COPY --from=builder /usr/local/lib/python3.12/site-packages …
```

```dockerfile
# Frontend: node:20-alpine no builder, nginx:1.27-alpine no runtime
FROM node:20-alpine AS builder
# ... npm build
FROM nginx:1.27-alpine AS runtime
COPY --from=builder /app/dist /usr/share/nginx/html
```

### 2. Usuário não-root

Criar usuário dedicado sem shell e sem diretório home; transferir ownership dos artefatos; executar o processo principal como esse usuário.

```dockerfile
# Backend
RUN addgroup --system appgroup \
    && adduser --system --ingroup appgroup --no-create-home appuser
COPY --chown=appuser:appgroup app/ ./app/
USER appuser

# Frontend (nginx limitação: porta < 1024 requer root)
RUN addgroup -S appgroup && adduser -S appuser -G appgroup \
    && chown -R appuser:appgroup /usr/share/nginx/html \
    && chown -R appuser:appgroup /var/cache/nginx /var/log/nginx \
    && touch /var/run/nginx.pid && chown appuser:appgroup /var/run/nginx.pid \
    && sed -i 's/user\s\+nginx;//g' /etc/nginx/nginx.conf
USER appuser
# → porta mapeada para 8080 (non-root pode ouvir >= 1024)
```

### 3. Imagens base slim/alpine

Usar variantes mínimas (`-slim`, `-alpine`) para reduzir superficie de ataque e tamanho da imagem.

### 4. Segredos via variáveis de ambiente

Nenhum segredo hardcoded na imagem. Todas as credenciais (`SECRET_KEY`, `MONGO_PASSWORD`) chegam via `.env` montado pelo Docker Compose em runtime, nunca copiado via `COPY`.

### 5. Rede isolada no Docker Compose

MongoDB não expõe porta para o host em produção (`expose` interno apenas). Apenas o nginx/api ficam expostos via `ports`.

## Consequências

**Positivas:**
- Processo comprometido dentro do container não tem acesso root ao host
- Imagens menores → menos CVEs potenciais, push/pull mais rápido
- Superfície de ataque reduzida (sem gcc, make, node no runtime)
- Credenciais nunca embutidas na imagem (inspecionável via `docker history`)

**Negativas:**
- nginx não pode ouvir na porta 80 como non-root — necessidade de mapeamento `80:8080` no Compose e remoção de `user nginx;` no nginx.conf principal
- Debugging dentro do container é mais difícil (sem shell, sem ferramentas)

**Mitigações:**
- Documentado aqui o motivo do mapeamento `80:8080` para evitar regressões futuras
- Para debugging emergencial: `docker compose run --rm --user root api sh`
