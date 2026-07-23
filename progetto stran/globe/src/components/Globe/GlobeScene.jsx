/**
 * GlobeScene.jsx
 * 
 * The main React Three Fiber Canvas container.
 * Sets up the camera, 3D environment, and post-processing effects.
 * 
 * Note on Post-Processing:
 * Bloom is configured with a high luminance threshold (0.65). 
 * This ensures that only the bright earthquake points trigger the glow effect,
 * while the dark teal globe particles remain sharp and unaffected.
 */

import { Suspense, lazy, memo } from 'react'
import { Canvas } from '@react-three/fiber'
import { EffectComposer, Bloom, Vignette } from '@react-three/postprocessing'
import NetworkNodes from './NetworkNodes'
import ParticleEarth from './ParticleEarth'
import Atmosphere from './Atmosphere'
import OrbitalRings from './OrbitalRings'
import WireframeGrid from './WireframeGrid'
import TectonicPlates from './TectonicPlates'
import CameraRig from './CameraRig'

const ArcConnections = lazy(() => import('./ArcConnections'))
const EarthquakeLayer = lazy(() => import('./EarthquakeLayer'))

const GlobeScene = memo(function GlobeScene() {
  return (
    <Canvas
      camera={{ position: [0, 0.3, 2.8], fov: 45, near: 0.1, far: 100 }}
      gl={{
        antialias: true,
        alpha: false,
        powerPreference: 'high-performance',
      }}
      style={{ background: '#000000' }}
      dpr={[1, 2]}
      performance={{ min: 0.5 }}
    >
      <color attach="background" args={['#000000']} />

      <Suspense fallback={null}>
        <ParticleEarth />
        <WireframeGrid />
        <TectonicPlates />
        <Atmosphere />
        <OrbitalRings />
        <ArcConnections />
        <NetworkNodes />
        <EarthquakeLayer />
      </Suspense>

      <CameraRig />

      <EffectComposer multisampling={0}>
        <Bloom
          intensity={0.35}
          luminanceThreshold={0.65}
          luminanceSmoothing={0.3}
          radius={0.4}
          mipmapBlur
        />
        <Vignette offset={0.2} darkness={0.55} />
      </EffectComposer>
    </Canvas>
  )
})

export default GlobeScene
