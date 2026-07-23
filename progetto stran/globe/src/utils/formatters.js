// Display formatting utilities. Nothing fancy, just consistent output.

export function timeAgo(timestamp) {
  const seconds = Math.floor((Date.now() - timestamp) / 1000)
  if (seconds < 60) return `${seconds}s ago`
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  return `${days}d ago`
}

export function formatCoord(lat, lng) {
  const latDir = lat >= 0 ? 'N' : 'S'
  const lngDir = lng >= 0 ? 'E' : 'W'
  return `${Math.abs(lat).toFixed(3)}°${latDir} ${Math.abs(lng).toFixed(3)}°${lngDir}`
}

export function formatDepth(km) {
  if (km < 1) return '<1 km'
  return `${km.toFixed(1)} km`
}

export function formatMagnitude(mag) {
  return mag.toFixed(1)
}

export function formatNumber(n) {
  return n.toLocaleString()
}
