import { memo } from 'react'
import { motion, AnimatePresence } from 'motion/react'
import useStore from '../../store/useStore'
import { LOADING_PHASES } from '../../constants'

const LoadingScreen = memo(function LoadingScreen() {
  const isLoading = useStore((s) => s.isLoading)
  const globeReady = useStore((s) => s.ui.globeReady)
  const loadingPhase = useStore((s) => s.loadingPhase)
  const particleProgress = useStore((s) => s.particleProgress)
  const performanceMode = useStore((s) => s.performanceMode)

  const show = isLoading || !globeReady

  const message = globeReady && isLoading
    ? 'Fetching seismic data'
    : loadingPhase === LOADING_PHASES.LOADING_PARTICLES
      ? 'Building globe'
      : 'Initializing'

  return (
    <AnimatePresence>
      {show && (
        <motion.div
          className="loading-screen"
          initial={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 1.2, ease: [0.25, 0.1, 0.25, 1] }}
        >
          <div className="loading-content">
            <motion.div
              className="loading-brand"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 0.1 }}
            >
              <span className="loading-brand-title">Seismic Monitor</span>
              <div className="loading-brand-line" />
            </motion.div>

            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.6, delay: 0.4 }}
            >
              <div className="loading-ring" />
            </motion.div>

            <motion.div
              className="loading-phase"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.6, delay: 0.6 }}
            >
              <p className="loading-text">{message}</p>

              {loadingPhase === LOADING_PHASES.LOADING_PARTICLES && (
                <div className="loading-progress-track">
                  <motion.div
                    className="loading-progress-fill"
                    initial={{ scaleX: 0 }}
                    animate={{ scaleX: particleProgress }}
                    transition={{ duration: 0.15, ease: 'linear' }}
                  />
                </div>
              )}

              {performanceMode === 'reduced' && (
                <p className="loading-text loading-reduced">
                  reduced mode
                </p>
              )}
            </motion.div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
})

export default LoadingScreen
