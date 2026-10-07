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


## geometry：{ faces, tints? }。tints が無ければ既定の色
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
				for k in 3:
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
