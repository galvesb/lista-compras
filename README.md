# Lista de Compras Colaborativas

App web responsivo para criar, gerenciar e compartilhar listas de compras em tempo real, com delegação de itens por colaborador.

**Stack:** FastAPI · MongoDB · ReactJS · Docker Compose

---

## Requisitos

- [Docker](https://docs.docker.com/get-docker/) ≥ 24
- [Docker Compose](https://docs.docker.com/compose/) ≥ 2.20 (incluído no Docker Desktop)

---

## Setup em 3 Passos

### 1. Configure as variáveis de ambiente

```bash
cp .env.example .env
```

Edite o `.env` e configure:

```env
# Gere um secret seguro com:
# python -c "import secrets; print(secrets.token_hex(32))"
JWT_SECRET_KEY=coloque_aqui_um_secret_de_256_bits

MONGO_USER=admin
MONGO_PASSWORD=uma_senha_forte
MONGO_DB=lista_compras
```

### 2. Suba o ambiente

```bash
docker compose up --build
```

Na primeira execução, o build pode levar 2–3 minutos. Aguarde a mensagem:

```
api        | INFO:     Application startup complete.
```

### 3. Acesse a aplicação

| Serviço       | URL                                    |
|---------------|----------------------------------------|
| **Frontend**  | http://localhost                       |
| **Swagger UI**| http://localhost:8000/api/v1/docs      |
| **ReDoc**     | http://localhost:8000/api/v1/redoc     |
| **Health**    | http://localhost:8000/health           |

---

## Comandos Úteis

```bash
# Subir em background
docker compose up -d --build

# Ver logs da API em tempo real
docker compose logs -f api

# Parar tudo
docker compose down

# Parar e remover volumes (⚠️ apaga dados do MongoDB)
docker compose down -v

# Recriar só a API após mudanças no código
docker compose up --build api
```

---

## Desenvolvimento Local (sem Docker)

### Backend

```bash
cd backend

# Crie e ative o venv
python -m venv .venv
source .venv/bin/activate        # Linux/Mac
# .venv\Scripts\activate         # Windows

# Instale dependências
pip install -e ".[dev]"

# Configure o .env apontando para MongoDB local
# MONGO_HOST=localhost

# Suba só o MongoDB via Docker
docker compose up -d mongodb

# Rode a API
uvicorn app.infra.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend

npm install
npm run dev     # Vite dev server em http://localhost:5173
```

O Vite já está configurado para fazer proxy de `/api` e `/ws` para `localhost:8000`.

---

## Estrutura do Projeto

```
lista-compras/
├── docker-compose.yml
├── .env.example
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── app/
│       ├── domain/          # Entidades, value objects, exceções
│       ├── use_cases/       # Regras de negócio puras
│       ├── ports/           # Interfaces (ABCs)
│       ├── adapters/        # Implementações MongoDB + bcrypt + JWT
│       └── infra/           # FastAPI, routers, middlewares, WebSocket
└── frontend/
    ├── Dockerfile
    ├── nginx.conf
    └── src/
        ├── api/             # Axios client
        ├── context/         # AuthContext
        ├── hooks/           # useListWebSocket
        ├── components/      # Avatar, ListItemRow, CheckModal
        ├── pages/           # Login, Lists, ListDetail
        └── types/           # TypeScript interfaces
```

---

## Segurança

- JWT com expiração de 15 minutos
- Senhas com bcrypt (cost=12)
- MongoDB isolado na rede interna Docker (não exposto externamente)
- Containers rodando como usuário non-root
- Multi-stage builds (imagens slim)
- Security headers em todas as respostas (CSP, X-Frame-Options, etc.)
- Rate limiting em rotas de autenticação
- Optimistic locking para evitar race conditions no check de itens

---

## Backup e Restore

```bash
# Backup manual (salva em ./backups/YYYY-MM-DD_HH-MM-SS/)
./scripts/backup.sh

# Restaurar (⚠️ sobrescreve banco atual)
./scripts/restore.sh ./backups/2026-03-04_02-00-00
```

Para automatizar com cron e política de retenção, veja [docs/backup-strategy.md](docs/backup-strategy.md).

---

## Documentação Arquitetural

| ADR | Decisão |
|-----|---------|
| [ADR-001](docs/adr/ADR-001-mongodb.md) | MongoDB como banco de dados principal |
| [ADR-002](docs/adr/ADR-002-clean-architecture.md) | Clean Architecture no FastAPI |
| [ADR-003](docs/adr/ADR-003-docker-security.md) | Segurança nos containers Docker |

---

## Padrões de Desenvolvimento

### Branches

```
main          → produção estável
feat/<nome>   → nova funcionalidade
fix/<nome>    → correção de bug
chore/<nome>  → manutenção (deps, config, docs)
```

### Commits (Conventional Commits)

```
feat: adicionar filtro "Meus Itens" na lista
fix: corrigir duplicação ao criar item via WebSocket
chore: atualizar bcrypt para versão compatível com passlib
docs: adicionar ADR-002 Clean Architecture
```
