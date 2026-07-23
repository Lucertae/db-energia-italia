// Thin lifecycle hook — initializes the earthquake worker on mount,
// forwards time-range changes, and bridges worker status to the UI store.
// No fetching or parsing happens here.

import { useEffect, useRef } from 'react'
import useStore from '../store/useStore'
import useEarthquakeStore from '../store/useEarthquakeStore'

export default function useEarthquakeData() {
  const timeRange = useStore((s) => s.filters.timeRange)
  const setIsLoading = useStore((s) => s.setIsLoading)
  const setLoadingMessage = useStore((s) => s.setLoadingMessage)

  const workerStatus = useEarthquakeStore((s) => s.workerStatus)
  const statusMessage = useEarthquakeStore((s) => s.statusMessage)
  const count = useEarthquakeStore((s) => s.count)

  // Start worker on mount, terminate on unmount.
  // No ref guard — the store's own _worker check prevents double-init,
  // and this must re-run after StrictMode's cleanup cycle.
  useEffect(() => {
    useEarthquakeStore.getState().initWorker(timeRange)
    return () => useEarthquakeStore.getState().terminateWorker()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // Forward time-range changes to worker
  const prevTimeRange = useRef(timeRange)
  useEffect(() => {
    if (prevTimeRange.current !== timeRange) {
      prevTimeRange.current = timeRange
      useStore.getState().setUI({ isFetchingData: true })
      useEarthquakeStore.getState().setTimeRange(timeRange)
    }
  }, [timeRange])

  // Bridge worker status into the UI loading state
  useEffect(() => {
    if (workerStatus === 'ready' && count > 0) {
      useStore.getState().setUI({ isFetchingData: false })
      document.title = `${count} earthquakes — Seismic Monitor`
      setLoadingMessage(`Plotting ${count.toLocaleString()} earthquakes...`)
      // Brief delay so the message is visible before dismissing the loading screen
      const id = setTimeout(() => setIsLoading(false), 800)
      return () => clearTimeout(id)
    } else if (workerStatus === 'error') {
      setLoadingMessage(statusMessage || 'Error fetching data. Retrying...')
    } else if (workerStatus !== 'idle' && workerStatus !== 'ready') {
      setLoadingMessage(statusMessage || 'Fetching seismic data...')
    }
  }, [workerStatus, statusMessage, count, setIsLoading, setLoadingMessage])
}
