// キットの「しみ」（汚れの置き場所の部品：床の斑・通り道・部屋の隅・壁を垂れるさびの筋。RoomKit.make_material の "blend": "mul"）。
// 下に描いてある物の色に掛ける（blend_mul）：床・壁の絵と継ぎ目は残したまま、そこだけ暗く・さび色にする。光の影響は受けない
// （掛ける相手がもう光を受けた色なので）。中は汚れの型（masks.png の G）でむらにする。縁は部品の形のまま（汚れの層と同じ、縁のはっきりした斑）。
shader_type spatial;
render_mode unshaded, blend_mul, depth_draw_never, shadows_disabled, cull_back, fog_disabled;

uniform vec4 color : source_color = vec4(0.62, 0.48, 0.38, 1.0);
// 濃さ（0 = 何もしない、1 = color をそのまま掛ける）
uniform float strength = 0.6;
uniform sampler2D detail_tex : filter_linear_mipmap, repeat_enable, hint_default_white;
uniform float uv_m = 1.6;
// むらの幅（0 = むらなし）
uniform float mottle = 0.45;

void fragment() {
	float m = texture(detail_tex, UV / uv_m + vec2(0.37, 0.61)).g;
	float k = strength * mix(1.0 - mottle, 1.0, m);
	ALBEDO = mix(vec3(1.0), color.rgb, k);
}
