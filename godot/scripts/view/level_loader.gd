class_name LevelLoader
## 地形の GLB を読み込み、見た目と当たり判定のデータに分ける。
## - メッシュは見た目にも当たり判定にも使う（名前に _nocol を含むものは当たり判定なし、_col は見た目なし）
## - 名前が m_ で始まるノードは目印（位置と向き）

const GRID := preload("res://assets/shaders/grid.gdshader")


## 返り値：{ node: 見た目の Node3D, geometry: { faces, markers } }
static func load_level(path: String) -> Dictionary:
	var scene: PackedScene = load(path)
	var root: Node3D = scene.instantiate()
	var faces: Array = []
	var markers := {}
	var mats := {}
	_walk(root, Transform3D.IDENTITY, faces, markers, mats)
	return {"node": root, "geometry": {"faces": faces, "markers": markers}}


static func _walk(n: Node, parent_xf: Transform3D, faces: Array, markers: Dictionary, mats: Dictionary) -> void:
	var xf := parent_xf
	if n is Node3D:
		xf = parent_xf * (n as Node3D).transform
	if n.name.begins_with("m_"):
		# 目印の向き：ローカルの +Z が正面（yaw=0 が +Z）
		var fwd := xf.basis.z
		markers[n.name.substr(2)] = {"pos": xf.origin, "yaw": atan2(fwd.x, fwd.z)}
	elif n is MeshInstance3D:
		var mi := n as MeshInstance3D
		if not mi.name.contains("_nocol"):
			var local := mi.mesh.get_faces()
			var world := PackedVector3Array()
			world.resize(local.size())
			for i in local.size():
				world[i] = xf * local[i]
			faces.append(world)
		if mi.name.contains("_col"):
			mi.visible = false
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
		for s in mi.mesh.get_surface_count():
			var src := mi.mesh.surface_get_material(s)
			var key := src.resource_name if src else "default"
			if not mats.has(key):
				var m := ShaderMaterial.new()
				m.shader = GRID
				var col := Color(0.6, 0.58, 0.55)
				if src is BaseMaterial3D:
					col = (src as BaseMaterial3D).albedo_color
				m.set_shader_parameter("albedo", col)
				mats[key] = m
			mi.set_surface_override_material(s, mats[key])
	for c in n.get_children():
		_walk(c, xf, faces, markers, mats)
