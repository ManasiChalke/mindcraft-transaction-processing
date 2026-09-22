import { useEffect, useState, useCallback } from 'react'
import { getTransactionHistory } from '../api'

const PAGE_SIZE = 5

export default function TransactionHistory({ customerId, refreshKey }) {
  const [data, setData] = useState(null)
  const [page, setPage] = useState(1)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  const load = useCallback(async () => {
    if (!customerId) return
    setLoading(true)
    setError(null)
    try {
      const result = await getTransactionHistory(customerId, page, PAGE_SIZE)
      setData(result)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [customerId, page])

  useEffect(() => {
    load()
  }, [load, refreshKey])

  useEffect(() => {
    setPage(1)
  }, [customerId])

  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1

  return (
    <div className="panel">
      <div className="panel-header">
        <h2>Transaction History</h2>
        {loading && <span className="muted">Refreshing…</span>}
      </div>
      {error && <p className="error" role="alert">{error}</p>}
      {data && (
        <>
          <div className="table-scroll">
            <table data-testid="history-table">
              <thead>
                <tr>
                  <th>Transaction ID</th>
                  <th>Type</th>
                  <th>Amount</th>
                  <th>Status</th>
                  <th>Failure Reason</th>
                  <th>Attempts</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((txn) => (
                  <tr key={txn.transaction_id}>
                    <td className="mono">{txn.transaction_id}</td>
                    <td>
                      <span className={`type-tag ${txn.type.toLowerCase()}`}>{txn.type}</span>
                    </td>
                    <td>{txn.amount.toLocaleString()} {txn.currency}</td>
                    <td>
                      <span className={`badge ${txn.status.toLowerCase()}`}>{txn.status}</span>
                    </td>
                    <td className="muted">{txn.failure_reason || '—'}</td>
                    <td>{txn.processing_attempts}</td>
                  </tr>
                ))}
                {data.items.length === 0 && (
                  <tr>
                    <td colSpan={6} className="muted empty-row">No transactions yet</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          <div className="pagination">
            <button className="ghost-button" onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page <= 1}>Prev</button>
            <span className="muted">Page {page} of {totalPages}</span>
            <button className="ghost-button" onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page >= totalPages}>Next</button>
          </div>
        </>
      )}
    </div>
  )
}
