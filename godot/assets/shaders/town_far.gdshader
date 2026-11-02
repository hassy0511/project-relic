shader_type spatial;
// 背の上の遠くの町（キットの部品 town/ordo_town・town/ordo_back。tools/blender/kit/town_far.py）。OrdoView の back_mesh が使う。
// 色 = 絵の帳 town_far.png（1024 × 1024、128 画素の升目 × 64：家の正面の 1 間 × 1 階・屋根・布・材）× 頂点の色（家ごとの色と足元の陰。線形）。
// 夜の灯：帳の A（窓のガラス・扉の上の明かり取り・店の中・灯の芯）× 頂点の色の A（灯の順。0 = 光らない）。
//   power：明るさ（OrdoView が雰囲気の明るさ（昼 0・夜明け 0.6・夜 1）× set_back_lights の明るさを渡す）、
//   flicker：ちらつき（0〜1）、out_amount：消えた割合（0〜1。灯の順が out_amount 以下の灯は消え、その手前の 0.15 は強くちらつく）。
//   灯の点 TownLights（town_lights.gdshader）と同じ決まりなので、同じ灯の順の窓と点が一緒に消える。
// blend_mul は使わない（スマホ・ブラウザ版の描き方で黒くなる：設計 42 の決まり）
render_mode cull_back, diffuse_lambert, specular_schlick_ggx;

uniform sampler2D atlas : source_color, filter_linear_mipmap_anisotropic, repeat_disable;
uniform float power = 0.0;
uniform float flicker = 0.0;
uniform float out_amount = 0.0;
uniform float energy = 2.4;
uniform vec3 warm : source_color = vec3(1.0, 0.6, 0.27);
uniform vec3 cool : source_color = vec3(1.0, 0.8, 0.52);

float hash(float n) {
	return fract(sin(n) * 43758.5453);
}

void fragment() {
	vec4 t = texture(atlas, UV);
	ALBEDO = t.rgb * COLOR.rgb;
	ROUGHNESS = 0.86;
	SPECULAR = 0.3;
	float order = COLOR.a;
	if (power > 0.001 && order > 0.002 && t.a > 0.01) {
		float lit = order > out_amount ? 1.0 : 0.0;
		float edge = clamp((order - out_amount) / 0.15, 0.0, 1.0);
		float fl = max(flicker, 1.0 - edge) * lit;
		float n = hash(floor(TIME * 13.0 + order * 97.0) + order * 311.0);
		float on = n < fl * 0.75 ? 0.12 : 1.0;
		vec3 c = mix(cool, warm, hash(order * 57.3));
		EMISSION = c * (t.a * lit * on * power * energy);
		// 光っている窓はガラスの暗い色を少し明るく（昼の暗いガラスの色のまま光らせると濁る）
		ALBEDO = mix(ALBEDO, c * 0.6, t.a * lit * on * min(power, 1.0) * 0.5);
	}
}
