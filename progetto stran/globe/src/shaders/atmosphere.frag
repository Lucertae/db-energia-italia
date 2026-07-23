// Atmosphere — dark teal haze at silhouette edges.
// Visible enough to define the globe's edge against the void.

uniform vec3 uColor;
uniform float uIntensity;

varying vec3 vNormal;
varying vec3 vWorldPosition;

void main() {
  vec3 viewDir = normalize(cameraPosition - vWorldPosition);
  float fresnel = 1.0 - abs(dot(viewDir, vNormal));

  // tighter fresnel power for a clean rim, not a blob
  float glow = pow(fresnel, 4.0) * uIntensity;

  // two-layer glow: tight bright rim + wide soft halo
  float tightRim = pow(fresnel, 8.0) * 0.35;
  float wideHalo = pow(fresnel, 2.5) * 0.06;

  float finalGlow = tightRim + wideHalo;

  gl_FragColor = vec4(uColor, finalGlow);
}
