# ADR-002 — Clean Architecture no backend FastAPI

**Status:** Aceito
**Data:** 2026-03-04

## Contexto

O backend precisa evoluir com segurança: adicionar novos casos de uso, trocar dependências (ex: MongoDB → outro banco) e testar regras de negócio sem depender de framework ou banco. A abordagem "tudo no router FastAPI" cria acoplamento forte entre HTTP, lógica de negócio e persistência.

## Decisão

Adotar **Clean Architecture** com quatro camadas bem definidas:

```
backend/app/
├── domain/           # Entidades e Value Objects (zero dependência externa)
│   ├── entities/     # User, ShoppingList, ListItem, ListMember
│   ├── value_objects/ # ItemStatus, MemberRole, ListStatus
│   └── exceptions/   # NotFound, Forbidden, Conflict
│
├── ports/            # Interfaces (ABCs Python)
│   ├── repositories/ # UserRepository, ListRepository, ItemRepository…
│   └── services/     # PasswordHasher, TokenService
│
├── use_cases/        # Regras de negócio puras (dependem só de ports)
│   ├── auth/         # RegisterUser, LoginUser
│   ├── lists/        # CreateList, ArchiveList, ReuseList
│   ├── items/        # AddItem, UpdateItemStatus, AssignItem, DeleteItem
│   └── members/      # InviteMember, RemoveMember
│
└── infra/            # Implementações concretas e glue code
    ├── db/           # MongoDB client, indexes
    ├── http/
    │   ├── routers/  # FastAPI routers (controllers)
    │   ├── schemas/  # Pydantic request/response models
    │   ├── dependencies/ # auth.py, permissions.py (FastAPI DI)
    │   └── middleware/   # SecurityHeaders
    ├── websocket/    # ConnectionManager
    └── main.py       # App factory, wiring de dependências
```

As dependências fluem **de fora para dentro**: `infra → use_cases → ports ← adapters`.
Os `adapters/` implementam os `ports/` e são injetados nos use cases via FastAPI `Depends`.

## Consequências

**Positivas:**
- Use cases testáveis com repositórios fake (sem MongoDB real nos testes unitários)
- Troca de banco de dados exige apenas novos adapters, sem tocar em lógica de negócio
- Routers FastAPI são finos — apenas validação HTTP e delegação ao use case
- Erros de domínio (`NotFound`, `Forbidden`) são mapeados para HTTP em um único lugar

**Negativas:**
- Mais arquivos e camadas que uma abordagem "flat"
- Onboarding inicial mais lento para desenvolvedores não familiarizados com Clean Architecture
- Injeção de dependência via `Depends` pode ser verbosa para use cases com muitas dependências

**Mitigações:**
- Este ADR e a estrutura de pastas servem como documentação viva
- `infra/main.py` concentra todo o wiring — um único lugar para entender as dependências
