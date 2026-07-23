// Magnitude -> visual properties. The exponential scaling is important because
// a mag 7 releases ~1000x more energy than a mag 5, so linear scaling looks wrong.

import { MAG_COLORS } from '../constants'

export function getMagnitudeColor(mag) {
  if (mag >= 7) return MAG_COLORS.great.color
  if (mag >= 6) return MAG_COLORS.major.color
  if (mag >= 4.5) return MAG_COLORS.strong.color
  if (mag >= 3) return MAG_COLORS.moderate.color
  if (mag >= 2) return MAG_COLORS.light.color
  return MAG_COLORS.minor.color
}

export function getMagnitudeLabel(mag) {
  if (mag >= 7) return 'Great'
  if (mag >= 6) return 'Major'
  if (mag >= 4.5) return 'Strong'
  if (mag >= 3) return 'Moderate'
  if (mag >= 2) return 'Light'
  return 'Minor'
}

// point size in 3D — exponential so big quakes stand out, but tightly controlled
// to prevent massive blobs on the globe (GitHub globe approach: small, clean dots)
export function getMagnitudeSize(mag) {
  return Math.max(0.002, 0.002 * Math.pow(1.45, Math.max(0, mag)))
}

// color as [r, g, b] floats for shader use
export function getMagnitudeColorRGB(mag) {
  const hex = getMagnitudeColor(mag)
  return hexToRGB(hex)
}

export function hexToRGB(hex) {
  const r = parseInt(hex.slice(1, 3), 16) / 255
  const g = parseInt(hex.slice(3, 5), 16) / 255
  const b = parseInt(hex.slice(5, 7), 16) / 255
  return [r, g, b]
}
