/**
 * earthquakeWorker.js
 * 
 * Web Worker responsible for fetching earthquake data from the USGS API,
 * parsing the GeoJSON response, validating coordinates, and preparing
 * the data for rendering in the 3D scene.
 * 
 * This offloads heavy computation (like trigonometry for positioning)
 * from the main thread to ensure the UI remains smooth.
 *
 * Message protocol:
 *   Main -> Worker:
 *     - START: Begin fetching data on an interval
 *     - SET_TIME_RANGE: Update the time range (day, week, month)
 *     - STOP: Halt all fetching
 *
 *   Worker -> Main:
 *     - DATA: Contains parsed earthquake metadata and Float32Arrays for the 3D instanced mesh
 *     - STATUS: Updates the loading phase/progress
 *     - ERROR: Reports any network or parsing issues
 */

// --- Constants (duplicated from constants.js to avoid import issues in worker) ---

const GLOBE_RADIUS = 1.0
const EARTH_RADIUS_KM = 6371

const API_URLS = {
  day: '/api/geojson?range=day',
  week: '/api/geojson?range=week',
  month: '/api/geojson?range=month',
  significant: '/api/geojson?range=day',
}

const LAYER_COLORS = {
  quakes: null, // use magnitude
  fires: [0.937, 0.267, 0.267],
  flights: [0.133, 0.827, 0.933],
  ais: [0.231, 0.510, 0.965],
  conflicts: [0.863, 0.149, 0.149],
  natural: [0.655, 0.545, 0.980],
  cyber: [0.518, 0.800, 0.086],
  climate: [0.078, 0.722, 0.651],
  other: [0.580, 0.639, 0.722],
}

const MAG_THRESHOLDS = [
  { min: 7,   r: 0.863, g: 0.149, b: 0.149 }, // #dc2626
  { min: 6,   r: 0.937, g: 0.267, b: 0.267 }, // #ef4444
  { min: 4.5, r: 0.976, g: 0.451, b: 0.086 }, // #f97316
  { min: 3,   r: 0.980, g: 0.800, b: 0.082 }, // #facc15
  { min: 2,   r: 0.290, g: 0.871, b: 0.502 }, // #4ade80
  { min: 0,   r: 0.133, g: 0.827, b: 0.933 }, // #22d3ee
]

// --- Coordinate Math ---

/**
 * Converts latitude and longitude to 3D Cartesian coordinates (x, y, z).
 * Assumes the globe is centered at (0,0,0).
 */
function latLngToXYZ(lat, lng, radius) {
  const phi = (90 - lat) * (Math.PI / 180)
  const theta = (lng + 180) * (Math.PI / 180)
  const x = -(radius * Math.sin(phi) * Math.cos(theta))
  const y = radius * Math.cos(phi)
  const z = radius * Math.sin(phi) * Math.sin(theta)
  return [x, y, z]
}

/**
 * Calculates the 3D position of an earthquake, taking its depth into account.
 * The depth slightly reduces the radius to place the point "inside" the globe.
 */
function latLngDepthToXYZ(lat, lng, depthKm) {
  const depthFraction = Math.min(depthKm, 700) / EARTH_RADIUS_KM
  const radius = GLOBE_RADIUS * (1 - depthFraction)
  return latLngToXYZ(lat, lng, radius)
}

// --- Visual Properties ---

/**
 * Maps an earthquake magnitude to a specific color threshold.
 */
function getMagnitudeColorRGB(mag) {
  for (const t of MAG_THRESHOLDS) {
    if (mag >= t.min) return [t.r, t.g, t.b]
  }
  return [0.133, 0.827, 0.933]
}

/**
 * Calculates the visual size of the earthquake marker based on magnitude.
 * Uses an exponential scale so larger quakes stand out significantly.
 */
function getMagnitudeSize(mag) {
  return Math.max(0.002, 0.002 * Math.pow(1.45, Math.max(0, mag)))
}

/**
 * Generates a deterministic hash from a string.
 * Used to give each earthquake a consistent, random-looking animation phase offset.
 */
function hashString(str) {
  let hash = 0
  for (let i = 0; i < str.length; i++) {
    hash = ((hash << 5) - hash) + str.charCodeAt(i)
    hash |= 0
  }
  return Math.abs(hash) / 2147483647
}

// --- GeoJSON Parsing & Validation ---

/**
 * Validates a GeoJSON feature from the USGS API and extracts the relevant data.
 * Skips malformed entries to prevent crashes during rendering.
 */
function validateFeature(feature) {
  if (!feature || typeof feature !== 'object') return null
  const { properties, geometry, id } = feature

  if (!geometry || !Array.isArray(geometry.coordinates) || geometry.coordinates.length < 2) return null
  const lng = geometry.coordinates[0]
  const lat = geometry.coordinates[1]
  const depth = geometry.coordinates.length > 2 ? geometry.coordinates[2] : 0
  if (typeof lng !== 'number' || typeof lat !== 'number' || !isFinite(lng) || !isFinite(lat)) return null
  if (lat < -90 || lat > 90 || lng < -180 || lng > 180) return null

  const mag = typeof properties?.mag === 'number' && isFinite(properties.mag) ? properties.mag : null
  if (mag === null) return null
  const layer = properties?.layer || (properties?.type === 'earthquake' ? 'quakes' : 'other')

  return {
    id: id || `${lat}_${lng}_${properties?.time || 0}`,
    magnitude: mag,
    lat,
    lng,
    depth: Math.max(0, typeof depth === 'number' && isFinite(depth) ? depth : 0),
    place: properties?.place || 'Unknown',
    time: properties?.time || 0,
    tsunami: !!properties?.tsunami,
    felt: properties?.felt || 0,
    url: properties?.url || '',
    type: properties?.type || 'earthquake',
    layer,
  }
}

function colorForQuake(q) {
  const fixed = LAYER_COLORS[q.layer]
  if (fixed) return fixed
  return getMagnitudeColorRGB(q.magnitude)
}

function parseGeoJSON(json) {
  if (!json || typeof json !== 'object' || !Array.isArray(json.features)) {
    throw new Error('INVALID_GEOJSON: missing or malformed "features" array')
  }

  const metadata = []
  const rejected = []

  for (let i = 0; i < json.features.length; i++) {
    const parsed = validateFeature(json.features[i])
    if (parsed) {
      metadata.push(parsed)
    } else {
      rejected.push(i)
    }
  }

  // Sort newest first
  metadata.sort((a, b) => b.time - a.time)

  if (rejected.length > 0) {
    console.warn(`[earthquakeWorker] Rejected ${rejected.length}/${json.features.length} malformed features`)
  }

  return metadata
}

// ── Pack metadata into typed arrays ──

function packBuffers(metadata) {
  const count = metadata.length
  const positions = new Float32Array(count * 3)
  const colors = new Float32Array(count * 3)
  const sizes = new Float32Array(count)
  const phases = new Float32Array(count)
  const magnitudes = new Float32Array(count)
  const times = new Float32Array(count)

  // Compute time range for normalization (metadata is sorted newest-first)
  const timeRangeEnd = count > 0 ? metadata[0].time : 0
  const timeRangeStart = count > 0 ? metadata[count - 1].time : 0
  const timeSpan = timeRangeEnd - timeRangeStart || 1

  for (let i = 0; i < count; i++) {
    const q = metadata[i]

    const [x, y, z] = latLngDepthToXYZ(q.lat, q.lng, q.depth)
    positions[i * 3] = x
    positions[i * 3 + 1] = y
    positions[i * 3 + 2] = z

    const [r, g, b] = colorForQuake(q)
    colors[i * 3] = r
    colors[i * 3 + 1] = g
    colors[i * 3 + 2] = b

    sizes[i] = getMagnitudeSize(q.magnitude) * 20
    phases[i] = hashString(q.id)
    magnitudes[i] = q.magnitude
    // Normalized time: 0.0 = oldest, 1.0 = newest
    times[i] = (q.time - timeRangeStart) / timeSpan
  }

  return { positions, colors, sizes, phases, magnitudes, times, timeRangeStart, timeRangeEnd, count }
}

// ── Fetch + process pipeline ──

async function fetchAndProcess(timeRange) {
  const url = API_URLS[timeRange] || API_URLS.day

  self.postMessage({ type: 'STATUS', phase: 'FETCHING', message: 'Fetching seismic data...' })

  const response = await fetch(url)
  if (!response.ok) {
    throw new Error(`USGS API returned HTTP ${response.status}`)
  }

  self.postMessage({ type: 'STATUS', phase: 'PARSING', message: 'Parsing GeoJSON...' })

  const json = await response.json()
  const metadata = parseGeoJSON(json)

  self.postMessage({
    type: 'STATUS',
    phase: 'PACKING',
    message: `Packing ${metadata.length.toLocaleString()} earthquakes...`,
  })

  const buffers = packBuffers(metadata)

  // Transfer typed arrays — they become detached in this worker after postMessage
  self.postMessage(
    {
      type: 'DATA',
      metadata,
      positions: buffers.positions,
      colors: buffers.colors,
      sizes: buffers.sizes,
      phases: buffers.phases,
      magnitudes: buffers.magnitudes,
      times: buffers.times,
      timeRangeStart: buffers.timeRangeStart,
      timeRangeEnd: buffers.timeRangeEnd,
      count: buffers.count,
    },
    [
      buffers.positions.buffer,
      buffers.colors.buffer,
      buffers.sizes.buffer,
      buffers.phases.buffer,
      buffers.magnitudes.buffer,
      buffers.times.buffer,
    ]
  )
}

// ── Polling lifecycle ──

let pollTimer = null
let activeTimeRange = 'day'
let retryCount = 0
const MAX_RETRIES = 5

function startPolling(timeRange, interval) {
  stopPolling()
  activeTimeRange = timeRange
  retryCount = 0

  const tick = async () => {
    try {
      await fetchAndProcess(activeTimeRange)
      retryCount = 0
    } catch (err) {
      retryCount++
      const retryDelay = Math.min(10000 * Math.pow(2, retryCount - 1), 60000)
      self.postMessage({
        type: 'ERROR',
        message: err.message,
        code: retryCount >= MAX_RETRIES ? 'MAX_RETRIES_EXCEEDED' : 'FETCH_FAILED',
        retryIn: retryDelay,
      })

      if (retryCount < MAX_RETRIES) {
        pollTimer = setTimeout(tick, retryDelay)
        return
      }
    }
    pollTimer = setTimeout(tick, interval)
  }

  tick()
}

function stopPolling() {
  if (pollTimer !== null) {
    clearTimeout(pollTimer)
    pollTimer = null
  }
}

// ── Message handler ──

self.onmessage = (e) => {
  const { type, timeRange, interval } = e.data

  switch (type) {
    case 'START':
      startPolling(timeRange || 'day', interval || 65000)
      break

    case 'SET_TIME_RANGE':
      activeTimeRange = timeRange || 'day'
      retryCount = 0
      // Immediate fetch with new range, polling continues on existing interval
      fetchAndProcess(activeTimeRange).catch((err) => {
        self.postMessage({ type: 'ERROR', message: err.message, code: 'FETCH_FAILED' })
      })
      break

    case 'STOP':
      stopPolling()
      break
  }
}
