import { memo } from 'react'
import { motion, AnimatePresence } from 'motion/react'
import useEarthquakeStore from '../../store/useEarthquakeStore'

const ErrorToast = memo(function ErrorToast() {
  const lastError = useEarthquakeStore((s) => s.lastError)
  const workerStatus = useEarthquakeStore((s) => s.workerStatus)

  const show = workerStatus === 'error' && lastError

  return (
    <AnimatePresence>
      {show && (
        <motion.div
          className="error-toast"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 20 }}
          role="alert"
        >
          <span className="error-toast-icon">!</span>
          <span className="error-toast-text">
            Connection issue — retrying...
          </span>
        </motion.div>
      )}
    </AnimatePresence>
  )
})

export default ErrorToast
