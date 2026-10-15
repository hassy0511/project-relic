// キットの「しみ」（汚れの置き場所の部品：床の斑・通り道・部屋の隅・壁を垂れるさびの筋。RoomKit.make_material の "blend": "mul"）。
// 下の床・壁の上に、汚れの暗い色を半透明で重ねる（下の面と同じ向きなので、光と影も同じに受ける）。中は汚れの型（masks.png の G）でむらにする。
// 縁は部品の形のまま（汚れの層と同じ、縁のはっきりした斑）。
// 初めは下の色に掛ける作り（blend_mul・光なし）だったが、スマホ・ブラウザ版（gl_compatibility）でしみが黒く塗られたので、
// 町の汚れの斑（kit_decal.gdshader）と同じ、光を受ける普通の半透明にした（2026-10-15）。"color"・"strength" は前と同じ意味
// （掛ける色・濃さ）で、掛け算に近い暗さになるように、重ねる色を color の shade 倍、不透明さを濃さの opacity 倍にしてある。
shader_type spatial;
render_mode blend_mix, depth_draw_never, cull_back;

uniform vec4 color : source_color = vec4(0.62, 0.48, 0.38, 1.0);
// 濃さ（0 = 何もしない、1 = いちばん濃い）
uniform float strength = 0.6;
uniform sampler2D detail_tex : filter_linear_mipmap, repeat_enable, hint_default_white;
uniform float uv_m = 1.6;
// むらの幅（0 = むらなし）
uniform float mottle = 0.45;
// 重ねる色の暗さ（color に掛ける）と、濃さ → 不透明さの割合
uniform float shade = 0.35;
uniform float opacity = 0.8;

void fragment() {
	float m = texture(detail_tex, UV / uv_m + vec2(0.37, 0.61)).g;
	float k = strength * mix(1.0 - mottle, 1.0, m);
	ALBEDO = color.rgb * shade;
	ROUGHNESS = 0.95;
	SPECULAR = 0.2;
	ALPHA = clamp(k * opacity, 0.0, 1.0);
}
