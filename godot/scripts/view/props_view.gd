class_name PropsView
extends Node3D
## 宝箱、住人、セーブビーコン、壊せる壁、拾える物の見た目

var _walls := {}
var _chests := {}
var _beams: Array[StandardMaterial3D] = []
var _npcs := {}
var _npc_models := {}   # id → {anim, face_mats, expr}
var _pickups := {}
var _time := 0.0
var _doors := {}
var _exits := {}
var _switches := {}
var _movers := {}
var _loot := {}
var _door_amt := {}

## 住人の 3D モデル（絵から起こした GLB。tools/blender/recon/build_char.py）。無ければ従来の簡単な形で描く
const NPC_MODELS := {"npc_yana": "res://assets/models/yana.glb"}
## 会話の行の顔（dialogue の face）→ 顔のテクスチャの 2×2 の区画（ヤーナ：0 通常、1 豪快に笑う、2 驚き、3 怒る）。
## 区画の無い顔は近いものか通常にする
const NPC_FACES := {"normal": 0, "smile": 0, "smirk": 0, "serious": 0, "sad": 0, "laugh": 1, "surprised": 2, "angry": 3}


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
		var path: String = NPC_MODELS.get(n.id, "")
		if path != "" and ResourceLoader.exists(path):
			_npc_models[n.id] = _add_npc_model(root, path)
		else:
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
	_build_world_objects(game)


## 部屋の仕掛け：扉・出口・スイッチ・動く足場・端末・置いてある物
func _build_world_objects(game: GameSim) -> void:
	var metal := MeshKit.mat(Color("#8c8478"), 0.4, 0.5)
	for d in game.doors:
		var root := Node3D.new()
		root.position = d.pos
		root.rotation.y = d.yaw
		add_child(root)
		MeshKit.add(root, MeshKit.box(d.size), metal, Vector3(0, d.size.y * 0.5, 0))
		MeshKit.add(root, MeshKit.box(Vector3(d.size.x * 0.8, 0.12, d.size.z + 0.04)), MeshKit.glow(Color("#ffb23e"), 1.5), Vector3(0, d.size.y * 0.55, 0))
		_doors[d] = root
		_door_amt[d] = 1.0 if d.is_open else 0.0
		root.visible = not d.is_open
	for x in game.exits:
		var glow := MeshKit.glow(Color("#5ad1ff"), 1.0, 0.12)
		var mi := MeshKit.add(self, MeshKit.box(x.half * 2.0), glow, x.center)
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		_exits[x] = glow
	for sw in game.switches:
		var glow := MeshKit.glow(Color("#7a8aa0"), 1.0)
		if sw.mode == "interact":
			MeshKit.add(self, MeshKit.box(Vector3(0.5, 1.0, 0.5)), metal, sw.pos + Vector3(0, 0.5, 0))
			MeshKit.add(self, MeshKit.sphere(0.2), glow, sw.pos + Vector3(0, 1.1, 0))
		else:
			MeshKit.add(self, MeshKit.sphere(sw.radius * 0.8), glow, sw.pos)
		_switches[sw] = glow
	for m in game.movers:
		var mi := MeshKit.add(self, MeshKit.box(m.size), MeshKit.mat(Color("#a79b86"), 0.5, 0.3), m.pos + Vector3(0, m.size.y * 0.5, 0))
		_movers[m] = mi
	for t in game.terminals:
		MeshKit.add(self, MeshKit.box(Vector3(0.8, 1.2, 0.6)), metal, t.pos + Vector3(0, 0.6, 0))
		MeshKit.add(self, MeshKit.box(Vector3(0.6, 0.4, 0.05)), MeshKit.glow(Color("#ffb23e"), 2.0), t.pos + Vector3(0, 1.0, 0.3))
	for lt in game.loot:
		var mi := MeshKit.add(self, MeshKit.sphere(0.22, 6), MeshKit.glow(Color("#ffd27a"), 2.5), lt.pos + Vector3(0, 0.6, 0))
		mi.visible = not lt.taken
		_loot[lt] = mi


func _sync_world_objects(game: GameSim, dt: float) -> void:
	for d in _doors:
		var a: float = _door_amt[d]
		a = U.approach(a, 1.0 if d.is_open else 0.0, dt * 2.0)
		_door_amt[d] = a
		var root: Node3D = _doors[d]
		root.visible = a < 1.0
		root.position.y = d.pos.y - a * d.size.y
	for x in _exits:
		var open: bool = Cond.eval(x.lock, game)
		_exits[x].albedo_color = Color(0.35, 0.82, 1.0, 0.12) if open else Color(1.0, 0.35, 0.25, 0.18)
	for sw in _switches:
		_switches[sw].albedo_color = Color("#5ad1ff") if sw.on else Color("#7a8aa0")
		_switches[sw].emission = Color("#5ad1ff") if sw.on else Color("#3a4252")
	for m in _movers:
		_movers[m].position = m.pos + Vector3(0, m.size.y * 0.5, 0)
	for lt in _loot:
		var mi: MeshInstance3D = _loot[lt]
		mi.visible = not lt.taken
		mi.position = lt.pos + Vector3(0, 0.6 + sin(_time * 3.0) * 0.08, 0)


func sync(game: GameSim, dt: float) -> void:
	_time += dt
	_sync_world_objects(game, dt)
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
		var info: Dictionary = _npc_models.get(n.id, {})
		if not info.is_empty():
			# 話している行の顔（この住人のセリフのときだけ。ほかは通常）
			var d: Dictionary = game.story.dialogue
			var face := 0
			if not d.is_empty() and d.get("who", "") == n.name:
				face = int(NPC_FACES.get(String(d.get("face", "normal")), 0))
			_set_npc_face(info, face)
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


## 住人のモデルを置く：材質を複製し（顔の区画のずれを共有しない）、待機の動作をくり返す
func _add_npc_model(root: Node3D, path: String) -> Dictionary:
	var scene: PackedScene = load(path)
	var model: Node3D = scene.instantiate()
	root.add_child(model)
	var face_mats: Array[BaseMaterial3D] = []
	for node in model.find_children("*", "MeshInstance3D", true, false):
		var mi := node as MeshInstance3D
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
		for s in mi.mesh.get_surface_count():
			var src := mi.mesh.surface_get_material(s)
			if src is BaseMaterial3D:
				var m: BaseMaterial3D = src.duplicate()
				mi.set_surface_override_material(s, m)
				if m.resource_name.contains("face"):
					face_mats.append(m)
	var anim: AnimationPlayer = model.find_child("AnimationPlayer", true, false)
	if anim and anim.has_animation("idle"):
		anim.get_animation("idle").loop_mode = Animation.LOOP_LINEAR
		anim.play("idle")
		# 何人いても同じ動きにそろわないように、始めの時刻をずらす
		anim.seek(fmod(absf(root.position.x * 0.37 + root.position.z * 0.23), 1.0) * anim.current_animation_length, true)
	return {"anim": anim, "face_mats": face_mats, "expr": 0}


func _set_npc_face(info: Dictionary, i: int) -> void:
	if int(info.expr) == i:
		return
	info.expr = i
	for m in info.face_mats:
		(m as BaseMaterial3D).uv1_offset = Vector3((i % 2) * 0.5, (i / 2) * 0.5, 0)
