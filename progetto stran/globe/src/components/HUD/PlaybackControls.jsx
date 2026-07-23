// Time-lapse playback controls — play/pause, speed, and scrub bar.
// Reads time range from earthquake store and playback state from main store.

import { memo, useCallback } from 'react'
import { motion, AnimatePresence } from 'motion/react'
import useStore from '../../store/useStore'
import useEarthquakeStore from '../../store/useEarthquakeStore'

function formatTimestamp(ms) {
  if (!ms) return '—'
  const d = new Date(ms)
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

const SPEED_OPTIONS = [0.5, 1, 2, 4]

const PlaybackControls = memo(function PlaybackControls() {
  const globeReady = useStore((s) => s.ui.globeReady)
  const playback = useStore((s) => s.playback)
  const setPlayback = useStore((s) => s.setPlayback)
  const timeRangeStart = useEarthquakeStore((s) => s.timeRangeStart)
  const timeRangeEnd = useEarthquakeStore((s) => s.timeRangeEnd)
  const count = useEarthquakeStore((s) => s.count)

  const togglePlay = useCallback(() => {
    const { isPlaying, progress } = useStore.getState().playback
    if (isPlaying) {
      setPlayback({ isPlaying: false })
    } else {
      // If at end, restart from beginning
      setPlayback({ isPlaying: true, progress: progress >= 0.99 ? 0.0 : progress })
    }
  }, [setPlayback])

  const handleScrub = useCallback((e) => {
    const progress = parseFloat(e.target.value)
    setPlayback({ progress, isPlaying: false })
  }, [setPlayback])

  const handleSpeedChange = useCallback((speed) => {
    setPlayback({ speed })
  }, [setPlayback])

  const handleReset = useCallback(() => {
    setPlayback({ progress: 1.0, isPlaying: false })
  }, [setPlayback])

  if (!globeReady || !count) return null

  const currentMs = timeRangeStart + (timeRangeEnd - timeRangeStart) * playback.progress

  return (
    <motion.div
      className="playback-controls"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.8 }}
    >
      <div className="playback-inner">
        <button className="playback-btn playback-play" onClick={togglePlay} aria-label={playback.isPlaying ? 'Pause time-lapse' : 'Play time-lapse'}>
          {playback.isPlaying ? (
            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
              <rect x="6" y="4" width="4" height="16" rx="1" />
              <rect x="14" y="4" width="4" height="16" rx="1" />
            </svg>
          ) : (
            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
              <polygon points="6,4 20,12 6,20" />
            </svg>
          )}
        </button>

        <div className="playback-scrub-wrap">
          <span className="playback-time mono">{formatTimestamp(timeRangeStart)}</span>
          <input
            type="range"
            className="playback-scrub"
            aria-label="Time-lapse progress"
            min="0"
            max="1"
            step="0.001"
            value={playback.progress}
            onChange={handleScrub}
          />
          <span className="playback-time mono">{formatTimestamp(timeRangeEnd)}</span>
        </div>

        <div className="playback-speed">
          {SPEED_OPTIONS.map((s) => (
            <button
              key={s}
              className={`playback-speed-btn ${playback.speed === s ? 'playback-speed-btn--active' : ''}`}
              onClick={() => handleSpeedChange(s)}
              aria-label={`Playback speed ${s}x`}
              aria-pressed={playback.speed === s}
            >
              {s}x
            </button>
          ))}
        </div>

        <button
          className="playback-btn playback-reset"
          onClick={handleReset}
          title="Show all"
          aria-label="Reset to show all earthquakes"
        >
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <polyline points="1 4 1 10 7 10" />
            <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10" />
          </svg>
        </button>
      </div>

      <div className="playback-cursor mono">
        {formatTimestamp(currentMs)}
      </div>
    </motion.div>
  )
})

export default PlaybackControls
