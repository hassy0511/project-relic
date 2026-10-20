// キットの材質の「動き」（材質の "sway"・"flow"。RoomKit.make_material が値を入れる。書き方は 42 章 14.2.2）。
// kit_surface.gdshaderinc（層あり・なし・近くを網目に消す版のどれも）が読む。値が 0 の材質は何もしない（前と同じ見た目・重さ）。
//
// どこを動かすかは、部品の頂点の色のアルファ（1 - 動きの重み）。Blender の書き出し（town_geo.sway・geo.Part.motion）が付ける：
// 重み 0 = 留まった端（竿・綱・棒・留め金の側）、1 = いちばん動く自由な端。重みの無い GLB と部屋の面はアルファ 1（動かない）。
// 時刻は描画の時計 TIME だけ（ゲームの中身は読まない。決まった刻みのテスト・見本の通しは変わらない）。描画の数は増えない。
// 掛け算の混ぜ方（blend_mul）は使わない（不透明の面の色を変えるだけ）。

// 揺れ：x = 突風で風下へ押す距離（m）、y = 揺れの幅（m）、z = 風下へ進む波（1 m あたりの山の数）、w = 突風の強さ（0〜1）。
// どれも重み 1 の頂点の値（重み 0.4 の垂れ幕の下の端なら 0.4 倍）
uniform vec4 sway_amp = vec4(0.0);
// 揺れ：xyz = 風の吹いていく向き（ワールド。水平にして使う。町は船首 +Z からの風で -Z）、w = 速さの倍率（1 = 落ち着いた揺れ）
uniform vec4 sway_wind = vec4(0.0, 0.0, -1.0, 1.0);
// 流れ（落砂の流れの面）：x = 下へ流れる速さ（m/s）、y = 模様の縦の大きさ（m）、z = 明暗の幅（0〜1）、w = 縁のちらつき（0〜1）
uniform vec4 flow = vec4(0.0);

// 格子の値の乱数（sin を使わない。入力は小さい数にして使う）
float kit_hash(vec2 p) {
	vec3 p3 = fract(vec3(p.xyx) * 0.1031);
	p3 += dot(p3, p3.yzx + 33.33);
	return fract((p3.x + p3.y) * p3.z);
}

// なめらかな値の雑音（0〜1）。x は period ごとに、y は 256 ごとに繰り返す（筒のまわりで継ぎ目が出ない・大きな時刻でも粗くならない）
float kit_noise(vec2 p, float period) {
	vec2 i = floor(p);
	vec2 f = fract(p);
	vec2 u = f * f * (3.0 - 2.0 * f);
	float x0 = mod(i.x, period);
	float x1 = mod(i.x + 1.0, period);
	float y0 = mod(i.y, 256.0);
	float y1 = mod(i.y + 1.0, 256.0);
	float a = kit_hash(vec2(x0, y0));
	float b = kit_hash(vec2(x1, y0));
	float c = kit_hash(vec2(x0, y1));
	float d = kit_hash(vec2(x1, y1));
	return mix(mix(a, b, u.x), mix(c, d, u.x), u.y);
}

// 揺れ：頂点を動かす（重み w）。ワールドの風下 W と、それに直角の水平の向き S へ、場所で少しずつずれた 2 つのゆっくりした揺れと、
// ときどき来る突風（風下へ流れていく帯）で押す。同じ所の頂点は同じだけ動く（布の表と裏・柄の板が裂けない）。
// 面の向き（NORMAL）は変えない：数 cm の揺れでは陰はほとんど変わらず（傾けても画素は変わらなかった）、スマホ・ブラウザ版の
// 描き方（gl_compatibility）で、傾けた面に一瞬だけ白い点が散った（2026-10-19）
void kit_sway(inout vec3 vertex, float w, mat4 model, float time) {
	if (w <= 0.002) {
		return;
	}
	mat3 m = mat3(model);
	vec3 wp = (model * vec4(vertex, 1.0)).xyz;
	vec3 wd = vec3(sway_wind.x, 0.0, sway_wind.z);
	vec3 W = length(wd) > 1e-4 ? normalize(wd) : vec3(0.0, 0.0, -1.0);
	vec3 S = vec3(-W.z, 0.0, W.x);
	float t = time * sway_wind.w;
	float along = dot(wp, W);
	// 突風：ふだんは 0、ときどき 1 まで（2 つの遅い波が重なったときだけ）。風下へゆっくり流れていく
	float g = sin(t * 0.23 - along * 0.045) * sin(t * 0.071 + 1.3 - along * 0.011);
	g = smoothstep(0.2, 0.85, g) * sway_amp.w;
	// 場所ごとのずれ（隣の布・旗とそろわない）
	float ph = dot(wp.xz, vec2(0.83, 0.61)) + 0.7 * sin(wp.x * 0.29 - wp.z * 0.41);
	float k = 6.2832 * sway_amp.z;
	float a1 = t * 1.9 - k * along + ph;
	float a2 = t * 1.37 - k * 0.8 * along + ph * 1.31 + 1.7;
	float fl = sway_amp.y * (0.55 + 0.6 * g);
	float push = sway_amp.x * (0.25 + 0.75 * g) * (0.85 + 0.15 * sin(t * 0.9 + ph));
	vec3 d = (W * (push + fl * 0.45 * sin(a2)) + S * (fl * sin(a1))) * w;
	vertex += inverse(m) * d;
}

// 流れ：落砂の流れの面の色に、下へ流れる明暗の筋と、縁（面が横を向く所）のちらつきを掛ける。fw = 重み、wp = ワールドの位置、
// origin = 部品の原点（流れの軸）、n・view = 画面の向きの法線と目への向き
vec3 kit_flow(vec3 c, float fw, vec3 wp, vec3 origin, vec3 n, vec3 view, float time) {
	if (fw <= 0.002) {
		return c;
	}
	vec2 rel = wp.xz - origin.xz;
	float ang = (atan(rel.y, rel.x) + 3.14159) * 0.159155;
	float v = (wp.y + time * flow.x) / max(flow.y, 0.01);
	float nz = kit_noise(vec2(ang * 6.0, v), 6.0) * 0.65 + kit_noise(vec2(ang * 12.0 + 3.7, v * 2.6 + 1.3), 12.0) * 0.35;
	// 雑音の値は真ん中に寄るので、明暗の筋がはっきり分かれるように広げる（細い流れでも下へ流れる筋に見える）
	nz = smoothstep(0.32, 0.68, nz);
	float lum = 1.0 + flow.z * (nz * 2.0 - 1.0);
	float edge = 1.0 - abs(dot(normalize(n), normalize(view)));
	float fl = kit_noise(vec2(ang * 9.0 + 7.1, v * 4.0 + time * 2.0), 9.0);
	lum *= 1.0 + flow.w * edge * (fl * 2.0 - 1.0);
	return c * mix(1.0, lum, clamp(fw, 0.0, 1.0));
}
