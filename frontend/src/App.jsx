import { useState } from 'react'
import TransactionForm from './components/TransactionForm.jsx'
import BalanceCard from './components/BalanceCard.jsx'
import TransactionHistory from './components/TransactionHistory.jsx'
import HealthBadge from './components/HealthBadge.jsx'

export default function App() {
  const [customerId, setCustomerId] = useState('CUST001')
  const [refreshKey, setRefreshKey] = useState(0)

  function handleProcessed(txn) {
    setCustomerId(txn.customer_id)
    setRefreshKey((k) => k + 1)
  }

  return (
    <div className="app">
      <header className="app-header">
        <div className="brand">
          <span className="brand-mark">TP</span>
          <div>
            <h1>Transaction Processor</h1>
            <p className="brand-subtitle">Async validation, retries &amp; concurrency-safe balances</p>
          </div>
        </div>
        <HealthBadge />
      </header>

      <section className="hero">
        <label className="customer-picker">
          <span>Customer</span>
          <input value={customerId} onChange={(e) => setCustomerId(e.target.value)} placeholder="CUST001" />
        </label>
        <BalanceCard customerId={customerId} refreshKey={refreshKey} />
      </section>

      <main className="layout">
        <TransactionForm onProcessed={handleProcessed} />
        <TransactionHistory customerId={customerId} refreshKey={refreshKey} />
      </main>
    </div>
  )
}
