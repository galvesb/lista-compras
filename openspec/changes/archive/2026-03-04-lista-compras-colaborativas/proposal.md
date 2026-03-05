# Proposal: Lista de Compras Colaborativas

## O Quê

Aplicativo web responsivo (mobile-first) para criação, gestão e compartilhamento de listas de compras em tempo real. O diferencial central é a **delegação de itens** — o criador da lista atribui responsabilidades específicas a cada colaborador antes ou durante a ida ao mercado.

## Por Quê

Grupos que fazem compras juntos (famílias, casais, repúblicas) hoje coordenam via WhatsApp com listas em texto puro. Isso causa:
- Itens duplicados (duas pessoas pegam o mesmo produto)
- Itens esquecidos (ninguém ficou responsável)
- Sem visibilidade de preços para controle de gastos
- Nenhum histórico estruturado para comparar preços entre compras

## Solução

Um app que combina **lista estruturada + delegação explícita + sincronização em tempo real**:

1. Criador monta a lista e atribui itens a colaboradores por nome
2. No mercado, cada pessoa vê "Meus Itens" — só o que precisa pegar
3. Check com preço opcional registra o gasto real
4. Ao finalizar, lista é arquivada com total calculado
5. Na próxima compra, reutiliza a lista mostrando preços anteriores para comparação

## Escopo do MVP

**Incluído:**
- Autenticação email/senha com JWT
- Criação de listas (mercado + endereço + título automático)
- Adição e remoção de itens por qualquer membro
- Delegação de itens (exclusivo do criador)
- Check/uncheck/indisponível com preço opcional
- Compartilhamento por busca de email
- Sincronização em tempo real via WebSocket
- Filtros: Visão Geral / Meus Itens
- Avatares dos usuários atribuídos aos itens
- Ciclo de vida da lista: ativa → arquivada
- Histórico de compras com total gasto
- Reutilização de lista com preços anteriores como referência

**Fora do escopo MVP:**
- Notificações push/email
- Login social (Google, Apple)
- Categorização automática de itens
- Múltiplos idiomas
- Modo offline

## Personas

| Persona | Papel | Necessidade Principal |
|---------|-------|-----------------------|
| Organizador | Criador da lista | Montar, delegar e acompanhar o andamento geral |
| Colaborador | Membro convidado | Ver e executar apenas seus itens atribuídos |
| Solo | Usa sozinho | Lista pessoal simples sem colaboração |

## Restrições Técnicas e de Segurança

- Backend: FastAPI (Python) com Clean Architecture
- Banco: MongoDB em container Docker (volumes para persistência)
- Frontend: ReactJS responsivo
- Infra: Docker Compose (3 serviços: api, frontend, mongodb)
- Segurança: OWASP Top 10, JWT com expiração curta, containers non-root, redes Docker isoladas
- Concorrência: Optimistic Locking com campo `version` nos itens

## Métricas de Sucesso

- Usuário consegue criar lista, convidar colaborador e atribuir itens em menos de 2 minutos
- Atualização de check visível para todos os colaboradores em menos de 1 segundo
- Zero vulnerabilidades críticas (OWASP) em análise estática

## Não-Objetivos

- Não é um app de gestão de estoque doméstico
- Não é uma plataforma de comparação de preços entre mercados
- Não substitui apps de finanças pessoais (o total de compras é apenas informativo)
