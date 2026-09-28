class_name PropsView
extends Node3D
## 宝箱、住人、セーブビーコン、壊せる壁、拾える物の見た目

var _walls := {}
var _chests := {}
var _beams: Array[StandardMaterial3D] = []
var _npcs := {}
var _pickups := {}
var _time := 0.0


func build(game: GameSim) -> void:
	var crack := StandardMaterial3D.new()
	crack.albedo_texture = load("res://assets/textures/crack.png")
	crack.albedo_color = Color("#d8c8ae")
	crack.roughness = 0.95
	for b in game.breakables:
		var mi := MeshKit.add(self, MeshKit.box(b.size), crack, b.center, Vector3(0, b.yaw, 0))
		mi.visible = not b.broken
		_walls[b.id] = mi
	for c in game.chests:
		var root := Node3D.new()
		root.position = c.pos
		root.rotation.y = c.yaw
		add_child(root)
		MeshKit.add(root, MeshKit.box(Vector3(1.2, 0.55, 0.8)), MeshKit.mat(Color("#e9e3d6"), 0.35), Vector3(0, 0.275, 0))
		MeshKit.add(root, MeshKit.box(Vector3(1.22, 0.08, 0.82)), MeshKit.mat(Color("#b08a4a"), 0.4, 0.6), Vector3(0, 0.45, 0))
		var lid := Node3D.new()
		lid.position = Vector3(0, 0.55, -0.4)
		root.add_child(lid)
		MeshKit.add(lid, MeshKit.box(Vector3(1.2, 0.22, 0.8)), MeshKit.mat(Color("#d9d2c3"), 0.35), Vector3(0, 0.11, 0.4))
		var light := OmniLight3D.new()
		light.light_color = Color("#ffb23e")
		light.light_energy = 0.0 if c.opened else 1.5
		light.omni_range = 3.0
		light.position.y = 1.0
		root.add_child(light)
		if c.opened:
			lid.rotation.x = -1.9
		_chests[c.id] = [lid, light]
	for n in game.npcs:
		var root := Node3D.new()
		root.position = n.pos
		root.rotation.y = n.yaw
		add_child(root)
		var cap := CapsuleMesh.new()
		cap.radius = 0.3
		cap.height = 1.6
		MeshKit.add(root, cap, MeshKit.mat(Color("#7a5a3a")), Vector3(0, 0.8, 0))
		MeshKit.add(root, MeshKit.sphere(0.2), MeshKit.mat(Color("#d9a07a")), Vector3(0, 1.55, 0))
		MeshKit.add(root, MeshKit.box(Vector3(0.45, 0.7, 0.05)), MeshKit.mat(Color("#4d5a4a")), Vector3(0, 0.8, 0.3))
		MeshKit.add(root, MeshKit.box(Vector3(0.12, 0.6, 0.12)), MeshKit.mat(Color("#8a8a8a"), 0.3, 0.7), Vector3(-0.4, 0.95, 0))
		root.add_child(MeshKit.label(n.name, 2.1, Color("#ffe7b8"), 48))
		_npcs[n.id] = root
	for b in game.beacons:
		MeshKit.add(self, MeshKit.cyl(0.5, 0.7, 0.4), MeshKit.mat(Color("#e9e3d6"), 0.35), b.pos + Vector3(0, 0.2, 0))
		var beam := MeshKit.glow(Color("#ffcf7a"), 1.5, 0.35)
		var cyl := MeshKit.cyl(0.25, 0.35, 12.0)
		cyl.cap_top = false
		cyl.cap_bottom = false
		MeshKit.add(self, cyl, beam, b.pos + Vector3(0, 6.2, 0))
		_beams.append(beam)


func sync(game: GameSim, dt: float) -> void:
	_time += dt
	for b in game.breakables:
		var m: MeshInstance3D = _walls.get(b.id)
		if m == null:
			continue
		m.visible = not b.broken
		# ドリルで削られている間は震える
		var shaking: bool = b.progress > 0.0 and not b.broken
		m.position.x = b.center.x + (sin(_time * 90.0) * 0.02 if shaking else 0.0)
	for c in game.chests:
		var v: Array = _chests.get(c.id, [])
		if v.is_empty() or not c.opened:
			continue
		v[0].rotation.x += (-1.9 - v[0].rotation.x) * minf(1.0, dt * 8.0)
		v[1].light_energy = maxf(0.0, v[1].light_energy - dt * 2.0)
	for n in game.npcs:
		var r: Node3D = _npcs.get(n.id)
		if r:
			r.rotation.y += U.wrap_angle(n.yaw - r.rotation.y) * minf(1.0, dt * 8.0)
	for beam in _beams:
		beam.albedo_color.a = 0.25 + sin(_time * 2.0) * 0.08
	# 拾える物
	var alive := {}
	for k in game.pickups:
		alive[k] = true
		var m: MeshInstance3D = _pickups.get(k)
		if m == null:
			var color := Color("#ffcf3a") if k.kind == "cells" else (Color("#5ad1ff") if k.kind == "energy" else Color("#7dff8a"))
			var s := 0.12 if k.kind == "cells" else 0.18
			m = MeshKit.add(self, MeshKit.sphere(s, 4), MeshKit.glow(color, 2.0))
			_pickups[k] = m
		m.position = k.pos + Vector3(0, sin(_time * 4.0 + k.age) * 0.05, 0)
		m.rotation.y = _time * 3.0
	for k in _pickups.keys():
		if not alive.has(k):
			_pickups[k].queue_free()
			_pickups.erase(k)
