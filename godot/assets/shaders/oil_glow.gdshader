// 油の灯（灯油ランプ・火）の安い光：灯のまわりのにじみ（カメラを向く板）と、床の明るい輪（床に寝た板）。部屋の油の灯の全部を
// 1 つの MultiMesh で描く（描画 1 回。本物の光 OmniLight3D はスマホの描き方で照らす物ごとに 1 回増えるので、人のいる所の数個だけ）。
// 粒ごとの値（INSTANCE_CUSTOM）：r = 形（0 = にじみ、1 = 床の輪）、g = 揺らぎの位相 0〜1、b = 強さ。大きさは変換の拡大（m）。
// 揺らぎは kit_surface.gdshaderinc の油の灯（power_source 2）と同じ式。足し合わせ（blend_add。掛け算の半透明はスマホで黒くなる）。
// TownPower.make_glows が作る（docs/design/42_コンテンツの書き方.md 14.8）
shader_type spatial;
render_mode unshaded, blend_add, depth_draw_never, cull_disabled, shadows_disabled, fog_disabled;

uniform vec4 color : source_color = vec4(1.0, 0.62, 0.3, 1.0);
// 全体の強さ（にじみ・床の輪）
uniform vec2 strength = vec2(0.8, 0.42);

varying float v_kind;
varying float v_amt;
varying float v_h;

void vertex() {
	v_kind = INSTANCE_CUSTOM.r;
	v_h = INSTANCE_CUSTOM.g;
	v_amt = INSTANCE_CUSTOM.b;
	float size = length(MODEL_MATRIX[0].xyz);
	vec3 center = MODEL_MATRIX[3].xyz;
	vec3 wp;
	if (v_kind < 0.5) {
		// にじみ：カメラを向く板。灯の体に隠れないよう、カメラの方へ少し寄せる
		vec3 right = INV_VIEW_MATRIX[0].xyz;
		vec3 up = INV_VIEW_MATRIX[1].xyz;
		vec3 to_cam = normalize(INV_VIEW_MATRIX[3].xyz - center);
		wp = center + (right * VERTEX.x + up * VERTEX.y) * size + to_cam * min(size * 0.5, 0.25);
	} else {
		// 床の輪：床に寝た板（床の 2 cm 上）
		wp = center + vec3(VERTEX.x, 0.0, VERTEX.y) * size + vec3(0.0, 0.02, 0.0);
	}
	UV = VERTEX.xy * 2.0;
	POSITION = PROJECTION_MATRIX * VIEW_MATRIX * vec4(wp, 1.0);
}

void fragment() {
	float d = length(UV);
	float h = v_h * 40.0;
	float fl = 0.88 + 0.12 * sin(TIME * 6.1 + h) * sin(TIME * 2.3 + h * 0.37);
	float a;
	if (v_kind < 0.5) {
		a = pow(max(1.0 - d, 0.0), 2.4) * strength.x;
	} else {
		a = pow(max(1.0 - d, 0.0), 1.6) * strength.y;
	}
	ALBEDO = color.rgb * a * v_amt * fl;
}
