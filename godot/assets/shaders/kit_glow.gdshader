// キットの光の筋（割れ目から差す光など）。足し合わせの半透明、影なし、光を受けない。
// 部品の UV.y は Blender の高さ z（m）の glTF の向き（v = 1 - z）：上の端（z = 0）が 1、下へ行くほど大きい。fade_m（m）で消える。
shader_type spatial;
render_mode unshaded, blend_add, depth_draw_never, cull_disabled, shadows_disabled;

uniform vec4 color : source_color = vec4(1.0, 0.85, 0.6, 1.0);
uniform float strength = 0.25;
uniform float fade_m = 7.0;

void fragment() {
	float along = clamp((UV.y - 1.0) / max(fade_m, 0.01), 0.0, 1.0);
	float edge = pow(abs(dot(NORMAL, VIEW)), 1.5);
	ALBEDO = color.rgb * strength * edge * (1.0 - along) * smoothstep(0.0, 0.15, along + 0.02);
}
