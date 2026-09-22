import { useEffect, useState, useCallback } from 'react'
import { getBalance } from '../api'

export default function BalanceCard({ customerId, refreshKey }) {
  const [balance, setBalance] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  const load = useCallback(async () => {
    if (!customerId) return
    setLoading(true)
    setError(null)
    try {
      const data = await getBalance(customerId)
      setBalance(data)
    } catch (err) {
      setError(err.message)
      setBalance(null)
    } finally {
      setLoading(false)
    }
  }, [customerId])

  useEffect(() => {
    load()
  }, [load, refreshKey])

  return (
    <div className="balance-tile">
      <div className="balance-tile-label">
        <span>Current Balance</span>
        <button className="icon-button" onClick={load} disabled={loading} aria-label="Refresh balance" title="Refresh">
          <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M21 12a9 9 0 1 1-2.64-6.36" strokeLinecap="round" />
            <path d="M21 4v6h-6" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
      </div>

      {loading && !balance && <div className="balance-amount skeleton">Loading…</div>}
      {error && <p className="error" role="alert">{error}</p>}
      {balance && (
        <div data-testid="balance-display">
          <div className="balance-amount">
            {balance.balance.toLocaleString()} <span className="balance-currency">{balance.currency}</span>
          </div>
          <div className="muted">{balance.customer_id}</div>
        </div>
      )}
    </div>
  )
}
