import { useRef, useState } from 'react'
import type { ListItem } from '../types'

interface CheckModalProps {
  item: ListItem
  onConfirm: (price: number | undefined) => void
  onCancel: () => void
}

/**
 * Modal shown when user taps the checkbox on a pending item.
 * Optionally collects price before confirming the check.
 */
export function CheckModal({ item, onConfirm, onCancel }: CheckModalProps) {
  const [priceInput, setPriceInput] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  const handleConfirm = () => {
    const price = priceInput.trim() ? parseFloat(priceInput.replace(',', '.')) : undefined
    if (price !== undefined && (isNaN(price) || price < 0)) return
    onConfirm(price)
  }

  return (
    <div style={overlay}>
      <div style={card}>
        <h3 style={{ margin: '0 0 4px' }}>Marcar como comprado</h3>
        <p style={{ margin: '0 0 16px', color: '#6b7280', fontSize: '14px' }}>
          <strong>{item.name}</strong> · {item.quantity}
        </p>

        <label style={labelStyle}>
          Preço pago (opcional)
        </label>
        <div style={{ position: 'relative', marginBottom: '20px' }}>
          <span style={currencyPrefix}>R$</span>
          <input
            ref={inputRef}
            type="number"
            min="0"
            step="0.01"
            placeholder="0,00"
            value={priceInput}
            onChange={(e) => setPriceInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleConfirm()}
            style={priceInput_style}
            autoFocus
          />
        </div>

        {item.last_price != null && (
          <p style={lastPriceHint}>
            Na última compra: R$ {item.last_price.toFixed(2).replace('.', ',')}
          </p>
        )}

        <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
          <button onClick={onCancel} style={btnSecondary}>
            Cancelar
          </button>
          <button onClick={handleConfirm} style={btnPrimary}>
            ✓ Confirmar
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Styles ─────────────────────────────────────────────────────────────────

const overlay: React.CSSProperties = {
  position: 'fixed',
  inset: 0,
  background: 'rgba(0,0,0,0.45)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  zIndex: 100,
  padding: '16px',
}

const card: React.CSSProperties = {
  background: '#fff',
  borderRadius: '16px',
  padding: '24px',
  width: '100%',
  maxWidth: '360px',
  boxShadow: '0 20px 40px rgba(0,0,0,0.15)',
}

const labelStyle: React.CSSProperties = {
  display: 'block',
  fontSize: '13px',
  fontWeight: 600,
  color: '#374151',
  marginBottom: '6px',
}

const currencyPrefix: React.CSSProperties = {
  position: 'absolute',
  left: '12px',
  top: '50%',
  transform: 'translateY(-50%)',
  color: '#6b7280',
  fontSize: '14px',
}

const priceInput_style: React.CSSProperties = {
  width: '100%',
  boxSizing: 'border-box',
  padding: '10px 12px 10px 36px',
  border: '1.5px solid #d1d5db',
  borderRadius: '8px',
  fontSize: '16px',
  outline: 'none',
}

const lastPriceHint: React.CSSProperties = {
  fontSize: '12px',
  color: '#9ca3af',
  margin: '-12px 0 16px',
}

const btnPrimary: React.CSSProperties = {
  background: '#6366f1',
  color: '#fff',
  border: 'none',
  borderRadius: '8px',
  padding: '10px 20px',
  fontSize: '14px',
  fontWeight: 600,
  cursor: 'pointer',
}

const btnSecondary: React.CSSProperties = {
  background: 'transparent',
  color: '#6b7280',
  border: '1.5px solid #d1d5db',
  borderRadius: '8px',
  padding: '10px 16px',
  fontSize: '14px',
  cursor: 'pointer',
}
