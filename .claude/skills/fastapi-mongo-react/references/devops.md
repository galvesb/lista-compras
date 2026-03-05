# DevOps — Docker, Nginx e CI/CD

## docker-compose.yml (Desenvolvimento)

```yaml
version: "3.9"
services:
  backend:
    build:
      context: ./backend
      target: development
    volumes:
      - ./backend:/app        # Hot reload
    ports:
      - "8000:8000"
    environment:
      - MONGODB_URL=mongodb://admin:secret@mongodb:27017/myapp?authSource=admin
      - SECRET_KEY=${SECRET_KEY}
    depends_on:
      mongodb:
        condition: service_healthy

  frontend:
    build:
      context: ./frontend
      target: development
    volumes:
      - ./frontend/src:/app/src
    ports:
      - "5173:5173"
    environment:
      - VITE_API_URL=http://localhost:8000/api/v1

  mongodb:
    image: mongo:7
    ports:
      - "27017:27017"
    environment:
      MONGO_INITDB_ROOT_USERNAME: admin
      MONGO_INITDB_ROOT_PASSWORD: secret
      MONGO_INITDB_DATABASE: myapp
    volumes:
      - mongo_data:/data/db
    healthcheck:
      test: ["CMD", "mongosh", "--eval", "db.adminCommand('ping')"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  mongo_data:
```

## Dockerfile Backend (Multi-stage)

```dockerfile
# backend/Dockerfile
FROM python:3.12-slim AS base
WORKDIR /app
RUN pip install uv

# Development
FROM base AS development
COPY pyproject.toml .
RUN uv sync --dev
COPY . .
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Production build
FROM base AS builder
COPY pyproject.toml .
RUN uv sync --no-dev --frozen

# Production final (imagem mínima)
FROM python:3.12-slim AS production
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY app/ ./app/
ENV PATH="/app/.venv/bin:$PATH"
RUN useradd --no-create-home appuser && chown -R appuser /app
USER appuser  # Nunca rodar como root!
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

## Dockerfile Frontend (Multi-stage)

```dockerfile
# frontend/Dockerfile
FROM node:20-alpine AS development
WORKDIR /app
COPY package*.json .
RUN npm ci
COPY . .
CMD ["npm", "run", "dev", "--", "--host"]

FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json .
RUN npm ci --production
COPY . .
ARG VITE_API_URL
RUN npm run build

FROM nginx:alpine AS production
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

## nginx.conf (Frontend + Proxy para Backend)

```nginx
server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    # SPA: redireciona tudo para index.html
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Proxy para API
    location /api/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Headers de segurança
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline';" always;

    # Gzip
    gzip on;
    gzip_types text/plain application/json application/javascript text/css;
}
```

## pyproject.toml

```toml
[project]
name = "myapp"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.32",
    "motor>=3.6",
    "beanie>=1.27",
    "pydantic-settings>=2.6",
    "python-jose[cryptography]>=3.3",
    "passlib[bcrypt]>=1.7",
    "slowapi>=0.1.9",
    "secure>=0.3",
    "python-multipart>=0.0.12",
]

[project.optional-dependencies]
dev = [
    "pytest>=8",
    "pytest-asyncio>=0.24",
    "httpx>=0.28",
    "ruff>=0.8",
    "mypy>=1.13",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "S", "UP"]
```

## .env.example Completo

```ini
# App
APP_NAME=MyApp
DEBUG=false

# MongoDB
MONGODB_URL=mongodb://user:password@localhost:27017/myapp?authSource=admin
MONGODB_DB_NAME=myapp

# Segurança — gerar com: openssl rand -hex 32
SECRET_KEY=SUBSTITUA_POR_CHAVE_FORTE_32_BYTES
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# CORS — separar por vírgula se múltiplos
ALLOWED_ORIGINS=["https://meusite.com"]

# Rate Limiting
RATE_LIMIT_LOGIN=5/minute
RATE_LIMIT_DEFAULT=100/minute
```

## GitHub Actions CI/CD Básico

```yaml
# .github/workflows/ci.yml
name: CI

on: [push, pull_request]

jobs:
  test-backend:
    runs-on: ubuntu-latest
    services:
      mongodb:
        image: mongo:7
        ports: ["27017:27017"]
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: uv sync --dev
        working-directory: backend
      - run: uv run pytest
        working-directory: backend
        env:
          MONGODB_URL: mongodb://localhost:27017
          SECRET_KEY: test-secret-key-for-ci-only

  test-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: "20" }
      - run: npm ci && npm run test
        working-directory: frontend

  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: uv run ruff check . && uv run mypy app/
        working-directory: backend
```