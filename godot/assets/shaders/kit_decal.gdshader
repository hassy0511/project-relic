// キットの「汚れの斑」の材質（材質の "blend": "decal"。RoomKit.make_material。42 章 14.2.1）。
// 床に置いた板の部品（town/grime_patch・town/oil_patch）が、下に描いた床の上に汚れの色を重ねる（半透明。床と同じ向きで光・影を受ける）。
// 斑の形は汚れの型の絵（assets/kit/grime/masks.png の G）をワールドの (x, z) で読み、1 本のしきい値で切る（kit_detail と同じ縁のはっきりした平らな斑）。
// 覆う割合は板の真ん中で cover、縁へ向かって 0 に下がる（板の四角い形は見えない）。遠く（fade_far）では消す（床とのちらつきを避ける）。
// 掛け算の半透明（blend_mul）は、スマホ・ブラウザ版（gl_compatibility）で板が黒く塗られたので使わない。
shader_type spatial;
render_mode blend_mix, depth_draw_never, cull_back;

uniform sampler2D detail_tex : filter_linear_mipmap_anisotropic, repeat_enable, hint_default_black;
// 汚れの色（パレット）と、いちばん濃い所の不透明さ
uniform vec4 color : source_color = vec4(0.66, 0.55, 0.42, 1.0);
uniform float amount = 0.5;
uniform float roughness_value = 0.95;
// 板の真ん中の覆う割合（0〜1）と、縁の幅（型の値で）
uniform float cover = 0.6;
uniform float edge = 0.04;
// 型の 1 枚の大きさ（m）と、ずらし
uniform float uv_m = 2.0;
uniform vec2 offset = vec2(0.21, 0.47);
// 板の縁から内へ、覆う割合を 0 から cover まで上げる範囲（板の半径を 1 とした割合）
uniform vec2 falloff = vec2(0.3, 1.0);
// カメラからこの距離（m）で消える（0.7 倍から薄くする）
uniform float fade_far = 70.0;

varying vec2 wpos;
varying vec2 lpos;

void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xz;
	lpos = VERTEX.xz;
}

void fragment() {
	float r = length(lpos) * 2.0;
	float w = cover * (1.0 - smoothstep(falloff.x, falloff.y, r));
	float m = texture(detail_tex, wpos / uv_m + offset).g;
	float e = max(edge, fwidth(m) * 0.7);
	float th = mix(1.0 + e, -e, clamp(w, 0.0, 1.0));
	float p = smoothstep(th - e, th + e, m);
	p *= 1.0 - smoothstep(fade_far * 0.7, fade_far, length(VERTEX));
	ALBEDO = color.rgb;
	ROUGHNESS = roughness_value;
	ALPHA = clamp(p * amount, 0.0, 1.0);
}
