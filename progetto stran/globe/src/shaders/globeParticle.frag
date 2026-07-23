// Globe particle fragment — dark holographic dots.
// Per-particle opacity jitter keeps the globe translucent and ethereal.
// Ceiling: rgb(0.18, 0.42, 0.52). Nothing brighter, ever.

uniform vec3 uBaseColor;
uniform vec3 uLitColor;
uniform float uGlobeOpacity;

varying float vRandom;
varying float vDepthFade;
varying float vOpacityJitter;

void main() {
  float dist = length(gl_PointCoord - vec2(0.5));
  if (dist > 0.5) discard;

  // crisp circular dot — tighter falloff for sharper edges
  float alpha = 1.0 - smoothstep(0.0, 0.42, dist);
  alpha *= 0.50; // base opacity — high enough to read, low enough to see through
  alpha *= vOpacityJitter; // per-particle randomization (0.5–1.0)

  // bright core — subtle center highlight for definition
  float core = 1.0 - smoothstep(0.0, 0.15, dist);
  alpha += core * 0.12;

  // teal color with slight variation
  vec3 color = mix(uBaseColor, uLitColor, vRandom * 0.4);

  // brighten center slightly
  color = mix(color, uLitColor, core * 0.3);

  // hard clamp — teal ceiling, visible but restrained
  color = min(color, vec3(0.18, 0.42, 0.52));

  gl_FragColor = vec4(color, alpha * vDepthFade * uGlobeOpacity);
}
