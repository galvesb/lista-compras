import { useState, useEffect } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'

interface UserResult {
  id: string
  name: string
  email: string
  avatar_url: string | null
}

interface Props {
  listId: string
  onClose: () => void
}

export function InviteMemberModal({ listId, onClose }: Props) {
  const queryClient = useQueryClient()
  const [emailQuery, setEmailQuery] = useState('')
  const [results, setResults] = useState<UserResult[]>([])
  const [searching, setSearching] = useState(false)
  const [selected, setSelected] = useState<UserResult | null>(null)
  const [successMsg, setSuccessMsg] = useState('')
  const [errorMsg, setErrorMsg] = useState('')

  // Debounced search
  useEffect(() => {
    if (emailQuery.length < 3) {
      setResults([])
      return
    }
    const timer = setTimeout(async () => {
      setSearching(true)
      try {
        const { data } = await api.get<UserResult[]>(`/users/search?email=${encodeURIComponent(emailQuery)}`)
        setResults(data)
      } catch {
        setResults([])
      } finally {
        setSearching(false)
      }
    }, 400)
    return () => clearTimeout(timer)
  }, [emailQuery])

  const inviteMutation = useMutation({
    mutationFn: (email: string) =>
      api.post(`/lists/${listId}/members`, { email }).then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['list', listId] })
      setSuccessMsg(`${selected?.name} foi convidado(a) com sucesso!`)
      setSelected(null)
      setEmailQuery('')
      setResults([])
      setErrorMsg('')
    },
    onError: (err: any) => {
      const detail = err.response?.data?.detail
      if (err.response?.status === 409) {
        setErrorMsg('Usuário já é membro desta lista.')
      } else if (err.response?.status === 404) {
        setErrorMsg('Usuário não encontrado.')
      } else {
        setErrorMsg(typeof detail === 'string' ? detail : 'Erro ao convidar.')
      }
    },
  })

  const handleInvite = () => {
    if (!selected) return
    setErrorMsg('')
    setSuccessMsg('')
    inviteMutation.mutate(selected.email)
  }

  return (
    <div style={overlay} onClick={(e) => { if (e.target === e.currentTarget) onClose() }}>
      <div style={card}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <h3 style={{ margin: 0, fontSize: '17px' }}>Convidar Membro</h3>
          <button onClick={onClose} style={closeBtn}>✕</button>
        </div>

        <input
          type="email"
          placeholder="Buscar por email..."
          value={emailQuery}
          onChange={(e) => { setEmailQuery(e.target.value); setSelected(null); setSuccessMsg(''); setErrorMsg('') }}
          autoFocus
          style={inputStyle}
        />

        {/* Search results */}
        {searching && (
          <p style={hintStyle}>Buscando...</p>
        )}
        {!searching && emailQuery.length >= 3 && results.length === 0 && !selected && (
          <p style={hintStyle}>Nenhum usuário encontrado.</p>
        )}
        {results.length > 0 && !selected && (
          <div style={resultList}>
            {results.map((u) => (
              <button
                key={u.id}
                onClick={() => { setSelected(u); setResults([]) }}
                style={resultItem}
              >
                <div style={avatar}>{u.name.charAt(0).toUpperCase()}</div>
                <div>
                  <p style={{ margin: 0, fontWeight: 600, fontSize: '14px' }}>{u.name}</p>
                  <p style={{ margin: 0, fontSize: '12px', color: '#6b7280' }}>{u.email}</p>
                </div>
              </button>
            ))}
          </div>
        )}

        {/* Selected user confirmation */}
        {selected && (
          <div style={selectedBox}>
            <div style={avatar}>{selected.name.charAt(0).toUpperCase()}</div>
            <div style={{ flex: 1 }}>
              <p style={{ margin: 0, fontWeight: 600, fontSize: '14px' }}>{selected.name}</p>
              <p style={{ margin: 0, fontSize: '12px', color: '#6b7280' }}>{selected.email}</p>
            </div>
            <button onClick={() => setSelected(null)} style={closeBtn}>✕</button>
          </div>
        )}

        {errorMsg && <p style={{ color: '#dc2626', fontSize: '13px', margin: '8px 0 0' }}>{errorMsg}</p>}
        {successMsg && <p style={{ color: '#16a34a', fontSize: '13px', margin: '8px 0 0' }}>{successMsg}</p>}

        <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end', marginTop: '16px' }}>
          <button onClick={onClose} style={cancelBtn}>Fechar</button>
          <button
            onClick={handleInvite}
            disabled={!selected || inviteMutation.isPending}
            style={{ ...confirmBtn, opacity: !selected ? 0.5 : 1 }}
          >
            {inviteMutation.isPending ? 'Convidando...' : 'Convidar'}
          </button>
        </div>
      </div>
    </div>
  )
}

const overlay: React.CSSProperties = {
  position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.45)',
  display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '16px', zIndex: 50,
}
const card: React.CSSProperties = {
  background: '#fff', borderRadius: '16px', padding: '24px',
  width: '100%', maxWidth: '380px', boxShadow: '0 8px 32px rgba(0,0,0,0.15)',
}
const inputStyle: React.CSSProperties = {
  width: '100%', boxSizing: 'border-box', padding: '10px 12px',
  border: '1.5px solid #e5e7eb', borderRadius: '8px', fontSize: '15px', outline: 'none',
}
const hintStyle: React.CSSProperties = {
  fontSize: '13px', color: '#9ca3af', margin: '8px 0 0', textAlign: 'center',
}
const resultList: React.CSSProperties = {
  marginTop: '8px', border: '1px solid #f3f4f6', borderRadius: '10px', overflow: 'hidden',
}
const resultItem: React.CSSProperties = {
  display: 'flex', alignItems: 'center', gap: '12px', width: '100%',
  padding: '10px 14px', background: '#fff', border: 'none', borderBottom: '1px solid #f3f4f6',
  cursor: 'pointer', textAlign: 'left',
}
const selectedBox: React.CSSProperties = {
  display: 'flex', alignItems: 'center', gap: '12px', marginTop: '8px',
  padding: '10px 14px', background: '#f0f9ff', border: '1.5px solid #bae6fd',
  borderRadius: '10px',
}
const avatar: React.CSSProperties = {
  width: '36px', height: '36px', borderRadius: '50%', background: '#6366f1',
  color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center',
  fontWeight: 700, fontSize: '15px', flexShrink: 0,
}
const closeBtn: React.CSSProperties = {
  background: 'none', border: 'none', color: '#9ca3af', cursor: 'pointer',
  fontSize: '16px', padding: '4px', lineHeight: 1,
}
const cancelBtn: React.CSSProperties = {
  background: 'transparent', color: '#6b7280', border: '1.5px solid #d1d5db',
  borderRadius: '8px', padding: '9px 16px', cursor: 'pointer', fontSize: '14px',
}
const confirmBtn: React.CSSProperties = {
  background: '#6366f1', color: '#fff', border: 'none',
  borderRadius: '8px', padding: '9px 20px', fontWeight: 600, cursor: 'pointer', fontSize: '14px',
}
