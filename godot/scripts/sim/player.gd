class_name Player
extends RefCounted
## プレイヤー（ハル）。移動、ジャンプ、ダッシュ、光刃、主武器、ブレイクドリル、被弾。
## 数値は content/tuning.json（docs/design/20_ゲームシステム設計.md 4 章）

const RADIUS := 0.35
const HEIGHT := 1.55
## 胸の高さ（撃つ位置、狙われる位置）
const CHEST := 1.1
## 奈落の高さ。これより下に落ちたら直前の足場に戻す
const KILL_Y := -30.0

var game  # GameSim
var body: CharacterBody3D
var pos := Vector3.ZERO
var vel := Vector3.ZERO
var yaw := 0.0
var grounded := true

var hp := 100.0
var max_hp := 100.0
var invuln := 0.0
var hurt_time := 0.0
var dead := false
var dead_time := 0.0
var heals := 2

var _coyote := 0.0
var _jump_buffer := 0.0
var _jumping := false
var dash_time := 0.0
var _dash_cooldown := 0.0
var _dash_dir := Vector3.ZERO
var _dash_jump := false
var _safe_pos := Vector3.ZERO

## 光刃の攻撃中の状態（null なら攻撃していない）
var attack: SwordAttack = null
var sword_hold := 0.0
var _air_slashes := 0

var gun_cooldown := 0.0
var gun_charge := 0.0
## 撃っている、または構えている（上半身を銃の構えにする）
var aiming := 0.0

var drilling := false
var _drill_tick := 0.0
var weapon_energy := 100.0


class SwordAttack:
	var move: String
	var time := 0.0
	var duration: float
	var active_from: float
	var active_to: float
	var damage: float
	var hit := {}
	## コンボの次の段の先行入力
	var buffered := false

	func _init(m: String, dmg: float, dur: float) -> void:
		move = m
		damage = dmg
		duration = dur
		active_from = dur * 0.25
		active_to = dur * 0.7


func _init(g, start: Vector3, start_yaw: float) -> void:
	game = g
	max_hp = g.tuning.player.maxHp
	hp = max_hp
	pos = start
	_safe_pos = start
	yaw = start_yaw
	body = g.phys.create_character(start, RADIUS, HEIGHT, Phys.PLAYER, Phys.TERRAIN | Phys.BREAKABLE | Phys.ENEMY)
	g.phys.set_owner_of(body, self)


func chest() -> Vector3:
	return Vector3(pos.x, pos.y + CHEST, pos.z)


func speed() -> float:
	return Vector2(vel.x, vel.z).length()


func dash_invulnerable() -> bool:
	var m: Dictionary = game.tuning.movement
	return dash_time > m.dashTime - m.dashInvuln


func anim() -> String:
	if dead:
		return "dead"
	if hurt_time > 0.0:
		return "hurt"
	if attack != null:
		return attack.move
	if drilling:
		return "drill"
	if dash_time > 0.0:
		return "dash"
	if not grounded:
		return "jump" if vel.y > 0.0 else "fall"
	return "run" if speed() > 0.5 else "idle"


func teleport(p: Vector3, new_yaw = null) -> void:
	pos = p
	_safe_pos = p
	vel = Vector3.ZERO
	if new_yaw != null:
		yaw = new_yaw
	game.phys.set_feet(body, p)


func update(dt: float) -> void:
	var g = game
	if dead:
		dead_time += dt
		return
	invuln = maxf(0.0, invuln - dt)
	hurt_time = maxf(0.0, hurt_time - dt)
	aiming = maxf(0.0, aiming - dt)

	_update_movement(dt)
	_update_sword(dt)
	_update_gun(dt)
	_update_drill(dt)

	if g.edges.pressed("heal") and heals > 0 and hp < max_hp:
		heals -= 1
		hp = minf(max_hp, hp + g.tuning.player.healAmount)
		g.emit_event({"type": "sfx", "id": "heal"})


# ---------------------------------------------------------------- 移動

func _move_input() -> Array:
	var g = game
	var x: float = g.input.move_x
	var y: float = g.input.move_y
	var mag := minf(1.0, Vector2(x, y).length())
	if mag < 0.15:
		return [Vector3.ZERO, 0.0]
	# カメラの向きを基準にする。前 = カメラが見ている方向、右 = 画面の右
	var fwd := U.yaw_to_dir(g.cam.yaw)
	var right := Vector3(-fwd.z, 0.0, fwd.x)
	var dir := (fwd * y + right * x).normalized()
	return [dir, mag]


func _update_movement(dt: float) -> void:
	var g = game
	var m: Dictionary = g.tuning.movement
	var locked = g.lock_on.target
	var mi := _move_input()
	var dir: Vector3 = mi[0]
	var mag: float = mi[1]
	var busy := attack != null and attack.move != "air"

	# 向き
	if locked != null and attack == null:
		var c: Vector3 = locked.center()
		yaw = U.dir_to_yaw(c.x - pos.x, c.z - pos.z)
	elif mag > 0.0 and not busy and dash_time <= 0.0:
		yaw = U.approach_angle(yaw, U.dir_to_yaw(dir.x, dir.z), m.turnSpeed * U.DEG * dt)

	# ダッシュの開始
	_dash_cooldown = maxf(0.0, _dash_cooldown - dt)
	if g.edges.pressed("dash") and _dash_cooldown <= 0.0 and grounded and hurt_time <= 0.0:
		attack = null
		dash_time = m.dashTime
		_dash_cooldown = m.dashCooldown
		if mag > 0.0:
			_dash_dir = dir
		elif locked != null:
			_dash_dir = -U.yaw_to_dir(yaw)
		else:
			_dash_dir = U.yaw_to_dir(yaw)
		g.emit_event({"type": "sfx", "id": "dash"})

	# 水平方向の速度
	var speed_scale := 1.0
	if gun_charge > 0.0 and g.charge_type():
		speed_scale = g.tuning.gun.chargeMoveScale
	if drilling:
		speed_scale = 0.5

	if dash_time > 0.0:
		dash_time -= dt
		vel.x = _dash_dir.x * m.dashSpeed
		vel.z = _dash_dir.z * m.dashSpeed
	elif hurt_time > 0.0:
		vel.x = U.approach(vel.x, 0.0, m.groundDecel * 0.3 * dt)
		vel.z = U.approach(vel.z, 0.0, m.groundDecel * 0.3 * dt)
	elif busy:
		vel.x = U.approach(vel.x, 0.0, m.groundDecel * dt)
		vel.z = U.approach(vel.z, 0.0, m.groundDecel * dt)
	else:
		var top: float = m.strafeSpeed if locked != null else m.runSpeed
		var spd := maxf(m.minWalkSpeed, top * mag) * speed_scale if mag > 0.0 else 0.0
		var tx := dir.x * spd
		var tz := dir.z * spd
		if grounded:
			var accel: float = m.groundAccel if mag > 0.0 else m.groundDecel
			_accelerate_to(tx, tz, accel * dt)
		else:
			var max_air: float = m.dashJumpSpeed if _dash_jump else m.airMaxSpeed
			var scale := max_air / maxf(0.01, spd) if _dash_jump and mag > 0.0 else 1.0
			_accelerate_to(tx * scale, tz * scale, m.airAccel * dt)
			var h := Vector2(vel.x, vel.z).length()
			if h > max_air:
				vel.x *= max_air / h
				vel.z *= max_air / h

	# ジャンプ（接地の猶予と先行入力つき）
	var grav: float = m.gravity
	var jump_v := sqrt(2.0 * grav * m.jumpHeight)
	var min_jump_v := sqrt(2.0 * grav * m.minJumpHeight)
	if g.edges.pressed("jump") and not g.consumed_jump:
		_jump_buffer = m.jumpBuffer
	else:
		_jump_buffer = maxf(0.0, _jump_buffer - dt)
	_coyote = m.coyoteTime if grounded else maxf(0.0, _coyote - dt)

	if _jump_buffer > 0.0 and _coyote > 0.0 and not busy and hurt_time <= 0.0:
		_jump_buffer = 0.0
		_coyote = 0.0
		vel.y = jump_v
		_jumping = true
		grounded = false
		if dash_time > 0.0:
			# ダッシュジャンプ：ダッシュの勢いを空中でも保つ
			_dash_jump = true
			dash_time = 0.0
			var h := Vector2(vel.x, vel.z).length()
			if h > 0.01:
				vel.x *= m.dashJumpSpeed / h
				vel.z *= m.dashJumpSpeed / h
		g.emit_event({"type": "sfx", "id": "jump"})
	if _jumping and not g.edges.down("jump") and vel.y > min_jump_v:
		vel.y = min_jump_v

	# 重力（空中斬りの間は落下を少し止める）
	var hang: bool = attack != null and attack.move == "air" and attack.time < g.tuning.sword.airHangTime
	var vy0 := vel.y
	if hang:
		vel.y = maxf(vel.y, 0.0) * 0.5
	elif not (grounded and vel.y <= 0.0):
		var gg: float = grav * m.fallGravityScale if vel.y < 0.0 else grav
		vel.y = maxf(-m.terminalFall, vel.y - gg * dt)
	# 位置は前後の速度の平均で進める（ジャンプの高さが刻みの大きさに左右されない）
	var dy := (vy0 + vel.y) * 0.5 * dt

	var was_grounded := grounded
	var snap := grounded and vel.y <= 0.0
	var want := Vector3(vel.x * dt, -0.05 if snap else dy, vel.z * dt)
	var res: Dictionary = g.phys.move_character(body, want, Phys.TERRAIN | Phys.BREAKABLE | Phys.ENEMY, snap)
	pos = g.phys.feet_of(body)
	grounded = res.grounded and vel.y <= 0.01 and _ground_below()
	if grounded:
		if not was_grounded:
			g.emit_event({"type": "sfx", "id": "land"})
			_air_slashes = 0
		vel.y = 0.0
		_jumping = false
		_dash_jump = false
		_safe_pos = pos
	elif vel.y > 0.0 and res.moved.y < want.y * 0.5:
		# 天井に頭をぶつけた
		vel.y = 0.0

	if pos.y < KILL_Y:
		teleport(_safe_pos)
		take_damage(10, pos, false, true)


## 足元の真下に地面があるか。カプセルの丸い底が段の角に引っかかっただけの状態を
## 「接地」とみなさないため（そこから段差の自動乗り越えで登れてしまうのを防ぐ）
func _ground_below() -> bool:
	var origin := Vector3(pos.x, pos.y + 0.3, pos.z)
	var hit: Dictionary = game.phys.raycast(origin, Vector3.DOWN, 0.75, Phys.TERRAIN | Phys.BREAKABLE | Phys.ENEMY)
	return not hit.is_empty() and pos.y - hit.point.y < 0.4


func _accelerate_to(tx: float, tz: float, step: float) -> void:
	var dx := tx - vel.x
	var dz := tz - vel.z
	var l := Vector2(dx, dz).length()
	if l <= step:
		vel.x = tx
		vel.z = tz
	else:
		vel.x += dx / l * step
		vel.z += dz / l * step


# ---------------------------------------------------------------- 光刃

func _start_attack(move: String, damage: float, duration: float) -> void:
	attack = SwordAttack.new(move, damage, duration)
	game.emit_event({"type": "sfx", "id": "slash_charge" if move == "charge" else "slash"})


func _update_sword(dt: float) -> void:
	var g = game
	var s: Dictionary = g.tuning.sword
	var locked = g.lock_on.target

	if g.edges.down("sword"):
		sword_hold += dt

	if g.edges.pressed("sword") and hurt_time <= 0.0 and not drilling:
		var a := attack
		if a != null and (a.move == "combo1" or a.move == "combo2"):
			if a.duration - a.time <= s.inputBuffer + a.duration * 0.3:
				a.buffered = true
		elif a == null:
			if dash_time > 0.0 and grounded:
				dash_time = 0.0
				_start_attack("dash", s.dashSlash, 0.35)
				var f := U.yaw_to_dir(yaw)
				vel = Vector3(f.x * 9.0, 0.0, f.z * 9.0)
			elif not grounded:
				if _air_slashes < s.airSlashMax:
					_air_slashes += 1
					_start_attack("air", s.airSlash, 0.3)
			elif locked != null:
				var d := U.hdist(locked.pos, pos)
				if d >= s.lungeMin and d <= s.lungeMax:
					_start_attack("lunge", s.lunge, 0.35)
				else:
					_start_attack("combo1", s.combo[0], s.comboTimes[0])
			else:
				_start_attack("combo1", s.combo[0], s.comboTimes[0])

	# 長押しからの溜め斬り
	if g.edges.released("sword"):
		if sword_hold >= s.chargeTime and grounded and not drilling and hurt_time <= 0.0:
			_start_attack("charge", s.chargeSlash, 0.5)
			var f := U.yaw_to_dir(yaw)
			g.spawn_player_shot({
				"origin": chest() + f * 0.8, "dir": f, "speed": 18.0, "range": s.shockwaveRange,
				"damage": s.shockwave, "radius": 0.9, "pierce": true, "kind": "wave",
			})
		sword_hold = 0.0

	var a := attack
	if a == null:
		return
	a.time += dt

	# 踏み込み
	var fw := U.yaw_to_dir(yaw)
	var mask := Phys.TERRAIN | Phys.BREAKABLE | Phys.ENEMY
	if a.move == "lunge" and locked != null and a.time < a.active_from:
		var d: float = U.hdist(locked.pos, pos) - (locked.radius + 1.0)
		var step := minf(maxf(d, 0.0), s.lungeSpeed * dt)
		g.phys.move_character(body, fw * step, mask)
		pos = g.phys.feet_of(body)
	elif a.move in ["combo1", "combo2", "combo3"] and a.time < 0.1 and grounded:
		var step2: float = s.comboStep / 0.1 * dt
		g.phys.move_character(body, fw * step2, mask)
		pos = g.phys.feet_of(body)

	# 当たり判定
	if a.time >= a.active_from and a.time <= a.active_to:
		var rng: float = s.range + 0.8 if a.move == "charge" else s.range
		var arc: float = (160.0 if a.move == "dash" or a.move == "charge" else float(s.arcDeg)) * U.DEG
		for e in g.enemies:
			if not e.alive or a.hit.has(e):
				continue
			var cp: Vector3 = e.closest_point(pos)
			var d: float = U.hdist(cp, pos) - e.radius
			if d > rng:
				continue
			if absf(e.center().y - chest().y) > 1.8:
				continue
			var rel := absf(U.wrap_angle(U.dir_to_yaw(cp.x - pos.x, cp.z - pos.z) - yaw))
			if rel > arc / 2.0 and d > 0.3:
				continue
			a.hit[e] = true
			var finisher := a.move == "combo3" or a.move == "charge"
			var reach := fw * minf(rng, maxf(d, 0.5) + e.radius * 0.5) + Vector3(0, 1.0, 0)
			g.damage_enemy(e, a.damage, pos, {"melee": true, "launch": a.move == "combo3", "at": pos + reach})
			var hs: float = s.hitstopCharge if a.move == "charge" else (s.hitstopFinisher if finisher else s.hitstop)
			g.hitstop = maxf(g.hitstop, hs)

	if a.time >= a.duration:
		if a.buffered and (a.move == "combo1" or a.move == "combo2"):
			var nxt := 1 if a.move == "combo1" else 2
			attack = null
			_start_attack("combo2" if nxt == 1 else "combo3", s.combo[nxt], s.comboTimes[nxt])
		else:
			attack = null


# ---------------------------------------------------------------- 主武器

func _update_gun(dt: float) -> void:
	var g = game
	var cfg: Dictionary = g.gun_cfg()
	gun_cooldown = maxf(0.0, gun_cooldown - dt)
	if hurt_time > 0.0 or drilling:
		gun_charge = 0.0
		return

	if not g.charge_type():
		if g.edges.down("fire") and gun_cooldown <= 0.0:
			_fire(cfg.damage, "normal")
			gun_cooldown = 1.0 / cfg.rate
		return

	# チャージ型：押すと単発、長押しで溜める
	if g.edges.pressed("fire") and gun_cooldown <= 0.0:
		_fire(cfg.damage, "normal")
		gun_cooldown = 1.0 / cfg.tapRate
	if g.edges.down("fire"):
		gun_charge += dt
		aiming = 0.3
	if g.edges.released("fire"):
		if gun_charge >= cfg.chargeLv2Time:
			_fire(cfg.damage * cfg.chargeLv2Mult, "charge2")
		elif gun_charge >= cfg.chargeLv1Time:
			_fire(cfg.damage * cfg.chargeLv1Mult, "charge1")
		gun_charge = 0.0


## 撃つ向き：ロックオン中は対象へ（弾は対象を追う）。ロックオンしていないときはハルの体の向き（yaw）へ水平に撃つ。
## 体の正面から少し（GameSim.SOFT_AIM_DEG）以内に敵か撃つスイッチがあれば、そこへ狙いを合わせる（上下の角度も）。
## カメラの向きは使わない（カメラを横へ回しても、ハルは向きを変えずに体の正面へ撃つ）
## 返り値：{ face: 撃つときの体の向き（yaw）, aim_at: 狙う点（無ければ null＝体の正面へ水平に） }。何も変えない（腕の構えの見た目にも使う）
func aim_plan() -> Dictionary:
	var g = game
	var target = g.lock_on.target
	if target != null:
		return {"face": yaw, "aim_at": target.center()}
	var sa: Dictionary = g.soft_aim(yaw)
	if sa.is_empty():
		return {"face": yaw, "aim_at": null}
	# 狙いを合わせた分（わずか）だけ体を向ける
	var p: Vector3 = sa.point
	return {"face": U.dir_to_yaw(p.x - pos.x, p.z - pos.z), "aim_at": p}


## 銃口（右手の先）の位置。face：撃つときの体の向き（yaw）
func muzzle(face: float) -> Vector3:
	var fwd := U.yaw_to_dir(face)
	var right := Vector3(-fwd.z, 0.0, fwd.x)
	return chest() - right * 0.3 + fwd * 0.4


## 弾の出る位置：ふつうは銃口。銃口が壁・箱・台にめり込むとき、または銃口からだと狙う点（aim_at）が柱の角などに隠れるときは胸から。
## （GameSim.soft_aim は胸から見える点だけを選ぶので、狙いを合わせた物には必ず届く）
func shot_origin(face: float, aim_at = null) -> Vector3:
	var g = game
	var c := chest()
	var m := muzzle(face)
	if g.has_clear_shot(c, m) and (aim_at == null or g.has_clear_shot(m, aim_at)):
		return m
	return c


func _fire(damage: float, kind: String) -> void:
	var g = game
	var cfg: Dictionary = g.gun_cfg()
	var plan := aim_plan()
	yaw = plan.face
	var origin := shot_origin(yaw, plan.aim_at)
	var dir: Vector3 = U.yaw_to_dir(yaw) if plan.aim_at == null else (plan.aim_at - origin).normalized()
	g.spawn_player_shot({
		"origin": origin, "dir": dir,
		"speed": cfg.speed * (1.1 if kind == "charge2" else 1.0),
		"range": cfg.range * (1.0 if kind == "normal" else 1.3),
		"damage": damage,
		"radius": 0.6 if kind == "charge2" else (0.35 if kind == "charge1" else 0.2),
		"pierce": kind != "normal", "kind": kind, "homing": g.lock_on.target,
	})
	aiming = 0.5
	g.alert_noise(pos, 12.0)
	g.emit_event({"type": "sfx", "id": "shot" if kind == "normal" else "shot_charge"})


# ---------------------------------------------------------------- 特殊武器（ブレイクドリル）

func _update_drill(dt: float) -> void:
	var g = game
	var cfg: Dictionary = g.tuning.drill
	var can: bool = g.has_item("special.drill") and weapon_energy > 0.0 and hurt_time <= 0.0 and attack == null
	var was := drilling
	drilling = can and g.edges.down("special")
	if not drilling:
		_drill_tick = 0.0
		return
	if not was:
		g.emit_event({"type": "sfx", "id": "drill"})
	weapon_energy = maxf(0.0, weapon_energy - cfg.energyPerSec * dt)
	_drill_tick -= dt
	if _drill_tick > 0.0:
		return
	_drill_tick = cfg.tickInterval

	var f := U.yaw_to_dir(yaw)
	var tip: Vector3 = chest() + f * (cfg.range * 0.6)
	for e in g.enemies:
		if not e.alive:
			continue
		if e.surface_dist(tip) <= cfg.range * 0.6:
			g.damage_enemy(e, cfg.damagePerTick, pos, {"melee": true, "armorBreak": true, "special": true, "at": tip})
	for b in g.breakables:
		if not b.broken and b.distance_to(tip) <= cfg.range * 0.7:
			g.drill_breakable(b, cfg.tickInterval)


# ---------------------------------------------------------------- 被弾

func take_damage(amount: float, from: Vector3, heavy: bool, ignore_invuln: bool = false) -> bool:
	var g = game
	if dead or g.god_mode:
		return false
	if not ignore_invuln and (invuln > 0.0 or dash_invulnerable()):
		return false
	hp = maxf(0.0, hp - amount)
	invuln = g.tuning.player.hurtInvuln
	hurt_time = 1.0 if heavy else 0.25
	attack = null
	drilling = false
	dash_time = 0.0
	var away := Vector3(pos.x - from.x, 0.0, pos.z - from.z)
	if away.length_squared() < 1e-4:
		away = -U.yaw_to_dir(yaw)
	away = away.normalized() * (7.0 if heavy else 4.0)
	vel.x = away.x
	vel.z = away.z
	if heavy and grounded:
		vel.y = 4.0
	g.emit_event({"type": "playerHurt", "amount": amount})
	g.emit_event({"type": "shake", "strength": 0.5 if heavy else 0.25})
	if hp <= 0.0:
		dead = true
		dead_time = 0.0
		g.emit_event({"type": "playerDied"})
	return true
