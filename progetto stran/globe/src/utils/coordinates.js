// Math for converting between geographic coordinates and 3D sphere positions.
// The sign flip on longitude tripped me up for hours — Three.js and geographic
// conventions disagree on which direction is positive X.

import { GLOBE_RADIUS, EARTH_RADIUS_KM } from '../constants'

/**
 * Convert lat/lng (degrees) to a position on the globe surface.
 * Returns [x, y, z] at the given radius.
 */
export function latLngToVector3(lat, lng, radius = GLOBE_RADIUS) {
  const phi = (90 - lat) * (Math.PI / 180)
  const theta = (lng + 180) * (Math.PI / 180)

  const x = -(radius * Math.sin(phi) * Math.cos(theta))
  const y = radius * Math.cos(phi)
  const z = radius * Math.sin(phi) * Math.sin(theta)

  return [x, y, z]
}

/**
 * Same as above but accounts for earthquake depth.
 * Depth in km gets mapped proportionally inside the globe.
 * 0km = surface (radius 1.0), 700km depth ≈ radius 0.89
 */
export function latLngDepthToVector3(lat, lng, depthKm) {
  const depthFraction = Math.min(depthKm, 700) / EARTH_RADIUS_KM
  const radius = GLOBE_RADIUS * (1 - depthFraction)
  return latLngToVector3(lat, lng, radius)
}

/**
 * Generate a cubic bezier arc between two points on the globe.
 * The arc height scales with distance so short arcs don't look ridiculous.
 * Returns an array of [x,y,z] points along the curve.
 */
export function generateArc(fromLatLng, toLatLng, segments = 64) {
  const [fromLat, fromLng] = fromLatLng
  const [toLat, toLng] = toLatLng

  const start = latLngToVector3(fromLat, fromLng)
  const end = latLngToVector3(toLat, toLng)

  // midpoint lifted above the surface for the arc peak
  const midLat = (fromLat + toLat) / 2
  const midLng = (fromLng + toLng) / 2

  // arc height based on distance between points
  const dx = start[0] - end[0]
  const dy = start[1] - end[1]
  const dz = start[2] - end[2]
  const dist = Math.sqrt(dx * dx + dy * dy + dz * dz)
  const arcHeight = GLOBE_RADIUS + dist * 0.4

  const mid = latLngToVector3(midLat, midLng, arcHeight)

  const points = []
  for (let i = 0; i <= segments; i++) {
    const t = i / segments
    // quadratic bezier: (1-t)^2 * P0 + 2(1-t)t * P1 + t^2 * P2
    const t2 = 1 - t
    const x = t2 * t2 * start[0] + 2 * t2 * t * mid[0] + t * t * end[0]
    const y = t2 * t2 * start[1] + 2 * t2 * t * mid[1] + t * t * end[1]
    const z = t2 * t2 * start[2] + 2 * t2 * t * mid[2] + t * t * end[2]
    points.push([x, y, z])
  }
  return points
}

/**
 * Haversine distance between two lat/lng points in km.
 * Used for "nearby quakes" feature.
 */
export function haversineDistance(lat1, lng1, lat2, lng2) {
  const R = EARTH_RADIUS_KM
  const dLat = (lat2 - lat1) * Math.PI / 180
  const dLng = (lng2 - lng1) * Math.PI / 180
  const a = Math.sin(dLat / 2) ** 2 +
    Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
    Math.sin(dLng / 2) ** 2
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
}
