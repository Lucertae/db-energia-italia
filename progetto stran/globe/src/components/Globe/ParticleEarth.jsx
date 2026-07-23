/**
 * ParticleEarth.jsx
 * 
 * Generates and renders the 3D globe surface using a particle system.
 * The particles are placed by sampling a high-resolution equirectangular world map image.
 * This technique provides a stylized, dotted representation of Earth's landmasses.
 */

import { useRef, useMemo, useEffect, useState } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import { loadMapData, generateImageBasedParticles } from '../../utils/landGenerator'
import {
  PARTICLE_COUNT,
  BREATHING_AMPLITUDE,
  LOADING_PHASES,
} from '../../constants'
import useStore from '../../store/useStore'

import vertexShader from '../../shaders/globeParticle.vert?raw'
import fragmentShader from '../../shaders/globeParticle.frag?raw'

const MAP_IMAGE_URL = '/textures/world-map.png'

export default function ParticleEarth() {
  const pointsRef = useRef()
  const geometryRef = useRef()

  const [mapData, setMapData] = useState(null)
  const currentCount = useRef(0)
  const readyFired = useRef(false)

  const setUI = useStore((s) => s.setUI)
  const setLoadingPhase = useStore((s) => s.setLoadingPhase)
  const setParticleProgress = useStore((s) => s.setParticleProgress)

  // pre-allocate max-size buffers
  const buffers = useMemo(() => ({
    positions: new Float32Array(PARTICLE_COUNT * 3),
    sizes: new Float32Array(PARTICLE_COUNT),
    randoms: new Float32Array(PARTICLE_COUNT),
  }), [])

  const uniforms = useMemo(() => ({
    uTime: { value: 0 },
    uBreathingAmplitude: { value: BREATHING_AMPLITUDE },
    // teal palette — CenturyLink reference
    uBaseColor: { value: new THREE.Color('#07344D') },
    uLitColor: { value: new THREE.Color('#1A495C') },
    uGlobeOpacity: { value: 1.0 },
  }), [])

  // 1. Fetch map image on mount
  useEffect(() => {
    setLoadingPhase(LOADING_PHASES.LOADING_PARTICLES)
    loadMapData(MAP_IMAGE_URL)
      .then((data) => {
        setMapData(data)
      })
      .catch((err) => {
        console.error("Failed to load map data:", err)
      })
  }, [setLoadingPhase])

  // 2. Once mapData is available, generate the particles
  useEffect(() => {
    if (!mapData) {
      // Hide points until valid
      if (geometryRef.current) {
        geometryRef.current.setDrawRange(0, 0)
      }
      return
    }

    // Generate all dots in one synchronous pass (it's fast enough)
    const count = generateImageBasedParticles(
      mapData,
      buffers.positions,
      buffers.sizes,
      buffers.randoms,
      PARTICLE_COUNT
    )

    currentCount.current = count

    // Tell Three.js to use the new data and only draw up to the actual count
    const geo = geometryRef.current
    if (geo) {
      if (geo.attributes.position) geo.attributes.position.needsUpdate = true
      if (geo.attributes.aSize) geo.attributes.aSize.needsUpdate = true
      if (geo.attributes.aRandom) geo.attributes.aRandom.needsUpdate = true
      geo.setDrawRange(0, count)
    }

    setParticleProgress(1)
    setLoadingPhase(LOADING_PHASES.READY)

  }, [mapData, buffers, setLoadingPhase, setParticleProgress])

  useFrame(({ clock }) => {
    if (!pointsRef.current) return
    pointsRef.current.material.uniforms.uTime.value = clock.getElapsedTime()

    // fire globeReady once generation finishes
    if (currentCount.current > 0 && !readyFired.current) {
      readyFired.current = true
      setUI({ globeReady: true })
    }
  })

  return (
    <points ref={pointsRef} frustumCulled={false}>
      <bufferGeometry ref={geometryRef}>
        <bufferAttribute
          attach="attributes-position"
          count={PARTICLE_COUNT}
          array={buffers.positions}
          itemSize={3}
        />
        <bufferAttribute
          attach="attributes-aSize"
          count={PARTICLE_COUNT}
          array={buffers.sizes}
          itemSize={1}
        />
        <bufferAttribute
          attach="attributes-aRandom"
          count={PARTICLE_COUNT}
          array={buffers.randoms}
          itemSize={1}
        />
      </bufferGeometry>
      <shaderMaterial
        vertexShader={vertexShader}
        fragmentShader={fragmentShader}
        uniforms={uniforms}
        transparent
        depthWrite={false}
        blending={THREE.NormalBlending}
      />
    </points>
  )
}
