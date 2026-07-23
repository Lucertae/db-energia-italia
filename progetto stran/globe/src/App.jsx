import { memo, useCallback } from 'react'
import { motion, AnimatePresence } from 'motion/react'
import GlobeScene from './components/Globe/GlobeScene'
import StatsPanel from './components/HUD/StatsPanel'
import EventFeed from './components/HUD/EventFeed'
import FilterBar from './components/HUD/FilterBar'
import PlaybackControls from './components/HUD/PlaybackControls'
import LastUpdated from './components/HUD/LastUpdated'
import DetailCard from './components/UI/DetailCard'
import LoadingScreen from './components/UI/LoadingScreen'
import ErrorToast from './components/UI/ErrorToast'
import LayerBar from './components/HUD/LayerBar'
import useEarthquakeData from './hooks/useEarthquakeData'
import useStore from './store/useStore'

const IconStats = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
    <path d="M4 20V14M10 20V10M16 20V4" strokeLinecap="round" />
  </svg>
)

const IconFeed = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
    <path d="M9 6h11M9 12h11M9 18h7" strokeLinecap="round" />
    <circle cx="5" cy="6" r="1" fill="currentColor" stroke="none" />
    <circle cx="5" cy="12" r="1" fill="currentColor" stroke="none" />
    <circle cx="5" cy="18" r="1" fill="currentColor" stroke="none" />
  </svg>
)

const IconPanels = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
    <rect x="3" y="3" width="7" height="7" rx="1" />
    <rect x="14" y="3" width="7" height="7" rx="1" />
    <rect x="3" y="14" width="7" height="7" rx="1" />
    <rect x="14" y="14" width="7" height="7" rx="1" />
  </svg>
)

const BrandHeader = memo(function BrandHeader() {
  const globeReady = useStore((s) => s.ui.globeReady)
  if (!globeReady) return null

  return (
    <motion.div
      className="brand-header"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 1.2, delay: 0.4 }}
    >
      <span className="brand-title">OPS DESK · GLOBE</span>
      <span className="brand-subtitle">World Monitor layers · USGS + live desk</span>
    </motion.div>
  )
})

const BrandFooter = memo(function BrandFooter() {
  const globeReady = useStore((s) => s.ui.globeReady)
  if (!globeReady) return null

  return (
    <motion.div
      className="brand-footer"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 1, delay: 1.2 }}
    >
      OPS DESK · base Real-Time Earthquake Globe
    </motion.div>
  )
})

const HudDock = memo(function HudDock() {
  const globeReady = useStore((s) => s.ui.globeReady)
  const showStats = useStore((s) => s.ui.showStats)
  const showFeed = useStore((s) => s.ui.showFeed)
  const hudCollapsed = useStore((s) => s.ui.hudCollapsed)
  const feedExpanded = useStore((s) => s.ui.feedExpanded)
  const setUI = useStore((s) => s.setUI)

  const toggleStats = useCallback(() => setUI({ showStats: !showStats }), [showStats, setUI])
  const toggleFeed = useCallback(() => setUI({ showFeed: !showFeed }), [showFeed, setUI])
  const toggleAll = useCallback(() => {
    const next = !hudCollapsed
    setUI({ hudCollapsed: next, showStats: !next, showFeed: !next })
  }, [hudCollapsed, setUI])

  if (!globeReady) return null

  return (
    <motion.div
      className={`hud-dock ${feedExpanded ? 'hud-dock--feed-open' : ''}`}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.6, delay: 0.9 }}
    >
      <button className={`dock-btn ${!hudCollapsed ? 'dock-btn--active' : ''}`} onClick={toggleAll}
        aria-label={hudCollapsed ? 'Show all panels' : 'Hide all panels'}
        aria-expanded={!hudCollapsed}>
        <IconPanels />
        <span className="dock-tooltip">{hudCollapsed ? 'Show' : 'Hide'}</span>
      </button>
      <button className={`dock-btn ${showStats ? 'dock-btn--active' : ''}`} onClick={toggleStats}
        aria-label={showStats ? 'Hide statistics panel' : 'Show statistics panel'}
        aria-expanded={showStats}>
        <IconStats />
        <span className="dock-tooltip">Stats</span>
      </button>
      <button className={`dock-btn ${showFeed ? 'dock-btn--active' : ''}`} onClick={toggleFeed}
        aria-label={showFeed ? 'Hide earthquake feed' : 'Show earthquake feed'}
        aria-expanded={showFeed}>
        <IconFeed />
        <span className="dock-tooltip">Feed</span>
      </button>
    </motion.div>
  )
})

export default function App() {
  useEarthquakeData()

  return (
    <div className="app">
      <a href="#filter-bar" className="skip-link">Skip to controls</a>
      <main className="globe-container" aria-label="Interactive 3D earthquake globe">
        <GlobeScene />
      </main>

      <BrandHeader />

      <aside className="hud-overlay" aria-label="Earthquake data panels">
        <StatsPanel />
        <EventFeed />
        <DetailCard />
        <FilterBar />
        <LayerBar />
        <PlaybackControls />
        <LastUpdated />
      </aside>

      <HudDock />
      <BrandFooter />
      <LoadingScreen />
      <ErrorToast />
    </div>
  )
}
