import { memo } from 'react'
import { getMagnitudeColor } from '../../utils/magnitudeScale'

const MagnitudeBadge = memo(function MagnitudeBadge({ magnitude, size = 'md' }) {
  const color = getMagnitudeColor(magnitude)
  const sizeClass = size === 'lg' ? 'mag-badge--lg' : 'mag-badge--md'

  return (
    <span
      className={`mag-badge ${sizeClass}`}
      style={{
        backgroundColor: `${color}15`,
        color: color,
      }}
    >
      {magnitude.toFixed(1)}
    </span>
  )
})

export default MagnitudeBadge
