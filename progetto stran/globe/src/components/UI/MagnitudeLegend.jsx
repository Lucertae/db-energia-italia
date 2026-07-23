import { memo } from 'react'
import { motion } from 'motion/react'
import useStore from '../../store/useStore'

const LEGEND_ITEMS = [
  { label: '7+', color: '#dc2626', size: 10 },
  { label: '6+', color: '#ef4444', size: 8 },
  { label: '4.5+', color: '#f97316', size: 6 },
  { label: '3+', color: '#facc15', size: 5 },
  { label: '2+', color: '#4ade80', size: 4 },
  { label: '<2', color: '#22d3ee', size: 3 },
]

const MagnitudeLegend = memo(function MagnitudeLegend() {
  const globeReady = useStore((s) => s.ui.globeReady)
  if (!globeReady) return null

  return (
    <motion.div
      className="mag-legend"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.6, delay: 1.0 }}
    >
      <span className="mag-legend-title">Magnitude</span>
      <div className="mag-legend-items">
        {LEGEND_ITEMS.map((item) => (
          <div key={item.label} className="mag-legend-item">
            <span
              className="mag-legend-dot"
              style={{
                backgroundColor: item.color,
                width: item.size,
                height: item.size,
                boxShadow: `0 0 ${item.size}px ${item.color}40`,
              }}
            />
            <span className="mag-legend-label">{item.label}</span>
          </div>
        ))}
      </div>
    </motion.div>
  )
})

export default MagnitudeLegend
