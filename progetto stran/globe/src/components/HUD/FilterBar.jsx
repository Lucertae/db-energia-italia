import { memo, useMemo } from 'react'
import { motion } from 'motion/react'
import useStore from '../../store/useStore'
import useEarthquakeStore from '../../store/useEarthquakeStore'
import { formatNumber } from '../../utils/formatters'
import { useAnimatedValue } from '../../utils/useAnimatedValue'

const AnimatedCount = ({ value }) => {
  const display = useAnimatedValue(value)
  return <span>{formatNumber(display)}</span>
}

const MAG_OPTIONS = [
  { label: 'All', value: 0 },
  { label: '2.5+', value: 2.5 },
  { label: '4.5+', value: 4.5 },
  { label: '6+', value: 6 },
  { label: '7+', value: 7 },
]

const TIME_OPTIONS = [
  { label: '24h', value: 'day' },
  { label: '7d', value: 'week' },
  { label: '30d', value: 'month' },
]

const DEPTH_OPTIONS = [
  { label: 'All', value: 'all' },
  { label: 'Shallow', value: 'shallow' },
  { label: 'Mid', value: 'mid' },
  { label: 'Deep', value: 'deep' },
]

const FilterSection = memo(function FilterSection({ label, options, value, onChange }) {
  return (
    <div className="cbar-section">
      <span className="cbar-label">{label}</span>
      <div className="cbar-buttons">
        {options.map((opt) => (
          <button
            key={opt.value}
            className={`cbar-btn ${value === opt.value ? 'cbar-btn--active' : ''}`}
            onClick={() => onChange(opt.value)}
            aria-label={`${label}: ${opt.label}`}
            aria-pressed={value === opt.value}
          >
            {opt.label}
          </button>
        ))}
      </div>
    </div>
  )
})

const FilterBar = memo(function FilterBar() {
  const filters = useStore((s) => s.filters)
  const setFilter = useStore((s) => s.setFilter)
  const globeReady = useStore((s) => s.ui.globeReady)
  const isFetching = useStore((s) => s.ui.isFetchingData)
  const earthquakes = useEarthquakeStore((s) => s.earthquakes)

  const filteredCount = useMemo(() => {
    return earthquakes.filter((q) => {
      if (q.magnitude < filters.magnitude) return false
      if (filters.depth === 'shallow' && q.depth > 70) return false
      if (filters.depth === 'mid' && (q.depth < 70 || q.depth > 300)) return false
      if (filters.depth === 'deep' && q.depth < 300) return false
      return true
    }).length
  }, [earthquakes, filters])

  if (!globeReady) return null

  return (
    <motion.div
      className="cbar"
      id="filter-bar"
      role="toolbar"
      aria-label="Earthquake filters"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.25, 0.1, 0.25, 1], delay: 0.5 }}
    >
      <div className="cbar-inner">
        <FilterSection
          label="Magnitude"
          options={MAG_OPTIONS}
          value={filters.magnitude}
          onChange={(v) => setFilter('magnitude', v)}
        />

        <div className="cbar-divider" />

        <FilterSection
          label="Time"
          options={TIME_OPTIONS}
          value={filters.timeRange}
          onChange={(v) => setFilter('timeRange', v)}
        />

        <div className="cbar-divider" />

        <FilterSection
          label="Depth"
          options={DEPTH_OPTIONS}
          value={filters.depth}
          onChange={(v) => setFilter('depth', v)}
        />

        <div className="cbar-divider" />

        <div className="cbar-counter">
          {isFetching ? (
            <span className="cbar-spinner" />
          ) : (
            <span className="cbar-counter-value mono">
              <AnimatedCount value={filteredCount} />
            </span>
          )}
          <span className="cbar-counter-label">{isFetching ? 'Loading...' : 'Events'}</span>
        </div>
      </div>
    </motion.div>
  )
})

export default FilterBar
