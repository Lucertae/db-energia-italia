// Depth -> color mapping. Shallow is bright white, deep is violet.
// This makes depth immediately visible in the UI without reading numbers.

import { DEPTH_COLORS } from '../constants'

export function getDepthColor(depthKm) {
  if (depthKm < 70) return DEPTH_COLORS.shallow.color
  if (depthKm < 300) return DEPTH_COLORS.mid.color
  return DEPTH_COLORS.deep.color
}

export function getDepthLabel(depthKm) {
  if (depthKm < 70) return 'Shallow'
  if (depthKm < 300) return 'Intermediate'
  return 'Deep'
}
