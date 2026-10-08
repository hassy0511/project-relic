// キットの面の材質（RoomKit）の中身。kit_surface.gdshader と kit_surface_fade.gdshader（近くを網目に消す版）が読む。
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
#ifdef NEAR_FADE
// カメラのすぐ近くを網目に消す距離（m）：x より近いと全部消え、y より遠いと全部見える（kit_surface_fade.gdshader）
uniform vec2 near_fade = vec2(0.8, 1.5);
#endif

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
	if (seam_every.x > 0.0 || seam_every.y > 0.0) {
		c = mix(c, seam_color.rgb, seam(UV));
	}
	ALBEDO = c;
	ROUGHNESS = roughness_value;
	METALLIC = metallic_value;
	EMISSION = emission_color.rgb * emission_energy;
}
