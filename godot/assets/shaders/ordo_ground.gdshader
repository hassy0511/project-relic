shader_type spatial;
// 巡礼機オルドの 120 m 下の砂の床（OrdoView の ground）。体を止めて地面を流す見方では、travel（体が進んだ距離）だけ模様が後ろへ流れる。
// 近くは砂丘のむら・砂利・風紋・小石の斑で動きが分かり、遠く（320〜850 m）は空の絵の下の帯の色（far_color）へ寄せながら透明にして、
// 空の絵の砂丘・遺構へつなぐ（前の遠景は平らな床を作らなかった：霞の平らな面が壁に見えたため。遠くまで描かない）。
// 光を受けない（雰囲気ごとの色は OrdoView.set_mood が渡す）。blend_mul は使わない（スマホ・ブラウザ版の描き方で黒くなる：設計 42 の決まり）
render_mode unshaded, blend_mix, depth_draw_opaque, cull_back, shadows_disabled;

uniform float travel = 0.0;
uniform vec3 near_color : source_color = vec3(0.86, 0.47, 0.32);
uniform vec3 dark_color : source_color = vec3(0.66, 0.32, 0.22);
uniform vec3 far_color : source_color = vec3(0.83, 0.58, 0.55);
uniform float ripple = 0.12;
uniform float fade_start = 320.0;   // ここから透明へ（120 m 下の地面を、地平線の 20 度下より遠くは空の絵の砂丘に任せる）
uniform float fade_end = 850.0;
uniform float rock_amount = 0.9;    // 岩・小石の斑の濃さ（低いカメラの場面では斑が横に伸びた黒い穴に見えるので、場面の間だけ薄くする：CineDirector）

varying vec2 gpos;

float hash(vec2 p) {
	p = fract(p * vec2(0.1031, 0.1030));
	p += dot(p, p.yx + 33.33);
	return fract((p.x + p.y) * p.x);
}

float vnoise(vec2 p) {
	vec2 i = floor(p);
	vec2 f = fract(p);
	f = f * f * (3.0 - 2.0 * f);
	float a = hash(i);
	float b = hash(i + vec2(1.0, 0.0));
	float c = hash(i + vec2(0.0, 1.0));
	float d = hash(i + vec2(1.0, 1.0));
	return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
}

void vertex() {
	// 地面の上の位置（m）：板の中の位置に、体が進んだ距離を足す（地面に描いた模様は体に対して後ろへ流れる）
	gpos = VERTEX.xz + vec2(0.0, travel);
}

void fragment() {
	vec2 p = gpos;
	float dist = length(VERTEX);
	// 砂丘のむら（大きい・中くらい）と、砂利の原の暗い斑（町の縁から 120 m 下を見下ろしても霞の中で流れが分かる濃さ）
	float dunes = vnoise(p / 180.0) * 0.55 + vnoise(p / 55.0) * 0.45;
	float gravel = smoothstep(0.55, 0.75, vnoise(p / 38.0 + 13.1));
	// 風紋（4〜5 m の縞）：遠くはちらつくので距離で消す
	float rw = clamp(1.0 - dist / 420.0, 0.0, 1.0);
	float rip = sin(p.x * 0.42 + p.y * 1.25 + vnoise(p / 26.0) * 7.0) * 0.5 + 0.5;
	// 岩・小石の斑（まばら）
	float rocks = smoothstep(0.72, 0.8, vnoise(p / 9.0 + 31.7)) * smoothstep(0.45, 0.62, vnoise(p / 80.0 + 7.3));
	vec3 c = mix(dark_color, near_color, 0.25 + 0.75 * dunes);
	c = mix(c, dark_color * 0.85, gravel * 0.55);
	c *= 1.0 - ripple * rip * rw;
	c = mix(c, dark_color * 0.45, rocks * rock_amount * clamp(1.0 - dist / 900.0, 0.0, 1.0));
	c = mix(c, far_color, smoothstep(fade_start * 0.35, fade_end, dist));
	ALBEDO = c;
	ALPHA = 1.0 - smoothstep(fade_start, fade_end, dist);
}
