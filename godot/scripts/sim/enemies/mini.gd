class_name Mini
extends Enemy
## 子番機：小動物のように跳ねて近づき、跳びついて体当たりする小さな番機（弱い）。全身が弱点。
## 状態：idle / alert / engage（跳ねて近づく）/ windup（身をかがめる）/ attack（跳びつく）/ recover

var _cooldown := 0.8
var _hop_timer := 0.0
var _leap_dir := Vector3.ZERO
var _hit_player := false


func _init(g, spawn: Vector3, start_yaw: float) -> void:
	var c: Dictionary = g.tuning.enemies.mini
	super(g, spawn, start_yaw, 0.25, 0.3, c.hp, c.poise)
	kind = "mini"


## 全身が弱点
func _damage_multiplier(_from: Vector3, _info: Dictionary) -> Array:
	return [1.5, "weak"]


func _hop(dir: Vector3, spd: float, up: float) -> void:
	vel.x = dir.x * spd
	vel.z = dir.z * spd
	vel.y = up
	_grounded = false


func _think(dt: float) -> void:
	var g = game
	var c: Dictionary = g.tuning.enemies.mini
	var p = g.player
	_cooldown -= dt
	match state:
		"idle":
			_wander(dt, c.moveSpeed * 0.3)
			if _can_see_player(c.sight):
				become_alert()
		"alert":
			_brake(dt)
			_face_towards(p.pos, 540.0, dt)
			if state_time > 0.6:
				set_state("engage")
		"engage":
			var seen := _track_sight(dt, c.sight)
			if state != "engage":
				return
			_face_towards(p.pos, 540.0, dt)
			var d := _dist_to_player()
			var to_p := Vector3(p.pos.x - pos.x, 0.0, p.pos.z - pos.z).normalized()
			if _grounded:
				_brake(dt, 40.0)
				_hop_timer -= dt
				if _hop_timer <= 0.0 and (d > 1.5 or not seen):
					# 少し左右にぶれながら跳ねる
					var side: Vector3 = Vector3(-to_p.z, 0.0, to_p.x) * g.rng.range_f(-0.5, 0.5)
					_hop((to_p + side).normalized(), c.moveSpeed, 3.4)
					_hop_timer = c.hopInterval
			if seen and _cooldown <= 0.0 and d <= c.leapRange and _grounded and g.tokens.request(self):
				set_state("windup")
		"windup":
			_brake(dt, 40.0)
			_face_towards(p.pos, 540.0, dt)
			if state_time >= c.windup:
				_leap_dir = forward()
				_hit_player = false
				set_state("attack")
				_hop(_leap_dir, c.leapSpeed, 3.0)
				g.emit_event({"type": "sfx", "id": "charge", "at": pos})
		"attack":
			if not _hit_player and U.hdist(pos, p.pos) < radius + 0.6 and absf(p.pos.y + 0.8 - center().y) < 1.2:
				_hit_player = p.take_damage(c.damage, pos, false)
			if state_time >= c.leapTime or (_grounded and state_time > 0.15):
				g.tokens.release(self)
				_cooldown = c.cooldown + g.rng.range_f(0.0, 0.5)
				set_state("recover")
		"recover":
			if _grounded:
				_brake(dt, 40.0)
			if state_time >= c.recover:
				set_state("engage")
		_:
			set_state("engage")
