class_name Sentry
extends Enemy
## 歩哨型：距離を保って 3 連射する基本の敵。弱点は背中の核

var _cooldown := 1.0
var _shots_left := 0
var _shot_timer := 0.0
var _strafe_dir := 1.0
var _strafe_timer := 0.0


func _init(g, spawn: Vector3, start_yaw: float) -> void:
	var c: Dictionary = g.tuning.enemies.sentry
	super(g, spawn, start_yaw, 0.45, 1.1, c.hp, c.poise)
	kind = "sentry"


## 背後（向きから 110° 以上）から当てると弱点
func _damage_multiplier(from: Vector3, _info: Dictionary) -> Array:
	var rel := absf(U.wrap_angle(U.dir_to_yaw(from.x - pos.x, from.z - pos.z) - yaw))
	return [1.5, "weak"] if rel > 110.0 * U.DEG else [1.0, "normal"]


func _think(dt: float) -> void:
	var g = game
	var c: Dictionary = g.tuning.enemies.sentry
	var p = g.player
	_cooldown -= dt
	match state:
		"idle":
			_wander(dt, c.moveSpeed * 0.5)
			if _can_see_player(c.sight):
				become_alert()
		"alert":
			_brake(dt)
			_face_towards(p.pos, 360.0, dt)
			if state_time > 0.6:
				set_state("engage")
		"engage":
			var seen := _track_sight(dt, c.sight)
			if state != "engage":
				return
			_face_towards(p.pos, 300.0, dt)
			var d := _dist_to_player()
			var to_p := Vector3(p.pos.x - pos.x, 0.0, p.pos.z - pos.z).normalized()
			_strafe_timer -= dt
			if _strafe_timer <= 0.0:
				_strafe_timer = g.rng.range_f(1.5, 3.0)
				_strafe_dir = 1.0 if g.rng.chance(0.5) else -1.0
			var near: float = c.keepDistance[0]
			var far: float = c.keepDistance[1]
			if d < near:
				_move_dir(-to_p, c.moveSpeed, dt)
			elif d > far or not seen:
				_move_dir(to_p, c.moveSpeed, dt)
			else:
				_move_dir(Vector3(-to_p.z, 0.0, to_p.x) * _strafe_dir, c.moveSpeed * 0.6, dt)
			if seen and _cooldown <= 0.0 and d <= far + 4.0 and g.tokens.request(self):
				set_state("windup")
		"windup":
			_brake(dt, 30.0)
			_face_towards(p.pos, 360.0, dt)
			if state_time >= c.windup:
				set_state("attack")
				_shots_left = int(c.burstCount)
				_shot_timer = 0.0
		"attack":
			_brake(dt, 30.0)
			_face_towards(p.pos, 180.0, dt)
			_shot_timer -= dt
			if _shot_timer <= 0.0 and _shots_left > 0:
				_shots_left -= 1
				_shot_timer = c.burstInterval
				var muzzle := center() + forward() * (radius + 0.1)
				g.spawn_enemy_shot(muzzle, _aim_at_player(muzzle), c.shotSpeed, c.shotDamage)
			if _shots_left <= 0 and _shot_timer <= 0.0:
				g.tokens.release(self)
				_cooldown = c.cooldown + g.rng.range_f(0.0, 0.6)
				set_state("engage")
		_:
			set_state("engage")


func receive(amount: float, from: Vector3, info: Dictionary) -> Dictionary:
	var r := super(amount, from, info)
	if not r.killed and state == "stagger":
		_shots_left = 0
	return r
