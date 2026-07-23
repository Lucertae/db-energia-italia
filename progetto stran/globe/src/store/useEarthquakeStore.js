/**
 * useEarthquakeStore.js
 * 
 * Zustand store utilizing a CQRS (Command Query Responsibility Segregation) pattern.
 * - Commands: Manage the lifecycle of the data-fetching Web Worker.
 * - Queries: Expose pre-computed typed arrays and parsed metadata to React components.
 * 
 * The store itself does not perform data fetching or heavy processing. It delegates 
 * those tasks to the Web Worker to prevent main thread blocking, and only receives 
 * the processed data payloads.
 */

import { create } from 'zustand'
import { API_URLS, POLL_INTERVAL } from '../constants'
import { latLngDepthToVector3 } from '../utils/coordinates'
import { getMagnitudeSize, getMagnitudeColorRGB } from '../utils/magnitudeScale'

const LAYER_RGB = {
  fires: [0.937, 0.267, 0.267],
  flights: [0.133, 0.827, 0.933],
  ais: [0.231, 0.510, 0.965],
  conflicts: [0.863, 0.149, 0.149],
  natural: [0.655, 0.545, 0.980],
  cyber: [0.518, 0.800, 0.086],
  climate: [0.078, 0.722, 0.651],
  other: [0.580, 0.639, 0.722],
}

function colorOf(q) {
  if (q.layer && LAYER_RGB[q.layer]) return LAYER_RGB[q.layer]
  return getMagnitudeColorRGB(q.magnitude)
}

// --- Cache Helpers (localStorage, stale-while-revalidate pattern) ---

const CACHE_PREFIX = 'eq_cache_'
const CACHE_MAX_ITEMS = 500

function getCachedData(timeRange) {
  try {
    const raw = localStorage.getItem(CACHE_PREFIX + timeRange)
    if (!raw) return null
    const cached = JSON.parse(raw)
    if (!cached?.metadata || !cached?.timestamp) return null
    return cached
  } catch { return null }
}

function setCachedData(timeRange, metadata) {
  try {
    const trimmed = metadata.slice(0, CACHE_MAX_ITEMS)
    localStorage.setItem(CACHE_PREFIX + timeRange, JSON.stringify({
      metadata: trimmed,
      timestamp: Date.now(),
    }))
  } catch { /* storage full */ }
}

// ── Hash helper (deterministic phase from string ID) ──

function hashFallback(str) {
  let hash = 0
  for (let i = 0; i < str.length; i++) {
    hash = ((hash << 5) - hash) + str.charCodeAt(i)
    hash |= 0
  }
  return Math.abs(hash) / 2147483647
}

// ── Repack metadata into typed arrays for the GPU layer ──

function repackMetadata(metadata) {
  const count = metadata.length
  const positions = new Float32Array(count * 3)
  const colors = new Float32Array(count * 3)
  const sizes = new Float32Array(count)
  const phases = new Float32Array(count)
  const magnitudes = new Float32Array(count)
  const times = new Float32Array(count)

  const timeRangeEnd = count > 0 ? metadata[0].time : 0
  const timeRangeStart = count > 0 ? metadata[count - 1].time : 0
  const timeSpan = timeRangeEnd - timeRangeStart || 1

  for (let i = 0; i < count; i++) {
    const q = metadata[i]
    const [x, y, z] = latLngDepthToVector3(q.lat, q.lng, q.depth)
    positions[i * 3] = x; positions[i * 3 + 1] = y; positions[i * 3 + 2] = z
    const [r, g, b] = colorOf(q)
    colors[i * 3] = r; colors[i * 3 + 1] = g; colors[i * 3 + 2] = b
    sizes[i] = getMagnitudeSize(q.magnitude) * 20
    phases[i] = hashFallback(q.id)
    magnitudes[i] = q.magnitude
    times[i] = (q.time - timeRangeStart) / timeSpan
  }

  return { positions, colors, sizes, phases, magnitudes, times, timeRangeStart, timeRangeEnd }
}

// ── Empty buffer sentinels (stable references for initial state) ──

const EMPTY_F32 = new Float32Array(0)

// ── Store ──

const useEarthquakeStore = create((set, get) => ({
  // ─── Query: metadata (for HUD components) ───
  earthquakes: [],
  count: 0,
  lastUpdated: null,

  // ─── Query: typed arrays (for EarthquakeLayer) ───
  positions: EMPTY_F32,
  colors: EMPTY_F32,
  sizes: EMPTY_F32,
  phases: EMPTY_F32,
  magnitudes: EMPTY_F32,
  times: EMPTY_F32,
  timeRangeStart: 0,
  timeRangeEnd: 0,

  // ─── Query: worker status ───
  workerStatus: 'idle', // idle | starting | fetching | parsing | packing | ready | error
  statusMessage: '',
  lastError: null,

  // ─── Internal: worker ref (not reactive) ───
  _worker: null,
  _fallbackMode: false,
  _activeTimeRange: 'day',

  // ─── Command: initialize worker ───
  initWorker: (timeRange = 'day') => {
    const state = get()
    if (state._worker) return // already running

    set({ _activeTimeRange: timeRange })

    // Serve cached data immediately (stale-while-revalidate)
    const cached = getCachedData(timeRange)
    if (cached?.metadata?.length) {
      const repacked = repackMetadata(cached.metadata)
      set({
        earthquakes: cached.metadata,
        ...repacked,
        count: cached.metadata.length,
        lastUpdated: cached.timestamp,
        workerStatus: 'ready',
        statusMessage: `${cached.metadata.length} earthquakes (cached)`,
      })
    }

    // Feature detection — fall back to main-thread fetch if Workers unavailable
    if (typeof Worker === 'undefined') {
      console.warn('[useEarthquakeStore] Web Workers unavailable, using main-thread fallback')
      set({ _fallbackMode: true })
      get()._startFallbackPolling(timeRange)
      return
    }

    const worker = new Worker(
      new URL('../workers/earthquakeWorker.js', import.meta.url),
      { type: 'module' }
    )

    worker.onmessage = (e) => {
      const msg = e.data
      switch (msg.type) {
        case 'DATA':
          set({
            earthquakes: msg.metadata,
            positions: msg.positions,
            colors: msg.colors,
            sizes: msg.sizes,
            phases: msg.phases,
            magnitudes: msg.magnitudes,
            times: msg.times,
            timeRangeStart: msg.timeRangeStart,
            timeRangeEnd: msg.timeRangeEnd,
            count: msg.count,
            lastUpdated: Date.now(),
            workerStatus: 'ready',
            statusMessage: `${msg.count.toLocaleString()} earthquakes loaded`,
            lastError: null,
          })
          // Cache metadata for stale-while-revalidate on next load
          setCachedData(get()._activeTimeRange, msg.metadata)
          break

        case 'STATUS':
          set({
            workerStatus: msg.phase.toLowerCase(),
            statusMessage: msg.message,
          })
          break

        case 'ERROR':
          set({
            workerStatus: 'error',
            statusMessage: msg.message,
            lastError: { message: msg.message, code: msg.code, time: Date.now() },
          })
          break
      }
    }

    worker.onerror = (err) => {
      console.error('[useEarthquakeStore] Worker error:', err)
      set({
        workerStatus: 'error',
        statusMessage: 'Worker crashed — switching to fallback',
        lastError: { message: err.message, code: 'WORKER_CRASH', time: Date.now() },
      })
      // Terminate dead worker and fall back
      get().terminateWorker()
      set({ _fallbackMode: true })
      get()._startFallbackPolling(timeRange)
    }

    set({ _worker: worker, workerStatus: 'starting', statusMessage: 'Starting worker...' })
    worker.postMessage({ type: 'START', timeRange, interval: POLL_INTERVAL })
  },

  // ─── Command: terminate worker ───
  terminateWorker: () => {
    const { _worker } = get()
    if (_worker) {
      _worker.postMessage({ type: 'STOP' })
      _worker.terminate()
      set({ _worker: null, workerStatus: 'idle' })
    }
  },

  // ─── Command: change time range (notifies worker) ───
  setTimeRange: (timeRange) => {
    set({ _activeTimeRange: timeRange })
    const { _worker, _fallbackMode } = get()
    if (_worker) {
      _worker.postMessage({ type: 'SET_TIME_RANGE', timeRange })
    } else if (_fallbackMode) {
      get()._startFallbackPolling(timeRange)
    }
  },

  // ─── Fallback: main-thread polling when Worker is unavailable ───
  _fallbackTimer: null,

  _startFallbackPolling: (timeRange) => {
    const state = get()
    if (state._fallbackTimer) clearInterval(state._fallbackTimer)

    const doFetch = async () => {
      try {

        set({ workerStatus: 'fetching', statusMessage: 'Fetching seismic data...' })

        const url = API_URLS[timeRange] || API_URLS.day
        const res = await fetch(url)
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const json = await res.json()

        if (!json?.features?.length) throw new Error('Empty GeoJSON response')

        const metadata = json.features
          .map((f) => {
            if (!f?.geometry?.coordinates || typeof f.properties?.mag !== 'number') return null
            const [lng, lat, depth] = f.geometry.coordinates
            if (!isFinite(lat) || !isFinite(lng)) return null
            return {
              id: f.id || `${lat}_${lng}_${f.properties?.time || 0}`,
              magnitude: f.properties.mag,
              lat, lng,
              depth: Math.max(0, depth || 0),
              place: f.properties?.place || 'Unknown',
              time: f.properties?.time || 0,
              tsunami: !!f.properties?.tsunami,
              felt: f.properties?.felt || 0,
              url: f.properties?.url || '',
              type: f.properties?.type || 'earthquake',
              layer: f.properties?.layer || 'quakes',
            }
          })
          .filter(Boolean)
          .sort((a, b) => b.time - a.time)

        const count = metadata.length
        const repacked = repackMetadata(metadata)

        set({
          earthquakes: metadata, ...repacked,
          count, lastUpdated: Date.now(), workerStatus: 'ready',
          statusMessage: `${count} earthquakes loaded (fallback)`, lastError: null,
        })
        // Cache for stale-while-revalidate
        setCachedData(timeRange, metadata)
      } catch (err) {
        console.error('[fallback] Fetch failed:', err)
        set({ workerStatus: 'error', statusMessage: err.message, lastError: { message: err.message, code: 'FALLBACK_FETCH_FAILED', time: Date.now() } })
      }
    }

    doFetch()
    const timer = setInterval(doFetch, POLL_INTERVAL)
    set({ _fallbackTimer: timer })
  },
}))

export default useEarthquakeStore
