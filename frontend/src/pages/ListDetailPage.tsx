import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import { itemsApi } from '../api/items'
import { useAuth } from '../context/AuthContext'
import { useListWebSocket } from '../hooks/useListWebSocket'
import { ListItemRow } from '../components/ListItemRow'
import { Avatar } from '../components/Avatar'
import { InviteMemberModal } from '../components/InviteMemberModal'
import type { ShoppingList, ListItem, Member } from '../types'

type FilterMode = 'all' | 'mine'

/**
 * Main shopping list detail page.
 * Shows members, items with avatars, filter tabs (Visão Geral / Meus Itens),
 * add item form, and real-time sync via WebSocket.
 */
export function ListDetailPage() {
  const { listId } = useParams<{ listId: string }>()
  const { user, token } = useAuth()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [filter, setFilter] = useState<FilterMode>('all')
  const [newName, setNewName] = useState('')
  const [newQty, setNewQty] = useState('')
  const [showInvite, setShowInvite] = useState(false)

  // Fetch list detail + members
  const { data: listData } = useQuery<ShoppingList>({
    queryKey: ['list', listId],
    queryFn: () => api.get(`/lists/${listId}`).then((r) => r.data),
    enabled: !!listId,
  })

  // Fetch items (re-runs when filter changes)
  const { data: items = [], isLoading } = useQuery<ListItem[]>({
    queryKey: ['list', listId, 'items', filter],
    queryFn: () => itemsApi.list(listId!, filter === 'mine' ? 'mine' : undefined),
    enabled: !!listId,
  })

  // Real-time updates via WebSocket (userId necessário para lógica filter-aware do cache 'mine')
  useListWebSocket(listId!, token, user?.id ?? null)

  const addItemMutation = useMutation({
    mutationFn: () => itemsApi.add(listId!, newName.trim(), newQty.trim() || '1 un'),
    onSuccess: (item) => {
      // Deduplicate: WS event may have arrived before HTTP response
      queryClient.setQueryData<ListItem[]>(
        ['list', listId, 'items', 'all'],
        (old = []) => old.some((i) => i.id === item.id) ? old : [...old, item]
      )
      setNewName('')
      setNewQty('')
    },
  })

  const handleAddItem = (e: React.FormEvent) => {
    e.preventDefault()
    if (!newName.trim()) return
    addItemMutation.mutate()
  }

  const userRole = listData?.members?.find((m: Member) => m.user_id === user?.id)?.role ?? 'member'
  const isOwner = userRole === 'owner'

  const totalChecked = items.filter((i) => i.status === 'checked' && i.price != null)
    .reduce((sum, i) => sum + (i.price ?? 0), 0)
  const itemsWithoutPrice = items.filter((i) => i.status === 'checked' && i.price == null).length

  if (!listData) {
    return <div style={{ padding: '24px', textAlign: 'center', color: '#9ca3af' }}>Carregando...</div>
  }

  return (
    <div style={{ maxWidth: '600px', margin: '0 auto', paddingBottom: '80px' }}>
      {/* Header */}
      <div style={headerStyle}>
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
          <button onClick={() => navigate('/lists')} style={backBtn} title="Voltar">‹</button>
          <div>
            <h1 style={{ margin: 0, fontSize: '20px', fontWeight: 700 }}>{listData.store_name}</h1>
            <p style={{ margin: '2px 0 0', fontSize: '13px', color: '#6b7280' }}>
              {listData.address} · {new Date(listData.created_at).toLocaleDateString('pt-BR')}
            </p>
          </div>
        </div>

        {/* Member avatars + invite button */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <div style={{ display: 'flex' }}>
            {listData.members?.map((m: Member) => (
              <div key={m.user_id} style={{ marginLeft: '-8px' }}>
                <Avatar user={{ user_id: m.user_id, name: m.name, avatar_url: m.avatar_url }} size="md" />
              </div>
            ))}
          </div>
          {isOwner && listData.status === 'active' && (
            <button onClick={() => setShowInvite(true)} style={inviteBtn} title="Convidar membro">
              + Convidar
            </button>
          )}
        </div>
      </div>

      {/* Filter tabs */}
      <div style={tabsStyle}>
        <button
          onClick={() => setFilter('all')}
          style={tabBtn(filter === 'all')}
        >
          Visão Geral
        </button>
        <button
          onClick={() => setFilter('mine')}
          style={tabBtn(filter === 'mine')}
        >
          Meus Itens
        </button>
      </div>

      {/* Add item form */}
      {listData.status === 'active' && (
        <form onSubmit={handleAddItem} style={addFormStyle}>
          <input
            placeholder="Nome do item (ex: Leite integral)"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            style={inputStyle}
          />
          <input
            placeholder="Qtd (ex: 2L)"
            value={newQty}
            onChange={(e) => setNewQty(e.target.value)}
            style={{ ...inputStyle, width: '100px', flexShrink: 0 }}
          />
          <button type="submit" disabled={!newName.trim() || addItemMutation.isPending} style={addBtnStyle}>
            +
          </button>
        </form>
      )}

      {/* Items list */}
      <div style={{ borderRadius: '12px', overflow: 'hidden', border: '1px solid #f3f4f6' }}>
        {isLoading ? (
          <div style={{ padding: '32px', textAlign: 'center', color: '#9ca3af' }}>Carregando...</div>
        ) : items.length === 0 ? (
          <div style={{ padding: '32px', textAlign: 'center', color: '#9ca3af' }}>
            {filter === 'mine' ? 'Nenhum item atribuído a você' : 'Nenhum item ainda. Adicione acima!'}
          </div>
        ) : (
          items.map((item) => (
            <ListItemRow
              key={item.id}
              item={item}
              listId={listId!}
              isOwner={isOwner}
              members={listData.members ?? []}
            />
          ))
        )}
      </div>

      {/* Running total */}
      {items.some((i) => i.status === 'checked') && (
        <div style={totalBarStyle}>
          <span style={{ fontWeight: 600 }}>Total parcial:</span>
          <span style={{ color: '#16a34a', fontWeight: 700 }}>
            R$ {totalChecked.toFixed(2).replace('.', ',')}
          </span>
          {itemsWithoutPrice > 0 && (
            <span style={{ fontSize: '12px', color: '#9ca3af' }}>
              ({itemsWithoutPrice} sem preço)
            </span>
          )}
        </div>
      )}

      {/* Archive button (owner only) */}
      {isOwner && listData.status === 'active' && (
        <div style={{ padding: '16px', textAlign: 'center' }}>
          <button
            onClick={() => {
              if (confirm('Arquivar lista? O total será calculado com os preços informados.')) {
                api.patch(`/lists/${listId}/archive`).then(() => {
                  queryClient.invalidateQueries({ queryKey: ['lists'] })
                  queryClient.invalidateQueries({ queryKey: ['list', listId] })
                  navigate('/lists')
                })
              }
            }}
            style={archiveBtnStyle}
          >
            Finalizar compras
          </button>
        </div>
      )}

      {/* Delete button (owner only) */}
      {isOwner && (
        <div style={{ padding: '0 16px 24px', textAlign: 'center' }}>
          <button
            onClick={() => {
              if (confirm(`Excluir "${listData.store_name}"? Esta ação é permanente e não pode ser desfeita.`)) {
                api.delete(`/lists/${listId}`).then(() => {
                  queryClient.removeQueries({ queryKey: ['list', listId] })
                  queryClient.invalidateQueries({ queryKey: ['lists'] })
                  navigate('/lists')
                })
              }
            }}
            style={deleteBtnStyle}
          >
            Excluir lista
          </button>
        </div>
      )}

      {/* Invite member modal */}
      {showInvite && (
        <InviteMemberModal listId={listId!} onClose={() => setShowInvite(false)} />
      )}
    </div>
  )
}

// ── Styles ──────────────────────────────────────────────────────────────────

const headerStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  padding: '20px 16px 12px',
  borderBottom: '1px solid #f3f4f6',
}

const tabsStyle: React.CSSProperties = {
  display: 'flex',
  padding: '8px 16px',
  gap: '8px',
  borderBottom: '1px solid #f3f4f6',
}

const tabBtn = (active: boolean): React.CSSProperties => ({
  padding: '6px 16px',
  borderRadius: '99px',
  border: 'none',
  background: active ? '#6366f1' : '#f3f4f6',
  color: active ? '#fff' : '#6b7280',
  fontWeight: active ? 700 : 400,
  fontSize: '14px',
  cursor: 'pointer',
  transition: 'all 0.15s',
})

const addFormStyle: React.CSSProperties = {
  display: 'flex',
  gap: '8px',
  padding: '12px 16px',
  borderBottom: '1px solid #f3f4f6',
}

const inputStyle: React.CSSProperties = {
  flex: 1,
  padding: '8px 12px',
  border: '1.5px solid #e5e7eb',
  borderRadius: '8px',
  fontSize: '14px',
  outline: 'none',
}

const addBtnStyle: React.CSSProperties = {
  width: '36px',
  height: '36px',
  borderRadius: '8px',
  background: '#6366f1',
  color: '#fff',
  border: 'none',
  fontSize: '20px',
  fontWeight: 700,
  cursor: 'pointer',
  flexShrink: 0,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
}

const totalBarStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: '8px',
  padding: '14px 16px',
  background: '#f9fafb',
  borderTop: '1px solid #f3f4f6',
  fontSize: '15px',
}

const archiveBtnStyle: React.CSSProperties = {
  background: '#f0fdf4',
  color: '#16a34a',
  border: '1.5px solid #bbf7d0',
  borderRadius: '10px',
  padding: '10px 24px',
  fontWeight: 600,
  fontSize: '14px',
  cursor: 'pointer',
}

const deleteBtnStyle: React.CSSProperties = {
  background: 'transparent',
  color: '#dc2626',
  border: '1.5px solid #fecaca',
  borderRadius: '10px',
  padding: '8px 20px',
  fontWeight: 600,
  fontSize: '13px',
  cursor: 'pointer',
}

const backBtn: React.CSSProperties = {
  background: 'none',
  border: 'none',
  fontSize: '26px',
  color: '#6b7280',
  cursor: 'pointer',
  padding: '0 4px',
  lineHeight: 1,
  marginTop: '1px',
}

const inviteBtn: React.CSSProperties = {
  background: '#f5f3ff',
  color: '#6366f1',
  border: '1.5px solid #c7d2fe',
  borderRadius: '8px',
  padding: '5px 10px',
  fontSize: '12px',
  fontWeight: 600,
  cursor: 'pointer',
  whiteSpace: 'nowrap',
  marginLeft: '6px',
}
