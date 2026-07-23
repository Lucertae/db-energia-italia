// Globe particle vertex shader — no assembly animation.
// Particles are at their final positions from frame 1.
// Depth-of-field: far-side particles shrink + dim to sell the sphere illusion.
// Per-particle opacity jitter creates holographic transparency.

uniform float uTime;
uniform float uBreathingAmplitude;

attribute float aSize;
attribute float aRandom;

varying float vRandom;
varying float vDepthFade;
varying float vOpacityJitter;

void main() {
  vRandom = aRandom;
  // randomize each dot's opacity so the globe reads as translucent, not solid
  vOpacityJitter = mix(0.5, 1.0, aRandom);

  vec3 pos = position;

  // very subtle breathing — the globe barely moves, just enough to feel alive
  vec3 normal = normalize(pos);
  float breathe = sin(uTime * 0.5 + aRandom * 6.28) * uBreathingAmplitude;
  pos += normal * breathe;

  // depth-of-field: dot product with view direction
  // front-facing = full size, back-facing = smaller and dimmer
  vec4 worldPos = modelMatrix * vec4(pos, 1.0);
  vec3 toCamera = normalize(cameraPosition - worldPos.xyz);
  float facing = dot(toCamera, normalize(worldPos.xyz));
  float depthScale = smoothstep(-0.2, 0.4, facing);
  vDepthFade = mix(0.04, 0.9, depthScale);

  vec4 mvPosition = modelViewMatrix * vec4(pos, 1.0);
  // 54.0 — crisper dots that hold definition at high DPR
  gl_PointSize = aSize * (54.0 / -mvPosition.z) * mix(0.18, 0.75, depthScale);
  gl_Position = projectionMatrix * mvPosition;
}
