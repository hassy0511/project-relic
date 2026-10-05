class_name ShieldBanki
extends Enemy
## 盾型：大きな盾を前に構えて、ゆっくり前進する。もう一方の腕で殴る。
## 正面は装甲（主武器の通常弾は ×0.25）。光刃・ドリルで盾の「守り」を削って崩すと、2 秒動けず全身が弱点になる。
## 背面（盾の反対側）は弱点（×1.5）。向きを変えるのが遅いので、回り込める。
## 状態：idle / alert / engage（盾を構えて前進）/ windup（拳を振りかぶる）/ attack / recover / stunned（盾が崩れた）

var guard := 0.0
var _guard_timer := 0.0
var _cooldown := 1.0
var _hit_player := false


func _init(g, spawn: Vector3, start_yaw: float) -> void:
	var c: Dictionary = g.tuning.enemies.shield
	super(g, spawn, start_yaw, 0.55, 1.8, c.hp, c.poise)
	kind = "shield"
	guard = c.guard


## 向きから見た相手の方向のずれ（0〜π）
func _angle_of(from: Vector3) -> float:
	return absf(U.wrap_angle(U.dir_to_yaw(from.x - pos.x, from.z - pos.z) - yaw))


func is_front(from: Vector3) -> bool:
	var c: Dictionary = game.tuning.enemies.shield
	return state != "stunned" and _angle_of(from) < c.guardArcDeg * 0.5 * U.DEG


func _damage_multiplier(from: Vector3, info: Dictionary) -> Array:
	if state == "stunned":
		return [1.5, "weak"]
	if _angle_of(from) > 110.0 * U.DEG:
		return [1.5, "weak"]
	if is_front(from):
		var breaks: bool = info.get("melee", false) or info.get("armorBreak", false)
		return [1.0 if breaks else 0.25, "armor"]
	return [1.0, "normal"]


func receive(amount: float, from: Vector3, info: Dictionary) -> Dictionary:
	var front := is_front(from)
	var r := super(amount, from, info)
	if r.killed or not front:
		return r
	# 光刃・ドリル・チャージ弾は守りを削る。通常弾は削れない
	if info.get("melee", false) or info.get("armorBreak", false):
		guard -= r.dealt
		_guard_timer = 0.0
		if guard <= 0.0:
			var c: Dictionary = game.tuning.enemies.shield
			guard = c.guard
			game.tokens.release(self)
			set_state("stunned")
			vel = Vector3.ZERO
			game.emit_event({"type": "sfx", "id": "crash", "at": pos})
			game.emit_event({"type": "shake", "strength": 0.25})
			game.emit_event({"type": "guardBroken", "at": center()})
	return r


func update(dt: float) -> void:
	super(dt)
	if alive and state != "stunned":
		_guard_timer += dt
		var c: Dictionary = game.tuning.enemies.shield
		if _guard_timer > c.guardRegenDelay:
			guard = minf(c.guard, guard + c.guard * 0.5 * dt)


func _think(dt: float) -> void:
	var g = game
	var c: Dictionary = g.tuning.enemies.shield
	var p = g.player
	_cooldown -= dt
	match state:
		"idle":
			_wander(dt, c.moveSpeed * 0.5)
			if _can_see_player(c.sight):
				become_alert()
		"alert":
			_brake(dt)
			_face_towards(p.pos, c.turnDeg * 2.0, dt)
			if state_time > 0.6:
				set_state("engage")
		"engage":
			var seen := _track_sight(dt, c.sight)
			if state != "engage":
				return
			_face_towards(p.pos, c.turnDeg, dt)
			var d := _dist_to_player()
			var to_p := Vector3(p.pos.x - pos.x, 0.0, p.pos.z - pos.z).normalized()
			if d > 2.0 or not seen:
				_move_dir(to_p, c.moveSpeed, dt, 12.0)
			else:
				_brake(dt)
			if seen and _cooldown <= 0.0 and d <= radius + c.punchRange and g.tokens.request(self):
				set_state("windup")
		"windup":
			_brake(dt, 30.0)
			_face_towards(p.pos, c.turnDeg * 0.6, dt)
			if state_time >= c.windup:
				_hit_player = false
				set_state("attack")
				g.emit_event({"type": "sfx", "id": "charge", "at": pos})
		"attack":
			_brake(dt, 30.0)
			# 振り下ろしの間（0.1〜0.22 秒）だけ当たる。正面の範囲
			var t: float = state_time / c.punchTime
			if not _hit_player and t > 0.3 and t < 0.75:
				if U.hdist(pos, p.pos) < radius + c.punchRange and _angle_of(p.pos) < 60.0 * U.DEG and absf(p.pos.y - pos.y) < 1.5:
					_hit_player = p.take_damage(c.damage, pos, false)
			if state_time >= c.punchTime:
				g.tokens.release(self)
				_cooldown = c.cooldown + g.rng.range_f(0.0, 0.6)
				set_state("recover")
		"recover":
			_brake(dt, 30.0)
			if state_time >= c.recover:
				set_state("engage")
		"stunned":
			_brake(dt, 40.0)
			if state_time >= c.guardBreakTime:
				_guard_timer = 0.0
				set_state("engage")
		_:
			set_state("engage")
