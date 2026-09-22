import { useState } from 'react'
import { submitTransaction, getTransaction } from '../api'

const POLL_INTERVAL_MS = 700
const POLL_TIMEOUT_MS = 8000

export default function TransactionForm({ onProcessed }) {
  const [form, setForm] = useState({
    transaction_id: '',
    customer_id: 'CUST001',
    amount: '',
    currency: 'INR',
    type: 'DEBIT',
  })
  const [status, setStatus] = useState(null) // 'submitting' | 'processing' | 'done'
  const [error, setError] = useState(null)
  const [result, setResult] = useState(null)

  function handleChange(e) {
    const { name, value } = e.target
    setForm((f) => ({ ...f, [name]: value }))
  }

  function setType(type) {
    setForm((f) => ({ ...f, type }))
  }

  async function pollUntilTerminal(transactionId) {
    const deadline = Date.now() + POLL_TIMEOUT_MS
    while (Date.now() < deadline) {
      const txn = await getTransaction(transactionId)
      if (txn.status === 'SUCCESS' || txn.status === 'FAILED') {
        return txn
      }
      await new Promise((r) => setTimeout(r, POLL_INTERVAL_MS))
    }
    throw new Error('Timed out waiting for transaction to finish processing')
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError(null)
    setResult(null)

    if (!form.transaction_id.trim() || !form.customer_id.trim()) {
      setError('Transaction ID and Customer ID are required')
      return
    }
    const amountNum = Number(form.amount)
    if (!form.amount || Number.isNaN(amountNum)) {
      setError('Amount must be a valid number')
      return
    }

    setStatus('submitting')
    try {
      const created = await submitTransaction({
        transaction_id: form.transaction_id.trim(),
        customer_id: form.customer_id.trim(),
        amount: amountNum,
        currency: form.currency,
        type: form.type,
      })

      if (created.status === 'SUCCESS' || created.status === 'FAILED') {
        setResult(created)
        setStatus('done')
        onProcessed?.(created)
        return
      }

      setStatus('processing')
      const final = await pollUntilTerminal(created.transaction_id)
      setResult(final)
      setStatus('done')
      onProcessed?.(final)
    } catch (err) {
      setError(err.message)
      setStatus('done')
    }
  }

  const isBusy = status === 'submitting' || status === 'processing'

  return (
    <div className="panel">
      <h2>Submit Transaction</h2>
      <form onSubmit={handleSubmit} data-testid="transaction-form">
        <div className="field-row">
          <label>
            Customer ID
            <input name="customer_id" value={form.customer_id} onChange={handleChange} placeholder="CUST001" />
          </label>
          <label>
            Transaction ID
            <input name="transaction_id" value={form.transaction_id} onChange={handleChange} placeholder="TXN1001" />
          </label>
        </div>

        <div className="field-row">
          <label>
            Amount
            <input name="amount" type="number" step="0.01" value={form.amount} onChange={handleChange} placeholder="500" />
          </label>
          <label>
            Currency
            <input name="currency" value={form.currency} onChange={handleChange} />
          </label>
        </div>

        <label>
          Type
          <div className="segmented" role="radiogroup" aria-label="Transaction type">
            <button
              type="button"
              className={form.type === 'DEBIT' ? 'active debit' : ''}
              onClick={() => setType('DEBIT')}
              aria-pressed={form.type === 'DEBIT'}
            >
              − DEBIT
            </button>
            <button
              type="button"
              className={form.type === 'CREDIT' ? 'active credit' : ''}
              onClick={() => setType('CREDIT')}
              aria-pressed={form.type === 'CREDIT'}
            >
              + CREDIT
            </button>
          </div>
        </label>

        <button type="submit" className="submit-button" disabled={isBusy}>
          {isBusy && <span className="spinner" />}
          {status === 'submitting' ? 'Submitting…' : status === 'processing' ? 'Processing…' : 'Submit Transaction'}
        </button>
      </form>

      {error && <p className="error" role="alert">{error}</p>}
      {result && (
        <div className={`result ${result.status === 'SUCCESS' ? 'success' : 'failed'}`} data-testid="transaction-result">
          <strong>{result.status}</strong>
          {result.failure_reason && <div>{result.failure_reason}</div>}
          <div className="muted">Attempts: {result.processing_attempts}</div>
        </div>
      )}
    </div>
  )
}
