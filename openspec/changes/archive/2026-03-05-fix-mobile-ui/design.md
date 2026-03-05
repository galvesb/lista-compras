# Design: fix-mobile-ui

## Fix 1 — Auto-zoom em inputs (iOS Safari)

**Causa:** iOS Safari dispara zoom automático quando `font-size` do input focado é menor que 16px.
No codebase atual: `ListsPage.tsx` usa `15px`, `ListDetailPage.tsx` usa `14px`.

**Estratégia:** regra global em `index.css` — garante que todos os inputs/selects tenham no mínimo 16px no mobile, sem alterar o visual no desktop.

```css
/* frontend/src/index.css — adicionar após as regras existentes */
@media (max-width: 768px) {
  input, textarea, select {
    font-size: 16px !important;
  }
}
```

**Por que media query e não mudar diretamente os inline styles?**
- Centraliza a correção em um único lugar
- Não espalha `16px` por todos os componentes
- O visual desktop permanece inalterado (14px/15px continuam sendo usados em telas grandes)
- `!important` garante override dos inline styles sem precisar tocar em cada componente

**Não alterar o viewport meta tag** (`maximum-scale=1` prejudica usuários com baixa visão que dependem de zoom de acessibilidade).

---

## Fix 2 — Botão FAB desalinhado (ListsPage)

**Causa:** `fabStyle` não tem Flexbox. O `+` é centralizado pelo comportamento padrão de `<button>`, que é inconsistente entre navegadores — especialmente o alinhamento vertical do baseline do caractere `+`.

**Solução:** adicionar `display: flex`, `alignItems: center`, `justifyContent: center` ao `fabStyle`:

```js
// frontend/src/pages/ListsPage.tsx
const fabStyle: React.CSSProperties = {
  position: 'fixed', bottom: '24px', right: '24px',
  width: '56px', height: '56px', borderRadius: '50%',
  background: '#6366f1', color: '#fff', border: 'none',
  fontSize: '28px', cursor: 'pointer',
  boxShadow: '0 4px 12px rgba(99,102,241,0.4)',
  display: 'flex',           // ← adicionar
  alignItems: 'center',      // ← adicionar
  justifyContent: 'center',  // ← adicionar
}
```

---

## Fix 3 — Ícone confuso no botão de delegação (ListItemRow)

**Causa:** o ícone `👤+` comunica "adicionar contato" (padrão de apps de contatos/WhatsApp), não "atribuir item".

**Solução:** remover o `+`, manter apenas `👤`:

```jsx
// frontend/src/components/ListItemRow.tsx — linha ~145
// Antes:
<button onClick={() => setShowAssignMenu(true)} style={assignBtn} title="Atribuir a um colaborador">
  👤+
</button>

// Depois:
<button onClick={() => setShowAssignMenu(true)} style={assignBtn} title="Atribuir a um colaborador">
  👤
</button>
```

O `title="Atribuir a um colaborador"` já explica a ação no hover/acessibilidade. O `👤` sozinho é semânticamente correto para "pessoa/usuário".
