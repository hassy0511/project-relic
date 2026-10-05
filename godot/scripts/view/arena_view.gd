class_name ArenaView
extends RefCounted
## 試しの部屋の見た目：Arena の地形の面をそのまま描き、レール（外周）の輪を足す。


static func build(geometry: Dictionary, rail_radius := 10.5) -> Node3D:
	var root := Node3D.new()
	root.name = "ArenaLevel"
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	for faces in geometry.faces:
		for i in range(0, faces.size(), 3):
			var n: Vector3 = (faces[i + 1] - faces[i]).cross(faces[i + 2] - faces[i]).normalized()
			for k in 3:
				st.set_normal(n)
				st.add_vertex(faces[i + k])
	var m := ShaderMaterial.new()
	m.shader = LevelLoader.GRID
	m.set_shader_parameter("albedo", Color(0.62, 0.59, 0.55))
	var mi := MeshInstance3D.new()
	mi.mesh = st.commit()
	mi.material_override = m
	root.add_child(mi)
	# レール：床に埋めた黒鉛の輪（外周を滑る道）
	var ring := MeshInstance3D.new()
	var tm := TorusMesh.new()
	tm.inner_radius = rail_radius - 0.25
	tm.outer_radius = rail_radius + 0.25
	tm.rings = 48
	tm.ring_segments = 6
	ring.mesh = tm
	ring.scale = Vector3(1, 0.12, 1)
	ring.position.y = 0.02
	ring.material_override = MeshKit.mat(Color("#3a3530"), 0.5, 0.4)
	ring.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	root.add_child(ring)
	return root
