// damned_waters/game/src/world/plate.gdshader
// Purpose: draw a pre-rendered background AND write its per-pixel depth into
// the depth buffer, so real-time characters are hidden by painted furniture.
// ELI5: the painting comes with a "how far away is each pixel" map. The GPU
// uses that map exactly like it would use real 3D walls.
shader_type spatial;
render_mode unshaded, cull_disabled, depth_draw_always, shadows_disabled, fog_disabled;

uniform sampler2D color_tex : source_color, filter_linear, repeat_disable;
uniform sampler2D depth_tex : filter_nearest, repeat_disable;
uniform float depth_max = 32.0;   // DepthCodec.DEPTH_MAX_M
uniform bool use_depth = true;
uniform float fade : hint_range(0.0, 1.0) = 1.0;

float decode_depth(vec2 rg) {
	float hi = floor(rg.r * 255.0 + 0.5);
	float lo = floor(rg.g * 255.0 + 0.5);
	return (hi * 256.0 + lo) / 65535.0;
}

void fragment() {
	ALBEDO = texture(color_tex, UV).rgb * fade;
	float d = use_depth ? decode_depth(texture(depth_tex, UV).rg) * depth_max : depth_max;
	d = max(d, 0.06);
	// View-space point straight ahead at planar depth d -> NDC depth. x/y don't
	// affect z for a perspective projection, so (0, 0, -d) is enough.
	vec4 clip = PROJECTION_MATRIX * vec4(0.0, 0.0, -d, 1.0);
	float ndc_z = clip.z / clip.w;
#if CURRENT_RENDERER == RENDERER_COMPATIBILITY
	DEPTH = ndc_z * 0.5 + 0.5;
#else
	DEPTH = ndc_z;
#endif
}
