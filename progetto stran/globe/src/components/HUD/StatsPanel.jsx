import { useMemo, memo } from 'react'
import { motion, AnimatePresence } from 'motion/react'
import GlassPanel from '../UI/GlassPanel'
import MagnitudeBadge from '../UI/MagnitudeBadge'
import useStore from '../../store/useStore'
import useEarthquakeStore from '../../store/useEarthquakeStore'
import { formatDepth, formatNumber } from '../../utils/formatters'
import { useAnimatedValue } from '../../utils/useAnimatedValue'

const AnimatedNumber = ({ value }) => {
  const display = useAnimatedValue(value)
  return <span className="mono">{formatNumber(display)}</span>
}

const StatsPanel = memo(function StatsPanel() {
  const earthquakes = useEarthquakeStore((s) => s.earthquakes)
  const globeReady = useStore((s) => s.ui.globeReady)
  const showStats = useStore((s) => s.ui.showStats)

  const stats = useMemo(() => {
    if (!earthquakes.length) return null

    const largest = earthquakes.reduce((max, q) =>
      q.magnitude > max.magnitude ? q : max, earthquakes[0]
    )

    const deepest = earthquakes.reduce((max, q) =>
      q.depth > max.depth ? q : max, earthquakes[0]
    )

    const regions = {}
    earthquakes.forEach((q) => {
      const region = q.place?.split(' of ').pop()?.trim() || 'Unknown'
      regions[region] = (regions[region] || 0) + 1
    })
    const mostActive = Object.entries(regions)
      .sort((a, b) => b[1] - a[1])[0]

    const avgDepth = earthquakes.reduce((sum, q) => sum + q.depth, 0) / earthquakes.length

    return { largest, deepest, mostActive, avgDepth, total: earthquakes.length }
  }, [earthquakes])

  if (!globeReady || !stats) return null

  const staggerChildren = {
    animate: { transition: { staggerChildren: 0.06 } }
  }

  const fadeUp = {
    initial: { opacity: 0, y: 6 },
    animate: { opacity: 1, y: 0 },
  }

  return (
    <AnimatePresence>
      {showStats && (
        <GlassPanel className="stats-panel" key="stats">
          <motion.div variants={staggerChildren} initial="initial" animate="animate" className="stat-list">
            <motion.h2 className="panel-title" variants={fadeUp}>
              Activity
            </motion.h2>

            <motion.div className="stat-row" variants={fadeUp}>
              <span className="stat-label">Events</span>
              <span className="stat-value-large"><AnimatedNumber value={stats.total} /></span>
            </motion.div>

            <motion.div className="stat-row" variants={fadeUp}>
              <span className="stat-label">Largest</span>
              <span className="stat-value-group">
                <MagnitudeBadge magnitude={stats.largest.magnitude} />
                <span className="stat-location">{stats.largest.place}</span>
              </span>
            </motion.div>

            <motion.div className="stat-row" variants={fadeUp}>
              <span className="stat-label">Hotspot</span>
              <span className="stat-value-group">
                <span className="stat-location" style={{ textAlign: 'right' }}>{stats.mostActive[0]}</span>
                <span className="stat-highlight"><AnimatedNumber value={stats.mostActive[1]} /></span>
              </span>
            </motion.div>

            <motion.div className="stat-row" variants={fadeUp}>
              <span className="stat-label">Avg depth</span>
              <span className="stat-value">{formatDepth(stats.avgDepth)}</span>
            </motion.div>

            <motion.div className="stat-row border-none" variants={fadeUp}>
              <span className="stat-label">Deepest</span>
              <span className="stat-value">{formatDepth(stats.deepest.depth)}</span>
            </motion.div>
          </motion.div>

          <motion.div variants={staggerChildren} initial="initial" animate="animate" className="stat-list mt-24">
            <motion.h2 className="panel-title" variants={fadeUp}>
              Magnitude
            </motion.h2>

            <motion.div className="mag-legend-inner" variants={fadeUp}>
              {[
                { label: '7+', color: '#dc2626', size: 10 },
                { label: '6+', color: '#ef4444', size: 8 },
                { label: '4.5+', color: '#f97316', size: 6 },
                { label: '3+', color: '#facc15', size: 5 },
                { label: '2+', color: '#4ade80', size: 4 },
                { label: '<2', color: '#22d3ee', size: 3 },
              ].map((item) => (
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
            </motion.div>
          </motion.div>
        </GlassPanel>
      )}
    </AnimatePresence>
  )
})

export default StatsPanel
