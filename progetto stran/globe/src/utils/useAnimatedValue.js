import { useState, useEffect, useRef } from 'react'

export function useAnimatedValue(target) {
  const [display, setDisplay] = useState(target)
  const rafRef = useRef(null)
  const currentRef = useRef(target)

  useEffect(() => {
    const start = currentRef.current
    const diff = target - start
    if (Math.abs(diff) < 1) { setDisplay(target); currentRef.current = target; return }
    const startTime = performance.now()
    const duration = 400

    const animate = (now) => {
      const t = Math.min((now - startTime) / duration, 1)
      const eased = 1 - Math.pow(1 - t, 3)
      const val = Math.round(start + diff * eased)
      if (t >= 1) {
        setDisplay(target)
        currentRef.current = target
        return
      }
      setDisplay(val)
      currentRef.current = val
      rafRef.current = requestAnimationFrame(animate)
    }

    rafRef.current = requestAnimationFrame(animate)
    return () => { if (rafRef.current) cancelAnimationFrame(rafRef.current) }
  }, [target])

  return display
}
