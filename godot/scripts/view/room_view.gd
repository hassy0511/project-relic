class_name RoomView
extends RefCounted
## 部屋の地形の見た目。GLB の部屋はそのまま、データから作った灰色の部屋は面を色ごとにまとめて 1 つのメッシュにする。


static func build(world: World, room_id: String) -> Node3D:
	var r := world.room(room_id)
	var root: Node3D
	if r.has("model"):
		root = LevelLoader.load_level("res://assets/%s" % r.model).node
		var extra := RoomGeo.build(r)
		if not extra.faces.is_empty():
			root.add_child(mesh_node(extra))
	else:
		root = Node3D.new()
		root.add_child(mesh_node(world.geometry(room_id)))
	root.name = "Room"
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
