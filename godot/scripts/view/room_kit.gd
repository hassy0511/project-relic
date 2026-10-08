class_name RoomKit
extends RefCounted
## 部屋の「キット」：データで組んだ灰色の地形に材質を貼り、飾りの部品（GLB）を並べる。見た目だけを作る。
## 当たり判定は今までどおり geometry だけから作る（ここは何も変えない）。書き方は docs/design/42_コンテンツの書き方.md の 14 章。
##   部屋 { "kit": "ruins_b1", "dress": [ { "part": "ruins/b1_pillar", "pos": [x,y,z], "yaw": 90, "scale": 1.0 } ] }
##   形   { ..., "skin": "metal" | { "floor": "sand", "wall": "plate" }, "hide": true, "trim": false }
## 軽さのため：材質はキットごとに 1 回だけ作って共有、部屋の面は材質ごとに 1 つのメッシュ、同じ部品は MultiMesh でまとめて 1 回で描く。
## 毎フレームの処理は無い。

const KIT_PATH := "res://content/kits/%s.json"
const PART_PATH := "res://assets/kit/%s.glb"
const SHADER := preload("res://assets/shaders/kit_surface.gdshader")
const SHADER_FADE := preload("res://assets/shaders/kit_surface_fade.gdshader")
const GLOW := preload("res://assets/shaders/kit_glow.gdshader")

## 読んだキットと部品の置き場。終了のときに一緒に消えるよう、static var ではなく木の根（root）のメタに持つ
##   kits：キットの id → { id, data, surf: { 面の名前: Material }, mats: { 部品の材質の名前: Material } }
##   parts："キット id|部品" → Mesh（無い部品は null）
static func _cache(key: String) -> Dictionary:
	var tree := Engine.get_main_loop() as SceneTree
	var holder: Object = tree.root if tree != null else Engine
	if not holder.has_meta("room_kit_cache"):
		holder.set_meta("room_kit_cache", {"kits": {}, "parts": {}})
	return holder.get_meta("room_kit_cache")[key]


## キットを読む（1 回だけ）。無いときは {} と警告
static func load_kit(id: String) -> Dictionary:
	if id == "":
		return {}
	var _kits := _cache("kits")
	if _kits.has(id):
		return _kits[id]
	var path := KIT_PATH % id
	if not FileAccess.file_exists(path):
		push_warning("キットが無い: %s" % path)
		_kits[id] = {}
		return {}
	var data: Dictionary = U.load_json(path)
	var kit := {"id": id, "data": data, "surf": {}, "mats": {}}
	var surfaces: Dictionary = data.get("surfaces", {})
	for k in surfaces:
		kit.surf[k] = make_material(surfaces[k])
	var mats: Dictionary = data.get("materials", {})
	for k in mats:
		kit.mats[k] = make_material(mats[k])
	_kits[id] = kit
	return kit


## 材質の定義 → 材質。{ "albedo": "res://…png", "color": "#rrggbb", "uv_m": 2, "roughness": 0.85, "metallic": 0,
##   "tint_mix": 0, "macro": 0, "tex_strength": 1, "seams": { "every": [2, 1.33], "width": 0.04, "color": "#444641" },
##   "emission": { "color": "#ffbc52", "energy": 3 } }
##   光の筋（"blend": "add"）：{ "blend": "add", "color", "strength": 0.25, "fade_m": 7 }（kit_glow.gdshader）
##   "near_fade": [0.8, 1.5]：カメラから 0.8 m より近い所を網目で消し、1.5 m で元に戻す（当たり判定の無い飾りの部品の材質に付ける。
##   日よけ・柱・灯がカメラの前を塞がない）。網目は discard を使うので、軽さを優先するスマホ・ブラウザ版（gl_compatibility）では付けない
static func make_material(def: Dictionary) -> Material:
	var m := ShaderMaterial.new()
	if def.get("blend", "") == "add":
		m.shader = GLOW
		m.set_shader_parameter("color", Color(def.get("color", "#ffd9a0")))
		m.set_shader_parameter("strength", float(def.get("strength", 0.25)))
		m.set_shader_parameter("fade_m", float(def.get("fade_m", 7.0)))
		return m
	m.shader = SHADER
	if def.has("near_fade") and RenderingServer.get_current_rendering_method() != "gl_compatibility":
		m.shader = SHADER_FADE
		var nf: Array = def.near_fade
		m.set_shader_parameter("near_fade", Vector2(float(nf[0]), float(nf[1])))
	if def.has("albedo"):
		var p := String(def.albedo)
		if ResourceLoader.exists(p):
			m.set_shader_parameter("albedo_tex", load(p))
		else:
			push_warning("キットの絵が無い: %s" % p)
	m.set_shader_parameter("color", Color(def.get("color", "#ffffff")))
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
		var em: Dictionary = def.emission
		m.set_shader_parameter("emission_color", Color(em.get("color", "#ffbc52")))
		m.set_shader_parameter("emission_energy", float(em.get("energy", 2.0)))
	return m


# ---------------------------------------------------------------- 部屋の面

## geometry を、キットの材質ごとに 1 つのメッシュにする（"hide": true の形は描かない）。kit が {} なら灰色の格子（今までの見た目）
static func surfaces(room: Dictionary, kit: Dictionary) -> MeshInstance3D:
	if kit.is_empty():
		var vis := room.duplicate()
		vis["geometry"] = room.get("geometry", []).filter(func(s): return not s.get("hide", false))
		var grey := RoomView.mesh_node(RoomGeo.build(vis))
		grey.name = "KitSurfaces"
		return grey
	var data: Dictionary = kit.data
	var auto: Dictionary = data.get("auto", {})
	var up := float(auto.get("up", 0.6))
	var trim: Dictionary = data.get("trim", {})
	var trim_on: Array = trim.get("on", ["wall"])
	var tools := {}
	for s in room.get("geometry", []):
		if s.get("hide", false):
			continue
		var tint := Color(s.tint) if s.has("tint") else RoomGeo.DEFAULT_TINT
		var skin = s.get("skin", null)
		var do_trim: bool = not trim.is_empty() and s.get("trim", true)
		for f in RoomGeo.shape(s):
			var tris: PackedVector3Array = f
			var n_tri := tris.size() / 3
			var i := 0
			while i < n_tri:
				var a := tris[i * 3]
				var b := tris[i * 3 + 1]
				var c := tris[i * 3 + 2]
				var n := (b - a).cross(c - a).normalized()
				var cls := "floor" if n.y > up else ("ceiling" if n.y < -up else "wall")
				var surf := _pick(skin, cls, auto)
				var st := _tool(tools, surf)
				_tri(st, a, b, c, n, cls, tint)
				# 箱の面は 2 つの三角形（a,b,c）（a,c,d）の四角。縦の四角には縁取り（幅木・笠木）を付ける
				if i + 1 < n_tri and tris[i * 3 + 3] == a and tris[i * 3 + 4] == c:
					var d := tris[i * 3 + 5]
					_tri(st, a, c, d, n, cls, tint)
					if do_trim and cls == "wall" and absf(n.y) < 0.05 and surf in trim_on:
						_trim(_tool(tools, String(trim.get("surface", "trim"))), [a, b, c, d], n, trim, tint)
					i += 2
				else:
					i += 1
	var mesh := ArrayMesh.new()
	for k in tools:
		var st: SurfaceTool = tools[k]
		st.commit(mesh)
		var mat: Material = kit.surf.get(k, null)
		if mat == null:
			push_warning("キット %s に面 %s が無い" % [kit.id, k])
			mat = make_material({"color": "#9a948c"})
			kit.surf[k] = mat
		mesh.surface_set_material(mesh.get_surface_count() - 1, mat)
	var mi := MeshInstance3D.new()
	mi.name = "KitSurfaces"
	mi.mesh = mesh
	return mi


static func _pick(skin, cls: String, auto: Dictionary) -> String:
	if skin is String:
		return skin
	if skin is Dictionary and skin.has(cls):
		return String(skin[cls])
	return String(auto.get(cls, cls))


static func _tool(tools: Dictionary, surf: String) -> SurfaceTool:
	if not tools.has(surf):
		var st := SurfaceTool.new()
		st.begin(Mesh.PRIMITIVE_TRIANGLES)
		tools[surf] = st
	return tools[surf]


## UV はメートル：床・天井は (x, z)、壁は (壁に沿った長さ, -高さ)（右手の向きに増え、絵が上下逆にならない）
static func _uv(p: Vector3, n: Vector3, cls: String) -> Vector2:
	if cls != "wall":
		return Vector2(p.x, p.z)
	var t := Vector3(n.z, 0.0, -n.x)
	if t.length_squared() < 1e-6:
		t = Vector3.RIGHT
	return Vector2(p.dot(t.normalized()), -p.y)


## a,b,c は RoomGeo の向き（(b-a)×(c-a) が外向きの法線）。Godot は時計回りが表なので、c と b を入れ替えて足す
static func _tri(st: SurfaceTool, a: Vector3, b: Vector3, c: Vector3, n: Vector3, cls: String, tint: Color) -> void:
	for p in [a, c, b]:
		st.set_normal(n)
		st.set_color(tint)
		st.set_uv(_uv(p, n, cls))
		st.add_vertex(p)


## 四角（向きの合った 2 つの三角形）を足す。法線 n の向きに表を向ける
static func _quad(st: SurfaceTool, q: Array, n: Vector3, cls: String, tint: Color) -> void:
	var a: Vector3 = q[0]
	var b: Vector3 = q[1]
	var c: Vector3 = q[2]
	var d: Vector3 = q[3]
	if (b - a).cross(c - a).dot(n) < 0.0:
		_tri(st, a, c, b, n, cls, tint)
		_tri(st, a, d, c, n, cls, tint)
	else:
		_tri(st, a, b, c, n, cls, tint)
		_tri(st, a, c, d, n, cls, tint)


## 縦の四角の下（幅木）と上（笠木）に、壁から out だけ出た帯を付ける。trim：{ base, top, out, min_h }
static func _trim(st: SurfaceTool, q: Array, n: Vector3, trim: Dictionary, tint: Color) -> void:
	var y0 := INF
	var y1 := -INF
	for p in q:
		y0 = minf(y0, p.y)
		y1 = maxf(y1, p.y)
	var h := y1 - y0
	var lo: Array = q.filter(func(p): return absf(p.y - y0) < 1e-3)
	if lo.size() != 2 or h < 0.05:
		return
	var p0 := Vector3(lo[0].x, 0, lo[0].z)
	var p1 := Vector3(lo[1].x, 0, lo[1].z)
	var base := float(trim.get("base", 0.3))
	var top := float(trim.get("top", 0.2))
	var out := float(trim.get("out", 0.05))
	if h < float(trim.get("min_h", 0.0)):
		return
	if h < base + top + 0.2:
		_band(st, p0, p1, y1 - minf(top, h), y1, n, out, tint)
		return
	if base > 0.0:
		_band(st, p0, p1, y0, y0 + base, n, out, tint)
	if top > 0.0:
		_band(st, p0, p1, y1 - top, y1, n, out, tint)


## 帯：壁の面（p0–p1、高さ y0〜y1）から法線の向きに out 出た薄い箱（正面・上・下・両端）
static func _band(st: SurfaceTool, p0: Vector3, p1: Vector3, y0: float, y1: float, n: Vector3, out: float, tint: Color) -> void:
	var o := n * out
	var a0 := p0 + Vector3(0, y0, 0)
	var a1 := p1 + Vector3(0, y0, 0)
	var b0 := p0 + Vector3(0, y1, 0)
	var b1 := p1 + Vector3(0, y1, 0)
	_quad(st, [a0 + o, a1 + o, b1 + o, b0 + o], n, "wall", tint)
	_quad(st, [b0, b1, b1 + o, b0 + o], Vector3.UP, "floor", tint)
	_quad(st, [a0, a0 + o, a1 + o, a1], Vector3.DOWN, "ceiling", tint)
	var side := (p1 - p0).normalized()
	_quad(st, [a0, b0, b0 + o, a0 + o], -side, "wall", tint)
	_quad(st, [a1, a1 + o, b1 + o, b1], side, "wall", tint)


# ---------------------------------------------------------------- 飾りの部品

## "dress" の部品を並べる。同じ部品が 2 つ以上なら MultiMesh。無い部品の名前は missing に足す（落とさずに飛ばす）
## 1 件：{ "part": "ruins/b1_pillar", "pos": [x,y,z], "yaw": 度, "rot": [x,y,z]（度、yaw より優先）, "scale": 1 か [x,y,z],
##        "count": 1, "step": [dx,dy,dz]（count 個をワールドの step ずつずらして並べる）, "shadow": true,
##        "light": { "at": [x,y,z]（部品の中の位置）, "color", "range", "energy" } }
static func dress(room: Dictionary, kit: Dictionary, missing: Array) -> Node3D:
	var root := Node3D.new()
	root.name = "Dress"
	var groups := {}   # "部品|影" → [Transform3D...]
	var kit_id := String(kit.get("id", ""))
	var default_shadow: bool = kit.get("data", {}).get("dress_shadows", true)
	for d in room.get("dress", []):
		var part := String(d.get("part", ""))
		var mesh := part_mesh(part, kit)
		if mesh == null:
			if not part in missing:
				missing.append(part)
			continue
		var basis := Basis.from_euler(RoomGeo.v3(d.rot) * U.DEG) if d.has("rot") else Basis(Vector3.UP, float(d.get("yaw", 0.0)) * U.DEG)
		var sc = d.get("scale", 1.0)
		basis = basis.scaled_local(RoomGeo.v3(sc) if sc is Array else Vector3.ONE * float(sc))
		var pos := RoomGeo.v3(d.get("pos", [0, 0, 0]))
		var step := RoomGeo.v3(d.get("step", [0, 0, 0]))
		var key := "%s|%s" % [part, str(d.get("shadow", default_shadow))]
		if not groups.has(key):
			groups[key] = []
		for k in maxi(1, int(d.get("count", 1))):
			var xf := Transform3D(basis, pos + step * k)
			groups[key].append(xf)
			if d.has("light"):
				root.add_child(_light(d.light, xf))
	for key in groups:
		var part: String = key.split("|")[0]
		var shadow: bool = key.split("|")[1] == "true"
		var mesh := part_mesh(part, kit)
		var xfs: Array = groups[key]
		var gi: GeometryInstance3D
		if xfs.size() == 1:
			var mi := MeshInstance3D.new()
			mi.mesh = mesh
			mi.transform = xfs[0]
			gi = mi
		else:
			var mm := MultiMesh.new()
			mm.transform_format = MultiMesh.TRANSFORM_3D
			mm.mesh = mesh
			mm.instance_count = xfs.size()
			for i in xfs.size():
				mm.set_instance_transform(i, xfs[i])
			var mmi := MultiMeshInstance3D.new()
			mmi.multimesh = mm
			gi = mmi
		gi.name = part.replace("/", "_")
		gi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON if shadow else GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		root.add_child(gi)
	if not missing.is_empty():
		push_warning("飾りの部品が無い（%s）：%s" % [room.get("id", "?"), ", ".join(missing)])
	return root


## 部品の明かり：{ "at": 部品の中の位置, "color", "range", "energy" }。"type": "spot" なら "dir"（部品の中の向き）・"angle"（度）・
## "shadow"（影。重いので部屋に 1 つまで）のスポット（割れ目から差す光など）
static func _light(l: Dictionary, xf: Transform3D) -> Light3D:
	var o: Light3D
	if l.get("type", "omni") == "spot":
		var sp := SpotLight3D.new()
		sp.spot_range = float(l.get("range", 12.0))
		sp.spot_angle = float(l.get("angle", 35.0))
		sp.spot_attenuation = float(l.get("attenuation", 0.6))
		var dir := (xf.basis * RoomGeo.v3(l.get("dir", [0, -1, 0]))).normalized()
		var up := Vector3.UP if absf(dir.y) < 0.95 else Vector3.FORWARD
		sp.basis = Basis.looking_at(dir, up)
		o = sp
	else:
		var om := OmniLight3D.new()
		om.omni_range = float(l.get("range", 6.0))
		o = om
	o.position = xf * RoomGeo.v3(l.get("at", [0, 1, 0]))
	o.light_color = Color(l.get("color", "#ffbc52"))
	o.light_energy = float(l.get("energy", 1.0))
	o.shadow_enabled = bool(l.get("shadow", false))
	return o


## 部品の GLB を 1 つのメッシュにまとめる（材質の名前ごとに 1 面）。キットの "materials" に同じ名前があれば、その共有の材質に替える
static func part_mesh(part: String, kit: Dictionary) -> Mesh:
	var key := "%s|%s" % [kit.get("id", ""), part]
	var _parts := _cache("parts")
	if _parts.has(key):
		return _parts[key]
	var path := PART_PATH % part
	if part == "" or part.contains("..") or not ResourceLoader.exists(path):
		_parts[key] = null
		return null
	var scene: PackedScene = load(path)
	var inst := scene.instantiate()
	var by_mat := {}    # 材質の名前 → [SurfaceTool, 元の材質]
	_collect(inst, Transform3D.IDENTITY, by_mat)
	inst.free()
	var mesh := ArrayMesh.new()
	var mats: Dictionary = kit.get("mats", {})
	for name in by_mat:
		var st: SurfaceTool = by_mat[name][0]
		st.commit(mesh)
		mesh.surface_set_material(mesh.get_surface_count() - 1, mats.get(name, by_mat[name][1]))
	_parts[key] = mesh
	return mesh


static func _collect(n: Node, parent_xf: Transform3D, by_mat: Dictionary) -> void:
	var xf := parent_xf
	if n is Node3D:
		xf = parent_xf * (n as Node3D).transform
	if n is MeshInstance3D and (n as MeshInstance3D).mesh != null:
		var m: Mesh = (n as MeshInstance3D).mesh
		for s in m.get_surface_count():
			var mat := m.surface_get_material(s)
			var name := mat.resource_name if mat != null and mat.resource_name != "" else "default"
			if not by_mat.has(name):
				var st := SurfaceTool.new()
				st.begin(Mesh.PRIMITIVE_TRIANGLES)
				by_mat[name] = [st, mat]
			(by_mat[name][0] as SurfaceTool).append_from(m, s, xf)
	for c in n.get_children():
		_collect(c, xf, by_mat)
