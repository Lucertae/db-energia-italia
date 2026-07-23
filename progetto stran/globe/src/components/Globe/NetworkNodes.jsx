// Network node points — static glowing teal dots at major seismic zones.
// These are reference markers, NOT earthquake points.
// They give the globe a "data network" feel like the CenturyLink reference.

import { useMemo, memo } from 'react'
import * as THREE from 'three'
import { GLOBE_RADIUS } from '../../constants'
import useStore from '../../store/useStore'

// Major seismic zone locations [lat, lng]
const NODE_LOCATIONS = [
    [35.6, 139.7],    // Tokyo
    [-33.4, -70.6],   // Santiago
    [61.2, -150.0],   // Anchorage
    [-6.2, 106.8],    // Jakarta
    [37.8, -122.4],   // San Francisco
    [28.6, 77.2],     // Delhi
    [-41.3, 174.8],   // Wellington
    [37.0, 37.0],     // Turkey
    [28.2, 84.0],     // Nepal
    [38.7, -9.1],     // Lisbon
    [-12.0, -77.0],   // Lima
    [14.6, 121.0],    // Manila
    [39.9, 116.4],    // Beijing
    [-34.6, -58.4],   // Buenos Aires
]

function latLngToVec3(lat, lng, radius) {
    const phi = (90 - lat) * (Math.PI / 180)
    const theta = (lng + 180) * (Math.PI / 180)
    return new THREE.Vector3(
        -radius * Math.sin(phi) * Math.cos(theta),
        radius * Math.cos(phi),
        radius * Math.sin(phi) * Math.sin(theta),
    )
}

const nodeVertShader = `
  attribute float aPhase;
  varying float vPhase;

  void main() {
    vPhase = aPhase;
    vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
    gl_PointSize = 1.5 * (25.0 / -mvPosition.z);
    gl_Position = projectionMatrix * mvPosition;
  }
`

const nodeFragShader = `
  varying float vPhase;

  void main() {
    float dist = length(gl_PointCoord - vec2(0.5));
    if (dist > 0.5) discard;

    // soft glow dot
    float alpha = 1.0 - smoothstep(0.0, 0.5, dist);
    alpha = pow(alpha, 1.2);

    // teal glow color
    vec3 color = vec3(0.275, 0.44, 0.53);

    // outer glow ring
    float ring = smoothstep(0.25, 0.35, dist) * (1.0 - smoothstep(0.35, 0.5, dist));
    alpha = max(alpha * 0.4, ring * 0.2);

    gl_FragColor = vec4(color, alpha);
  }
`

const NetworkNodes = memo(function NetworkNodes() {
    const globeReady = useStore((s) => s.ui.globeReady)

    const { positions, phases } = useMemo(() => {
        const pos = new Float32Array(NODE_LOCATIONS.length * 3)
        const ph = new Float32Array(NODE_LOCATIONS.length)

        NODE_LOCATIONS.forEach(([lat, lng], i) => {
            const v = latLngToVec3(lat, lng, GLOBE_RADIUS * 1.008)
            pos[i * 3] = v.x
            pos[i * 3 + 1] = v.y
            pos[i * 3 + 2] = v.z
            ph[i] = Math.random()
        })

        return { positions: pos, phases: ph }
    }, [])

    if (!globeReady) return null

    return (
        <points frustumCulled={false}>
            <bufferGeometry>
                <bufferAttribute
                    attach="attributes-position"
                    count={NODE_LOCATIONS.length}
                    array={positions}
                    itemSize={3}
                />
                <bufferAttribute
                    attach="attributes-aPhase"
                    count={NODE_LOCATIONS.length}
                    array={phases}
                    itemSize={1}
                />
            </bufferGeometry>
            <shaderMaterial
                vertexShader={nodeVertShader}
                fragmentShader={nodeFragShader}
                transparent
                depthWrite={false}
                blending={THREE.AdditiveBlending}
            />
        </points>
    )
})

export default NetworkNodes
