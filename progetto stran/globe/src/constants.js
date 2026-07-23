/**
 * constants.js
 * 
 * Central configuration file for the application.
 * Defines physical constraints, graphical constants, API endpoints, and color palettes.
 * The globe radius is normalized to 1.0 in Three.js world units.
 */

export const GLOBE_RADIUS = 1.0
export const EARTH_RADIUS_KM = 6371

// particle config — 75k max buffer size for pixel sampling
export const PARTICLE_COUNT = 75000
export const PARTICLE_BASE_SIZE = 0.6
export const PARTICLE_SIZE_VARIANCE = 0.2

// coastline density weighting
export const COASTLINE_BORDER_FRACTION = 0.3
export const COASTLINE_BORDER_WIDTH = 2.5

export const AUTO_ROTATE_SPEED = 0.4
export const BREATHING_AMPLITUDE = 0.001
export const BREATHING_SPEED = 0.5

// earthquake point config
export const MAX_EARTHQUAKE_POINTS = 10000
export const EARTHQUAKE_PULSE_SPEED = 2.0
export const SHOCKWAVE_DURATION = 1.5
export const EARTHQUAKE_FADE_IN = 1.5

// USGS endpoints
export const API_URLS = {
  day: '/api/geojson?range=day',
  week: '/api/geojson?range=week',
  month: '/api/geojson?range=month',
  significant: '/api/geojson?range=day',
}

export const GLOBE_LAYERS = [
  { id: 'quakes', label: 'Quakes', color: '#f97316' },
  { id: 'fires', label: 'Fires', color: '#ef4444' },
  { id: 'flights', label: 'Flights', color: '#22d3ee' },
  { id: 'ais', label: 'AIS', color: '#3b82f6' },
  { id: 'conflicts', label: 'Conflicts', color: '#dc2626' },
  { id: 'natural', label: 'Natural', color: '#a78bfa' },
  { id: 'cyber', label: 'Cyber', color: '#84cc16' },
  { id: 'climate', label: 'Climate', color: '#14b8a6' },
  { id: 'other', label: 'Other', color: '#94a3b8' },
]

export const POLL_INTERVAL = 65000

// Magnitude Colors
// These colors provide a stark contrast against the dark base theme.
export const MAG_COLORS = {
  minor: { range: [0, 2], color: '#22d3ee', label: 'Minor' },
  light: { range: [2, 3], color: '#4ade80', label: 'Light' },
  moderate: { range: [3, 4.5], color: '#facc15', label: 'Moderate' },
  strong: { range: [4.5, 6], color: '#f97316', label: 'Strong' },
  major: { range: [6, 7], color: '#ef4444', label: 'Major' },
  great: { range: [7, 10], color: '#dc2626', label: 'Great' },
}

export const DEPTH_COLORS = {
  shallow: { range: [0, 70], color: '#ffffff' },
  mid: { range: [70, 300], color: '#a78bfa' },
  deep: { range: [300, 700], color: '#7c3aed' },
}

export const SEISMIC_ARCS = [
  { from: [35.6, 139.7], to: [-33.4, -70.6] },
  { from: [61.2, -150.0], to: [35.6, 139.7] },
  { from: [-6.2, 106.8], to: [28.2, 84.0] },
  { from: [37.8, -122.4], to: [61.2, -150.0] },
  { from: [-33.4, -70.6], to: [-41.3, 174.8] },
  { from: [37.0, 37.0], to: [28.6, 77.2] },
]

export const LOADING_PHASES = {
  LOADING_PARTICLES: 'LOADING_PARTICLES',
  READY: 'READY',
}

// Theming Palette
export const COLORS = {
  void: '#000000',
  surface: '#020a10',
  panel: 'rgba(2, 10, 16, 0.92)',
  border: 'rgba(26, 73, 92, 0.15)',
  globeDot: '#07344D',
  globeDotLit: '#1A495C',
  accent: '#467087',
  accentDim: '#07344D',
  textPrimary: '#E6E6E7',
  textMuted: '#5B5C5C',
}
