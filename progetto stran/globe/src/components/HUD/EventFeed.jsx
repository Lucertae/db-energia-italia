import { memo, useRef, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'motion/react'
import GlassPanel from '../UI/GlassPanel'
import MagnitudeBadge from '../UI/MagnitudeBadge'
import useStore from '../../store/useStore'
import useEarthquakeStore from '../../store/useEarthquakeStore'
import { timeAgo, formatDepth } from '../../utils/formatters'
import { getDepthColor } from '../../utils/depthScale'

const EventFeed = memo(function EventFeed() {
  const earthquakes = useEarthquakeStore((s) => s.earthquakes)
  const globeReady = useStore((s) => s.ui.globeReady)
  const showFeed = useStore((s) => s.ui.showFeed)
  const setSelectedQuake = useStore((s) => s.setSelectedQuake)
  const setCameraTarget = useStore((s) => s.setCameraTarget)
  const selectedQuake = useStore((s) => s.selectedQuake)
  const prevCountRef = useRef(0)
  const scrollRef = useRef(null)
  
  // Mobile feed toggle state (synced to store so dock can hide)
  const isExpanded = useStore((s) => s.ui.feedExpanded)
  const setUI = useStore((s) => s.setUI)
  const setIsExpanded = useCallback((v) => setUI({ feedExpanded: v }), [setUI])

  useEffect(() => {
    if (earthquakes.length > 0 && scrollRef.current) {
      scrollRef.current.scrollTo({ top: 0, behavior: 'smooth' })
    }
  }, [earthquakes])

  const isNewBatch = earthquakes.length !== prevCountRef.current
  useEffect(() => {
    prevCountRef.current = earthquakes.length
  }, [earthquakes.length])

  if (!globeReady || !earthquakes.length) return null

  const recentQuakes = earthquakes.slice(0, 40)

  const handleClick = (quake) => {
    setSelectedQuake(quake)
    const depthTilt = quake.depth > 70 ? Math.min(25, quake.depth / 10) : 0
    setCameraTarget({ lat: quake.lat - depthTilt, lng: quake.lng, zoom: 2.0 })
    useStore.getState().setUI({ showDetail: true })
  }

  return (
    <AnimatePresence>
      {showFeed && (
        <GlassPanel className={`event-feed ${isExpanded ? 'mobile-expanded' : 'mobile-collapsed'}`} key="feed">
          <div aria-live="polite" aria-atomic="false" className="sr-only">
            {isNewBatch && recentQuakes[0] && (
              <span>New earthquake: magnitude {recentQuakes[0].magnitude.toFixed(1)}, {recentQuakes[0].place}</span>
            )}
          </div>
          <div 
            className="feed-header feed-header-toggle" 
            onClick={() => setIsExpanded(!isExpanded)}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setIsExpanded(!isExpanded) } }}
          >
            <h2 className="panel-title">
              <span className="live-dot" />
              Live feed
            </h2>
            <span className="feed-toggle-icon">
              {isExpanded ? (
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M6 15l6-6 6 6" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              ) : (
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M6 9l6 6 6-6" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              )}
            </span>
          </div>

          <div ref={scrollRef} className="feed-scroll" role="list" aria-label="Recent earthquakes">
            <div className="feed-list">
              <AnimatePresence initial={false}>
                {recentQuakes.map((quake, i) => {
                  const isSelected = selectedQuake?.id === quake.id
                  const isNew = isNewBatch && i < 3

                  return (
                    <motion.div
                      layout
                      initial={{ opacity: 0, y: -16 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0 }}
                      transition={{ duration: 0.3, ease: [0.25, 0.1, 0.25, 1] }}
                      key={quake.id}
                      onClick={() => handleClick(quake)}
                      className={`feed-item ${isSelected ? 'feed-item--active' : ''} ${isNew ? 'feed-item--new' : ''}`}
                      role="listitem"
                      aria-label={`Magnitude ${quake.magnitude.toFixed(1)} earthquake, ${quake.place}, ${timeAgo(quake.time)}`}
                      tabIndex={0}
                      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handleClick(quake) } }}
                    >
                      <div className="feed-item-content">
                        <div className="feed-badge-wrap">
                          <MagnitudeBadge magnitude={quake.magnitude} />
                        </div>
                        <div className="feed-item-info">
                          <div className="feed-item-place">
                            {quake.place}
                          </div>
                          <div className="feed-item-meta">
                            <span className="mono feed-item-time">{timeAgo(quake.time)}</span>
                            <span style={{ opacity: 0.2 }}>|</span>
                            <span className="feed-depth-wrap">
                              <span
                                className="depth-indicator"
                                style={{
                                  height: `${Math.max(4, Math.min(12, (quake.depth / 700) * 12))}px`,
                                  backgroundColor: getDepthColor(quake.depth),
                                }}
                              />
                              <span className="mono feed-item-depth">{formatDepth(quake.depth)}</span>
                            </span>
                          </div>
                        </div>
                        {isSelected && (
                          <span className="feed-item-flyto mono" aria-hidden="true">
                            &#8599;
                          </span>
                        )}
                      </div>
                    </motion.div>
                  )
                })}
              </AnimatePresence>
            </div>
          </div>

          <div className="feed-fade" />
        </GlassPanel>
      )}
    </AnimatePresence>
  )
})

export default EventFeed
