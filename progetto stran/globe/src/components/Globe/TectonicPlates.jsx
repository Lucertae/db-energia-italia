// Tectonic plate boundary lines rendered as static LineSegments.
// Geometry is built once on mount — zero per-frame allocations.

import { useMemo, memo } from 'react'
import * as THREE from 'three'
import { GLOBE_RADIUS } from '../../constants'
import { PLATE_BOUNDARIES } from '../../data/plateBoundaries'

const PLATE_RADIUS = GLOBE_RADIUS * 1.002

function latLngToVec3(lat, lng, radius) {
  const phi = (90 - lat) * (Math.PI / 180)
  const theta = (lng + 180) * (Math.PI / 180)
  return [
    -(radius * Math.sin(phi) * Math.cos(theta)),
    radius * Math.cos(phi),
    radius * Math.sin(phi) * Math.sin(theta),
  ]
}

const TectonicPlates = memo(function TectonicPlates() {
  const geometry = useMemo(() => {
    // Count total line segments: each boundary of N points produces N-1 segments, each segment = 2 vertices
    let totalSegments = 0
    for (const boundary of PLATE_BOUNDARIES) {
      totalSegments += boundary.length - 1
    }

    const positions = new Float32Array(totalSegments * 2 * 3)
    let offset = 0

    for (const boundary of PLATE_BOUNDARIES) {
      for (let i = 0; i < boundary.length - 1; i++) {
        const [x1, y1, z1] = latLngToVec3(boundary[i][0], boundary[i][1], PLATE_RADIUS)
        const [x2, y2, z2] = latLngToVec3(boundary[i + 1][0], boundary[i + 1][1], PLATE_RADIUS)

        positions[offset++] = x1
        positions[offset++] = y1
        positions[offset++] = z1
        positions[offset++] = x2
        positions[offset++] = y2
        positions[offset++] = z2
      }
    }

    const geo = new THREE.BufferGeometry()
    geo.setAttribute('position', new THREE.BufferAttribute(positions, 3))
    return geo
  }, [])

  return (
    <lineSegments geometry={geometry} frustumCulled={false}>
      <lineBasicMaterial
        color="#1A495C"
        opacity={0.25}
        transparent
        blending={THREE.AdditiveBlending}
        depthWrite={false}
      />
    </lineSegments>
  )
})

export default TectonicPlates
