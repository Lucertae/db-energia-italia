// Generates land-based particles using the GitHub globe technique:
// sampling an equirectangular world map image to find land pixels.

import { latLngToVector3 } from './coordinates'
import {
  GLOBE_RADIUS,
  PARTICLE_BASE_SIZE,
  PARTICLE_SIZE_VARIANCE,
} from '../constants'

export function seededRandom(seed) {
  let s = seed
  return () => {
    s = (s * 16807) % 2147483647
    return (s - 1) / 2147483646
  }
}

/**
 * Async load the world map image, draw to a hidden canvas, and return the pixel data.
 */
export async function loadMapData(imageUrl) {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.crossOrigin = 'anonymous'
    img.onload = () => {
      const canvas = document.createElement('canvas')
      canvas.width = img.width
      canvas.height = img.height
      const ctx = canvas.getContext('2d', { willReadFrequently: true })
      ctx.drawImage(img, 0, 0)
      resolve({
        width: img.width,
        height: img.height,
        data: ctx.getImageData(0, 0, img.width, img.height).data
      })
    }
    img.onerror = reject
    img.src = imageUrl
  })
}

/**
 * Convert lat/lng to image XY and check if the pixel specifies land.
 */
function visibilityForCoordinate(lng, lat, mapData) {
  // map image fits -180 to 180 longitude, 90 to -90 latitude
  const x = Math.floor(((lng + 180) / 360) * mapData.width)
  const y = Math.floor(((90 - lat) / 180) * mapData.height)

  // clamp to prevent out of bounds reading
  const safeX = Math.max(0, Math.min(x, mapData.width - 1))
  const safeY = Math.max(0, Math.min(y, mapData.height - 1))

  const index = (safeY * mapData.width + safeX) * 4

  // The provided image (earth-water.png) has water as white and land as black.
  // We check the red channel. If it's dark (< 128), it's land.
  const r = mapData.data[index]
  return r < 128
}

/**
 * Generate full sphere grid, sample the map, and fill particle buffers.
 * Returns the actual number of particles created.
 */
export function generateImageBasedParticles(
  mapData, positions, sizes, randoms,
  maxCount, rows = 200, dotDensity = 210
) {
  const rand = seededRandom(42)
  let idx = 0

  // The GitHub technique: vary dots per row based on circumference at that latitude
  for (let lat = -90; lat <= 90; lat += 180 / rows) {
    const radius = Math.cos(Math.abs(lat) * (Math.PI / 180)) * GLOBE_RADIUS
    const circumference = radius * Math.PI * 2
    const dotsForLat = Math.max(1, Math.floor(circumference * dotDensity))

    for (let x = 0; x < dotsForLat; x++) {
      if (idx >= maxCount) return idx // Safety check if buffer fills

      const lng = -180 + (x * 360) / dotsForLat
      if (!visibilityForCoordinate(lng, lat, mapData)) continue

      // Add a tiny bit of jitter so the grid feels more organic and less rigid
      const jitterLat = lat + (rand() - 0.5) * (180 / rows) * 0.4
      const jitterLng = lng + (rand() - 0.5) * (360 / dotsForLat) * 0.4
      const radiusJitter = GLOBE_RADIUS + (rand() - 0.5) * 0.005

      const [px, py, pz] = latLngToVector3(jitterLat, jitterLng, radiusJitter)

      positions[idx * 3] = px
      positions[idx * 3 + 1] = py
      positions[idx * 3 + 2] = pz

      // Random variance between 0.8x and 1.2x
      const sizeMultiplier = 0.8 + rand() * 0.4
      sizes[idx] = PARTICLE_BASE_SIZE * sizeMultiplier

      randoms[idx] = rand()

      idx++
    }
  }

  return idx // Returns the actual count of particles we wrote
}
