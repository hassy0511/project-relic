// キットの面の材質（RoomKit）の中身。kit_surface.gdshader と kit_surface_fade.gdshader（近くを網目に消す版）が読む。
// 汚れ・傷みの層（材質の "detail"）のある材質は、DETAIL を定義した kit_surface_detail.gdshader・kit_surface_detail_fade.gdshader
// （中身は kit_detail.gdshaderinc）。DETAIL の無い版は前と同じ。
// 動き（材質の "sway" 風で揺れる布・垂れたケーブル、"flow" 落砂の流れ）は、どの版にも入っている（kit_motion.gdshaderinc）。
// 値が 0 の材質は何もしない（揺れは頂点の色のアルファ = 1 - 重みのある頂点だけ）。
// 部屋の灰色の地形と、飾りの部品（GLB）の両方に使う。
// UV はメートル（部屋の面は RoomKit がワールド座標から、部品は Blender で付けた値）。1 枚の絵 = uv_m メートル。
// seam_every を 0 より大きくすると、その間隔（m）で板の継ぎ目の線を描く（壁の白磁の板など）。

uniform vec4 color : source_color = vec4(1.0);
uniform sampler2D albedo_tex : source_color, filter_linear_mipmap_anisotropic, repeat_enable, hint_default_white;
uniform float uv_m = 2.0;
// 絵の強さ（0 = 絵を使わず color だけ、1 = 絵のまま）。黒鉛の擦り目など、模様が強すぎる絵を弱める
uniform float tex_strength = 1.0;
uniform float roughness_value = 0.85;
uniform float metallic_value = 0.0;
// 地形の tint（頂点の色）をどれだけ掛けるか（0 = 使わない）
uniform float tint_mix = 0.0;
// 大きな斑（同じ絵の繰り返しを目立たなくする）：別の縮尺で同じ絵を引き、明るさの揺れだけを掛ける
uniform float macro = 0.0;
uniform vec2 seam_every = vec2(0.0);
uniform float seam_width = 0.04;
uniform vec4 seam_color : source_color = vec4(0.27, 0.27, 0.25, 1.0);
uniform vec4 emission_color : source_color = vec4(0.0, 0.0, 0.0, 1.0);
uniform float emission_energy = 0.0;
// 町の電気（材質の "source"。RoomKit・TownPower。docs/design/42_コンテンツの書き方.md 14.8）：0 = 電気に関係しない（いつも同じ）、
// 1 = 電気の灯・窓の明かり（町の電気が切れると消える。消えた灯のガラスは暗く）、2 = 油の灯・火（停電でも灯り、ゆっくり揺らぐ）
uniform float power_source = 0.0;
// 電気の灯の今の状態（TownPower が電気の材質のすべてに入れる。同じ式を TownPower.wave_k が部屋の明かりに使う）：
// x = 明るさ 0〜1（波の無いとき）、y = 波の向き（0 なし・1 点いていく・-1 消えていく）、z = 波を始めてからの秒、w = 波の進む速さ（m/秒）
uniform vec4 power_state = vec4(1.0, 0.0, 0.0, 14.0);
// 波の原点（ワールドの位置）と、灯ごとのばらつき（秒）
uniform vec4 power_origin = vec4(0.0, 0.0, 0.0, 0.8);
// 消えたときに残す発光の割合（窓の外の月明かり）
uniform float power_floor = 0.0;
#ifdef NEAR_FADE
// カメラのすぐ近くを網目に消す距離（m）：x より近いと全部消え、y より遠いと全部見える（kit_surface_fade.gdshader）
uniform vec2 near_fade = vec2(0.8, 1.5);
#endif
#ifdef DETAIL
#include "res://assets/shaders/kit_detail.gdshaderinc"
#endif
#include "res://assets/shaders/kit_motion.gdshaderinc"

// 町の電気：2 m の升ごとの決まった乱数（灯ごとのばらつき・ちらつきの位相）。升は部品の置き場所（下の v_power_h）
float power_hash(vec3 p) {
	return fract(sin(dot(floor(p * 0.5), vec3(12.9898, 78.233, 37.719))) * 43758.5453);
}

// 灯ごとのばらつきの乱数は、面のかけらごとではなく部品 1 つ（MultiMesh なら 1 粒）の置き場所から決める。
// かけらごとに決めると、2 m の升の境をまたぐ窓・灯の芯が別々の時に点き・消え、別々にちらついた。
// 部屋の明かり（TownPower）も同じ置き場所から決めるので、灯の芯と光が一緒に点く
varying flat float v_power_h;

void vertex() {
	// MODEL_MATRIX は vertex() では MultiMesh の 1 粒の変換も含む
	v_power_h = power_hash(MODEL_MATRIX[3].xyz);
	// 揺れ（材質の "sway"：風で揺れる布・垂れたケーブル。kit_motion.gdshaderinc）。重みは頂点の色のアルファ（1 - 重み）
	if (sway_amp.x + sway_amp.y > 0.0) {
		kit_sway(VERTEX, 1.0 - COLOR.a, MODEL_MATRIX, TIME);
	}
	// オルドの足音の揺れ（jolt。OrdoSteps が足の着いたあと数秒だけ入れる）
	if (jolt.w > 0.0) {
		kit_jolt(VERTEX, 1.0 - COLOR.a, MODEL_MATRIX);
	}
}

// 電気の灯の明るさ 0〜1（TownPower.wave_k と同じ式）。波の間は、原点からの距離 / 速さ + ばらつきの秒で点く（消える）。
// 切り替わる前後の 0.5 秒は 1/20 秒ごとにちらつく（点く波は点いている割合が増えていき、消える波は減っていく）。h は部品ごとの乱数
float power_k(vec3 wp, float h) {
	if (power_state.y == 0.0) {
		return power_state.x;
	}
	float t = power_state.z - (length(wp - power_origin.xyz) / max(power_state.w, 0.01) + h * power_origin.w);
	float on = step(0.5, t);
	if (t >= 0.0 && t < 0.5) {
		float r = fract(sin((floor(power_state.z * 20.0) + h * 97.0) * 12.9898) * 43758.5453);
		on = step(r, 0.25 + t * 1.3);
	}
	return power_state.y > 0.0 ? on : 1.0 - on;
}

float seam(vec2 uvm) {
	vec2 e = max(seam_every, vec2(1e-3));
	vec2 d = abs(fract(uvm / e - 0.5) - 0.5) * e;
	vec2 fw = fwidth(uvm);
	vec2 s = 1.0 - smoothstep(vec2(seam_width * 0.5), vec2(seam_width * 0.5) + fw, d);
	s *= step(vec2(1e-3), seam_every);
	return max(s.x, s.y);
}

void fragment() {
#ifdef NEAR_FADE
	// 当たり判定の無い飾り（日よけ・柱・灯・壁の板）がカメラの前を塞がないよう、近い所を 4×4 の網目で抜く。
	// 壁に寄って立ったときにカメラを上へ回すと（camera_rig.gd）、頭の上の日よけがプレイヤーを隠すため
	float k = clamp((length(VERTEX) - near_fade.x) / max(near_fade.y - near_fade.x, 1e-3), 0.0, 1.0);
	if (k < 1.0) {
		int bayer[16] = {0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5};
		ivec2 q = ivec2(FRAGCOORD.xy) & ivec2(3);
		if (k * 16.0 <= float(bayer[q.y * 4 + q.x]) + 0.5) {
			discard;
		}
	}
#endif
	vec3 t = texture(albedo_tex, UV / uv_m).rgb;
	// 絵の平均の明るさは保ったまま、模様だけを弱める（平均 = 縮小の最後の段の色）
	vec3 avg = textureLod(albedo_tex, vec2(0.5), 12.0).rgb;
	vec3 c = mix(avg, t, tex_strength) * color.rgb;
	if (macro > 0.0) {
		vec3 m = texture(albedo_tex, UV / (uv_m * 3.7) + vec2(0.37, 0.71)).rgb;
		float l = dot(m, vec3(0.333));
		c *= mix(1.0, clamp(l * 1.6, 0.6, 1.25), macro);
	}
	c = mix(c, c * COLOR.rgb, tint_mix);
#ifdef DETAIL
	// 汚れ・傷みの層（継ぎ目の線は、その上に描く）
	c = kit_detail(c, UV, UV2, normalize((INV_VIEW_MATRIX * vec4(NORMAL, 0.0)).xyz));
#endif
	if (seam_every.x > 0.0 || seam_every.y > 0.0) {
		c = mix(c, seam_color.rgb, seam(UV));
	}
	// 流れ（材質の "flow"：落砂の流れの面に下へ流れる模様。kit_motion.gdshaderinc）
	if (flow.x > 0.0) {
		c = kit_flow(c, 1.0 - COLOR.a, (INV_VIEW_MATRIX * vec4(VERTEX, 1.0)).xyz, MODEL_MATRIX[3].xyz, NORMAL, VIEW, TIME);
	}
	// 町の電気（"source"）：電気の灯は町の電気（power_state）で点き・消え、油の灯は揺らぐ
	float pk = 1.0;
	if (power_source > 0.5) {
		vec3 wp = (INV_VIEW_MATRIX * vec4(VERTEX, 1.0)).xyz;
		if (power_source < 1.5) {
			pk = power_k(wp, v_power_h);
			c *= mix(0.3, 1.0, pk);
			pk = mix(power_floor, 1.0, pk);
		} else {
			float h = v_power_h * 40.0;
			pk = 0.88 + 0.12 * sin(TIME * 6.1 + h) * sin(TIME * 2.3 + h * 0.37);
		}
	}
	ALBEDO = c;
	ROUGHNESS = roughness_value;
	METALLIC = metallic_value;
	EMISSION = emission_color.rgb * emission_energy * pk;
}
