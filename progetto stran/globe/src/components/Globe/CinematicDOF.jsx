// Cinematic Depth of Field — focus lerps to the selected earthquake's
// 3D position. When nothing is selected, focus sits at the globe center.
// All focus distance updates happen in useFrame via direct ref mutation
// (no React re-renders, no GC pressure).
//
// The effect is intentionally subtle — just enough to add depth separation
// between the globe and distant orbital rings without washing out detail.

import { useRef, memo } from 'react'
import { useFrame, useThree } from '@react-three/fiber'
import { DepthOfField } from '@react-three/postprocessing'
import * as THREE from 'three'
import useStore from '../../store/useStore'
import { latLngDepthToVector3 } from '../../utils/coordinates'

// Pre-allocated scratch vectors — never allocate in useFrame
const _targetPos = new THREE.Vector3()
const _currentFocus = new THREE.Vector3()
const _globeCenter = new THREE.Vector3(0, 0, 0)

const LERP_SPEED = 3.0

const CinematicDOF = memo(function CinematicDOF() {
  const dofRef = useRef()
  const { camera } = useThree()
  const selectedRef = useRef(null)
  const focusInitialized = useRef(false)

  useFrame((_, delta) => {
    if (!dofRef.current) return

    const quake = useStore.getState().selectedQuake
    if (quake && quake !== selectedRef.current) {
      selectedRef.current = quake
      const [x, y, z] = latLngDepthToVector3(quake.lat, quake.lng, quake.depth)
      _targetPos.set(x, y, z)
    } else if (!quake) {
      selectedRef.current = null
      _targetPos.copy(_globeCenter)
    }

    if (!focusInitialized.current) {
      focusInitialized.current = true
      _currentFocus.copy(_targetPos)
    }

    const lerpFactor = 1 - Math.exp(-LERP_SPEED * delta)
    _currentFocus.lerp(_targetPos, lerpFactor)

    // focusDistance is normalized: distance-to-focus / camera.far
    const distToFocus = camera.position.distanceTo(_currentFocus)
    const normalizedDist = distToFocus / camera.far

    const uniforms = dofRef.current.circleOfConfusionMaterial.uniforms
    if (uniforms.focusDistance) {
      uniforms.focusDistance.value = normalizedDist
    }
  })

  // Initial focusDistance: camera starts at z=2.8, globe at origin → dist = ~2.83
  // Normalized: 2.83 / 100 (far plane) ≈ 0.028
  return (
    <DepthOfField
      ref={dofRef}
      focusDistance={0.028}
      focalLength={0.015}
      bokehScale={0.8}
      focusRange={0.04}
    />
  )
})

export default CinematicDOF
