// Arc connections between seismic zones — dark blue, very subtle.
// The arcs should be barely visible, just enough to see the connection.

import { useRef, useMemo, memo } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import { SEISMIC_ARCS } from '../../constants'
import { generateArc } from '../../utils/coordinates'
import useStore from '../../store/useStore'

const arcVertShader = `
  attribute float aT;
  uniform float uPulsePosition;
  varying float vT;
  varying float vPulseGlow;

  void main() {
    vT = aT;

    float distToPulse = aT - uPulsePosition;
    float trail = smoothstep(-0.2, 0.0, distToPulse) * step(distToPulse, 0.0);
    float ahead = smoothstep(0.08, 0.0, distToPulse) * step(0.0, distToPulse);
    vPulseGlow = trail * 0.7 + ahead * 0.3;

    vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
    // GitHub globe style — small clean dots that trace the arc path
    gl_PointSize = (1.0 + vPulseGlow * 0.8) * (30.0 / -mvPosition.z);
    gl_Position = projectionMatrix * mvPosition;
  }
`

const arcFragShader = `
  varying float vT;
  varying float vPulseGlow;
  uniform vec3 uColor;

  void main() {
    float dist = length(gl_PointCoord - vec2(0.5));
    if (dist > 0.5) discard;

    float alpha = 1.0 - smoothstep(0.0, 0.5, dist);
    alpha = pow(alpha, 1.5);

    // gradient: brighter at endpoints, dimmer in middle
    float edgeDist = min(vT, 1.0 - vT);
    float endpointBright = 1.0 - smoothstep(0.0, 0.25, edgeDist);
    float baseAlpha = mix(0.06, 0.2, endpointBright);

    float finalAlpha = min((baseAlpha + vPulseGlow * 0.35) * alpha, 0.3);

    // pulse brightens toward light teal
    vec3 col = mix(uColor, vec3(0.25, 0.50, 0.60), vPulseGlow * 0.5);

    gl_FragColor = vec4(col, finalAlpha);
  }
`

const ARC_SEGMENTS = 64

const SingleArc = memo(function SingleArc({ from, to, index }) {
  const pointsRef = useRef()

  const { positions, tValues } = useMemo(() => {
    const pts = generateArc(from, to, ARC_SEGMENTS)
    const pos = new Float32Array(pts.length * 3)
    const tv = new Float32Array(pts.length)
    pts.forEach(([x, y, z], i) => {
      pos[i * 3] = x
      pos[i * 3 + 1] = y
      pos[i * 3 + 2] = z
      tv[i] = i / (pts.length - 1)
    })
    return { positions: pos, tValues: tv }
  }, [from, to])

  const uniforms = useMemo(() => ({
    uPulsePosition: { value: 0 },
    // teal arc color
    uColor: { value: new THREE.Color('#0d3550') },
  }), [])

  useFrame(({ clock }) => {
    if (!pointsRef.current) return
    const t = clock.getElapsedTime()
    const speed = 0.15 + index * 0.03
    const offset = index * 0.4
    pointsRef.current.material.uniforms.uPulsePosition.value =
      ((t * speed + offset) % 1.4) - 0.2
  })

  return (
    <points ref={pointsRef} frustumCulled={false}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" count={ARC_SEGMENTS + 1} array={positions} itemSize={3} />
        <bufferAttribute attach="attributes-aT" count={ARC_SEGMENTS + 1} array={tValues} itemSize={1} />
      </bufferGeometry>
      <shaderMaterial
        vertexShader={arcVertShader}
        fragmentShader={arcFragShader}
        uniforms={uniforms}
        transparent
        depthWrite={false}
        blending={THREE.NormalBlending}
      />
    </points>
  )
})

const ArcConnections = memo(function ArcConnections() {
  const globeReady = useStore((s) => s.ui.globeReady)
  if (!globeReady) return null

  return (
    <group>
      {SEISMIC_ARCS.map((arc, i) => (
        <SingleArc key={i} from={arc.from} to={arc.to} index={i} />
      ))}
    </group>
  )
})

export default ArcConnections
