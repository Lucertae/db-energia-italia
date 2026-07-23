// Camera controls — orbit with smooth auto-rotation and fly-to.
//
// Fly-to uses a cubic deceleration curve (1 - (1-t)^3) instead of constant lerp.
// This starts fast and slows down smoothly — feels cinematic, not mechanical.
// The constant lerp (0.04) from v1 felt floaty and took forever to settle.

import { useRef, useEffect, memo } from 'react'
import { useFrame, useThree } from '@react-three/fiber'
import { OrbitControls } from '@react-three/drei'
import * as THREE from 'three'
import useStore from '../../store/useStore'
import { latLngToVector3 } from '../../utils/coordinates'

// pre-allocated — no new Vector3() in useFrame
const _flyStart = new THREE.Vector3()
const _flyEnd = new THREE.Vector3()
const _interpolated = new THREE.Vector3()

const CameraRig = memo(function CameraRig() {
  const controlsRef = useRef()
  const flyTarget = useRef(null)
  const flyStartPos = useRef(null)
  const flyProgress = useRef(0)
  const initialMount = useRef(true)
  const { camera } = useThree()

  const cameraTarget = useStore((s) => s.cameraTarget)
  const selectedQuake = useStore((s) => s.selectedQuake)

  // On mobile, bring the camera closer so the globe fills the screen
  useEffect(() => {
    const isMobile = window.innerWidth <= 700
    if (isMobile) {
      camera.position.set(0, 0.15, 2.35)
    }
  }, [camera])

  useEffect(() => {
    if (initialMount.current) {
      initialMount.current = false
      return
    }
    if (!controlsRef.current) return

    const [x, y, z] = latLngToVector3(cameraTarget.lat, cameraTarget.lng, cameraTarget.zoom)
    _flyEnd.set(x, y, z)
    _flyStart.copy(camera.position)

    flyStartPos.current = _flyStart.clone()
    flyTarget.current = _flyEnd.clone()
    flyProgress.current = 0
  }, [cameraTarget, camera])

  useFrame((_, delta) => {
    if (!controlsRef.current || !flyTarget.current || !flyStartPos.current) return

    // advance progress — speed tuned so most fly-tos take ~1.5 seconds
    flyProgress.current += delta * 1.2
    const t = Math.min(flyProgress.current, 1.0)

    // cubic ease-out: fast start, smooth deceleration
    // feels like the camera is decelerating to a stop, not floating endlessly
    const eased = 1 - Math.pow(1 - t, 3)

    _interpolated.lerpVectors(flyStartPos.current, flyTarget.current, eased)
    camera.position.copy(_interpolated)

    if (t >= 1.0) {
      flyTarget.current = null
      flyStartPos.current = null
    }
  })

  return (
    <OrbitControls
      ref={controlsRef}
      enablePan={false}
      enableDamping
      dampingFactor={0.06}
      minDistance={1.5}
      maxDistance={6}
      autoRotate={!selectedQuake}
      autoRotateSpeed={0.3}
      rotateSpeed={0.5}
    />
  )
})

export default CameraRig
