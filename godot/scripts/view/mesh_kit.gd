class_name MeshKit
## 単純な形と材質を作る道具（仮の番機や仕掛けの見た目に使う）


static func mat(color: Color, roughness: float = 0.6, metallic: float = 0.0) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.albedo_color = color
	m.roughness = roughness
	m.metallic = metallic
	return m


static func glow(color: Color, energy: float = 2.0, alpha: float = 1.0) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.albedo_color = Color(color, alpha)
	m.emission_enabled = true
	m.emission = color
	m.emission_energy_multiplier = energy
	if alpha < 1.0:
		m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
		m.no_depth_test = false
		m.cull_mode = BaseMaterial3D.CULL_DISABLED
	return m


static func add(parent: Node3D, mesh: Mesh, material: Material, pos: Vector3 = Vector3.ZERO, rot: Vector3 = Vector3.ZERO) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	mi.mesh = mesh
	mi.material_override = material
	mi.position = pos
	mi.rotation = rot
	parent.add_child(mi)
	return mi


static func box(size: Vector3) -> BoxMesh:
	var b := BoxMesh.new()
	b.size = size
	return b


static func cyl(top: float, bottom: float, height: float, segs: int = 12) -> CylinderMesh:
	var c := CylinderMesh.new()
	c.top_radius = top
	c.bottom_radius = bottom
	c.height = height
	c.radial_segments = segs
	return c


static func sphere(r: float, segs: int = 12) -> SphereMesh:
	var s := SphereMesh.new()
	s.radius = r
	s.height = r * 2.0
	s.radial_segments = segs
	s.rings = segs / 2
	return s


## 番機の警戒の合図（頭上の「！」）：Codex の部品 ui_parts_lockon_alert を、いつも正面を向く板にして出す（絵が無ければ文字）
static func alert_mark(height: float) -> Node3D:
	var t := UiArt.tex("ui_parts_lockon_alert")
	if t == null:
		return label("!", height)
	var s := Sprite3D.new()
	s.texture = t
	s.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	s.no_depth_test = true
	s.shaded = false
	s.pixel_size = 0.0032
	s.render_priority = 10
	s.position.y = height
	return s


static func label(text: String, height: float, color: Color = Color("#ffcc33"), size: int = 64) -> Label3D:
	var l := Label3D.new()
	l.text = text
	l.font_size = size
	l.modulate = color
	l.outline_size = 12
	l.outline_modulate = Color(0.1, 0.08, 0.06, 0.8)
	l.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	l.no_depth_test = true
	l.pixel_size = 0.006
	l.position.y = height
	return l
