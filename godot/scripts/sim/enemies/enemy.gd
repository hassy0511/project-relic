class_name Enemy
extends RefCounted
## 番機の共通部分。型ごとの行動はサブクラスで書く。
## 状態：idle / alert / engage / windup / attack / recover / stunned / stagger / dead

var game
var kind := "enemy"
var pos := Vector3.ZERO
var home := Vector3.ZERO
var vel := Vector3.ZERO
var yaw := 0.0
var radius: float
var height: float
var hp: float
var max_hp: float
var poise: float
var max_poise: float
var _poise_timer := 0.0
var state := "idle"
var state_time := 0.0
var alive := true
## 被弾の瞬間の光（見た目用）
var flash := 0.0
## 撃破からの経過時間（見た目の演出用）
var dead_time := 0.0
var body: CharacterBody3D
var _grounded := true
var _no_sight := 0.0
## 無敵（ボスの段階の変わり目など）。当たっても減らない
var invulnerable := false
var _wander_target := Vector3.ZERO


func _init(g, spawn: Vector3, start_yaw: float, r: float, h: float, hp_max: float, poise_max: float) -> void:
	game = g
	pos = spawn
	home = spawn
	_wander_target = spawn
	yaw = start_yaw
	radius = r
	height = h
	hp = hp_max
	max_hp = hp_max
	poise = poise_max
	max_poise = poise_max
	body = g.phys.create_character(spawn, r, h, Phys.ENEMY, Phys.TERRAIN | Phys.BREAKABLE | Phys.PLAYER | Phys.ENEMY)
	g.phys.set_owner_of(body, self)


func center() -> Vector3:
	return Vector3(pos.x, pos.y + height * 0.5, pos.z)


## 弾が当たるか（球で近似。大きな敵は上書きする）。線分 a→b の上の位置 t（0〜1）、当たらなければ -1
func hit_segment(a: Vector3, b: Vector3, r: float) -> float:
	return U.segment_sphere(a, b, center(), radius + r)


## 点 p にいちばん近い体の中の点（近接攻撃の距離・向きの判定に使う）
func closest_point(_p: Vector3) -> Vector3:
	return center()


## 点 p から体の表面までの距離（3D）
func surface_dist(p: Vector3) -> float:
	return closest_point(p).distance_to(p) - radius


func set_state(s: String) -> void:
	if state == s:
		return
	state = s
	state_time = 0.0


## 攻撃の予備動作中か（見た目で光らせる）
func telegraphing() -> bool:
	return state == "windup"


## 見つかった時の「！」を出している間
func alerting() -> bool:
	return state == "alert"


func update(dt: float) -> void:
	if not alive:
		dead_time += dt
		return
	state_time += dt
	flash = maxf(0.0, flash - dt * 4.0)
	_poise_timer += dt
	if _poise_timer > 2.0:
		poise = max_poise
	if state == "stagger":
		_brake(dt, 30.0)
		if state_time > 0.6:
			set_state("engage")
	else:
		_think(dt)
	_integrate(dt)


func _think(_dt: float) -> void:
	pass


## 被弾の倍率（弱点など）。型ごとに上書きする。返り値：[倍率, 種類（normal / weak / armor）]
func _damage_multiplier(_from: Vector3, _info: Dictionary) -> Array:
	return [1.0, "normal"]


## ダメージを受ける。返り値：{ killed, kind, dealt }
func receive(amount: float, from: Vector3, info: Dictionary) -> Dictionary:
	if invulnerable:
		return {"killed": false, "kind": "armor", "dealt": 0.0}
	var dm := _damage_multiplier(from, info)
	var dealt: float = amount * dm[0]
	hp -= dealt
	flash = 1.0
	_poise_timer = 0.0
	poise -= dealt
	if state == "idle":
		become_alert()
	if hp <= 0.0:
		alive = false
		set_state("dead")
		game.phys.remove(body)
		game.tokens.release(self)
		_on_killed()
		return {"killed": true, "kind": dm[1], "dealt": dealt}
	if poise <= 0.0 and state != "stunned":
		poise = max_poise
		game.tokens.release(self)
		set_state("stagger")
		var away := Vector3(pos.x - from.x, 0.0, pos.z - from.z).normalized() * (3.0 if info.get("melee", false) else 1.5)
		vel.x = away.x
		vel.z = away.z
		if info.get("launch", false):
			vel.y = 6.0
	return {"killed": false, "kind": dm[1], "dealt": dealt}


## 倒れた瞬間（型ごとに上書きする）
func _on_killed() -> void:
	pass


## プレイヤーがやられて再開するとき（ボスは最初からやり直す）
func on_player_died() -> void:
	game.tokens.release(self)


# ------------------------------------------------------------ 知覚

func _dist_to_player() -> float:
	return U.hdist(pos, game.player.pos)


func _can_see_player(sight: float) -> bool:
	var p = game.player
	if p.dead:
		return false
	if _dist_to_player() > sight:
		return false
	var rel := absf(U.wrap_angle(U.dir_to_yaw(p.pos.x - pos.x, p.pos.z - pos.z) - yaw))
	if state == "idle" and rel > 60.0 * U.DEG:
		return false
	return _line_of_sight()


func _line_of_sight() -> bool:
	var from := center()
	var to: Vector3 = game.player.chest()
	var d := to - from
	var l := d.length()
	if l < 0.01:
		return true
	return game.phys.raycast(from, d / l, l, Phys.TERRAIN | Phys.BREAKABLE).is_empty()


func become_alert() -> void:
	if state == "idle":
		set_state("alert")
		game.emit_event({"type": "sfx", "id": "alert", "at": pos})


## 交戦中に見失ったら、しばらく探してから持ち場に戻る
func _track_sight(dt: float, sight: float) -> bool:
	if _can_see_player(sight * 1.3):
		_no_sight = 0.0
		return true
	_no_sight += dt
	if _no_sight > 5.0:
		_no_sight = 0.0
		game.tokens.release(self)
		set_state("idle")
	return false


# ------------------------------------------------------------ 移動

func _face_towards(p: Vector3, deg_per_sec: float, dt: float) -> void:
	yaw = U.approach_angle(yaw, U.dir_to_yaw(p.x - pos.x, p.z - pos.z), deg_per_sec * U.DEG * dt)


func _move_dir(dir: Vector3, spd: float, dt: float, accel: float = 20.0) -> void:
	var tx := dir.x * spd
	var tz := dir.z * spd
	var dx := tx - vel.x
	var dz := tz - vel.z
	var l := Vector2(dx, dz).length()
	var step := accel * dt
	if l <= step:
		vel.x = tx
		vel.z = tz
	else:
		vel.x += dx / l * step
		vel.z += dz / l * step


func _brake(dt: float, decel: float = 20.0) -> void:
	_move_dir(Vector3.ZERO, 0.0, dt, decel)


func _wander(dt: float, spd: float) -> void:
	if U.hdist(pos, _wander_target) < 0.5 or state_time > 6.0:
		var r: Rng = game.rng
		_wander_target = Vector3(home.x + r.range_f(-3, 3), home.y, home.z + r.range_f(-3, 3))
		state_time = 0.0
	if state_time < 1.5:
		_brake(dt)
		return
	var dir := Vector3(_wander_target.x - pos.x, 0.0, _wander_target.z - pos.z).normalized()
	_face_towards(_wander_target, 180.0, dt)
	_move_dir(dir, spd, dt)


## 実際の移動。壁にぶつかった割合（0〜1）を返す
func _integrate(dt: float) -> float:
	if not (_grounded and vel.y <= 0.0):
		vel.y = maxf(-25.0, vel.y - 22.0 * dt)
	var snap := _grounded and vel.y <= 0.0
	var want := Vector3(vel.x * dt, -0.05 if snap else vel.y * dt, vel.z * dt)
	var res: Dictionary = game.phys.move_character(body, want, _move_filter(), snap)
	pos = game.phys.feet_of(body)
	_grounded = res.grounded and vel.y <= 0.01
	if _grounded:
		vel.y = 0.0
	var want_h := Vector2(want.x, want.z).length()
	if want_h < 1e-4:
		return 0.0
	var moved: Vector3 = res.moved
	return 1.0 - Vector2(moved.x, moved.z).length() / want_h


## 移動でぶつかる相手のレイヤー
func _move_filter() -> int:
	return Phys.TERRAIN | Phys.BREAKABLE | Phys.PLAYER | Phys.ENEMY


## プレイヤーの胸へ向かう単位ベクトル
func _aim_at_player(from: Vector3) -> Vector3:
	return (game.player.chest() - from).normalized()


func forward() -> Vector3:
	return U.yaw_to_dir(yaw)


## 同時に攻撃してくる敵の数を制限する（死角から理不尽に殴られないように）
class AttackTokens:
	var holders := {}
	var max_fn: Callable

	func _init(f: Callable) -> void:
		max_fn = f

	func request(e) -> bool:
		if holders.has(e):
			return true
		if holders.size() >= int(max_fn.call()):
			return false
		holders[e] = true
		return true

	func release(e) -> void:
		holders.erase(e)

	func count() -> int:
		return holders.size()
