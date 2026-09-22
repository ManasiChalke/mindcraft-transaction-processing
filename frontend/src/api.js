const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

async function request(path, options) {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  const contentType = res.headers.get('content-type') || ''
  const body = contentType.includes('application/json') ? await res.json() : null

  if (!res.ok) {
    const message = (body && (body.detail || body.failure_reason)) || `Request failed with status ${res.status}`
    throw new Error(typeof message === 'string' ? message : JSON.stringify(message))
  }
  return body
}

export function submitTransaction(payload) {
  return request('/transactions', { method: 'POST', body: JSON.stringify(payload) })
}

export function getTransaction(transactionId) {
  return request(`/transactions/${encodeURIComponent(transactionId)}`)
}

export function getBalance(customerId) {
  return request(`/customers/${encodeURIComponent(customerId)}/balance`)
}

export function getTransactionHistory(customerId, page = 1, pageSize = 10) {
  return request(`/customers/${encodeURIComponent(customerId)}/transactions?page=${page}&page_size=${pageSize}`)
}

export function getHealth() {
  return request('/health')
}
