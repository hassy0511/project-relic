shader_type spatial;
// 背の上の町の灯（TownLights。MultiMesh の 1 粒 = 1 つの灯）。遠くても小さな光の点に見えるよう、カメラからの距離で大きさを決める
// （近くは base_size m、遠くは px_size 画素より小さくしない）。足し合わせの光。霞は受けない代わりに、遠いほど少し暗くする。
// 粒ごとの値（INSTANCE_CUSTOM）：x = ちらつきの位相（0〜1）、y = 大きさの倍率、z = 消える順（0〜1。out_amount を超えた灯から消える）、w = 色の暖かさ（0〜1）。
// power：全体の明るさ（0〜1）、flicker：ちらつきの強さ（0〜1）、out_amount：消えた灯の割合（0〜1。消える直前の灯は強くちらつく）。
// blend_mul は使わない（スマホ・ブラウザ版の描き方で黒くなる：設計 42 の決まり）
render_mode unshaded, blend_add, depth_draw_never, cull_disabled, shadows_disabled, fog_disabled, skip_vertex_transform;

uniform float power = 1.0;
uniform float flicker = 0.0;
uniform float out_amount = 0.0;
uniform float base_size = 1.7;
uniform float px_size = 5.5;
uniform float gain = 3.2;
uniform vec3 warm : source_color = vec3(1.0, 0.66, 0.30);
uniform vec3 cool : source_color = vec3(1.0, 0.86, 0.62);

varying vec3 v_col;
varying vec2 v_uv;

float hash(float n) {
	return fract(sin(n) * 43758.5453);
}

void vertex() {
	vec3 origin = (VIEW_MATRIX * vec4(MODEL_MATRIX[3].xyz, 1.0)).xyz;
	float dist = length(origin);
	// 1 画素の大きさ（m）：この距離での画面の縦の広さ ÷ 画面の縦の画素
	float px_m = dist * 2.0 / (PROJECTION_MATRIX[1][1] * VIEWPORT_SIZE.y);
	vec4 c = INSTANCE_CUSTOM;
	float s = max(base_size * c.y, px_m * px_size * (0.8 + 0.4 * c.y));
	VERTEX = origin + vec3(VERTEX.xy * s, 0.0);
	NORMAL = vec3(0.0, 0.0, 1.0);
	v_uv = UV;
	// 消える順：out_amount を超えた灯から消え、その手前（幅 0.15）の灯は強くちらつく
	float edge = clamp((c.z - out_amount) / 0.15, 0.0, 1.0);
	float lit = c.z > out_amount ? 1.0 : 0.0;
	float fl = max(flicker, 1.0 - edge) * lit;
	// ちらつき：1/13 秒ごとに灯ごとの乱数で、強いほど暗い刻みが増える
	float n = hash(floor(TIME * 13.0 + c.x * 97.0) + c.x * 311.0);
	float on = n < fl * 0.75 ? 0.12 : 1.0;
	// 遠いほど少し暗く（霞の代わり）
	float far_k = mix(1.0, 0.55, smoothstep(250.0, 1500.0, dist));
	v_col = mix(cool, warm, c.w) * power * lit * on * far_k * gain;
}

void fragment() {
	vec2 d = v_uv - vec2(0.5);
	float r2 = dot(d, d) * 4.0;
	// 明るい芯と、やわらかいにじみ
	float a = exp(-r2 * 9.0) + 0.35 * exp(-r2 * 2.5);
	ALBEDO = v_col * a;
}
