import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import type { ShoppingList } from '../types'

export function ListsPage() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [tab, setTab] = useState<'active' | 'archived'>('active')
  const [showModal, setShowModal] = useState(false)
  const [storeName, setStoreName] = useState('')
  const [address, setAddress] = useState('')

  const { data: lists = [] } = useQuery<ShoppingList[]>({
    queryKey: ['lists', tab],
    queryFn: () => api.get(`/lists?status=${tab}`).then((r) => r.data),
  })

  const createMutation = useMutation({
    mutationFn: () => api.post<ShoppingList>('/lists', { store_name: storeName, address }).then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['lists'] })
      setShowModal(false)
      setStoreName('')
      setAddress('')
    },
  })

  const reuseMutation = useMutation({
    mutationFn: (listId: string) => api.post<ShoppingList>(`/lists/${listId}/reuse`).then((r) => r.data),
    onSuccess: (newList) => {
      queryClient.invalidateQueries({ queryKey: ['lists'] })
      navigate(`/lists/${newList.id}`)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (listId: string) => api.delete(`/lists/${listId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['lists'] })
    },
  })

  return (
    <div style={{ maxWidth: '600px', margin: '0 auto', paddingBottom: '80px' }}>
      {/* Top bar */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '20px 16px' }}>
        <h1 style={{ margin: 0, fontSize: '20px' }}>🛒 Minhas Listas</h1>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <span style={{ fontSize: '14px', color: '#6b7280' }}>{user?.name}</span>
          <button onClick={logout} style={{ background: 'none', border: 'none', color: '#9ca3af', cursor: 'pointer', fontSize: '13px' }}>
            Sair
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', padding: '0 16px 12px', gap: '8px', borderBottom: '1px solid #f3f4f6' }}>
        <button onClick={() => setTab('active')} style={tabBtn(tab === 'active')}>Ativas</button>
        <button onClick={() => setTab('archived')} style={tabBtn(tab === 'archived')}>Histórico</button>
      </div>

      {/* List */}
      <div style={{ padding: '12px 16px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
        {lists.length === 0 && (
          <p style={{ textAlign: 'center', color: '#9ca3af', padding: '32px 0' }}>
            {tab === 'active' ? 'Nenhuma lista ativa. Crie uma!' : 'Nenhuma compra finalizada ainda.'}
          </p>
        )}
        {lists.map((list) => (
          <div
            key={list.id}
            onClick={() => navigate(`/lists/${list.id}`)}
            style={cardStyle}
          >
            <div style={{ flex: 1 }}>
              <p style={{ margin: 0, fontWeight: 600, fontSize: '15px' }}>{list.store_name}</p>
              <p style={{ margin: '2px 0 0', fontSize: '13px', color: '#9ca3af' }}>
                {new Date(list.created_at).toLocaleDateString('pt-BR')}
                {list.total_cost != null && (
                  <span style={{ color: '#16a34a', fontWeight: 600, marginLeft: '8px' }}>
                    R$ {list.total_cost.toFixed(2).replace('.', ',')}
                  </span>
                )}
              </p>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              {tab === 'archived' && (
                <button
                  onClick={(e) => { e.stopPropagation(); reuseMutation.mutate(list.id) }}
                  style={reuseBtn}
                >
                  Reutilizar
                </button>
              )}
              {/* Botão lixeira — visível APENAS para o dono da lista */}
              {list.role === 'owner' && (
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    if (confirm(`Excluir "${list.store_name}"? Esta ação não pode ser desfeita.`)) {
                      deleteMutation.mutate(list.id)
                    }
                  }}
                  style={deleteCardBtn}
                  title="Excluir lista"
                  disabled={deleteMutation.isPending}
                >
                  🗑
                </button>
              )}
              <span style={{ color: '#d1d5db' }}>›</span>
            </div>
          </div>
        ))}
      </div>

      {/* FAB */}
      {tab === 'active' && (
        <button onClick={() => setShowModal(true)} style={fabStyle}>+</button>
      )}

      {/* Create modal */}
      {showModal && (
        <div style={overlay}>
          <div style={modalCard}>
            <h3 style={{ margin: '0 0 16px' }}>Nova Lista</h3>
            <input
              placeholder="Nome do mercado"
              value={storeName}
              onChange={(e) => setStoreName(e.target.value)}
              style={inputStyle}
            />
            <input
              placeholder="Endereço"
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              style={{ ...inputStyle, marginTop: '8px' }}
            />
            <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end', marginTop: '16px' }}>
              <button onClick={() => setShowModal(false)} style={cancelBtn}>Cancelar</button>
              <button
                onClick={() => createMutation.mutate()}
                disabled={!storeName.trim() || createMutation.isPending}
                style={confirmBtn}
              >
                Criar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

const tabBtn = (active: boolean): React.CSSProperties => ({
  padding: '6px 16px', borderRadius: '99px', border: 'none',
  background: active ? '#6366f1' : '#f3f4f6',
  color: active ? '#fff' : '#6b7280',
  fontWeight: active ? 700 : 400, fontSize: '14px', cursor: 'pointer',
})

const cardStyle: React.CSSProperties = {
  display: 'flex', alignItems: 'center', gap: '12px',
  padding: '14px 16px', background: '#fff', borderRadius: '12px',
  border: '1px solid #f3f4f6', cursor: 'pointer',
  boxShadow: '0 1px 4px rgba(0,0,0,0.04)',
}

const fabStyle: React.CSSProperties = {
  position: 'fixed', bottom: '24px', right: '24px',
  width: '56px', height: '56px', borderRadius: '50%',
  background: '#6366f1', color: '#fff', border: 'none',
  fontSize: '28px', cursor: 'pointer', boxShadow: '0 4px 12px rgba(99,102,241,0.4)',
  display: 'flex', alignItems: 'center', justifyContent: 'center',
}

const overlay: React.CSSProperties = {
  position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)',
  display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '16px',
}

const modalCard: React.CSSProperties = {
  background: '#fff', borderRadius: '16px', padding: '24px',
  width: '100%', maxWidth: '360px',
}

const inputStyle: React.CSSProperties = {
  width: '100%', boxSizing: 'border-box', padding: '10px 12px',
  border: '1.5px solid #e5e7eb', borderRadius: '8px', fontSize: '15px', outline: 'none',
}

const cancelBtn: React.CSSProperties = {
  background: 'transparent', color: '#6b7280', border: '1.5px solid #d1d5db',
  borderRadius: '8px', padding: '9px 16px', cursor: 'pointer',
}

const confirmBtn: React.CSSProperties = {
  background: '#6366f1', color: '#fff', border: 'none',
  borderRadius: '8px', padding: '9px 20px', fontWeight: 600, cursor: 'pointer',
}

const reuseBtn: React.CSSProperties = {
  background: '#f0f9ff', color: '#0369a1', border: '1.5px solid #bae6fd',
  borderRadius: '8px', padding: '4px 10px', fontSize: '12px', fontWeight: 600, cursor: 'pointer',
}

const deleteCardBtn: React.CSSProperties = {
  background: 'transparent', border: 'none', color: '#fca5a5',
  cursor: 'pointer', fontSize: '16px', padding: '4px',
  display: 'flex', alignItems: 'center', justifyContent: 'center',
  flexShrink: 0,
}
