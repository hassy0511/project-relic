class_name BkTest
extends RefCounted
## BlenderKit の素材を試す比べ（docs/art_orders/BlenderKit検討.md）。見本（--demo）の撮影のときだけ、引数で付ける。ふだんのゲームは何も変わらない。
##   --bk_kit=<フォルダ>    フォルダの <キットの id>.json を、content/kits の同じ id のキットの代わりに使う（RoomKit の読み置きに先に入れる）。
##                          材質の "albedo" はリポジトリの外のファイル（絶対パス）でもよい（読むときにミップマップを作り VRAM 圧縮する）。
##                          材質に "detail"（汚れ・傷みの層、下の SHADER）を書ける
##   --bk_props=<JSON>      部屋に BlenderKit の小物（GLB、リポジトリの外）を足す：
##                          [{"room": "ch1.r02", "glb": "/…/model.glb", "pos": [x,y,z], "yaw": 度, "height": m, "shadow": true}]
##                          （height：見た目の高さをこれに合わせる。底の真ん中が pos。"glb" の代わりに "part": "town/barrel" で今のキットの部品）
## どちらも、撮影のたびに描画の数・絵のメモリを「BK計測」の行に出す。
## 素材のファイルは tools/blenderkit_fetch.py が build/blenderkit に落とす（CC0 でない物はリポジトリに入れない）。

## 汚れ・傷みの層の付いたキットの面の材質。中身は assets/shaders/kit_surface.gdshaderinc と同じに、層を 2 つ足したもの。
## 層（"detail" と "detail2"）：{ "albedo": パス, "mode": "mask" | "mul" | "color", "uv_m": m か [横 m, 縦 m], "strength": 0〜1,
##   "color": "#rrggbb", "band": [lo, hi], "pick": "dark" | "light" | "red", "floor_fade": [y0, y1],
##   "gate": { "albedo": パス, "uv_m": m, "band": [lo, hi] }, "edge": [近い m, 遠い m] }
##   mask：絵が平均より lo〜hi だけ暗い（light：明るい、red：赤みが強い＝さび）所を color（パレットの色）で塗る。幅を狭くすると縁のはっきりした平らな斑
##   mul：絵の明暗だけを掛ける（平均の明るさは保つ）。color：絵の色をそのまま混ぜる（写実の絵の比べ）
##   floor_fade：壁の面だけ、ワールドの高さ y0 で最も濃く y1 で消える（壁の足元の汚れ）
##   gate：別の絵（大きな縮尺）の平均より暗い所にだけ層を出す（一面に同じ斑が散らないように）
##   edge：板の継ぎ目（seams の格子）の近くにだけ出す（近い m で最も濃く、遠い m で消える。角の欠け・縁の傷み）
const SHADER_CODE := """
shader_type spatial;
uniform vec4 color : source_color = vec4(1.0);
uniform sampler2D albedo_tex : source_color, filter_linear_mipmap_anisotropic, repeat_enable, hint_default_white;
uniform float uv_m = 2.0;
uniform float tex_strength = 1.0;
uniform float roughness_value = 0.85;
uniform float metallic_value = 0.0;
uniform float tint_mix = 0.0;
uniform float macro = 0.0;
uniform vec2 seam_every = vec2(0.0);
uniform float seam_width = 0.04;
uniform vec4 seam_color : source_color = vec4(0.27, 0.27, 0.25, 1.0);
uniform vec4 emission_color : source_color = vec4(0.0, 0.0, 0.0, 1.0);
uniform float emission_energy = 0.0;
#ifdef NEAR_FADE
uniform vec2 near_fade = vec2(0.8, 1.5);
#endif
uniform sampler2D d1_tex : source_color, filter_linear_mipmap_anisotropic, repeat_enable, hint_default_white;
uniform int d1_mode = 0;
uniform vec2 d1_uv_m = vec2(2.0);
uniform float d1_strength = 0.0;
uniform vec4 d1_color : source_color = vec4(0.72, 0.36, 0.26, 1.0);
uniform vec2 d1_band = vec2(0.08, 0.14);
uniform int d1_pick = 0;
uniform vec2 d1_floor_fade = vec2(0.0);
uniform vec3 d1_avg = vec3(0.5);
uniform sampler2D d1_gate_tex : source_color, filter_linear_mipmap_anisotropic, repeat_enable, hint_default_white;
uniform float d1_gate_on = 0.0;
uniform vec2 d1_gate_uv_m = vec2(6.0);
uniform vec2 d1_gate_band = vec2(0.05, 0.12);
uniform vec3 d1_gate_avg = vec3(0.5);
uniform vec2 d1_edge = vec2(0.0);
uniform sampler2D d2_tex : source_color, filter_linear_mipmap_anisotropic, repeat_enable, hint_default_white;
uniform int d2_mode = 0;
uniform vec2 d2_uv_m = vec2(2.0);
uniform float d2_strength = 0.0;
uniform vec4 d2_color : source_color = vec4(0.35, 0.26, 0.2, 1.0);
uniform vec2 d2_band = vec2(0.08, 0.14);
uniform int d2_pick = 0;
uniform vec2 d2_floor_fade = vec2(0.0);
uniform vec3 d2_avg = vec3(0.5);
uniform sampler2D d2_gate_tex : source_color, filter_linear_mipmap_anisotropic, repeat_enable, hint_default_white;
uniform float d2_gate_on = 0.0;
uniform vec2 d2_gate_uv_m = vec2(6.0);
uniform vec2 d2_gate_band = vec2(0.05, 0.12);
uniform vec3 d2_gate_avg = vec3(0.5);
uniform vec2 d2_edge = vec2(0.0);

float seam(vec2 uvm) {
	vec2 e = max(seam_every, vec2(1e-3));
	vec2 d = abs(fract(uvm / e - 0.5) - 0.5) * e;
	vec2 fw = fwidth(uvm);
	vec2 s = 1.0 - smoothstep(vec2(seam_width * 0.5), vec2(seam_width * 0.5) + fw, d);
	s *= step(vec2(1e-3), seam_every);
	return max(s.x, s.y);
}

// 板の継ぎ目（seam_every の格子）までの距離（m）。継ぎ目の無い材質では大きな値
float seam_dist(vec2 uvm) {
	if (seam_every.x <= 0.0 && seam_every.y <= 0.0) {
		return 1e3;
	}
	vec2 e = max(seam_every, vec2(1e-3));
	vec2 d = abs(fract(uvm / e - 0.5) - 0.5) * e;
	d = mix(vec2(1e3), d, step(vec2(1e-3), seam_every));
	return min(d.x, d.y);
}

float lum(vec3 v) {
	return dot(v, vec3(0.299, 0.587, 0.114));
}

// 層を 1 つ重ねる。gate：別の絵（大きな縮尺）の暗い所だけに層を出す（傷・斑を一面に散らさず、汚れた所に寄せる）
vec3 layer(vec3 c, vec3 t, vec3 avg, int mode, float k, vec3 col, vec2 band, int pick, vec2 ff, float wy, float wall, float gate) {
	if (ff.y > ff.x) {
		k *= mix(1.0, 1.0 - smoothstep(ff.x, ff.y, wy), wall);
	}
	k *= gate;
	float l = lum(t);
	float la = max(lum(avg), 1e-3);
	if (mode == 0) {
		float d = pick == 2 ? (t.r - t.b) - (avg.r - avg.b) : (pick == 1 ? l - la : la - l);
		return mix(c, col, smoothstep(band.x, band.y, d) * k);
	} else if (mode == 1) {
		return c * mix(1.0, clamp(l / la, 0.0, 2.0), k);
	}
	return mix(c, t * col, k);
}

void fragment() {
#ifdef NEAR_FADE
	float nk = clamp((length(VERTEX) - near_fade.x) / max(near_fade.y - near_fade.x, 1e-3), 0.0, 1.0);
	if (nk < 1.0) {
		int bayer[16] = {0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5};
		ivec2 q = ivec2(FRAGCOORD.xy) & ivec2(3);
		if (nk * 16.0 <= float(bayer[q.y * 4 + q.x]) + 0.5) {
			discard;
		}
	}
#endif
	vec3 t = texture(albedo_tex, UV / uv_m).rgb;
	vec3 avg = textureLod(albedo_tex, vec2(0.5), 12.0).rgb;
	vec3 c = mix(avg, t, tex_strength) * color.rgb;
	if (macro > 0.0) {
		vec3 m = texture(albedo_tex, UV / (uv_m * 3.7) + vec2(0.37, 0.71)).rgb;
		float l = dot(m, vec3(0.333));
		c *= mix(1.0, clamp(l * 1.6, 0.6, 1.25), macro);
	}
	c = mix(c, c * COLOR.rgb, tint_mix);
	vec3 wpos = (INV_VIEW_MATRIX * vec4(VERTEX, 1.0)).xyz;
	vec3 wn = normalize((INV_VIEW_MATRIX * vec4(NORMAL, 0.0)).xyz);
	float wall = 1.0 - smoothstep(0.5, 0.8, abs(wn.y));
	if (d1_strength > 0.0) {
		float g = 1.0;
		if (d1_gate_on > 0.5) {
			g = smoothstep(d1_gate_band.x, d1_gate_band.y, lum(d1_gate_avg) - lum(texture(d1_gate_tex, UV / d1_gate_uv_m + vec2(0.31, 0.17)).rgb));
		}
		if (d1_edge.y > d1_edge.x) {
			g *= 1.0 - smoothstep(d1_edge.x, d1_edge.y, seam_dist(UV));
		}
		c = layer(c, texture(d1_tex, UV / d1_uv_m).rgb, d1_avg, d1_mode, d1_strength, d1_color.rgb, d1_band, d1_pick, d1_floor_fade, wpos.y, wall, g);
	}
	if (d2_strength > 0.0) {
		float g = 1.0;
		if (d2_gate_on > 0.5) {
			g = smoothstep(d2_gate_band.x, d2_gate_band.y, lum(d2_gate_avg) - lum(texture(d2_gate_tex, UV / d2_gate_uv_m + vec2(0.31, 0.17)).rgb));
		}
		if (d2_edge.y > d2_edge.x) {
			g *= 1.0 - smoothstep(d2_edge.x, d2_edge.y, seam_dist(UV));
		}
		c = layer(c, texture(d2_tex, UV / d2_uv_m).rgb, d2_avg, d2_mode, d2_strength, d2_color.rgb, d2_band, d2_pick, d2_floor_fade, wpos.y, wall, g);
	}
	if (seam_every.x > 0.0 || seam_every.y > 0.0) {
		c = mix(c, seam_color.rgb, seam(UV));
	}
	ALBEDO = c;
	ROUGHNESS = roughness_value;
	METALLIC = metallic_value;
	EMISSION = emission_color.rgb * emission_energy;
}
"""
const MODES := {"mask": 0, "mul": 1, "color": 2}
const PICKS := {"dark": 0, "light": 1, "red": 2}

static var _shaders := {}
static var _tex := {}
## 外の絵の平均の色（いちばん小さいミップマップ。層の「平均より暗い所」の基準）
static var _avg := {}
static var _glb := {}
static var tex_bytes := 0


## 見本（Demo）の _ready の終わりから呼ぶ。引数が無ければ何もしない
static func wrap(demo) -> void:
	var args: Dictionary = demo.main.args
	if not (args.has("bk_kit") or args.has("bk_props")):
		return
	if args.has("bk_kit"):
		var dir := String(args.bk_kit)
		for f in DirAccess.get_files_at(dir):
			if f.ends_with(".json"):
				_inject_kit(dir.path_join(f))
	var props: Array = []
	if args.has("bk_props"):
		props = U.load_json(String(args.bk_props))
	var steps: Array = demo._steps
	var out: Array = []
	for s in steps:
		if s.has("shot"):
			var shot_name := String(s.shot)
			out.append({"ticks": 2, "setup": func(): _decorate(demo.main, props)})
			var before = s.get("after", null)
			s["after"] = func():
				if before != null:
					before.call()
				_report(shot_name)
		out.append(s)
	demo._steps = out


## キットの JSON（RoomKit.load_kit と同じ形）を読み、材質を作って RoomKit の読み置きに入れる
static func _inject_kit(path: String) -> void:
	var data: Dictionary = U.load_json(path)
	var id := String(data.get("id", path.get_file().get_basename()))
	var kit := {"id": id, "data": data, "surf": {}, "mats": {}}
	for k in data.get("surfaces", {}):
		kit.surf[k] = material(data.surfaces[k])
	for k in data.get("materials", {}):
		kit.mats[k] = material(data.materials[k])
	RoomKit._cache("kits")[id] = kit
	print("BK：キット %s を差し替え（%s）" % [id, path])


## 材質の定義 → 材質。"detail" も外のファイルも無ければ RoomKit.make_material と同じ
static func material(def: Dictionary) -> Material:
	var outside: bool = def.has("albedo") and not String(def.albedo).begins_with("res://")
	if not (def.has("detail") or def.has("detail2") or outside):
		return RoomKit.make_material(def)
	var fade: bool = def.has("near_fade") and RenderingServer.get_current_rendering_method() != "gl_compatibility"
	var m := ShaderMaterial.new()
	m.shader = _shader(fade)
	if fade:
		m.set_shader_parameter("near_fade", Vector2(float(def.near_fade[0]), float(def.near_fade[1])))
	if def.has("albedo"):
		m.set_shader_parameter("albedo_tex", tex(String(def.albedo)))
	m.set_shader_parameter("color", _col(def.get("color", "#ffffff")))
	m.set_shader_parameter("uv_m", float(def.get("uv_m", 2.0)))
	m.set_shader_parameter("roughness_value", float(def.get("roughness", 0.85)))
	m.set_shader_parameter("metallic_value", float(def.get("metallic", 0.0)))
	m.set_shader_parameter("tint_mix", float(def.get("tint_mix", 0.0)))
	m.set_shader_parameter("macro", float(def.get("macro", 0.0)))
	m.set_shader_parameter("tex_strength", float(def.get("tex_strength", 1.0)))
	if def.has("seams"):
		var s: Dictionary = def.seams
		var e = s.get("every", [2, 2])
		m.set_shader_parameter("seam_every", Vector2(float(e[0]), float(e[1])) if e is Array else Vector2(float(e), float(e)))
		m.set_shader_parameter("seam_width", float(s.get("width", 0.04)))
		m.set_shader_parameter("seam_color", Color(s.get("color", "#444641")))
	if def.has("emission"):
		m.set_shader_parameter("emission_color", Color(def.emission.get("color", "#ffbc52")))
		m.set_shader_parameter("emission_energy", float(def.emission.get("energy", 2.0)))
	for pair in [["detail", "d1"], ["detail2", "d2"]]:
		if not def.has(pair[0]):
			continue
		var d: Dictionary = def[pair[0]]
		var p: String = pair[1]
		m.set_shader_parameter(p + "_tex", tex(String(d.albedo)))
		m.set_shader_parameter(p + "_mode", int(MODES.get(String(d.get("mode", "mask")), 0)))
		var uv = d.get("uv_m", 2.0)
		m.set_shader_parameter(p + "_uv_m", Vector2(float(uv[0]), float(uv[1])) if uv is Array else Vector2(float(uv), float(uv)))
		m.set_shader_parameter(p + "_strength", float(d.get("strength", 0.5)))
		m.set_shader_parameter(p + "_color", _col(d.get("color", "#b75b43")))
		var b: Array = d.get("band", [0.08, 0.14])
		m.set_shader_parameter(p + "_band", Vector2(float(b[0]), float(b[1])))
		m.set_shader_parameter(p + "_pick", int(PICKS.get(String(d.get("pick", "dark")), 0)))
		var ff: Array = d.get("floor_fade", [0, 0])
		m.set_shader_parameter(p + "_floor_fade", Vector2(float(ff[0]), float(ff[1])))
		m.set_shader_parameter(p + "_avg", _mean(String(d.albedo)))
		var ed: Array = d.get("edge", [0, 0])
		m.set_shader_parameter(p + "_edge", Vector2(float(ed[0]), float(ed[1])))
		if d.has("gate"):
			var gd: Dictionary = d.gate
			m.set_shader_parameter(p + "_gate_tex", tex(String(gd.albedo)))
			m.set_shader_parameter(p + "_gate_on", 1.0)
			var gu = gd.get("uv_m", 6.0)
			m.set_shader_parameter(p + "_gate_uv_m", Vector2(float(gu[0]), float(gu[1])) if gu is Array else Vector2(float(gu), float(gu)))
			var gb: Array = gd.get("band", [0.05, 0.12])
			m.set_shader_parameter(p + "_gate_band", Vector2(float(gb[0]), float(gb[1])))
			m.set_shader_parameter(p + "_gate_avg", _mean(String(gd.albedo)))
	return m


## 外の絵の平均の色（vec3 の uniform には Color でなく Vector3 で渡す。Color だと 0 になる）
static func _mean(path: String) -> Vector3:
	var c: Color = _avg.get(path, Color(0.5, 0.5, 0.5))
	return Vector3(c.r, c.g, c.b)


## 色："#rrggbb" か [r, g, b]（1 を超えてよい。絵の平均の色をパレットに寄せる掛け算）
static func _col(v) -> Color:
	return Color(float(v[0]), float(v[1]), float(v[2])) if v is Array else Color(String(v))


static func _shader(fade: bool) -> Shader:
	if not _shaders.has(fade):
		var sh := Shader.new()
		sh.code = ("#define NEAR_FADE\n" if fade else "") + SHADER_CODE
		_shaders[fade] = sh
	return _shaders[fade]


## 絵：res:// はそのまま。外のファイルはミップマップを作り、VRAM 圧縮して読む（取り込みの compress/mode=2・mipmaps と同じ扱い）
static func tex(path: String) -> Texture2D:
	if path.begins_with("res://"):
		return load(path)
	if _tex.has(path):
		return _tex[path]
	var img := Image.load_from_file(path)
	if img == null:
		push_warning("BK：絵が読めない %s" % path)
		return null
	img.convert(Image.FORMAT_RGB8)
	img.generate_mipmaps()
	var data := img.get_data()
	var o := img.get_mipmap_offset(img.get_mipmap_count())
	# 色の絵は読むときに sRGB から直線の値になる（source_color）。比べる平均も直線の値に
	_avg[path] = Color8(data[o], data[o + 1], data[o + 2]).srgb_to_linear()
	if RenderingServer.get_current_rendering_method() != "gl_compatibility":
		img.compress(Image.COMPRESS_S3TC, Image.COMPRESS_SOURCE_SRGB)
	tex_bytes += img.get_data_size()
	var t := ImageTexture.create_from_image(img)
	_tex[path] = t
	return t


## 今の部屋に小物を足す（部屋を作り直すたびに 1 回）
static func _decorate(main, props: Array) -> void:
	var level: Node3D = main.level
	if level == null or level.has_meta("bk_props") or props.is_empty():
		return
	level.set_meta("bk_props", true)
	var room := String(main.game.room_id)
	var holder := Node3D.new()
	holder.name = "BkProps"
	level.add_child(holder)
	for p in props:
		if String(p.get("room", "")) != room:
			continue
		var node: Node3D
		if p.has("part"):
			# 比べのために、今のキットの部品（キットの材質で）も同じ並びに置ける
			var mi := MeshInstance3D.new()
			mi.mesh = RoomKit.part_mesh(String(p.part), RoomKit.load_kit(String(main.game.room.get("kit", ""))))
			mi.scale = Vector3.ONE * float(p.get("scale", 1.0))
			node = Node3D.new()
			node.add_child(mi)
		else:
			node = _instance(String(p.glb), float(p.get("height", 0.0)))
		if node == null:
			continue
		node.position = RoomGeo.v3(p.get("pos", [0, 0, 0]))
		node.rotation.y = float(p.get("yaw", 0.0)) * U.DEG
		var shadow: bool = p.get("shadow", false)
		for mi in node.find_children("*", "GeometryInstance3D", true, false):
			(mi as GeometryInstance3D).cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON if shadow else GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		holder.add_child(node)


## GLB（リポジトリの外）を読み、底の真ん中を原点に、高さ height（m）にそろえた節を返す
static func _instance(path: String, height: float) -> Node3D:
	if not _glb.has(path):
		var doc := GLTFDocument.new()
		var state := GLTFState.new()
		if doc.append_from_file(path, state) != OK:
			push_warning("BK：GLB が読めない %s" % path)
			_glb[path] = null
		else:
			var scene := doc.generate_scene(state)
			var packed := PackedScene.new()
			for c in scene.find_children("*", "", true, false):
				c.owner = scene
			packed.pack(scene)
			scene.free()
			_glb[path] = packed
	if _glb[path] == null:
		return null
	var inner: Node3D = _glb[path].instantiate()
	var box := _aabb(inner, Transform3D.IDENTITY)
	var s := height / box.size.y if height > 0.0 and box.size.y > 0.0 else 1.0
	var outer := Node3D.new()
	outer.name = path.get_base_dir().get_file()
	inner.scale = Vector3.ONE * s
	inner.position = -Vector3(box.get_center().x, box.position.y, box.get_center().z) * s
	outer.add_child(inner)
	return outer


static func _aabb(n: Node, xf: Transform3D) -> AABB:
	var box := AABB()
	var first := true
	var x := xf
	if n is Node3D:
		x = xf * (n as Node3D).transform
	if n is MeshInstance3D and (n as MeshInstance3D).mesh != null:
		box = x * (n as MeshInstance3D).mesh.get_aabb()
		first = false
	for c in n.get_children():
		var b := _aabb(c, x)
		if b.size == Vector3.ZERO:
			continue
		box = b if first else box.merge(b)
		first = false
	return box


static func _report(shot_name: String) -> void:
	print("BK計測 %s：draw %d・物 %d・三角形 %d・絵のメモリ %.1f MB・VRAM %.1f MB（BK の絵 %.1f MB）" % [shot_name,
		RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_DRAW_CALLS_IN_FRAME),
		RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_OBJECTS_IN_FRAME),
		RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_PRIMITIVES_IN_FRAME),
		RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TEXTURE_MEM_USED) / 1048576.0,
		RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_VIDEO_MEM_USED) / 1048576.0,
		tex_bytes / 1048576.0])
