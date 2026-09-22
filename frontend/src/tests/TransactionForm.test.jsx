import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import TransactionForm from '../components/TransactionForm.jsx'
import * as api from '../api.js'

describe('TransactionForm', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('shows a validation error and never calls the API when required fields are missing', async () => {
    const submitSpy = vi.spyOn(api, 'submitTransaction')
    render(<TransactionForm />)

    fireEvent.click(screen.getByRole('button', { name: /submit transaction/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent(/transaction id and customer id are required/i)
    expect(submitSpy).not.toHaveBeenCalled()
  })

  it('submits a transaction and displays the terminal SUCCESS result', async () => {
    vi.spyOn(api, 'submitTransaction').mockResolvedValue({
      transaction_id: 'TXN1',
      customer_id: 'CUST001',
      status: 'SUCCESS',
      failure_reason: null,
      processing_attempts: 1,
    })
    const onProcessed = vi.fn()

    render(<TransactionForm onProcessed={onProcessed} />)

    fireEvent.change(screen.getByPlaceholderText('TXN1001'), { target: { value: 'TXN1' } })
    fireEvent.change(screen.getByPlaceholderText('500'), { target: { value: '100' } })
    fireEvent.click(screen.getByRole('button', { name: /submit transaction/i }))

    const result = await screen.findByTestId('transaction-result')
    expect(result).toHaveTextContent('SUCCESS')
    expect(onProcessed).toHaveBeenCalledWith(expect.objectContaining({ transaction_id: 'TXN1', status: 'SUCCESS' }))
  })

  it('displays the failure reason for a FAILED transaction', async () => {
    vi.spyOn(api, 'submitTransaction').mockResolvedValue({
      transaction_id: 'TXN2',
      customer_id: 'CUST001',
      status: 'FAILED',
      failure_reason: 'Insufficient balance',
      processing_attempts: 1,
    })

    render(<TransactionForm />)

    fireEvent.change(screen.getByPlaceholderText('TXN1001'), { target: { value: 'TXN2' } })
    fireEvent.change(screen.getByPlaceholderText('500'), { target: { value: '999999' } })
    fireEvent.click(screen.getByRole('button', { name: /submit transaction/i }))

    const result = await screen.findByTestId('transaction-result')
    expect(result).toHaveTextContent('FAILED')
    expect(result).toHaveTextContent('Insufficient balance')
  })

  it('surfaces API errors returned as rejected promises', async () => {
    vi.spyOn(api, 'submitTransaction').mockRejectedValue(new Error('Network error'))

    render(<TransactionForm />)

    fireEvent.change(screen.getByPlaceholderText('TXN1001'), { target: { value: 'TXN3' } })
    fireEvent.change(screen.getByPlaceholderText('500'), { target: { value: '100' } })
    fireEvent.click(screen.getByRole('button', { name: /submit transaction/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Network error')
  })
})
