class_name Floater
extends Enemy
## 浮遊型：空中でプレイヤーの周りを旋回し、急降下して 2 発撃つ。降下のあと上へ戻る間は上部の核が見えて弱点。
## 状態：idle（持ち場で浮く）/ alert / engage（旋回）/ windup（止まって砲口が光る）/ attack（急降下して撃つ）/ recover（上昇）
## 位置 pos は機体の下端（見た目の原点）。center() は 0.25 m 上。

var _cooldown := 1.5
var _orbit_angle := 0.0
var _orbit_dir := 1.0
var _orbit_init := false
var _flip_timer := 4.0
var _shots_left := 0
var _shot_timer := 0.0
var _dive_point := Vector3.ZERO
var _bob := 0.0


func _init(g, spawn: Vector3, start_yaw: float) -> void:
	var c: Dictionary = g.tuning.enemies.floater
	super(g, spawn, start_yaw, 0.4, 0.5, c.hp, c.poise)
	kind = "floater"
	_bob = g.rng.range_f(0.0, TAU)


## 上から撃たれたとき、または降下のあとの上昇中（核が出ている間）は弱点
func _damage_multiplier(from: Vector3, _info: Dictionary) -> Array:
	if state == "recover" or from.y > center().y + 0.8:
		return [1.5, "weak"]
	return [1.0, "normal"]


## 目標の高さへ向かう上下の速さ
func _fly_y(target_y: float, max_speed: float) -> void:
	vel.y = clampf((target_y - pos.y) * 4.0, -max_speed, max_speed)


func _think(dt: float) -> void:
	var g = game
	var c: Dictionary = g.tuning.enemies.floater
	var p = g.player
	_cooldown -= dt
	_bob += dt * 2.0
	match state:
		"idle":
			_brake(dt)
			_fly_y(home.y + c.hover + sin(_bob) * 0.15, 2.0)
			if _can_see_player(c.sight):
				become_alert()
		"alert":
			_brake(dt)
			_face_towards(p.pos, 360.0, dt)
			_fly_y(home.y + c.hover, 2.0)
			if state_time > 0.6:
				set_state("engage")
		"engage":
			var seen := _track_sight(dt, c.sight)
			if state != "engage":
				return
			_face_towards(p.pos, 300.0, dt)
			if not _orbit_init:
				_orbit_angle = atan2(pos.x - p.pos.x, pos.z - p.pos.z)
				_orbit_init = true
			_flip_timer -= dt
			if _flip_timer <= 0.0:
				_flip_timer = g.rng.range_f(3.0, 6.0)
				_orbit_dir = -_orbit_dir
			_orbit_angle += _orbit_dir * c.orbitDegPerSec * U.DEG * dt
			var want := Vector3(p.pos.x + sin(_orbit_angle) * c.orbitRadius, 0.0, p.pos.z + cos(_orbit_angle) * c.orbitRadius)
			var to := Vector3(want.x - pos.x, 0.0, want.z - pos.z)
			var spd: float = c.moveSpeed * clampf(to.length() / 2.0, 0.2, 1.0)
			_move_dir(to.normalized(), spd, dt, 14.0)
			_fly_y(p.pos.y + c.hover + sin(_bob) * 0.2, 3.0)
			if seen and _cooldown <= 0.0 and _dist_to_player() < c.sight * 0.8 and g.tokens.request(self):
				set_state("windup")
		"windup":
			_brake(dt, 25.0)
			_face_towards(p.pos, 360.0, dt)
			_fly_y(pos.y + 0.4, 1.0)
			if state_time >= c.windup:
				# プレイヤーの 5 m 手前の、胸の高さまで降りる
				var away := Vector3(pos.x - p.pos.x, 0.0, pos.z - p.pos.z).normalized()
				_dive_point = Vector3(p.pos.x + away.x * 5.0, p.pos.y + 0.9, p.pos.z + away.z * 5.0)
				_shots_left = int(c.burstCount)
				_shot_timer = 0.25
				set_state("attack")
				g.emit_event({"type": "sfx", "id": "charge", "at": pos})
		"attack":
			_face_towards(p.pos, 360.0, dt)
			var to := Vector3(_dive_point.x - pos.x, 0.0, _dive_point.z - pos.z)
			_move_dir(to.normalized(), c.diveSpeed * clampf(to.length() / 1.5, 0.0, 1.0), dt, 40.0)
			_fly_y(_dive_point.y, c.diveSpeed)
			_shot_timer -= dt
			if _shot_timer <= 0.0 and _shots_left > 0:
				_shots_left -= 1
				_shot_timer = c.burstInterval
				var muzzle := Vector3(pos.x, pos.y + 0.05, pos.z) + forward() * 0.2
				g.spawn_enemy_shot(muzzle, _aim_at_player(muzzle), c.shotSpeed, c.shotDamage)
			if state_time >= c.diveTime and _shots_left <= 0:
				g.tokens.release(self)
				_cooldown = c.cooldown + g.rng.range_f(0.0, 0.8)
				set_state("recover")
		"recover":
			_brake(dt, 25.0)
			_fly_y(p.pos.y + c.hover, 3.0)
			if state_time >= c.recover:
				set_state("engage")
		_:
			set_state("engage")


func receive(amount: float, from: Vector3, info: Dictionary) -> Dictionary:
	var r := super(amount, from, info)
	if not r.killed and state == "stagger":
		_shots_left = 0
	return r


## 空を飛ぶ：重力なし。壁・床・天井にはぶつかる
func _integrate(dt: float) -> float:
	if state == "stagger":
		vel.y = U.approach(vel.y, 0.0, 30.0 * dt)
	var want := Vector3(vel.x * dt, vel.y * dt, vel.z * dt)
	var res: Dictionary = game.phys.move_character(body, want, _move_filter(), false)
	pos = game.phys.feet_of(body)
	var want_h := Vector2(want.x, want.z).length()
	if want_h < 1e-4:
		return 0.0
	var moved: Vector3 = res.moved
	return 1.0 - Vector2(moved.x, moved.z).length() / want_h
