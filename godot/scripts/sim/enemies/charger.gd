class_name Charger
extends Enemy
## 突撃型：溜めてから一直線に突進する。壁に激突すると動けなくなり、側面の核が露出する

var _cooldown := 1.5
var _charge_dir := Vector3.ZERO
var _hit_player := false


func _init(g, spawn: Vector3, start_yaw: float) -> void:
	var c: Dictionary = g.tuning.enemies.charger
	super(g, spawn, start_yaw, 0.7, 1.2, c.hp, c.poise)
	kind = "charger"


## 壁に激突して動けない間は、全身が弱点になる
func _damage_multiplier(_from: Vector3, _info: Dictionary) -> Array:
	return [1.5, "weak"] if state == "stunned" else [1.0, "normal"]


func _think(dt: float) -> void:
	var g = game
	var c: Dictionary = g.tuning.enemies.charger
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
			_face_towards(p.pos, 240.0, dt)
			var d := _dist_to_player()
			var to_p := Vector3(p.pos.x - pos.x, 0.0, p.pos.z - pos.z).normalized()
			if d > 10.0 or not seen:
				_move_dir(to_p, c.moveSpeed, dt)
			elif d < 5.0:
				_move_dir(-to_p, c.moveSpeed * 0.7, dt)
			else:
				_brake(dt)
			if seen and _cooldown <= 0.0 and d < 16.0 and g.tokens.request(self):
				set_state("windup")
		"windup":
			# 予備動作：プレイヤーの方を向いて力を溜める。最後の瞬間の向きで突進する
			_brake(dt, 30.0)
			_face_towards(p.pos, 400.0, dt)
			if state_time >= c.windup:
				_charge_dir = forward()
				_hit_player = false
				set_state("attack")
				g.emit_event({"type": "sfx", "id": "charge", "at": pos})
		"attack":
			vel.x = _charge_dir.x * c.chargeSpeed
			vel.z = _charge_dir.z * c.chargeSpeed
			if not _hit_player and U.hdist(pos, p.pos) < radius + 0.6 and absf(p.pos.y - pos.y) < 1.2:
				_hit_player = p.take_damage(c.damage, pos, true) or _hit_player
				if _hit_player:
					_finish_charge(false)
					return
			if state_time >= c.chargeTime:
				_finish_charge(false)
		"stunned":
			_brake(dt, 40.0)
			if state_time >= c.stunTime:
				set_state("recover")
		"recover":
			_brake(dt, 30.0)
			if state_time >= c.recover:
				set_state("engage")
		_:
			set_state("engage")


func _finish_charge(wall: bool) -> void:
	var g = game
	g.tokens.release(self)
	_cooldown = 2.0 + g.rng.range_f(0.0, 1.0)
	vel.x = 0.0
	vel.z = 0.0
	if wall:
		set_state("stunned")
		g.emit_event({"type": "sfx", "id": "crash", "at": pos})
		g.emit_event({"type": "shake", "strength": 0.3})
	else:
		set_state("recover")


## 突進中はプレイヤーをすり抜ける（ダッシュで避けられたときに、プレイヤーを壁と誤認しないため）
func _move_filter() -> int:
	var f := super()
	return f & ~Phys.PLAYER if state == "attack" else f


func _integrate(dt: float) -> float:
	var blocked := super(dt)
	# 突進中に大きく止められたら、壁への激突とみなす
	if state == "attack" and state_time > 0.1 and blocked > 0.6:
		_finish_charge(true)
	return blocked
