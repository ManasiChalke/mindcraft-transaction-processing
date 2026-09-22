import { useEffect, useState } from 'react'
import { getHealth } from '../api'

const POLL_MS = 8000

export default function HealthBadge() {
  const [online, setOnline] = useState(null)
  const [queueSize, setQueueSize] = useState(0)

  useEffect(() => {
    let cancelled = false

    async function check() {
      try {
        const health = await getHealth()
        if (!cancelled) {
          setOnline(true)
          setQueueSize(health.queue_size)
        }
      } catch {
        if (!cancelled) setOnline(false)
      }
    }

    check()
    const interval = setInterval(check, POLL_MS)
    return () => {
      cancelled = true
      clearInterval(interval)
    }
  }, [])

  if (online === null) return null

  return (
    <div className={`health-badge ${online ? 'online' : 'offline'}`} data-testid="health-badge">
      <span className="health-dot" />
      {online ? `API online${queueSize ? ` · ${queueSize} queued` : ''}` : 'API unreachable'}
    </div>
  )
}
