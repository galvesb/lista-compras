import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { itemsApi } from '../api/items'
import { useAuth } from '../context/AuthContext'
import { Avatar } from './Avatar'
import { CheckModal } from './CheckModal'
import type { ListItem, Member } from '../types'

interface ListItemRowProps {
  item: ListItem
  listId: string
  isOwner: boolean
  members: Member[]
}

export function ListItemRow({ item, listId, isOwner, members }: ListItemRowProps) {
  const [showCheckModal, setShowCheckModal] = useState(false)
  const [showAssignMenu, setShowAssignMenu] = useState(false)
  const queryClient = useQueryClient()
  const { user } = useAuth()

  // Update item em ambos os caches com lógica filter-aware para 'mine'
  const updateItemInCache = (updated: ListItem) => {
    // cache 'all': update in-place (item sempre existe aqui)
    queryClient.setQueryData<ListItem[]>(
      ['list', listId, 'items', 'all'],
      (old) => old?.map((i) => (i.id === updated.id ? updated : i))
    )

    // cache 'mine': add se agora é meu, update se já estava, remove se deixou de ser
    queryClient.setQueryData<ListItem[]>(
      ['list', listId, 'items', 'mine'],
      (old = []) => {
        const isNowMine = updated.assigned_to?.user_id === user?.id
        const alreadyInMine = old.some((i) => i.id === updated.id)

        if (isNowMine && !alreadyInMine) return [...old, updated]
        if (isNowMine && alreadyInMine) return old.map((i) => (i.id === updated.id ? updated : i))
        return old.filter((i) => i.id !== updated.id)
      }
    )
  }

  const removeItemFromCache = (itemId: string) => {
    for (const f of ['all', 'mine'] as const) {
      queryClient.setQueryData<ListItem[]>(
        ['list', listId, 'items', f],
        (old) => old?.filter((i) => i.id !== itemId)
      )
    }
  }

  const updateMutation = useMutation({
    mutationFn: (payload: { version: number; status?: ListItem['status']; price?: number }) =>
      itemsApi.update(listId, item.id, payload),
    onSuccess: (updated) => updateItemInCache(updated),
    onError: (err: any) => {
      if (err.response?.status === 409) {
        queryClient.invalidateQueries({ queryKey: ['list', listId, 'items'] })
        alert('Este item foi atualizado por outra pessoa. A lista foi recarregada — tente novamente.')
      }
    },
  })

  const assignMutation = useMutation({
    mutationFn: (userId: string | null) => itemsApi.assign(listId, item.id, userId),
    onSuccess: (updated) => {
      updateItemInCache(updated)
      setShowAssignMenu(false)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: () => itemsApi.delete(listId, item.id),
    onSuccess: () => removeItemFromCache(item.id),
  })

  const handleCheckboxClick = () => {
    if (item.status === 'checked') {
      updateMutation.mutate({ version: item.version, status: 'pending' })
    } else {
      setShowCheckModal(true)
    }
  }

  const handleUnavailable = () => {
    const nextStatus = item.status === 'unavailable' ? 'pending' : 'unavailable'
    updateMutation.mutate({ version: item.version, status: nextStatus })
  }

  const handleConfirmCheck = (price: number | undefined) => {
    setShowCheckModal(false)
    updateMutation.mutate({ version: item.version, status: 'checked', price })
  }

  const isChecked = item.status === 'checked'
  const isUnavailable = item.status === 'unavailable'
  const isPending = updateMutation.isPending || assignMutation.isPending

  return (
    <>
      <div style={{ ...rowStyle, opacity: isUnavailable ? 0.55 : 1 }}>
        {/* Checkbox */}
        <button
          onClick={handleCheckboxClick}
          disabled={isPending}
          style={checkboxStyle(isChecked)}
          aria-label={isChecked ? 'Desmarcar item' : 'Marcar como comprado'}
        >
          {isChecked && '✓'}
        </button>

        {/* Item info */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{
              fontSize: '15px', fontWeight: 500,
              textDecoration: isChecked || isUnavailable ? 'line-through' : 'none',
              color: isChecked ? '#9ca3af' : '#111827',
              whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
            }}>
              {item.name}
            </span>
            <span style={{ fontSize: '13px', color: '#9ca3af', flexShrink: 0 }}>
              {item.quantity}
            </span>
          </div>

          {/* Price row */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '2px' }}>
            {isChecked && item.price != null && (
              <span style={{ fontSize: '13px', color: '#16a34a', fontWeight: 600 }}>
                R$ {item.price.toFixed(2).replace('.', ',')}
              </span>
            )}
            {!isChecked && item.last_price != null && (
              <span style={{ fontSize: '11px', color: '#d1d5db' }}>
                ~R$ {item.last_price.toFixed(2).replace('.', ',')}
              </span>
            )}
          </div>
        </div>

        {/* Assigned user avatar — clickable for owner to reassign */}
        {item.assigned_to ? (
          <div
            onClick={() => isOwner && setShowAssignMenu(true)}
            style={{ cursor: isOwner ? 'pointer' : 'default' }}
            title={isOwner ? `Atribuído a ${item.assigned_to.name} — clique para reatribuir` : `Atribuído a ${item.assigned_to.name}`}
          >
            <Avatar user={item.assigned_to} size="sm" />
          </div>
        ) : isOwner ? (
          <button
            onClick={() => setShowAssignMenu(true)}
            style={assignBtn}
            title="Atribuir a um colaborador"
          >
            👤
          </button>
        ) : null}

        {/* Status chip */}
        {isUnavailable && (
          <span style={unavailableChip}>Indisponível</span>
        )}

        {/* Unavailable toggle */}
        <button
          onClick={handleUnavailable}
          style={iconBtn}
          title={isUnavailable ? 'Marcar como pendente' : 'Marcar como indisponível'}
          disabled={isChecked || isPending}
        >
          ✕
        </button>

        {/* Delete (owner only) */}
        {isOwner && (
          <button
            onClick={() => { if (confirm(`Remover "${item.name}"?`)) deleteMutation.mutate() }}
            style={{ ...iconBtn, color: '#fca5a5' }}
            title="Remover item"
            disabled={deleteMutation.isPending}
          >
            🗑
          </button>
        )}
      </div>

      {/* Assign member dropdown */}
      {showAssignMenu && (
        <div style={assignOverlay} onClick={(e) => { if (e.target === e.currentTarget) setShowAssignMenu(false) }}>
          <div style={assignCard}>
            <p style={{ margin: '0 0 12px', fontWeight: 600, fontSize: '15px' }}>
              Atribuir "{item.name}" a:
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              {members.map((m) => (
                <button
                  key={m.user_id}
                  onClick={() => assignMutation.mutate(m.user_id)}
                  disabled={assignMutation.isPending}
                  style={{
                    ...memberItem,
                    background: item.assigned_to?.user_id === m.user_id ? '#f0f9ff' : '#fff',
                    fontWeight: item.assigned_to?.user_id === m.user_id ? 700 : 400,
                  }}
                >
                  <div style={miniAvatar}>{m.name.charAt(0).toUpperCase()}</div>
                  <div style={{ textAlign: 'left' }}>
                    <p style={{ margin: 0, fontSize: '14px' }}>{m.name}</p>
                    <p style={{ margin: 0, fontSize: '11px', color: '#9ca3af' }}>{m.role === 'owner' ? 'Dono' : 'Colaborador'}</p>
                  </div>
                  {item.assigned_to?.user_id === m.user_id && (
                    <span style={{ marginLeft: 'auto', color: '#6366f1', fontSize: '13px' }}>✓</span>
                  )}
                </button>
              ))}
              {item.assigned_to && (
                <button
                  onClick={() => assignMutation.mutate(null)}
                  disabled={assignMutation.isPending}
                  style={{ ...memberItem, color: '#9ca3af', justifyContent: 'center' }}
                >
                  Remover atribuição
                </button>
              )}
            </div>
            <button onClick={() => setShowAssignMenu(false)} style={cancelAssignBtn}>Fechar</button>
          </div>
        </div>
      )}

      {showCheckModal && (
        <CheckModal
          item={item}
          onConfirm={handleConfirmCheck}
          onCancel={() => setShowCheckModal(false)}
        />
      )}
    </>
  )
}

// ── Styles ───────────────────────────────────────────────────────────────────

const rowStyle: React.CSSProperties = {
  display: 'flex', alignItems: 'center', gap: '10px',
  padding: '12px 16px', borderBottom: '1px solid #f3f4f6',
  background: '#fff', transition: 'opacity 0.2s',
}

const checkboxStyle = (checked: boolean): React.CSSProperties => ({
  width: '24px', height: '24px', borderRadius: '6px',
  border: checked ? 'none' : '2px solid #d1d5db',
  background: checked ? '#6366f1' : 'transparent',
  color: '#fff', fontSize: '14px', fontWeight: 700, cursor: 'pointer',
  display: 'flex', alignItems: 'center', justifyContent: 'center',
  flexShrink: 0, transition: 'background 0.15s',
})

const unavailableChip: React.CSSProperties = {
  fontSize: '11px', padding: '2px 8px', borderRadius: '99px',
  background: '#fee2e2', color: '#dc2626', fontWeight: 600, flexShrink: 0,
}

const iconBtn: React.CSSProperties = {
  background: 'transparent', border: 'none', color: '#d1d5db',
  cursor: 'pointer', fontSize: '14px', padding: '4px', flexShrink: 0,
}

const assignBtn: React.CSSProperties = {
  background: '#f5f3ff', border: '1px dashed #c7d2fe',
  borderRadius: '50%', width: '28px', height: '28px',
  fontSize: '12px', cursor: 'pointer', flexShrink: 0,
  display: 'flex', alignItems: 'center', justifyContent: 'center',
}

const assignOverlay: React.CSSProperties = {
  position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)',
  display: 'flex', alignItems: 'center', justifyContent: 'center',
  padding: '16px', zIndex: 50,
}

const assignCard: React.CSSProperties = {
  background: '#fff', borderRadius: '16px', padding: '20px',
  width: '100%', maxWidth: '340px', boxShadow: '0 8px 32px rgba(0,0,0,0.15)',
}

const memberItem: React.CSSProperties = {
  display: 'flex', alignItems: 'center', gap: '10px',
  padding: '10px 12px', borderRadius: '10px', border: 'none',
  cursor: 'pointer', width: '100%', transition: 'background 0.1s',
}

const miniAvatar: React.CSSProperties = {
  width: '32px', height: '32px', borderRadius: '50%',
  background: '#6366f1', color: '#fff',
  display: 'flex', alignItems: 'center', justifyContent: 'center',
  fontWeight: 700, fontSize: '13px', flexShrink: 0,
}

const cancelAssignBtn: React.CSSProperties = {
  marginTop: '12px', width: '100%', padding: '10px',
  background: 'transparent', border: '1.5px solid #e5e7eb',
  borderRadius: '8px', cursor: 'pointer', color: '#6b7280', fontSize: '14px',
}
