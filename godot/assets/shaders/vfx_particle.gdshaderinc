// エフェクトの粒（scripts/view/vfx.gd の層）。1 つの MultiMesh の 1 粒 = 1 枚の四角。
// マスク（W2-09 の vfx_tex_*.png、白黒）を、粒ごとの色（MultiMesh の色。明るさ込み、1 を超えてよい）で塗る。
// 粒ごとの値（INSTANCE_CUSTOM）：
//   x = 画面の中での回転（rad。向きが 0 のときだけ）
//   y = 向き：0 = いつもカメラを向く板、1 = 変換のまま（床の輪・斬撃の帯）、2 = 変換の Y 軸に沿って伸び、軸のまわりでカメラを向く（火花・弾の筋）
//   z = 拭き出し（0 = なし、0〜1 = 円弧の始まりからどこまで見せるか。斬撃の帯が振り抜く向きに伸びる）
// 影なし・光を受けない・深さを書かない。掛け算の混ぜ方（blend_mul）は gl_compatibility で黒くなるので使わない。

uniform sampler2D mask : hint_default_black, filter_linear_mipmap, repeat_disable;
// マスクの中の使う窓：中心・倍率・回転（rad）。絵の小さい素材（光点・火花）を四角いっぱいに使う
uniform vec2 uv_center = vec2(0.5);
uniform float uv_scale = 1.0;
uniform float uv_rot = 0.0;
// マスクの濃さの整え：(m - lo) / (hi - lo) を 0〜1 にして pow
uniform float mask_lo = 0.0;
uniform float mask_hi = 1.0;
uniform float mask_pow = 1.0;
// 色にマスクの濃淡を残す割合（0 = 一色、1 = マスクの濃淡のまま。陶器の破片・煙）
uniform float shade = 0.0;
// 拭き出しの円弧（マスクの UV で）：中心と、始まり・終わりの角度（rad）
uniform vec2 wipe_center = vec2(0.5);
uniform float wipe_a0 = 0.0;
uniform float wipe_a1 = 1.0;

varying vec2 v_uv;
varying float v_wipe;

void vertex() {
	vec4 c = INSTANCE_CUSTOM;
	vec3 origin = MODEL_MATRIX[3].xyz;
	vec3 ax = MODEL_MATRIX[0].xyz;
	vec3 ay = MODEL_MATRIX[1].xyz;
	vec3 world;
	if (c.y < 0.5) {
		vec2 v = VERTEX.xy * vec2(length(ax), length(ay));
		float cs = cos(c.x);
		float sn = sin(c.x);
		v = vec2(cs * v.x - sn * v.y, sn * v.x + cs * v.y);
		world = origin + INV_VIEW_MATRIX[0].xyz * v.x + INV_VIEW_MATRIX[1].xyz * v.y;
	} else if (c.y < 1.5) {
		world = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	} else {
		vec3 side = cross(ay, INV_VIEW_MATRIX[3].xyz - origin);
		float sl = length(side);
		side = sl > 1e-5 ? side / sl * length(ax) : ax;
		world = origin + ay * VERTEX.y + side * VERTEX.x;
	}
	VERTEX = (VIEW_MATRIX * vec4(world, 1.0)).xyz;
	NORMAL = vec3(0.0, 0.0, 1.0);
	vec2 uv = UV - vec2(0.5);
	float rc = cos(uv_rot);
	float rs = sin(uv_rot);
	v_uv = vec2(rc * uv.x - rs * uv.y, rs * uv.x + rc * uv.y) * uv_scale + uv_center;
	v_wipe = c.z;
}

void fragment() {
	float raw = texture(mask, v_uv).r;
	float m = pow(clamp((raw - mask_lo) / max(mask_hi - mask_lo, 0.001), 0.0, 1.0), mask_pow);
	if (v_wipe > 0.0) {
		vec2 d = v_uv - wipe_center;
		float k = (atan(d.y, d.x) - wipe_a0) / (wipe_a1 - wipe_a0);
		m *= 1.0 - smoothstep(v_wipe - 0.18, v_wipe, k);
	}
	ALBEDO = COLOR.rgb * mix(1.0, raw, shade);
	ALPHA = clamp(COLOR.a * m, 0.0, 1.0);
}
