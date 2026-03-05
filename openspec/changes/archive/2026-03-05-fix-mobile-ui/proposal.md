# Proposal: fix-mobile-ui

## O que

Corrigir três bugs de UI/UX identificados durante testes em dispositivos móveis no aplicativo de Listas de Compras Colaborativas.

## Por que

Esses bugs afetam diretamente a usabilidade mobile, que é o principal contexto de uso do app (compras são feitas no celular):

1. **Auto-zoom em inputs** — iOS Safari dispara zoom automático ao focar em campos com `font-size < 16px`, quebrando o layout e obrigando o usuário a tirar o zoom manualmente. Todos os inputs do app usam `14px` ou `15px`.
2. **Botão FAB desalinhado** — O `+` do botão flutuante "Criar Lista" não está centralizado verticalmente por falta de Flexbox explícito, comportamento inconsistente entre navegadores.
3. **Ícone confuso no botão de delegar** — O ícone `👤+` no botão de atribuição de item comunica "adicionar usuário" (semanticamente errado) em vez de "atribuir item a alguém".

## Escopo

- `frontend/index.html` — meta viewport
- `frontend/src/index.css` (ou equivalente global) — regra global de font-size para inputs
- `frontend/src/pages/ListsPage.tsx` — FAB style + inputStyle
- `frontend/src/pages/ListDetailPage.tsx` — inputStyle
- `frontend/src/components/ListItemRow.tsx` — ícone do botão de delegação

Sem mudanças no backend. Sem novas dependências.
