/**
 * WireframeGrid.jsx
 * 
 * Generates a spherical latitude/longitude wireframe grid.
 * Renders as a web of thin lines positioned slightly outside the particle sphere
 * to provide structural volume to the globe.
 */

import { useMemo, memo } from 'react'
import * as THREE from 'three'
import { GLOBE_RADIUS } from '../../constants'

const GRID_COLOR = new THREE.Color('#1A495C')
const GRID_RADIUS = GLOBE_RADIUS * 1.005 // Render just outside the particle sphere
const LAT_COUNT = 12      // Number of horizontal rings
const LNG_COUNT = 24      // Number of vertical meridians
const SEGMENTS = 128      // Segments per line for smoothness

/**
 * Generates vertices for a single latitude ring.
 */
function createLatLine(latDeg) {
  const latRad = (latDeg * Math.PI) / 180
  const y = Math.sin(latRad) * GRID_RADIUS
  const ringRadius = Math.cos(latRad) * GRID_RADIUS
  const pts = []
  for (let i = 0; i <= SEGMENTS; i++) {
    const angle = (i / SEGMENTS) * Math.PI * 2
    pts.push(new THREE.Vector3(
      Math.cos(angle) * ringRadius,
      y,
      Math.sin(angle) * ringRadius,
    ))
  }
  return pts
}

function createLngLine(lngDeg) {
  const lngRad = (lngDeg * Math.PI) / 180
  const pts = []
  for (let i = 0; i <= SEGMENTS; i++) {
    const latRad = (i / SEGMENTS) * Math.PI - Math.PI / 2
    pts.push(new THREE.Vector3(
      Math.cos(latRad) * Math.cos(lngRad) * GRID_RADIUS,
      Math.sin(latRad) * GRID_RADIUS,
      Math.cos(latRad) * Math.sin(lngRad) * GRID_RADIUS,
    ))
  }
  return pts
}

const WireframeGrid = memo(function WireframeGrid() {
  const geometry = useMemo(() => {
    const positions = []

    // latitude lines — evenly spaced from -75° to 75° (skip poles, they collapse)
    for (let i = 0; i < LAT_COUNT; i++) {
      const lat = -75 + (150 / (LAT_COUNT - 1)) * i
      const pts = createLatLine(lat)
      for (let j = 0; j < pts.length - 1; j++) {
        positions.push(pts[j].x, pts[j].y, pts[j].z)
        positions.push(pts[j + 1].x, pts[j + 1].y, pts[j + 1].z)
      }
    }

    // longitude lines — evenly spaced around 360°
    for (let i = 0; i < LNG_COUNT; i++) {
      const lng = (360 / LNG_COUNT) * i
      const pts = createLngLine(lng)
      for (let j = 0; j < pts.length - 1; j++) {
        positions.push(pts[j].x, pts[j].y, pts[j].z)
        positions.push(pts[j + 1].x, pts[j + 1].y, pts[j + 1].z)
      }
    }

    const geo = new THREE.BufferGeometry()
    geo.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3))
    return geo
  }, [])

  return (
    <lineSegments geometry={geometry} frustumCulled={false}>
      <lineBasicMaterial
        color={GRID_COLOR}
        transparent
        opacity={0.18}
        depthWrite={false}
        blending={THREE.NormalBlending}
      />
    </lineSegments>
  )
})

export default WireframeGrid
