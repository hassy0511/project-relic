// キットの光の筋（割れ目から差す光など）と蒸気。足し合わせの半透明、影なし、光を受けない。
// 部品の UV.y は Blender の高さ z（m）の glTF の向き（v = 1 - z）：上の端（z = 0）が 1、下へ行くほど大きい。fade_m（m）で消える。
// 材質の "flow"（蒸気 ruins/b2_steam）：吹き出し口から外へ流れる濃淡と、ゆっくりした強弱（kit_motion.gdshaderinc の雑音。時刻は TIME だけ）。
// flow.x が 0 なら前と同じ（光の筋）。掛け算の混ぜ方（blend_mul）は使わない（gl_compatibility で黒くなる）
shader_type spatial;
render_mode unshaded, blend_add, depth_draw_never, cull_disabled, shadows_disabled;

#include "res://assets/shaders/kit_motion.gdshaderinc"

uniform vec4 color : source_color = vec4(1.0, 0.85, 0.6, 1.0);
uniform float strength = 0.25;
uniform float fade_m = 7.0;
// 蒸気の流れは kit_motion.gdshaderinc の uniform flow を使う：x = 外へ流れる速さ（m/s）、y = 模様の大きさ（m）、z = 濃淡の幅（0〜1）、
// w = ゆっくりした強弱の幅（0〜1）（落砂の面の flow とは w の意味だけ違う）

varying vec3 v_local;

void vertex() {
	v_local = VERTEX;
}

void fragment() {
	float along = clamp((UV.y - 1.0) / max(fade_m, 0.01), 0.0, 1.0);
	float edge = pow(abs(dot(NORMAL, VIEW)), 1.5);
	float k = 1.0;
	if (flow.x > 0.0) {
		// 吹き出し口からの距離（m）と、筒のまわりの角度（0〜1）。部品ごとのずれは原点の位置から
		float s = UV.y - 1.0;
		float ang = (atan(v_local.z, v_local.x) + 3.14159) * 0.159155;
		float ph = fract(dot(MODEL_MATRIX[3].xyz, vec3(0.731, 0.413, 0.527))) * 6.2832;
		float q = (s - TIME * flow.x) / max(flow.y, 0.01);
		float n = kit_noise(vec2(ang * 5.0 + ph, q + ph), 5.0) * 0.6 + kit_noise(vec2(ang * 11.0 + 2.0 * ph, q * 2.3 + 4.1), 11.0) * 0.4;
		k = max(0.0, 1.0 + flow.z * (n * 2.0 - 1.0) * 1.3);
		k *= 1.0 - flow.w * (0.5 + 0.5 * sin(TIME * 0.9 + ph));
	}
	ALBEDO = color.rgb * strength * edge * (1.0 - along) * smoothstep(0.0, 0.15, along + 0.02) * k;
}
