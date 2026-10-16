class_name RoomView
extends RefCounted
## 部屋の地形の見た目。GLB の部屋はそのまま、データから作った灰色の部屋は面を色ごとにまとめて 1 つのメッシュにする。


static func build(world: World, room_id: String) -> Node3D:
	var r := world.room(room_id)
	# キット（"kit"）・飾り（"dress"）・形ごとの "skin" / "hide"：RoomKit（docs/design/42_コンテンツの書き方.md 14 章）
	var kit := RoomKit.load_kit(String(r.get("kit", "")))
	var custom: bool = r.has("kit") or r.get("geometry", []).any(func(s): return s.get("hide", false))
	var root: Node3D
	if r.has("model"):
		root = LevelLoader.load_level("res://assets/%s" % r.model).node
		var extra := RoomGeo.build(r)
		if custom:
			root.add_child(RoomKit.surfaces(r, kit))
		elif not extra.faces.is_empty():
			root.add_child(mesh_node(extra))
	else:
		root = Node3D.new()
		root.add_child(RoomKit.surfaces(r, kit) if custom else mesh_node(world.geometry(room_id)))
	if r.has("dress"):
		var missing: Array = []
		root.add_child(RoomKit.dress(r, kit, missing))
		root.set_meta("missing_parts", missing)
	if r.has("kit") and kit.is_empty():
		root.set_meta("missing_kit", String(r.kit))
	# 町の下の巡礼機オルド（"ordo": { "pos": [x,y,z], "ground": true, "back": "town/ordo_back" }。部屋の座標でのオルドの原点 = 背の歩行面の
	# 真ん中、+Z が船首）：体は部屋と一緒に止まり、120 m 下の砂の床が流れる（OrdoView の body_fixed・ground）。"back" は背の上の遠くの町の
	# キットの部品で、オルドと同じ 3 つの面にまとめて描く。歩く・止まるは main.gd がフラグから決める（docs/design/42_コンテンツの書き方.md 14.5）
	if r.has("ordo"):
		var o := OrdoView.new()
		o.name = "Ordo"
		o.body_fixed = true
		o.ground = bool(r.ordo.get("ground", true))
		o.back_part = String(r.ordo.get("back", ""))
		o.position = RoomGeo.v3(r.ordo.get("pos", [0, 0, 0]))
		root.add_child(o)
	root.name = "Room"
	# 部屋の明かり（街灯・窓・室内灯）：{ "lights": [ { "pos": [x,y,z], "color": "#ffb060", "range": 10, "energy": 1.5 } ] }
	for l in r.get("lights", []):
		var o := OmniLight3D.new()
		o.position = RoomGeo.v3(l.pos)
		o.light_color = Color(l.get("color", "#ffc87a"))
		o.light_energy = float(l.get("energy", 1.5))
		o.omni_range = float(l.get("range", 10.0))
		root.add_child(o)
	return root


## geometry：{ faces, tints? }。tints が無ければ既定の色。
## 面の三角形 a,b,c は RoomGeo の向き（(b-a)×(c-a) が外向きの法線）。Godot は時計回りが表なので、c と b を入れ替えて足す
## （RoomKit._tri と同じ）。前は a,b,c の順のまま足して表と裏が逆になり、灰色の部屋の箱が裏返しに描かれた
## （手前の面が消えて奥の面の裏が見え、床は暗く、段・溝・坂の形が読み取りにくかった。2026-10-15、
## docs/progress_shots/stage/grey_rooms_winding_before_after.jpg）
static func mesh_node(geo: Dictionary) -> MeshInstance3D:
	var by_tint := {}
	var tints: Array = geo.get("tints", [])
	for i in geo.faces.size():
		var c: Color = tints[i] if i < tints.size() else RoomGeo.DEFAULT_TINT
		if not by_tint.has(c):
			by_tint[c] = []
		by_tint[c].append(geo.faces[i])
	var mesh := ArrayMesh.new()
	for c in by_tint:
		var st := SurfaceTool.new()
		st.begin(Mesh.PRIMITIVE_TRIANGLES)
		for faces in by_tint[c]:
			for i in range(0, faces.size(), 3):
				var n: Vector3 = (faces[i + 1] - faces[i]).cross(faces[i + 2] - faces[i]).normalized()
				for k in [0, 2, 1]:
					st.set_normal(n)
					st.add_vertex(faces[i + k])
		var m := ShaderMaterial.new()
		m.shader = LevelLoader.GRID
		m.set_shader_parameter("albedo", c)
		st.commit(mesh)
		mesh.surface_set_material(mesh.get_surface_count() - 1, m)
	var mi := MeshInstance3D.new()
	mi.mesh = mesh
	return mi
