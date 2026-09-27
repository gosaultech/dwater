// damned_waters/game/src/ui/film_grain.gdshader
// Purpose: very subtle animated grain + vignette. Grain breaks up banding in
// dark pre-rendered gradients; it should be felt, not seen.
shader_type canvas_item;

uniform float grain_strength = 0.022;
uniform float vignette_strength = 0.5;

float hash(vec2 p) {
	return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453);
}

void fragment() {
	float n = hash(floor(FRAGCOORD.xy) + fract(TIME * 7.13) * 311.0);
	float v = smoothstep(0.45, 1.0, distance(SCREEN_UV, vec2(0.5)) * 1.3);
	// Soft gray grain (0.5 +- small) blended at low alpha, plus black vignette.
	float grain_a = grain_strength * (1.0 - v);
	COLOR = vec4(vec3(n), grain_a);
	COLOR = mix(COLOR, vec4(0.0, 0.0, 0.0, 1.0), v * vignette_strength);
}
