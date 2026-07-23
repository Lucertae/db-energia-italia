// Nearly invisible dark blue atmosphere haze. NOT bright. NOT white.
// Just a whisper of dark blue at the silhouette edges.

import { useMemo, memo } from 'react'
import * as THREE from 'three'
import { GLOBE_RADIUS } from '../../constants'

import vertexShader from '../../shaders/atmosphere.vert?raw'
import fragmentShader from '../../shaders/atmosphere.frag?raw'

const Atmosphere = memo(function Atmosphere() {
  const uniforms = useMemo(() => ({
    uColor: { value: new THREE.Color('#0e6080') },
    uIntensity: { value: 1.0 },
  }), [])

  return (
    <mesh
      scale={[1.12, 1.12, 1.12]}
      rotation={[Math.PI * 0.03, Math.PI * 0.03, 0]}
    >
      <sphereGeometry args={[GLOBE_RADIUS, 64, 64]} />
      <shaderMaterial
        vertexShader={vertexShader}
        fragmentShader={fragmentShader}
        uniforms={uniforms}
        transparent
        side={THREE.BackSide}
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </mesh>
  )
})

export default Atmosphere
