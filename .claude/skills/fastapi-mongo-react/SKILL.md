---
name: fastapi-mongo-react
description: >
  Guia completo de arquitetura, padrões de projeto e segurança para aplicações com FastAPI, MongoDB e React.
  Use esta skill sempre que o usuário mencionar FastAPI, MongoDB, React, ou qualquer combinação destes,
  mesmo que não cite explicitamente "padrões" ou "segurança". Aplique também quando o usuário pedir para
  criar APIs REST, backends Python, frontends React com autenticação, ou sistemas fullstack com banco NoSQL.
  Inclui: estrutura de pastas, autenticação JWT, validação Pydantic, middleware de segurança,
  gerenciamento de estado no frontend, variáveis de ambiente, rate limiting, CORS, e muito mais.
---

# Skill: FastAPI + MongoDB + React — Padrões e Segurança

## Quando usar este guia
- Criar um novo projeto fullstack com este stack
- Revisar ou refatorar código existente
- Adicionar autenticação/autorização
- Configurar segurança, CORS, rate limiting
- Estruturar pastas, módulos e camadas

---

## 1. Estrutura de Pastas Recomendada

```
projeto/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── v1/
│   │   │   │   ├── endpoints/       # Rotas separadas por domínio
│   │   │   │   │   ├── auth.py
│   │   │   │   │   ├── users.py
│   │   │   │   │   └── items.py
│   │   │   │   └── router.py        # Agrega todos os endpoints v1
│   │   │   └── deps.py              # Dependências injetáveis (get_db, get_current_user)
│   │   ├── core/
│   │   │   ├── config.py            # Settings via pydantic-settings
│   │   │   ├── security.py          # JWT, hashing, OAuth2
│   │   │   └── logging.py           # Logs estruturados
│   │   ├── db/
│   │   │   ├── mongodb.py           # Conexão Motor/Beanie
│   │   │   └── repositories/        # Padrão Repository por coleção
│   │   │       ├── base.py
│   │   │       ├── user_repo.py
│   │   │       └── item_repo.py
│   │   ├── models/                  # Modelos Beanie (ODM)
│   │   │   └── user.py
│   │   ├── schemas/                 # Schemas Pydantic (request/response)
│   │   │   ├── user.py
│   │   │   └── token.py
│   │   ├── services/                # Lógica de negócio
│   │   │   ├── auth_service.py
│   │   │   └── user_service.py
│   │   ├── middleware/
│   │   │   ├── rate_limit.py
│   │   │   └── logging.py
│   │   └── main.py
│   ├── tests/
│   │   ├── conftest.py
│   │   └── test_auth.py
│   ├── .env.example
│   ├── pyproject.toml
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── api/                     # Camada HTTP (axios + interceptors)
│   │   │   ├── client.ts
│   │   │   └── auth.ts
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── pages/
│   │   ├── store/                   # Zustand ou Redux Toolkit
│   │   │   └── authStore.ts
│   │   └── types/
│   ├── .env.local
│   └── vite.config.ts
└── docker-compose.yml
```

---

## 2. Backend: FastAPI

### 2.1 Configuração com pydantic-settings

```python
# core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    APP_NAME: str = "MyApp"
    DEBUG: bool = False
    MONGODB_URL: str
    MONGODB_DB_NAME: str
    SECRET_KEY: str              # openssl rand -hex 32
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALLOWED_ORIGINS: list[str] = []

settings = Settings()
```

```ini
# .env.example (commitar isso, nunca o .env real)
MONGODB_URL=mongodb://user:pass@localhost:27017
MONGODB_DB_NAME=myapp
SECRET_KEY=TROQUE_ISSO_openssl_rand_hex_32
ALLOWED_ORIGINS=["http://localhost:5173"]
```

### 2.2 MongoDB com Motor + Beanie

```python
# db/mongodb.py
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from app.core.config import settings
from app.models.user import User

async def init_db():
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.MONGODB_DB_NAME]
    await init_beanie(database=db, document_models=[User])
    return client

# main.py — usar lifespan (substitui @app.on_event deprecated)
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    client = await init_db()
    yield
    client.close()

app = FastAPI(lifespan=lifespan)
```

```python
# models/user.py
from beanie import Document, Indexed
from pydantic import EmailStr

class User(Document):
    email: Indexed(EmailStr, unique=True)
    hashed_password: str
    full_name: str
    is_active: bool = True
    is_superuser: bool = False

    class Settings:
        name = "users"
        indexes = ["email"]
```

### 2.3 Autenticação JWT + Bcrypt

```python
# core/security.py
from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta, UTC

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(subject: str) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": subject, "exp": expire}, settings.SECRET_KEY, settings.ALGORITHM)

def create_refresh_token(subject: str) -> str:
    expire = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    return jwt.encode({"sub": subject, "exp": expire, "type": "refresh"}, settings.SECRET_KEY, settings.ALGORITHM)
```

```python
# api/v1/endpoints/auth.py — Refresh token em cookie HttpOnly
@router.post("/login")
@limiter.limit("5/minute")
async def login(request: Request, form: OAuth2PasswordRequestForm = Depends()):
    user = await auth_service.authenticate(form.username, form.password)
    if not user:
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
    access_token = create_access_token(str(user.id))
    refresh_token = create_refresh_token(str(user.id))
    response = JSONResponse({"access_token": access_token, "token_type": "bearer"})
    response.set_cookie(
        key="refresh_token", value=refresh_token,
        httponly=True, secure=True, samesite="strict",
        max_age=60 * 60 * 24 * settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    return response
```

### 2.4 Padrão Repository

```python
# db/repositories/base.py
from typing import Generic, TypeVar, Optional, List, Type
from beanie import Document

T = TypeVar("T", bound=Document)

class BaseRepository(Generic[T]):
    def __init__(self, model: Type[T]):
        self.model = model

    async def find_by_id(self, id: str) -> Optional[T]:
        return await self.model.get(id)

    async def find_all(self, skip: int = 0, limit: int = 20) -> List[T]:
        return await self.model.find_all().skip(skip).limit(limit).to_list()

    async def create(self, doc: T) -> T:
        return await doc.insert()

    async def update(self, doc: T, data: dict) -> T:
        await doc.set(data)
        return doc

    async def delete(self, doc: T) -> None:
        await doc.delete()
```

### 2.5 Dependências Injetáveis

```python
# api/deps.py
from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends, HTTPException, status

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, [settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Token inválido")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado")
    user = await User.get(user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Usuário não encontrado ou inativo")
    return user

# Uso nas rotas:
@router.get("/me")
async def read_me(current_user: User = Depends(get_current_user)):
    return current_user
```

### 2.6 CORS, Rate Limiting e Headers de Segurança

```python
# main.py
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from secure import SecureHeaders

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,  # NUNCA "*" em produção
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["Authorization", "Content-Type"],
)

secure_headers = SecureHeaders()

@app.middleware("http")
async def set_secure_headers(request, call_next):
    response = await call_next(request)
    secure_headers.starlette(response)
    return response

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
```

### 2.7 Validação Pydantic com Regras de Negócio

```python
# schemas/user.py
import re
from pydantic import BaseModel, EmailStr, Field, field_validator

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=100)
    full_name: str = Field(min_length=2, max_length=100)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        errors = []
        if not re.search(r"[A-Z]", v):
            errors.append("pelo menos uma letra maiúscula")
        if not re.search(r"\d", v):
            errors.append("pelo menos um número")
        if not re.search(r"[!@#$%^&*]", v):
            errors.append("pelo menos um caractere especial")
        if errors:
            raise ValueError(f"Senha precisa ter: {', '.join(errors)}")
        return v

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    is_active: bool
    # Nunca retornar hashed_password!
```

---

## 3. Frontend: React + TypeScript

### 3.1 Cliente HTTP com Axios + Interceptors

```typescript
// api/client.ts
import axios from "axios";
import { useAuthStore } from "@/store/authStore";

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
  withCredentials: true,  // Necessário para cookies HttpOnly (refresh token)
});

api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken;
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

let isRefreshing = false;
api.interceptors.response.use(
  (res) => res,
  async (error) => {
    if (error.response?.status === 401 && !error.config._retry) {
      if (isRefreshing) return Promise.reject(error);
      error.config._retry = true;
      isRefreshing = true;
      try {
        const { data } = await axios.post(`${import.meta.env.VITE_API_URL}/auth/refresh`, {}, { withCredentials: true });
        useAuthStore.getState().setToken(data.access_token);
        error.config.headers.Authorization = `Bearer ${data.access_token}`;
        return api(error.config);
      } catch {
        useAuthStore.getState().logout();
        window.location.href = "/login";
      } finally {
        isRefreshing = false;
      }
    }
    return Promise.reject(error);
  }
);
```

### 3.2 State com Zustand

```typescript
// store/authStore.ts
import { create } from "zustand";

interface User { id: string; email: string; full_name: string; }

interface AuthState {
  user: User | null;
  accessToken: string | null;  // Mantém só em memória — NÃO no localStorage
  setToken: (token: string) => void;
  setUser: (user: User) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  accessToken: null,
  setToken: (accessToken) => set({ accessToken }),
  setUser: (user) => set({ user }),
  logout: () => set({ user: null, accessToken: null }),
}));
```

### 3.3 Proteção de Rotas

```tsx
// components/ProtectedRoute.tsx
import { Navigate, Outlet } from "react-router-dom";
import { useAuthStore } from "@/store/authStore";

export function ProtectedRoute() {
  const { user } = useAuthStore();
  return user ? <Outlet /> : <Navigate to="/login" replace />;
}

// router/index.tsx
<Routes>
  <Route path="/login" element={<LoginPage />} />
  <Route element={<ProtectedRoute />}>
    <Route path="/dashboard" element={<Dashboard />} />
    <Route path="/profile" element={<Profile />} />
  </Route>
</Routes>
```

### 3.4 Custom Hook de Auth

```typescript
// hooks/useAuth.ts
export function useAuth() {
  const { setUser, setToken, logout } = useAuthStore();

  const login = async (email: string, password: string) => {
    const params = new URLSearchParams({ username: email, password });
    const { data } = await api.post("/auth/login", params);
    setToken(data.access_token);
    const { data: user } = await api.get("/users/me");
    setUser(user);
  };

  const signOut = async () => {
    await api.post("/auth/logout");  // Limpa cookie no backend
    logout();
  };

  return { login, logout: signOut };
}
```

---

## 4. Checklist de Segurança Completo

### Backend
- [ ] Senhas com `bcrypt` (passlib) — nunca MD5/SHA1
- [ ] JWT: `SECRET_KEY` forte via `openssl rand -hex 32`
- [ ] Access token de vida curta (15–60 min), refresh em cookie `HttpOnly`
- [ ] Rate limiting em `/auth/login` e `/auth/register`
- [ ] CORS restrito às origens conhecidas
- [ ] Headers de segurança (CSP, HSTS, X-Frame-Options) via `secure`
- [ ] MongoDB com usuário de permissão mínima (não root)
- [ ] Validação rigorosa de input com Pydantic
- [ ] Nunca logar tokens, senhas ou dados pessoais
- [ ] Índices únicos para prevenir duplicidade (email)
- [ ] HTTPS obrigatório em produção

### Frontend
- [ ] Access token apenas em memória (Zustand) — nunca `localStorage`
- [ ] `withCredentials: true` para cookies HttpOnly
- [ ] `npm audit` regularmente
- [ ] Evitar `dangerouslySetInnerHTML`; usar `DOMPurify` se necessário
- [ ] Variáveis `VITE_*` nunca contêm secrets reais
- [ ] Validação no cliente E no servidor (nunca só no cliente)

---

## 5. Testes

```python
# tests/conftest.py
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

@pytest.fixture
async def auth_headers(client):
    await client.post("/api/v1/auth/register", json={"email": "test@test.com", "password": "Test@1234", "full_name": "Test"})
    resp = await client.post("/api/v1/auth/login", data={"username": "test@test.com", "password": "Test@1234"})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
```

---

## Referências

Para implementações mais detalhadas, leia os arquivos em `references/`:

| Arquivo | Conteúdo |
|---|---|
| `references/backend-security.md` | Refresh token rotation, revogação, OAuth2 social |
| `references/backend-db.md` | Transações MongoDB, aggregation, índices avançados |
| `references/devops.md` | Docker multi-stage, Nginx, CI/CD, variáveis de produção |