class_name PropsView
extends Node3D
## 宝箱、住人、セーブビーコン、壊せる壁、拾える物の見た目

var _walls := {}
var _chests := {}
var _npcs := {}
var _npc_models := {}   # id → {anim, face_mats, expr}
var _pickups := {}
var _time := 0.0
var _doors := {}
var _switches := {}
var _movers := {}
var _loot := {}
var _door_amt := {}
var _leaving := {}   # 走り去っている住人：id → _npc_models の値（leave：残りの秒数、leave_dir：向き）

## 住人の 3D モデル（絵から起こした GLB。tools/blender/recon/build_char.py）。無ければ従来の簡単な形で描く
const NPC_MODELS := {"npc_yana": "res://assets/models/yana.glb", "npc_burton": "res://assets/models/burton.glb",
	# 町の住人 8 人（tools/blender/models/townsfolk.py のキット。1 人の設定は tools/blender/recon/chars/townsfolk/<名前>.json）
	"npc_gen": "res://assets/models/tf_gen.glb", "npc_martha": "res://assets/models/tf_martha.glb",
	"npc_domi": "res://assets/models/tf_domi.glb", "npc_tobi": "res://assets/models/tf_tobi.glb",
	"npc_woman": "res://assets/models/tf_mina.glb", "npc_lookout": "res://assets/models/tf_rob.glb",
	"npc_clerk": "res://assets/models/tf_clerk.glb", "npc_rita": "res://assets/models/tf_rita.glb",
	"npc_nico": "res://assets/models/nico.glb", "npc_trude": "res://assets/models/trude.glb",
	"npc_shopkeeper": "res://assets/models/shopkeeper.glb", "npc_junker": "res://assets/models/junker.glb"}
## 会話の行の顔（dialogue の face）→ 顔のテクスチャの 2×2 の区画（ヤーナ：0 通常、1 豪快に笑う、2 驚き、3 怒る）。
## 区画の無い顔は近いものか通常にする
const NPC_FACES := {"normal": 0, "smile": 0, "smirk": 0, "serious": 0, "sad": 0, "laugh": 1, "surprised": 2, "angry": 3}
## ニコ・トルーデの顔の区画（0 通常、1 笑顔、2 驚き、3 怒り。nico_face_expressions_r2.png・trude_face_expressions.png の順）
const NICO_FACES := {"normal": 0, "serious": 0, "sad": 0, "smile": 1, "smirk": 1, "laugh": 1, "surprised": 2, "angry": 3}
## 雑貨屋の店主の顔の区画（shopkeeper_face_expressions.png は通常・笑顔を 2 回描いた 2×2。笑顔は口の色のよい右下の区画 3）
const SHOPKEEPER_FACES := {"normal": 0, "serious": 0, "sad": 0, "surprised": 0, "angry": 0, "smile": 3, "smirk": 3, "laugh": 3}
## ジャンク屋の顔の区画（junker_face_expressions.png は通常・笑顔を 2 回描いた 2×2：0 通常、1 笑顔）
const JUNKER_FACES := {"normal": 0, "serious": 0, "sad": 0, "surprised": 0, "angry": 0, "smile": 1, "smirk": 1, "laugh": 1}
## 表情を切り替える住人（顔のテクスチャが 2×2 の区画）。バートンは顔が 1 枚なので通常のまま
const NPC_FACE_SETS := {"npc_yana": NPC_FACES, "npc_nico": NICO_FACES, "npc_trude": NICO_FACES, "npc_shopkeeper": SHOPKEEPER_FACES,
	"npc_junker": JUNKER_FACES}
## 会話の話し手の名前が名札と違う住人（ch1.plaza の話し手は「トルーデ」、名札は「町長トルーデ」）
const NPC_SPEAKERS := {"npc_trude": ["トルーデ"]}
## 名札の高さ（m）。既定は 2.1（大人の背丈）。ニコは 120cm、トルーデは 140cm、店主は 160cm（お団子の上 0.4m）
const NPC_LABEL_Y := {"npc_nico": 1.6, "npc_trude": 1.8, "npc_shopkeeper": 2.0}
## 町の住人の名札の高さ（体の土台ごと：子ども 113cm 1.6・老人 140〜150cm 1.8〜1.85・大人の女 156〜160cm 1.95〜2.0。大人の男は既定の 2.1）
const TOWNSFOLK_LABEL_Y := {"npc_tobi": 1.6, "npc_woman": 1.8, "npc_gen": 1.85, "npc_rita": 1.95, "npc_martha": 2.0,
	"npc_clerk": 2.0}
## イベントで消える（remove）とき、走り去ってから消える住人と、その秒数（ニコは禁足扉へ走っていく。ch1.nico_run）
const NPC_RUN_OFF := {"npc_nico": 1.3}
const NPC_RUN_SPEED := 3.6
## 繰り返す動作（GLB の動作の名前）
const NPC_LOOPS := ["idle", "walk", "run", "cower"]


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
		root.add_child(MeshKit.label(n.name, float(NPC_LABEL_Y.get(n.id, TOWNSFOLK_LABEL_Y.get(n.id, 2.1))), Color("#ffe7b8"), 48))
		_npcs[n.id] = root
	# セーブビーコンの台（定常の光の柱は Fx._beacon_beam が光柱の素材で描く）
	for b in game.beacons:
		MeshKit.add(self, MeshKit.cyl(0.5, 0.7, 0.4), MeshKit.mat(Color("#e9e3d6"), 0.35), b.pos + Vector3(0, 0.2, 0))
	# 看板・名札（見た目だけ）：{ "type": "sign", "text": "ハルの家", "pos": [x,y,z], "size": 48 }。pos の高さに文字を浮かべる
	for p in game.room.get("props", []):
		if p.type == "sign":
			var m := game.place(p)
			var lb := MeshKit.label(String(p.text), 0.0, Color(p.get("color", "#ffe7b8")), int(p.get("size", 64)))
			lb.position = m.pos
			lb.no_depth_test = false
			if p.has("board"):
				_sign_board(game, p, m, lb)
			add_child(lb)
	# 遠景の飾り（当たり判定なし）：{ "type": "decor", "pos": [x,y,z] 底の中心, "size": [幅,高さ,奥行き], "color": "#46506a", "yaw": 度 }
	for p in game.room.get("props", []):
		if p.type == "decor" and (not p.has("when") or Cond.eval(p.when, game)) and (not p.has("unless") or not Cond.eval(p.unless, game)):
			var sz := RoomGeo.v3(p.size)
			var dm := MeshKit.mat(Color(p.get("color", "#46506a")), 0.9, 0.0)
			var node := Node3D.new()
			node.position = RoomGeo.v3(p.pos)
			node.rotation.y = float(p.get("yaw", 0.0)) * U.DEG
			add_child(node)
			MeshKit.add(node, MeshKit.box(sz), dm, Vector3(0, sz.y * 0.5, 0))
	_build_world_objects(game)


## 看板の板：{ "type": "sign", "text": "雑貨屋", "pos": 文字の中心, "board": "town/sign_post_2", "yaw": 180, "board_w": 2.2 }
## 板はキットの部品（原点 = 上の棒、文字の中心は棒の 0.62 m 下・板の表の 0.08 m 前）。文字は浮かべず板の表に貼る（ビルボードにしない）。
## 文字は板の幅に収まるよう小さくする。灯の無い夜でも読めるよう、文字は光の影響を受けない（Label3D の既定）
func _sign_board(game: GameSim, p: Dictionary, m: Dictionary, lb: Label3D) -> void:
	var kit := RoomKit.load_kit(String(game.room.get("kit", "")))
	var mesh := RoomKit.part_mesh(String(p.board), kit)
	var basis := Basis(Vector3.UP, m.yaw)
	if mesh != null:
		var mi := MeshInstance3D.new()
		mi.mesh = mesh
		mi.position = m.pos + Vector3(0, 0.62, 0)
		mi.basis = basis
		add_child(mi)
	lb.billboard = BaseMaterial3D.BILLBOARD_DISABLED
	lb.double_sided = false
	lb.basis = basis
	lb.position = m.pos + basis * Vector3(0, 0, 0.08)
	var inner := float(p.get("board_w", 2.2)) - 0.45
	var chars := maxi(1, String(p.text).length())
	lb.pixel_size = minf(lb.pixel_size, inner / float(chars * lb.font_size))


## 部屋の仕掛け：扉・出口・スイッチ・動く足場・端末・置いてある物
func _build_world_objects(game: GameSim) -> void:
	var metal := MeshKit.mat(Color("#8c8478"), 0.4, 0.5)
	# 扉の "part"（キットの部品。原点 = 扉の箱の下の中心、正面 +Z）：箱と灯の帯の代わりに部品で描く（下段の禁足扉。42 章 14.1）
	var door_parts := {}
	for p in game.room.get("props", []):
		if p.get("type", "") == "door" and p.has("part"):
			door_parts[String(p.get("id", ""))] = String(p.part)
	for d in game.doors:
		var root := Node3D.new()
		root.position = d.pos
		root.rotation.y = d.yaw
		add_child(root)
		var part_mesh: Mesh = RoomKit.part_mesh(door_parts[d.id], RoomKit.load_kit(String(game.room.get("kit", "")))) if door_parts.has(d.id) else null
		if part_mesh != null:
			var mi := MeshInstance3D.new()
			mi.mesh = part_mesh
			root.add_child(mi)
		else:
			MeshKit.add(root, MeshKit.box(d.size), metal, Vector3(0, d.size.y * 0.5, 0))
			MeshKit.add(root, MeshKit.box(Vector3(d.size.x * 0.8, 0.12, d.size.z + 0.04)), MeshKit.glow(Color("#ffb23e"), 1.5), Vector3(0, d.size.y * 0.55, 0))
		_doors[d] = root
		_door_amt[d] = 1.0 if d.is_open else 0.0
		root.visible = not d.is_open
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
	# 端末の "hide": true は、箱と光る画面を描かない（部屋の飾りが同じ所に物を置く：ベッドの横の台・作業台・望遠鏡・リフトの操作盤。42 章 14.1）
	var hidden := {}
	for p in game.room.get("props", []):
		if p.get("type", "") == "terminal" and p.get("hide", false):
			hidden[String(p.get("id", ""))] = true
	for t in game.terminals:
		if hidden.has(t.id):
			continue
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
			# 顔の区画（2×2）があるのはヤーナ・ニコ・トルーデ・店主。バートンは顔が 1 枚なので通常のまま
			var faces: Dictionary = NPC_FACE_SETS.get(n.id, {})
			var who: String = d.get("who", "")
			if not faces.is_empty() and not d.is_empty() and (who == n.name or NPC_SPEAKERS.get(n.id, []).has(who)):
				face = int(faces.get(String(d.get("face", "normal")), 0))
			_set_npc_face(info, face)
			_play_npc(info, _npc_anim_for(game, n, info))
	_sync_leaving(game, dt)
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
	if anim:
		for nm in NPC_LOOPS:
			if anim.has_animation(nm):
				anim.get_animation(nm).loop_mode = Animation.LOOP_LINEAR
	if anim and anim.has_animation("idle"):
		anim.play("idle")
		# 何人いても同じ動きにそろわないように、始めの時刻をずらす
		anim.seek(fmod(absf(root.position.x * 0.37 + root.position.z * 0.23), 1.0) * anim.current_animation_length, true)
	return {"anim": anim, "face_mats": face_mats, "expr": 0, "clip": "idle", "saw_enemy": false}


## 住人の今の動作。ニコは遺構 B1（ch1.r01）で救われるまで、番機を怖がってしゃがむ（cower）。
## 子番機が出て、倒されたら立ち上がる（救出の会話 ch1.nico_saved は立って話す）。ほかは待機
func _npc_anim_for(game: GameSim, n, info: Dictionary) -> String:
	if n.id != "npc_nico" or game.room_id != "ch1.r01" or game.flag("ch1.nico_rescued"):
		return "idle"
	var alive: bool = game.enemies.any(func(e): return e.alive)
	if alive:
		info.saw_enemy = true
	return "cower" if alive or not info.saw_enemy else "idle"


func _play_npc(info: Dictionary, clip: String) -> void:
	var anim: AnimationPlayer = info.get("anim")
	if anim == null or info.get("clip", "") == clip or not anim.has_animation(clip):
		return
	info.clip = clip
	anim.play(clip, 0.35)


## イベントで住人が去ったとき。走り去る住人（NPC_RUN_OFF）は、ハルから離れる向きへ走ってから消える（見た目だけ。
## 当たり判定・会話は消えた時点でもう無い）
func hide_npc(id: String) -> void:
	var r: Node3D = _npcs.get(id)
	if r == null:
		return
	var info: Dictionary = _npc_models.get(id, {})
	if NPC_RUN_OFF.has(id) and not info.is_empty() and info.anim != null and info.anim.has_animation("run"):
		info.leave = float(NPC_RUN_OFF[id])
		info.leave_dir = Vector3.ZERO
		_play_npc(info, "run")
		_leaving[id] = info
		return
	r.visible = false


func _sync_leaving(game: GameSim, dt: float) -> void:
	for id in _leaving.keys():
		var info: Dictionary = _leaving[id]
		var r: Node3D = _npcs.get(id)
		info.leave = float(info.leave) - dt
		if r == null or float(info.leave) <= 0.0:
			if r != null:
				r.visible = false
			_leaving.erase(id)
			continue
		if info.leave_dir == Vector3.ZERO:
			var away: Vector3 = r.position - game.player.pos
			away.y = 0.0
			info.leave_dir = away.normalized() if away.length() > 0.1 else Basis(Vector3.UP, r.rotation.y) * Vector3.BACK
		var dir: Vector3 = info.leave_dir
		var yaw := U.dir_to_yaw(dir.x, dir.z)
		r.rotation.y += U.wrap_angle(yaw - r.rotation.y) * minf(1.0, dt * 10.0)
		r.position += dir * NPC_RUN_SPEED * dt


func _set_npc_face(info: Dictionary, i: int) -> void:
	if int(info.expr) == i:
		return
	info.expr = i
	for m in info.face_mats:
		(m as BaseMaterial3D).uv1_offset = Vector3((i % 2) * 0.5, (i / 2) * 0.5, 0)
