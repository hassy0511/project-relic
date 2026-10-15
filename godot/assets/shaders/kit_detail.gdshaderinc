// キットの面の材質の「汚れ・傷みの層」（材質の "detail"。RoomKit.make_material が値を入れる。書き方は 42 章 14.2）。
// kit_surface.gdshaderinc が DETAIL を定義した版（kit_surface_detail*.gdshader）だけで読む。"detail" の無い材質は今までのシェーダーのまま。
//
// 型の絵（tools/grime_masks.py が CC0 の写真から作る）は 2 枚に 4 つの型：
//   detail_tex（assets/kit/grime/masks.png）  RGB = 汚れの斑（白黒。G を読む）、A = 欠け
//   detail_tex2（assets/kit/grime/masks2.png） RGB = むら（白黒）、A = 縦の筋
// どれも 0〜1 に均した値で、「値が 1 - p より大きい所」の面積がちょうど p。
// 層は、型を 1 本のしきい値で切った形の内側を、パレットの色で平らに塗る（写真の色・明暗は使わない）。
// 型はなめらかな山と谷の形なので、近くで見ても縁のはっきりした平らな斑になり、写真の粒は出ない。
//
// 面の UV2（RoomKit が付ける）：x = 形・部品の下の端からの高さ（m）、y = 上の端までの深さ（m）。足元・上の端の汚れに使う。

#define DETAIL_MAX 4

uniform sampler2D detail_tex : filter_linear_mipmap_anisotropic, repeat_enable, hint_default_black;
uniform sampler2D detail_tex2 : filter_linear_mipmap_anisotropic, repeat_enable, hint_default_black;
uniform int detail_count = 0;
// 層ごとの値（RoomKit._detail_params が詰める）
// 色：rgb = 塗る色（パレット）、a = 強さ（0〜1）
uniform vec4 d_color[DETAIL_MAX] : source_color;
// 型の選び：x = 汚れの斑、y = 欠け、z = むら、w = 縦の筋 の重み（どれか 1 つが 1）
uniform vec4 d_pick[DETAIL_MAX];
// xy = 1 / 型の 1 枚の大きさ（m）、zw = ずらし（同じ型を重ねても斑の位置がそろわないように）
uniform vec4 d_uv[DETAIL_MAX];
// x = 覆う割合（0〜1）、y = 縁の幅（型の値で。小さいほどはっきり）、z = 塗り方（0 = 色で塗る、1 = 色を掛ける）、
// w = 付ける面（0 = 全部、1 = 上向き（床）、2 = 縦（壁）、3 = 下向き（天井））
uniform vec4 d_shape[DETAIL_MAX];
// 縦の面だけ：xy = 足元 [濃い高さ, 消える高さ]（m）、zw = 上の端から [濃い深さ, 消える深さ]（m）。x < y のときだけ使う
uniform vec4 d_feet[DETAIL_MAX];
// xy = 板の継ぎ目（seams）から [濃い距離, 消える距離]（m）。z = 大きな汚れの斑の中だけ（その斑の覆う割合。0 = 使わない）、
// w = その斑の型の 1 枚の大きさの逆数（1/m）
uniform vec4 d_gate[DETAIL_MAX];

// 板の継ぎ目（seam_every の格子）までの距離（m）。継ぎ目の無い材質では大きな値
float kit_seam_dist(vec2 uvm) {
	if (seam_every.x <= 0.0 && seam_every.y <= 0.0) {
		return 1e3;
	}
	vec2 e = max(seam_every, vec2(1e-3));
	vec2 d = abs(fract(uvm / e - 0.5) - 0.5) * e;
	d = mix(vec2(1e3), d, step(vec2(1e-3), seam_every));
	return min(d.x, d.y);
}

// 層を順に重ねる。c：今の色、uvm：面の UV（m）、hd：UV2（下の端からの高さ, 上の端までの深さ）、wn：ワールドの法線
// （型の絵の読み出し・fwidth はどれも同じ流れの中（層の数は uniform）で行う。画素ごとに分かれる if の中では読まない）
vec3 kit_detail(vec3 c, vec2 uvm, vec2 hd, vec3 wn) {
	float wall = 1.0 - smoothstep(0.5, 0.8, abs(wn.y));
	float up = smoothstep(0.5, 0.8, wn.y);
	float down = smoothstep(0.5, 0.8, -wn.y);
	float sd = kit_seam_dist(uvm);
	vec2 tex_px1 = vec2(textureSize(detail_tex, 0));
	vec2 tex_px2 = vec2(textureSize(detail_tex2, 0));
	vec2 fw_uv = fwidth(uvm);
	for (int i = 0; i < DETAIL_MAX; i++) {
		if (i >= detail_count) {
			break;
		}
		vec4 sh = d_shape[i];
		float face = sh.w < 0.5 ? 1.0 : (sh.w < 1.5 ? up : (sh.w < 2.5 ? wall : down));
		// 置き場所の重み（0〜1）。覆う割合に掛けるので、重みが下がるほど斑が細り、縁ははっきりしたまま消えていく
		float w = sh.x * face;
		vec4 f = d_feet[i];
		if (f.y > f.x) {
			w *= mix(1.0, 1.0 - smoothstep(f.x, f.y, hd.x), wall);
		}
		if (f.w > f.z) {
			w *= mix(1.0, 1.0 - smoothstep(f.z, f.w, hd.y), wall);
		}
		vec4 g = d_gate[i];
		if (g.y > g.x) {
			w *= 1.0 - smoothstep(g.x, g.y, sd);
		}
		if (g.z > 0.0) {
			float gm = texture(detail_tex, uvm * g.w + vec2(0.37, 0.61)).g;
			w *= smoothstep(1.0 - g.z - 0.1, 1.0 - g.z + 0.1, gm);
		}
		vec2 duv = uvm * d_uv[i].xy + d_uv[i].zw;
		vec4 pk = d_pick[i];
		bool first = pk.x + pk.y > 0.0;
		float m;
		if (first) {
			vec4 t = texture(detail_tex, duv);
			m = t.g * pk.x + t.a * pk.y;
		} else {
			vec4 t = texture(detail_tex2, duv);
			m = t.g * pk.z + t.a * pk.w;
		}
		// 縁：決めた幅か、1 画素ぶんの値の変わり（遠くでぎざぎざにしない）の広いほう
		float e = max(sh.y, fwidth(m) * 0.7);
		float th = mix(1.0 + e, -e, clamp(w, 0.0, 1.0));
		float p = smoothstep(th - e, th + e, m);
		// 遠く（型の 1 画素が画面の数画素ぶんより細かい）では、斑の形の代わりに、覆う割合の平均の濃さにする。
		// 縮小した型（ミップマップ）は値がならされ、しきい値を越えなくなって汚れが消えるため
		vec2 texel = fw_uv * abs(d_uv[i].xy) * (first ? tex_px1 : tex_px2);
		p = mix(p, clamp(w, 0.0, 1.0), smoothstep(3.0, 8.0, max(texel.x, texel.y)));
		vec4 col = d_color[i];
		vec3 target = sh.z < 0.5 ? col.rgb : c * col.rgb;
		c = mix(c, target, p * col.a);
	}
	return c;
}
