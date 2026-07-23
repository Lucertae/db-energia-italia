import { useState, useEffect, memo } from 'react'
import useStore from '../../store/useStore'
import { timeAgo } from '../../utils/formatters'

const LastUpdated = memo(function LastUpdated() {
  const lastUpdated = useStore((s) => s.lastUpdated)
  const [, forceUpdate] = useState(0)

  useEffect(() => {
    const interval = setInterval(() => forceUpdate((n) => n + 1), 10000)
    return () => clearInterval(interval)
  }, [])

  if (!lastUpdated) return null

  return (
    <div className="last-updated mono">
      USGS data {timeAgo(lastUpdated)}
    </div>
  )
})

export default LastUpdated
