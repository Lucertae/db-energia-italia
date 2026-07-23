// Decorative rings — subtle teal. Visible but not dominant.

import { useMemo, memo, useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import { Line } from '@react-three/drei'
import { GLOBE_RADIUS } from '../../constants'

const Ring = memo(function Ring({ radius, rotation, opacity = 0.06 }) {
  const points = useMemo(() => {
    const pts = []
    const segments = 128
    for (let i = 0; i <= segments; i++) {
      const angle = (i / segments) * Math.PI * 2
      pts.push([Math.cos(angle) * radius, 0, Math.sin(angle) * radius])
    }
    return pts
  }, [radius])

  return (
    <group rotation={rotation}>
      <Line
        points={points}
        color="#0f3d55"
        lineWidth={1}
        transparent
        opacity={opacity}
      />
    </group>
  )
})

const OrbitalRings = memo(function OrbitalRings() {
  const groupRef = useRef()

  useFrame((state, delta) => {
    if (groupRef.current) {
      // Very slow rotation for parallax depth effect
      groupRef.current.rotation.y += delta * 0.05
    }
  })

  return (
    <group ref={groupRef}>
      <Ring
        radius={GLOBE_RADIUS * 1.35}
        rotation={[Math.PI * 0.08, 0, Math.PI * 0.15]}
        opacity={0.14}
      />
      <Ring
        radius={GLOBE_RADIUS * 1.5}
        rotation={[-Math.PI * 0.12, Math.PI * 0.3, Math.PI * 0.05]}
        opacity={0.1}
      />
    </group>
  )
})

export default OrbitalRings
