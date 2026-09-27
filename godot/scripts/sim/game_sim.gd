class_name GameSim
extends Node3D
## ゲームの中身。描画を知らない（テストでは画面なしで動く）。
## 1 刻み（1/60 秒）ごとに step(入力) を呼ぶ。見た目・音・UI へは出来事（events）で伝える。
##
## 地形は「当たり判定用の三角形の面」と「名前つきの目印」で渡す：
##   geometry = { faces: [PackedVector3Array...], markers: { 名前: { pos: Vector3, yaw: float } } }

const ITEM_NAMES := {
	"special.drill": "特殊武器「ブレイクドリル」",
	"chip.charge": "チューニングチップ「チャージ化」",
}
const SAVE_VERSION := 1
const DT := 1.0 / 60.0

var phys: Phys
var tuning: Dictionary
var placement: Dictionary
var geometry: Dictionary
var dialogues: Dictionary
var events_data: Dictionary
var rng: Rng
var edges := InputFrame.Edges.new()
var input := InputFrame.new()
var cam: CameraOrbit
var lock_on: LockOn
var tokens: Enemy.AttackTokens
var story: Story
var player: Player

var enemies: Array = []
var shots: Array = []
var breakables: Array = []
var chests: Array = []
var npcs: Array = []
var beacons: Array = []
var pickups: Array = []
var triggers: Array = []
var checkpoints: Array = []

var time := 0.0
var tick := 0
var play_time := 0.0
var hitstop := 0.0
var cells := 0
var items := {}
var equipped_chips := {}
var objective := ""
var checkpoint := ""
var god_mode := false
## このフレームのジャンプボタンを「調べる」に使ったか
var consumed_jump := false
## 今「調べる」ことができる対象
var focus = null
## 積まれた出来事（見た目・音・UI が取り出す）
var _events: Array = []


## init：{ geometry, placement, tuning, dialogues, events, seed?, save? }
func setup(init: Dictionary) -> void:
	geometry = init.geometry
	placement = init.placement
	tuning = init.tuning
	dialogues = init.dialogues
	events_data = init.events
	rng = Rng.new(init.get("seed", 12345))
	phys = Phys.new()
	phys.name = "Phys"
	add_child(phys)
	cam = CameraOrbit.new(tuning)
	lock_on = LockOn.new(self)
	tokens = Enemy.AttackTokens.new(func(): return tuning.enemies.maxAttackers)
	story = Story.new(dialogues, events_data, self)
	_build(init.get("save"))


func charge_type() -> bool:
	return equipped_chips.has("chip.charge")


func emit_event(e: Dictionary) -> void:
	_events.append(e)


## 積まれた出来事を取り出して空にする
func drain_events() -> Array:
	var out := _events
	_events = []
	return out


func marker(name: String) -> Dictionary:
	assert(geometry.markers.has(name), "目印が見つからない: %s" % name)
	return geometry.markers[name]


func _build(save) -> void:
	for faces in geometry.faces:
		phys.add_trimesh(faces, Phys.TERRAIN)
	var broken := {}
	var opened := {}
	if save != null:
		for id in save.broken:
			broken[id] = true
		for id in save.opened:
			opened[id] = true

	for p in placement.get("props", []):
		var m := marker(p.at)
		match p.type:
			"breakable":
				var size := Vector3(p.size[0], p.size[1], p.size[2])
				var center: Vector3 = m.pos + Vector3(0, size.y / 2.0, 0)
				var b := Props.Breakable.new(p.id, center, size, m.yaw)
				if broken.has(p.id):
					b.broken = true
				else:
					b.body = phys.add_box(center, size * 0.5, Phys.BREAKABLE, m.yaw)
					phys.set_owner_of(b.body, b)
				breakables.append(b)
			"chest":
				var c := Props.Chest.new(p.id, m.pos, m.yaw, p.contents)
				c.opened = opened.has(p.id)
				phys.add_box(m.pos + Vector3(0, 0.4, 0), Vector3(0.6, 0.4, 0.4), Phys.TERRAIN, m.yaw)
				chests.append(c)
			"npc":
				npcs.append(Props.Npc.new(p.id, m.pos, m.yaw, p.name, p.talk))
				phys.add_box(m.pos + Vector3(0, 0.8, 0), Vector3(0.3, 0.8, 0.3), Phys.TERRAIN)
			"beacon":
				beacons.append(Props.Beacon.new(p.id, m.pos))
	for t in placement.get("triggers", []):
		var m := marker(t.at)
		var size := Vector3(t.size[0], t.size[1], t.size[2])
		var tr := Props.Trigger.new(t.id, m.pos + Vector3(0, size.y / 2.0, 0), size * 0.5, t.event, t.get("once", true))
		if save != null and save.flags.get("trigger." + t.id, false):
			tr.fired = true
		triggers.append(tr)
	for c in placement.get("checkpoints", []):
		var m := marker(c.at)
		checkpoints.append(Props.Checkpoint.new(c.id, m.pos, m.yaw, c.get("radius", 4.0)))
	for e in placement.get("enemies", []):
		var m := marker(e.at)
		enemies.append(Sentry.new(self, m.pos, m.yaw) if e.type == "sentry" else Charger.new(self, m.pos, m.yaw))

	var start := marker(placement.playerStart)
	player = Player.new(self, start.pos, start.yaw)
	cam.yaw = start.yaw
	checkpoint = placement.playerStart
	objective = placement.get("objective", "")
	if save != null:
		_apply_save(save)


# ---------------------------------------------------------------- 1 刻み

func step(frame: InputFrame) -> void:
	input = frame
	edges.update(frame)
	consumed_jump = false

	# 会話中は世界を止める
	if story.blocking():
		if edges.pressed("jump") or edges.pressed("sword") or edges.pressed("fire"):
			story.confirm()
		story.update(DT)
		tick += 1
		return
	story.update(DT)

	cam.apply_look(frame)
	if frame.camera_reset:
		cam.request_recenter()

	if hitstop > 0.0:
		hitstop -= DT
		tick += 1
		return

	lock_on.update(DT)
	_update_interaction()
	player.update(DT)
	for e in enemies:
		e.update(DT)
	_update_shots(DT)
	_update_pickups(DT)
	_update_triggers()
	_update_respawn()

	var t = lock_on.target
	cam.update(DT, player.pos, player.yaw, player.speed(), t.pos if t != null else null)
	time += DT
	play_time += DT
	tick += 1


# ---------------------------------------------------------------- 調べる

func _update_interaction() -> void:
	var p := player
	focus = null
	if not p.grounded or p.attack != null or p.dead:
		return
	var best = null
	var best_d := INF
	for it in chests + npcs + beacons:
		if not it.enabled():
			continue
		var d := U.hdist(it.pos, p.pos)
		if d > it.range_m or absf(it.pos.y - p.pos.y) > 1.5:
			continue
		if d < best_d:
			best_d = d
			best = it
	focus = best
	if best != null and edges.pressed("jump"):
		consumed_jump = true
		_interact(best)


func _interact(it) -> void:
	if it is Props.Chest:
		it.opened = true
		emit_event({"type": "chestOpened", "id": it.id})
		emit_event({"type": "sfx", "id": "chest"})
		if it.contents.has("cells"):
			give_cells(int(it.contents.cells))
		if it.contents.has("item"):
			give_item(it.contents.item)
	elif it is Props.Npc:
		it.yaw = U.dir_to_yaw(player.pos.x - it.pos.x, player.pos.z - it.pos.z)
		player.yaw = U.dir_to_yaw(it.pos.x - player.pos.x, it.pos.z - player.pos.z)
		var key: String = it.talk + ".done"
		var repeat: String = it.talk + ".again"
		story.start_dialogue(repeat if story.flags.get(key, false) and story.has_dialogue(repeat) else it.talk)
		story.flags[key] = true
	elif it is Props.Beacon:
		it.activated = true
		player.hp = player.max_hp
		player.weapon_energy = 100.0
		emit_event({"type": "saved"})
		emit_event({"type": "sfx", "id": "save"})


# ---------------------------------------------------------------- 所持品

func give_item(item: String) -> void:
	items[item] = true
	if item == "chip.charge":
		equipped_chips[item] = true
	emit_event({"type": "message", "text": "%s を手に入れた" % ITEM_NAMES.get(item, item)})
	emit_event({"type": "sfx", "id": "item"})


func give_cells(n: int) -> void:
	cells += n


func has_item(item: String) -> bool:
	return items.has(item)


func toggle_chip(chip: String) -> void:
	if not items.has(chip):
		return
	if equipped_chips.has(chip):
		equipped_chips.erase(chip)
	else:
		equipped_chips[chip] = true


# ---------------------------------------------------------------- 戦闘

## ロックオンしていないときの「弱い自動照準」。カメラ正面から 10° 以内の敵
func soft_aim_target():
	var chest := player.chest()
	var best = null
	var best_rel := 10.0 * U.DEG
	for e in enemies:
		if not e.alive:
			continue
		var c: Vector3 = e.center()
		if c.distance_to(chest) > tuning.gun.range * 1.2:
			continue
		var rel := absf(U.wrap_angle(U.dir_to_yaw(c.x - chest.x, c.z - chest.z) - cam.yaw))
		if rel < best_rel:
			best_rel = rel
			best = e
	return best


func damage_enemy(e, amount: float, from: Vector3, info: Dictionary) -> void:
	if not e.alive:
		return
	var r: Dictionary = e.receive(amount, from, info)
	var c: Vector3 = e.center()
	emit_event({"type": "hit", "at": c, "kind": r.kind})
	emit_event({"type": "sfx", "id": "hit_weak" if r.kind == "weak" else "hit", "at": c})
	if r.killed:
		emit_event({"type": "enemyDestroyed", "at": c})
		emit_event({"type": "sfx", "id": "explode", "at": c})
		_drop_loot(c)


func _drop_loot(at: Vector3) -> void:
	var n := rng.int_in(2, 4)
	for i in n:
		spawn_pickup("cells", rng.int_in(3, 5), at)
	if rng.chance(0.25):
		spawn_pickup("energy", 20, at)
	if rng.chance(0.15):
		spawn_pickup("repair", 15, at)


func spawn_pickup(kind: String, amount: float, at: Vector3) -> void:
	var p := Props.Pickup.new(kind, amount, at)
	var a := rng.range_f(0.0, TAU)
	p.vel = Vector3(cos(a) * 2.0, 4.0, sin(a) * 2.0)
	pickups.append(p)


func drill_breakable(b, dt: float) -> void:
	b.progress += dt
	emit_event({"type": "hit", "at": b.center, "kind": "armor"})
	if b.progress >= b.toughness and not b.broken:
		b.broken = true
		if b.body != null:
			phys.remove(b.body)
		b.body = null
		emit_event({"type": "wallBroken", "id": b.id})
		emit_event({"type": "sfx", "id": "wall_break"})
		emit_event({"type": "shake", "strength": 0.4})


func alert_noise(at: Vector3, radius: float) -> void:
	for e in enemies:
		if e.alive and e.state == "idle" and U.hdist(e.pos, at) <= radius:
			e.become_alert()


func spawn_player_shot(spec: Dictionary) -> void:
	shots.append(Shot.new(spec, true))


func spawn_enemy_shot(origin: Vector3, dir: Vector3, speed: float, damage: float) -> void:
	shots.append(Shot.new({
		"origin": origin, "dir": dir, "speed": speed, "range": 40.0, "damage": damage,
		"radius": 0.25, "pierce": false, "kind": "enemy",
	}, false))


func _update_shots(dt: float) -> void:
	var homing_rate: float = tuning.lockOn.homingDegPerSec * U.DEG
	for s in shots:
		if not s.alive:
			continue
		# 追尾：ロックオン対象へ緩やかに曲げる
		if s.homing != null and s.homing.alive:
			var want: Vector3 = (s.homing.center() - s.pos).normalized()
			var cur: Vector3 = s.vel.normalized()
			var angle := cur.angle_to(want)
			if angle > 1e-4:
				var t := minf(1.0, homing_rate * dt / angle)
				s.vel = cur.lerp(want, t).normalized() * s.speed
		s.prev = s.pos
		var move: Vector3 = s.vel * dt
		var l := move.length()
		var end: Vector3 = s.pos + move

		# 地形
		var terrain := phys.raycast(s.pos, move / l, l, Phys.TERRAIN | Phys.BREAKABLE)
		var stop_at: float = terrain.distance / l if not terrain.is_empty() else 1.0

		if s.from_player:
			for e in enemies:
				if not e.alive or s.hit.has(e):
					continue
				var t := U.segment_sphere(s.pos, end, e.center(), e.radius + s.radius)
				if t < 0.0 or t > stop_at:
					continue
				s.hit[e] = true
				damage_enemy(e, s.damage, s.pos, {"armorBreak": s.kind != "normal"})
				if not s.pierce:
					stop_at = t
					s.alive = false
					break
		else:
			var p := player
			var t := U.segment_sphere(s.pos, end, p.chest(), 0.45 + s.radius)
			if t >= 0.0 and t <= stop_at and not p.dead:
				# 無敵中（ダッシュや被弾直後）でも弾はプレイヤーで消す。すり抜けた弾がカメラの目の前を横切らないように
				p.take_damage(s.damage, s.pos, false)
				s.alive = false
				stop_at = t

		s.pos = s.pos.lerp(end, stop_at)
		s.traveled += l * stop_at
		if not terrain.is_empty() and stop_at < 1.0 and s.alive:
			s.alive = false
			emit_event({"type": "hit", "at": s.pos, "kind": "armor"})
		if s.traveled >= s.range_m:
			s.alive = false
	shots = shots.filter(func(s): return s.alive)


func _update_pickups(dt: float) -> void:
	var p := player
	var chest := p.chest()
	for k in pickups:
		if k.collected:
			continue
		k.age += dt
		var d: float = k.pos.distance_to(chest)
		if k.age > 0.4 and d < 3.0:
			# 近づくと吸い寄せられる
			k.pos += (chest - k.pos).normalized() * 14.0 * dt
		else:
			k.vel.y -= 18.0 * dt
			k.pos += k.vel * dt
			var hit := phys.raycast(k.pos + Vector3(0, 0.5, 0), Vector3.DOWN, 0.7, Phys.TERRAIN)
			if not hit.is_empty():
				k.pos.y = hit.point.y + 0.2
				k.vel = Vector3.ZERO
		if k.pos.distance_to(chest) < 0.8 or (k.age > 0.4 and d < 1.0):
			k.collected = true
			match k.kind:
				"cells":
					cells += int(k.amount)
				"energy":
					p.weapon_energy = minf(100.0, p.weapon_energy + k.amount)
				_:
					p.hp = minf(p.max_hp, p.hp + k.amount)
			emit_event({"type": "sfx", "id": "pickup"})
		if k.age > 30.0:
			k.collected = true
	pickups = pickups.filter(func(k): return not k.collected)


func _update_triggers() -> void:
	var pos := player.pos
	for t in triggers:
		if t.fired and t.once:
			continue
		if t.contains(pos):
			t.fired = true
			story.flags["trigger." + t.id] = true
			story.start_event(t.event)
	for c in checkpoints:
		if c.id != checkpoint and U.hdist(c.pos, pos) <= c.radius:
			checkpoint = c.id


func _update_respawn() -> void:
	var p := player
	if not p.dead or p.dead_time < 2.0:
		return
	# やられたら直前の中継地点から再開（ノーマルでは何も失わない）
	var at := {}
	for c in checkpoints:
		if c.id == checkpoint:
			at = {"pos": c.pos, "yaw": c.yaw}
	if at.is_empty():
		at = marker(placement.playerStart)
	p.dead = false
	p.hp = p.max_hp
	p.invuln = 2.0
	p.teleport(at.pos, at.yaw)
	cam.yaw = at.yaw
	lock_on.release()
	for s in shots:
		if not s.from_player:
			s.alive = false
	for e in enemies:
		tokens.release(e)


# ---------------------------------------------------------------- セーブ

func to_save(area_id: String) -> Dictionary:
	var p := player
	return {
		"version": SAVE_VERSION,
		"playTime": play_time,
		"area": area_id,
		"checkpoint": checkpoint,
		"pos": [p.pos.x, p.pos.y, p.pos.z],
		"yaw": p.yaw,
		"hp": p.hp,
		"maxHp": p.max_hp,
		"heals": p.heals,
		"weaponEnergy": p.weapon_energy,
		"cells": cells,
		"items": items.keys(),
		"equippedChips": equipped_chips.keys(),
		"flags": story.flags.duplicate(),
		"opened": chests.filter(func(c): return c.opened).map(func(c): return c.id),
		"broken": breakables.filter(func(b): return b.broken).map(func(b): return b.id),
		"scanned": lock_on.scanned.keys(),
		"objective": objective,
	}


func _apply_save(s: Dictionary) -> void:
	var p := player
	p.teleport(Vector3(s.pos[0], s.pos[1], s.pos[2]), s.yaw)
	cam.yaw = s.yaw
	p.hp = s.hp
	p.max_hp = s.maxHp
	p.heals = int(s.heals)
	p.weapon_energy = s.weaponEnergy
	cells = int(s.cells)
	for i in s.items:
		items[i] = true
	for c in s.equippedChips:
		equipped_chips[c] = true
	story.flags.merge(s.flags, true)
	for k in s.scanned:
		lock_on.scanned[k] = true
	checkpoint = s.checkpoint
	play_time = s.playTime
	objective = s.objective


## 保存されたデータを読む。形式が合わなければ null
static func parse_save(text: String):
	var d = JSON.parse_string(text)
	if typeof(d) != TYPE_DICTIONARY or int(d.get("version", 0)) != SAVE_VERSION:
		return null
	for k in ["pos", "yaw", "hp", "items", "flags", "checkpoint"]:
		if not d.has(k):
			return null
	return d
