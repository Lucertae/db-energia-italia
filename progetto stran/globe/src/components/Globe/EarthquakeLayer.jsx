/**
 * EarthquakeLayer.jsx
 * 
 * Renders earthquake data points inside the 3D globe based on their depth.
 * Uses a highly optimized Instanced Points approach driven by custom WebGL shaders.
 * 
 * Data Flow:
 * - Reads pre-computed Float32Arrays from the Zustand store (populated by the Web Worker).
 * - Only applies lightweight filter indexing on the main thread.
 * - Handles time-lapse visibility, sizing, and colors entirely on the GPU via shaders.
 */

import { useRef, useMemo, memo } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import { useThree } from '@react-three/fiber'
import useStore from '../../store/useStore'
import useEarthquakeStore from '../../store/useEarthquakeStore'
import { MAX_EARTHQUAKE_POINTS, EARTHQUAKE_FADE_IN } from '../../constants'

const vertexShader = `
  attribute float aSize;
  attribute float aPhase;
  attribute float aMagnitude;
  attribute float aIsSelected;
  attribute float aIsHovered;
  attribute float aTime;
  varying vec3 vColor;
  varying float vAlpha;
  varying float vMagnitude;
  varying float vDepthFade;
  varying float vIsSelected;
  varying float vIsHovered;
  uniform float uTime;
  uniform float uFadeIn;
  uniform float uPlaybackProgress;

  void main() {
    // --- Time-lapse visibility gate ---
    // aTime is normalized [0,1] where 0=oldest, 1=newest.
    // If the playback cursor hasn't reached this point's time, hide it.
    float timeVisible = step(aTime, uPlaybackProgress);
    if (timeVisible < 0.5) {
      gl_PointSize = 0.0;
      gl_Position = vec4(2.0, 2.0, 2.0, 1.0); // Push off-screen
      vAlpha = 0.0;
      vColor = vec3(0.0);
      vMagnitude = 0.0;
      vDepthFade = 0.0;
      vIsSelected = 0.0;
      vIsHovered = 0.0;
      return;
    }

    // Smoothly fade in earthquakes that just occurred near the playback cursor
    float timeFade = smoothstep(uPlaybackProgress - 0.03, uPlaybackProgress - 0.005, aTime);
    float recentBoost = 1.0 + timeFade * 0.4;

    vColor = color;
    vMagnitude = aMagnitude;
    vIsSelected = aIsSelected;
    vIsHovered = aIsHovered;

    // Give each point a subtle pulsing animation at a unique speed
    float speed = 1.8 + aPhase * 0.6;
    float pulse = 0.85 + sin(uTime * speed + aPhase * 6.28) * 0.15;
    vAlpha = pulse * uFadeIn;

    vec4 worldPos = modelMatrix * vec4(position, 1.0);
    vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);

    // Calculate depth fade based on the normal of the sphere vs the camera direction.
    // This hides earthquakes that are on the back side of the globe.
    vec3 toCamera = normalize(cameraPosition - worldPos.xyz);
    float facing = dot(toCamera, normalize(worldPos.xyz));

    // smoothstep creates a soft horizon fade rather than a hard visual clip
    vDepthFade = smoothstep(-0.15, 0.2, facing);

    // Base point size scaled by distance to camera
    float baseSize = aSize * (48.0 / -mvPosition.z) * pulse * recentBoost;

    // Apply a size boost for major earthquakes (magnitude 6+)
    float majorBoost = step(6.0, aMagnitude) * 0.5;

    // Apply a size boost when hovered
    float interactionBoost = max(1.0, vIsHovered * 1.3);

    // Clamp the final size so mid-magnitude quakes stay legible
    float finalSize = min(baseSize * (1.0 + majorBoost), 12.0) * mix(0.4, 1.0, vDepthFade) * interactionBoost;
    
    // selected points get a massive size boost
    if (vIsSelected > 0.5) finalSize = max(finalSize, 16.0 * mix(0.4, 1.0, vDepthFade));

    gl_PointSize = finalSize;
    gl_Position = projectionMatrix * mvPosition;
  }
`

const fragmentShader = `
  varying vec3 vColor;
  varying float vAlpha;
  varying float vMagnitude;
  varying float vDepthFade;
  varying float vIsSelected;
  varying float vIsHovered;

  void main() {
    // Drop points that are completely on the backside to save fill rate
    // but mag 5+ always stay partially visible (min 0.25 fade)
    float effectiveDepthFade = vDepthFade;
    if (vMagnitude >= 5.0) effectiveDepthFade = max(effectiveDepthFade, 0.25);
    if (effectiveDepthFade <= 0.01) discard;

    float dist = length(gl_PointCoord - vec2(0.5));
    if (dist > 0.5) discard;

    // outer glow ring — soft halo behind the main dot at 15% opacity
    float outerGlow = smoothstep(0.5, 0.25, dist) * 0.15;

    // main dot with bright core
    float alpha = 1.0 - smoothstep(0.0, 0.5, dist);

    // selected: distinct hollow ring
    if (vIsSelected > 0.5) {
      float ringThickness = 0.1;
      float inner = smoothstep(0.5 - ringThickness, 0.5 - ringThickness * 0.5, dist);
      float outer = 1.0 - smoothstep(0.5 - ringThickness * 0.5, 0.5, dist);
      float ringAlpha = inner * outer;
      alpha = max(alpha * 0.2, ringAlpha * 2.0);
    } else {
      alpha = pow(alpha, 1.5);
    }

    // combine main dot with outer glow
    alpha = max(alpha, outerGlow);

    // warm center — brighter core of the quake color
    float core = 1.0 - smoothstep(0.0, 0.15, dist);
    vec3 baseCoreColor = mix(vColor, vColor * 1.4, core * 0.3);

    // hovered points glow white at core
    vec3 col = mix(baseCoreColor, vec3(1.0), vIsHovered * core * 0.8);

    // selected ring is pure white/cyan
    if (vIsSelected > 0.5 && dist > 0.3) col = mix(col, vec3(0.8, 1.0, 1.0), 0.8);

    // bloom trigger: push color above 1.0 for mag 4+ so post-processing catches it
    float bloomBoost = step(4.0, vMagnitude) * 0.4 + step(5.0, vMagnitude) * 0.3;
    col *= (1.0 + bloomBoost);

    // god ray effect for major quakes (6+)
    float isMajor = step(6.0, vMagnitude);
    if (isMajor > 0.0) {
      vec2 centered = gl_PointCoord - vec2(0.5);
      float axisProximity = min(abs(centered.x), abs(centered.y));
      float ray = (1.0 - smoothstep(0.0, 0.06, axisProximity)) * (1.0 - dist * 1.5);
      alpha += ray * 0.5;
      float diag = abs(abs(centered.x) - abs(centered.y));
      float diagRay = (1.0 - smoothstep(0.0, 0.04, diag)) * (1.0 - dist * 1.8);
      alpha += diagRay * 0.3;
      col *= 1.2;
    }

    // final output — multiply by depth fade
    gl_FragColor = vec4(col, alpha * vAlpha * effectiveDepthFade);
  }
`

const EarthquakeLayer = memo(function EarthquakeLayer() {
  const pointsRef = useRef()
  const fadeStartRef = useRef(null)
  const hoverIdxRaw = useRef(null)

  // ─── Queries: typed arrays from earthquake store (worker-produced) ───
  const srcPositions = useEarthquakeStore((s) => s.positions)
  const srcColors = useEarthquakeStore((s) => s.colors)
  const srcSizes = useEarthquakeStore((s) => s.sizes)
  const srcPhases = useEarthquakeStore((s) => s.phases)
  const srcMagnitudes = useEarthquakeStore((s) => s.magnitudes)
  const srcTimes = useEarthquakeStore((s) => s.times)
  const earthquakes = useEarthquakeStore((s) => s.earthquakes)
  const totalCount = useEarthquakeStore((s) => s.count)

  // ─── UI state from main store ───
  const filters = useStore((s) => s.filters)
  const globeReady = useStore((s) => s.ui.globeReady)
  const selectedQuake = useStore((s) => s.selectedQuake)
  const setSelectedQuake = useStore((s) => s.setSelectedQuake)
  const setCameraTarget = useStore((s) => s.setCameraTarget)
  const setUI = useStore((s) => s.setUI)
  const { gl } = useThree()

  // ─── Filter: build index of passing quakes, then slice typed arrays ───
  const { positions, colors, sizes, phases, magnitudes, isSelected, isHovered, quakeTimes, filtered } = useMemo(() => {
    if (!totalCount || !earthquakes.length) {
      return {
        positions: new Float32Array(0), colors: new Float32Array(0),
        sizes: new Float32Array(0), phases: new Float32Array(0),
        magnitudes: new Float32Array(0), isSelected: new Float32Array(0),
        isHovered: new Float32Array(0), quakeTimes: new Float32Array(0), filtered: [],
      }
    }

    // Build passing-index list (lightweight — no coordinate math)
    const indices = []
    for (let i = 0; i < earthquakes.length && indices.length < MAX_EARTHQUAKE_POINTS; i++) {
      const q = earthquakes[i]
      if (q.magnitude < filters.magnitude) continue
      if (filters.depth === 'shallow' && q.depth > 70) continue
      if (filters.depth === 'mid' && (q.depth < 70 || q.depth > 300)) continue
      if (filters.depth === 'deep' && q.depth < 300) continue
      const layer = q.layer || 'quakes'
      if (filters.layers && filters.layers[layer] === false) continue
      indices.push(i)
    }

    const count = indices.length
    const pos = new Float32Array(count * 3)
    const col = new Float32Array(count * 3)
    const sz = new Float32Array(count)
    const ph = new Float32Array(count)
    const mag = new Float32Array(count)
    const sel = new Float32Array(count)
    const hov = new Float32Array(count)
    const tm = new Float32Array(count)
    const filteredMeta = new Array(count)

    for (let j = 0; j < count; j++) {
      const i = indices[j]
      pos[j * 3] = srcPositions[i * 3]
      pos[j * 3 + 1] = srcPositions[i * 3 + 1]
      pos[j * 3 + 2] = srcPositions[i * 3 + 2]
      col[j * 3] = srcColors[i * 3]
      col[j * 3 + 1] = srcColors[i * 3 + 1]
      col[j * 3 + 2] = srcColors[i * 3 + 2]
      sz[j] = srcSizes[i]
      ph[j] = srcPhases[i]
      mag[j] = srcMagnitudes[i]
      tm[j] = srcTimes[i]
      sel[j] = (selectedQuake && selectedQuake.id === earthquakes[i].id) ? 1.0 : 0.0
      hov[j] = 0.0
      filteredMeta[j] = earthquakes[i]
    }

    return {
      positions: pos, colors: col, sizes: sz, phases: ph,
      magnitudes: mag, isSelected: sel, isHovered: hov,
      quakeTimes: tm, filtered: filteredMeta,
    }
  }, [earthquakes, totalCount, srcPositions, srcColors, srcSizes, srcPhases, srcMagnitudes, srcTimes, filters, selectedQuake])

  const uniforms = useMemo(() => ({
    uTime: { value: 0 },
    uFadeIn: { value: 0 },
    uPlaybackProgress: { value: 1.0 },
  }), [])

  useFrame(({ clock }) => {
    if (!pointsRef.current) return
    const elapsed = clock.getElapsedTime()
    const mat = pointsRef.current.material

    mat.uniforms.uTime.value = elapsed

    // fade in after globe is ready — earthquake points appear smoothly
    if (globeReady && fadeStartRef.current === null) {
      fadeStartRef.current = elapsed
    }
    if (fadeStartRef.current !== null) {
      const fadeProgress = Math.min((elapsed - fadeStartRef.current) / EARTHQUAKE_FADE_IN, 1.0)
      mat.uniforms.uFadeIn.value = fadeProgress
    }

    // ── Time-lapse playback: read progress directly from store (no re-render) ──
    const { isPlaying, speed, progress } = useStore.getState().playback
    if (isPlaying) {
      const newProgress = Math.min(progress + speed * 0.003 * (60 * Math.min(clock.getDelta(), 0.05)), 1.0)
      useStore.getState().setPlayback({ progress: newProgress })
      mat.uniforms.uPlaybackProgress.value = newProgress
    } else {
      mat.uniforms.uPlaybackProgress.value = progress
    }
  })

  if (!globeReady || !filtered.length) return null

  const handlePointerOver = (e) => {
    e.stopPropagation()
    const idx = e.index
    if (idx !== undefined) {
      hoverIdxRaw.current = idx
      gl.domElement.style.cursor = 'pointer'
      const geo = pointsRef.current.geometry
      geo.attributes.aIsHovered.array[idx] = 1.0
      geo.attributes.aIsHovered.needsUpdate = true
    }
  }

  const handlePointerOut = (e) => {
    e.stopPropagation()
    const idx = e.index
    if (idx !== undefined) {
      if (hoverIdxRaw.current === idx) hoverIdxRaw.current = null
      gl.domElement.style.cursor = 'crosshair'
      const geo = pointsRef.current.geometry
      geo.attributes.aIsHovered.array[idx] = 0.0
      geo.attributes.aIsHovered.needsUpdate = true
    }
  }

  const handleClick = (e) => {
    if (e.delta > 2) return
    e.stopPropagation()
    const idx = e.index
    if (idx !== undefined) {
      const quake = filtered[idx]
      setSelectedQuake(quake)
      const depthTilt = quake.depth > 70 ? Math.min(25, quake.depth / 10) : 0
      setCameraTarget({ lat: quake.lat - depthTilt, lng: quake.lng, zoom: 2.0 })
      setUI({ showDetail: true })
    }
  }

  return (
    <points
      ref={pointsRef}
      frustumCulled={false}
      onPointerOver={handlePointerOver}
      onPointerOut={handlePointerOut}
      onClick={handleClick}
    >
      <bufferGeometry key={filtered.length}>
        <bufferAttribute attach="attributes-position" count={filtered.length} array={positions} itemSize={3} />
        <bufferAttribute attach="attributes-color" count={filtered.length} array={colors} itemSize={3} />
        <bufferAttribute attach="attributes-aSize" count={filtered.length} array={sizes} itemSize={1} />
        <bufferAttribute attach="attributes-aPhase" count={filtered.length} array={phases} itemSize={1} />
        <bufferAttribute attach="attributes-aMagnitude" count={filtered.length} array={magnitudes} itemSize={1} />
        <bufferAttribute attach="attributes-aIsSelected" count={filtered.length} array={isSelected} itemSize={1} />
        <bufferAttribute attach="attributes-aIsHovered" count={filtered.length} array={isHovered} itemSize={1} />
        <bufferAttribute attach="attributes-aTime" count={filtered.length} array={quakeTimes} itemSize={1} />
      </bufferGeometry>
      <shaderMaterial
        vertexShader={vertexShader}
        fragmentShader={fragmentShader}
        uniforms={uniforms}
        vertexColors
        transparent
        depthWrite={false}
        blending={THREE.NormalBlending}
      />
    </points>
  )
})

export default EarthquakeLayer
