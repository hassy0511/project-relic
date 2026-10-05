class_name Kannuki
extends Enemy
## 大番機「閂」（第 1 章のボス、docs/design/30_レベルデザイン設計.md 4.5）。
## 円形の部屋（直径 32 m）で戦う。胴は長さ 10 m の筒（向き yaw の方向が前）で、4 本の削岩腕がある。
##   第 1 段階（〜66%）：外周のレールを滑りながら 削岩突き・回転薙ぎ・破片射出
##   第 2 段階（〜33%）：レールを外れて降りてくる。叩きつけ（輪状の衝撃波）・番機の呼び出し、第 1 段階の技も使う
##   第 3 段階（〜0%） ：過熱（腕が赤熱）。動きが速く、連続突進（3 回）・床の過熱。核が露出する回数が増える
## 弱点は背中の錠前核。ふだんは蓋と板で閉じていて、突きが壁に刺さって止まったとき、叩きつけのあとなどに露出する。
## 閉じている間：光刃・ドリルは ×1.0、通常弾は ×0.25（装甲）。露出中は ×1.5（ドリルは ×2.0）。
## 腕は個別に壊せる（壊した腕の技は弱くなる・使えなくなる）。腕の当たりは胴の外側の球で判定する。
## 状態：idle（待機。部屋に入ると始まる）/ intro / engage / *_windup・技 / stuck（壁に刺さる）/ recover / shift（段階の変わり目）/ dead
## ボス戦のルール：段階は飛ばせない（HP は段階の境で止まる）。やられたら最初からやり直す。

const ARMS := ["fl", "fr", "rl", "rr"]
## 腕の当たりの球の位置（胴のローカル座標。+X が本人の左、+Z が前、y は胴の軸から）
const ARM_LOCAL := {
	"fl": Vector3(2.4, 0.7, 3.4), "fr": Vector3(-2.4, 0.7, 3.4),
	"rl": Vector3(2.4, 0.7, -3.35), "rr": Vector3(-2.4, 0.7, -3.35),
}
const ARM_R := 1.3
const LINES := {
	"intro": [["ナゴミ", "『侵入者を排除します』……だそうです"], ["ハル", "通してもらうよ、閂さん！"]],
	"phase2": [["ナゴミ", "レールから降りてきます！ 床に気をつけて！"]],
	"phase3": [["ナゴミ", "腕が赤熱しています……過熱です！ 核が開く回数が増えます！"], ["ハル", "なら、そこを叩くだけだ"]],
	"defeat": [["ナゴミ", "沈黙しました……閂のコアを回収しましょう"]],
}

var arena := Vector3.ZERO
var phase := 1
var core_open := false
var overheat := false
var arm_hp := {}
var arm_broken := {}
## 床の過熱：0 なし、1 予告、2 熱い
var heat_state := 0
var heat_time := 0.0
## 叩きつけの衝撃波の半径（-1 なし）
var wave_r := -1.0
## 回転薙ぎの半径（回転の予告・回転中だけ >0）
var spin_r := 0.0
## 突進の予告線を出しているか
var lane := false
var spin_speed := 0.0

var _cooldown := 1.0
var _rail_angle := 0.0
var _charge_dir := Vector3.ZERO
var _chain := 0
var _hit_player := false
var _spin_hit := false
var _wave_hit := false
var _shots_left := 0
var _shot_timer := 0.0
var _last_attack := ""
var _summons: Array = []
var _phase_pending := false
var _heat_timer := 6.0
var _heat_tick := 0.0
var _hp_floor_taken := 0.0
var _summon_cd := 0.0
var _rail_face := 0.0
var _recover_time := 1.0


func _init(g, center_pos: Vector3, start_yaw: float) -> void:
	var c: Dictionary = g.tuning.boss
	super(g, center_pos, start_yaw, 1.75, 3.4, c.hp, 1.0e9)
	kind = "kannuki"
	arena = center_pos
	_reset_state()


func _reset_state() -> void:
	var c: Dictionary = game.tuning.boss
	hp = max_hp
	phase = 1
	core_open = false
	overheat = false
	invulnerable = false
	heat_state = 0
	wave_r = -1.0
	spin_r = 0.0
	lane = false
	_phase_pending = false
	_chain = 0
	_cooldown = 1.0
	_heat_timer = 6.0
	for a in ARMS:
		arm_hp[a] = float(c.armHp)
		arm_broken[a] = false
	# 最初の位置：レールの上（部屋の奥）。向きは接線
	_rail_angle = PI
	var at := _rail_point(_rail_angle)
	pos = at
	game.phys.set_feet(body, at)
	vel = Vector3.ZERO
	yaw = _rail_yaw(_rail_angle)
	state = "idle"
	state_time = 0.0


func _rail_point(a: float) -> Vector3:
	var r: float = game.tuning.boss.railRadius
	return Vector3(arena.x + sin(a) * r, arena.y, arena.z + cos(a) * r)


## レールの接線の向き（プレイヤーに近い側の腕が前になる方向でなく、時計回りに固定）
func _rail_yaw(a: float) -> float:
	return U.dir_to_yaw(cos(a), -sin(a))


# ------------------------------------------------------------ 体の形

func axis_center() -> Vector3:
	return Vector3(pos.x, pos.y + game.tuning.boss.bodyHeight, pos.z)


func center() -> Vector3:
	return axis_center()


## 胴の軸（尾から鼻まで）の線分
func _axis() -> Array:
	var c: Dictionary = game.tuning.boss
	var f := forward()
	var m := axis_center()
	return [m - f * c.bodyHalfLen, m + f * c.bodyHalfLen]


static func _closest_on_segment(a: Vector3, b: Vector3, p: Vector3) -> Vector3:
	var ab := b - a
	var t := clampf((p - a).dot(ab) / maxf(ab.length_squared(), 1e-6), 0.0, 1.0)
	return a + ab * t


func closest_point(p: Vector3) -> Vector3:
	var ax := _axis()
	return _closest_on_segment(ax[0], ax[1], p)


func arm_center(a: String) -> Vector3:
	return axis_center() + Basis(Vector3.UP, yaw) * ARM_LOCAL[a]


## 点 p にいちばん近い（壊れていない）腕。当たっていなければ ""
func _arm_at(p: Vector3) -> String:
	var best := ""
	var best_d := ARM_R + 0.4
	for a in ARMS:
		if arm_broken[a]:
			continue
		var d := arm_center(a).distance_to(p)
		if d < best_d:
			best_d = d
			best = a
	return best


func hit_segment(a: Vector3, b: Vector3, r: float) -> float:
	var c: Dictionary = game.tuning.boss
	var ax := _axis()
	var len := a.distance_to(b)
	var n := maxi(2, int(ceil(len / 0.4)))
	for i in n + 1:
		var t := float(i) / n
		var p := a.lerp(b, t)
		if _closest_on_segment(ax[0], ax[1], p).distance_to(p) <= c.bodyRadius + r:
			return t
		for arm in ARMS:
			if not arm_broken[arm] and arm_center(arm).distance_to(p) <= ARM_R + r:
				return t
	return -1.0


func arms_alive() -> int:
	var n := 0
	for a in ARMS:
		if not arm_broken[a]:
			n += 1
	return n


# ------------------------------------------------------------ 被弾

func receive(amount: float, from: Vector3, info: Dictionary) -> Dictionary:
	var c: Dictionary = game.tuning.boss
	if invulnerable or not alive or state == "idle" or state == "intro":
		return {"killed": false, "kind": "armor", "dealt": 0.0}
	var at: Vector3 = info.get("at", from)
	var melee: bool = info.get("melee", false) or info.get("armorBreak", false)
	var arm := _arm_at(at)
	var dealt := 0.0
	var kind_hit := "normal"
	if arm != "":
		# 腕：壊れるまで削る。本体にも一部通る
		arm_hp[arm] -= amount
		dealt = amount * c.armShare
		if arm_hp[arm] <= 0.0:
			_break_arm(arm)
	elif core_open:
		var mult := 2.0 if info.get("special", false) else 1.5
		dealt = amount * mult
		kind_hit = "weak"
	elif melee:
		dealt = amount
	else:
		dealt = amount * 0.25
		kind_hit = "armor"
	hp -= dealt
	flash = 1.0
	# 段階は飛ばさない：境で止めて、次の区切りで段階を移す
	var floor_hp := 0.0
	if phase == 1:
		floor_hp = max_hp * c.phaseAt[0]
	elif phase == 2:
		floor_hp = max_hp * c.phaseAt[1]
	if floor_hp > 0.0 and hp <= floor_hp:
		hp = floor_hp
		_phase_pending = true
	if hp <= 0.0:
		hp = 0.0
		alive = false
		invulnerable = false
		core_open = false
		heat_state = 0
		wave_r = -1.0
		spin_r = 0.0
		lane = false
		set_state("dead")
		game.phys.remove(body)
		game.tokens.release(self)
		_on_killed()
		return {"killed": true, "kind": kind_hit, "dealt": dealt}
	return {"killed": false, "kind": kind_hit, "dealt": dealt}


func _break_arm(a: String) -> void:
	arm_broken[a] = true
	game.emit_event({"type": "bossArmBroken", "arm": a, "at": arm_center(a)})
	game.emit_event({"type": "sfx", "id": "explode", "at": arm_center(a)})
	game.emit_event({"type": "shake", "strength": 0.4})
	game.hitstop = maxf(game.hitstop, 0.12)


func _on_killed() -> void:
	for s in _summons:
		if s.alive:
			s.alive = false
			game.phys.remove(s.body)
	_summons.clear()
	game.emit_event({"type": "bossDefeated", "at": axis_center()})
	game.emit_event({"type": "shake", "strength": 0.8})
	game.hitstop = maxf(game.hitstop, 0.3)
	game.story.flags["ch1.boss_defeated"] = true
	_say("defeat")
	# 閂のコア（ブレイクドリルの素）：セルを多めに落とす
	for i in 12:
		game.spawn_pickup("cells", 12, axis_center() + Vector3(0, 0.5, 0))
	game.spawn_pickup("repair", 30, axis_center())
	game.spawn_pickup("energy", 40, axis_center())


func on_player_died() -> void:
	super()
	# 最初からやり直す：呼び出した番機を消し、腕を直し、レールの上で待機
	for s in _summons:
		if s.alive:
			s.alive = false
			game.phys.remove(s.body)
		game.enemies.erase(s)
	_summons.clear()
	if alive:
		_reset_state()
		game.emit_event({"type": "bossReset"})


func _say(key: String) -> void:
	for l in LINES[key]:
		game.emit_event({"type": "bossLine", "who": l[0], "text": l[1]})


# ------------------------------------------------------------ 行動

func update(dt: float) -> void:
	super(dt)
	if not alive:
		return
	_update_hazards(dt)
	_push_player_out()


func _think(dt: float) -> void:
	var g = game
	var c: Dictionary = g.tuning.boss
	var p = g.player
	_cooldown -= dt
	_summon_cd -= dt
	match state:
		"idle":
			_brake(dt, 30.0)
			if not p.dead and U.hdist(p.pos, arena) < c.arenaRadius - 1.5:
				set_state("intro")
				g.emit_event({"type": "bossStart"})
				_say("intro")
		"intro":
			_brake(dt, 30.0)
			if state_time >= c.intro:
				set_state("engage")
		"engage":
			_engage(dt)
		"shift":
			# 段階の変わり目：動かず、無敵。咆哮
			_brake(dt, 30.0)
			if state_time >= c.phaseShift:
				invulnerable = false
				set_state("engage")
				_cooldown = 0.8
		"thrust_windup":
			_brake(dt, 40.0)
			lane = true
			var w: float = c.thrust.windupOverheat if overheat else c.thrust.windup
			# 最後の 0.25 秒は向きを固定する（横へ避ける猶予）
			if state_time < w - 0.25:
				_face_towards(p.pos, 240.0, dt)
			if state_time >= w:
				_charge_dir = forward()
				_hit_player = false
				lane = false
				set_state("thrust")
				g.emit_event({"type": "sfx", "id": "charge", "at": pos})
		"thrust":
			var spd: float = c.thrust.speedOverheat if overheat else c.thrust.speed
			vel.x = _charge_dir.x * spd
			vel.z = _charge_dir.z * spd
			_thrust_contact()
			_crush_pillars()
			var nose: Vector3 = axis_center() + _charge_dir * c.bodyHalfLen
			if U.hdist(nose, arena) >= c.arenaRadius - 0.6:
				_thrust_end(true)
			elif state_time > 2.4:
				_thrust_end(false)
		"stuck":
			_brake(dt, 60.0)
			core_open = true
			if state_time >= _stuck_time():
				core_open = false
				if _chain > 0:
					_chain -= 1
					set_state("thrust_windup")
				else:
					_finish_attack(0.6)
		"spin_windup":
			_brake(dt, 40.0)
			spin_r = _spin_radius()
			var w: float = c.spin.windup * (0.75 if overheat else 1.0)
			if state_time >= w:
				_spin_hit = false
				set_state("spin")
				g.emit_event({"type": "sfx", "id": "charge", "at": pos})
		"spin":
			_brake(dt, 40.0)
			spin_r = _spin_radius()
			var t: float = c.spin.timeOverheat if overheat else c.spin.time
			var ease := minf(1.0, state_time / 0.3)
			spin_speed = c.spin.degPerSec * U.DEG * ease
			yaw += spin_speed * dt
			if not p.dead and U.hdist(p.pos, pos) < spin_r and p.pos.y < pos.y + 1.1:
				if p.take_damage(c.spin.damage, pos, true):
					_spin_hit = true
			if state_time >= t:
				spin_r = 0.0
				spin_speed = 0.0
				yaw = U.wrap_angle(yaw)
				core_open = overheat
				_finish_attack(c.spin.recover, overheat)
		"volley_windup":
			_brake(dt, 40.0)
			_face_towards(p.pos, 120.0, dt)
			if state_time >= c.volley.windup:
				_shots_left = int(c.volley.count)
				_shot_timer = 0.0
				set_state("volley")
		"volley":
			_brake(dt, 40.0)
			_face_towards(p.pos, 120.0, dt)
			_shot_timer -= dt
			if _shot_timer <= 0.0 and _shots_left > 0:
				_shots_left -= 1
				_shot_timer = c.volley.interval
				var muzzle: Vector3 = axis_center() + forward() * (c.bodyHalfLen + 0.3)
				var dir := _aim_at_player(muzzle)
				var spread: float = c.volley.spreadDeg * U.DEG
				dir = dir.rotated(Vector3.UP, g.rng.range_f(-spread, spread)).normalized()
				g.spawn_enemy_shot(muzzle, dir, c.volley.speed, c.volley.damage)
				g.emit_event({"type": "sfx", "id": "shot", "at": muzzle})
			if _shots_left <= 0 and _shot_timer <= 0.0:
				_finish_attack(c.volley.recover)
		"slam_windup":
			_brake(dt, 40.0)
			_face_towards(p.pos, 180.0, dt)
			if state_time >= c.slam.windup:
				wave_r = 2.0
				_wave_hit = false
				set_state("slam")
				g.emit_event({"type": "sfx", "id": "crash", "at": pos})
				g.emit_event({"type": "shake", "strength": 0.6})
				_crush_pillars(5.0)
		"slam":
			_brake(dt, 40.0)
			wave_r += c.slam.waveSpeed * dt
			# 衝撃波：輪が通るときに地面にいると当たる（ジャンプで越える）
			if not _wave_hit and not p.dead and p.grounded and absf(U.hdist(p.pos, pos) - wave_r) < c.slam.waveWidth * 0.5 + 0.35:
				_wave_hit = p.take_damage(c.slam.damage, pos, true)
			if wave_r > c.arenaRadius + 2.0:
				wave_r = -1.0
				core_open = true
				set_state("slam_open")
		"slam_open":
			# 叩きつけのあとは必ず核が開く（反撃の好機）
			_brake(dt, 40.0)
			core_open = true
			if state_time >= c.slam.open:
				core_open = false
				_finish_attack(0.5)
		"summon_windup":
			_brake(dt, 40.0)
			core_open = true
			if state_time >= c.summon.windup:
				_do_summon()
				core_open = false
				_finish_attack(c.summon.recover)
		"recover":
			_brake(dt, 40.0)
			if state_time >= _recover_time:
				core_open = false
				set_state("engage")
		_:
			set_state("engage")


func _finish_attack(recover: float, open := false) -> void:
	_recover_time = recover
	core_open = open
	_cooldown = 1.2 if phase == 1 else (0.9 if phase == 2 else 0.6)
	set_state("recover")


func _stuck_time() -> float:
	var c: Dictionary = game.tuning.boss
	if _chain > 0:
		return c.thrust.chainStuck
	return c.thrust.stuckOverheat if overheat else c.thrust.stuck


func _spin_radius() -> float:
	var c: Dictionary = game.tuning.boss
	return maxf(2.0, c.spin.radius - 1.6 * (4 - arms_alive()))


func _engage(dt: float) -> void:
	var g = game
	var c: Dictionary = g.tuning.boss
	var p = g.player
	if p.dead:
		_brake(dt, 30.0)
		return
	var d := _dist_to_player()
	if phase == 1:
		# レールの上を、プレイヤーに近い向きへ滑る
		var want := atan2(p.pos.x - arena.x, p.pos.z - arena.z)
		var diff := U.wrap_angle(want - _rail_angle)
		var spd: float = c.railSpeed / c.railRadius
		_rail_angle += clampf(diff, -spd * dt, spd * dt) if absf(diff) > 0.15 else 0.0
		var target := _rail_point(_rail_angle)
		var to := Vector3(target.x - pos.x, 0.0, target.z - pos.z)
		_move_dir(to.normalized(), minf(c.railSpeed, to.length() * 3.0), dt, 12.0)
		if diff > 0.15:
			_rail_face = 0.0
		elif diff < -0.15:
			_rail_face = PI
		yaw = U.approach_angle(yaw, _rail_yaw(_rail_angle) + _rail_face, 120.0 * U.DEG * dt)
	else:
		_face_towards(p.pos, 90.0 if phase == 2 else 130.0, dt)
		var to_p := Vector3(p.pos.x - pos.x, 0.0, p.pos.z - pos.z).normalized()
		var spd2: float = c.walkSpeed[phase - 1]
		if d > 7.0:
			_move_dir(to_p, spd2, dt, 10.0)
		else:
			_brake(dt, 15.0)
		# 部屋の外へ出ない
		if U.hdist(pos, arena) > c.arenaRadius - 6.0:
			var back := Vector3(arena.x - pos.x, 0.0, arena.z - pos.z).normalized()
			_move_dir(back, spd2, dt, 10.0)
	# 次の区切りで段階を移す
	if _phase_pending and _cooldown <= 0.0:
		_start_shift()
		return
	if _cooldown <= 0.0:
		_pick_attack(d)


func _start_shift() -> void:
	var c: Dictionary = game.tuning.boss
	_phase_pending = false
	phase += 1
	invulnerable = true
	core_open = false
	if phase >= 3:
		overheat = true
		_heat_timer = 8.0
	set_state("shift")
	game.emit_event({"type": "bossPhase", "phase": phase})
	game.emit_event({"type": "shake", "strength": 0.5})
	game.emit_event({"type": "sfx", "id": "crash", "at": pos})
	_say("phase2" if phase == 2 else "phase3")


func _pick_attack(d: float) -> void:
	var c: Dictionary = game.tuning.boss
	var front_arm: bool = not (arm_broken["fl"] and arm_broken["fr"])
	var opts := {}
	opts["thrust"] = 4.0 if phase == 1 else (2.0 if phase == 2 else 3.5)
	if arms_alive() >= 2:
		opts["spin"] = 3.0 if phase == 1 else (1.5 if phase == 2 else 2.0)
	opts["volley"] = 3.0 if phase == 1 else (2.0 if phase == 2 else 1.5)
	if phase >= 2 and front_arm and d < 12.0:
		opts["slam"] = 3.0 if phase == 2 else 2.0
	if phase >= 2:
		_summons = _summons.filter(func(s): return s.alive)
		if _summons.size() < int(c.summon.max) and _summon_cd <= 0.0:
			opts["summon"] = 2.0
	opts.erase(_last_attack)
	var total := 0.0
	for k in opts:
		total += opts[k]
	var r: float = game.rng.range_f(0.0, total)
	var pick := "volley"
	for k in opts:
		r -= opts[k]
		if r <= 0.0:
			pick = k
			break
	_last_attack = pick
	match pick:
		"thrust":
			_chain = 2 if overheat else 0
			set_state("thrust_windup")
		"spin":
			set_state("spin_windup")
		"volley":
			set_state("volley_windup")
		"slam":
			set_state("slam_windup")
		"summon":
			set_state("summon_windup")
			_summon_cd = 20.0


func _thrust_contact() -> void:
	var c: Dictionary = game.tuning.boss
	var p = game.player
	if _hit_player or p.dead:
		return
	var pt := closest_point(p.pos + Vector3(0, 1.0, 0))
	if U.hdist(pt, p.pos) < c.bodyRadius + 0.5 and p.pos.y < pos.y + 4.4:
		var dmg: float = c.thrust.damage * (1.0 if not (arm_broken["fl"] and arm_broken["fr"]) else 0.7)
		_hit_player = p.take_damage(dmg, pos - _charge_dir * 2.0, true)


func _thrust_end(wall: bool) -> void:
	vel.x = 0.0
	vel.z = 0.0
	if wall:
		set_state("stuck")
		core_open = true
		game.emit_event({"type": "sfx", "id": "crash", "at": axis_center() + _charge_dir * 4.0})
		game.emit_event({"type": "shake", "strength": 0.6})
		game.emit_event({"type": "bossStuck", "at": axis_center() + _charge_dir * 4.6})
	else:
		_chain = 0
		_finish_attack(1.2)


## 突進・叩きつけの通り道にある壊れる柱を壊す
func _crush_pillars(reach := 2.6) -> void:
	var c: Dictionary = game.tuning.boss
	var ax := _axis()
	for b in game.breakables:
		if b.broken:
			continue
		var cp := _closest_on_segment(ax[0], ax[1], b.center)
		if U.hdist(cp, b.center) < c.bodyRadius + reach * 0.5:
			game.break_breakable(b)


func _do_summon() -> void:
	var c: Dictionary = game.tuning.boss
	var base: float = game.rng.range_f(0.0, TAU)
	for i in int(c.summon.count):
		var a: float = base + PI * i
		var at := Vector3(arena.x + sin(a) * (c.arenaRadius - 3.0), arena.y, arena.z + cos(a) * (c.arenaRadius - 3.0))
		var s: Enemy = game.add_enemy("sentry", at, U.dir_to_yaw(arena.x - at.x, arena.z - at.z))
		s.become_alert()
		_summons.append(s)
		game.emit_event({"type": "bossSummon", "at": at + Vector3(0, 1, 0)})
	game.emit_event({"type": "sfx", "id": "alert", "at": pos})


# ------------------------------------------------------------ 危険な床・体の押し出し

func _update_hazards(dt: float) -> void:
	var c: Dictionary = game.tuning.boss
	var p = game.player
	if phase < 3 or state == "shift" or state == "idle" or state == "intro":
		heat_state = 0
		return
	heat_time += dt
	match heat_state:
		0:
			_heat_timer -= dt
			if _heat_timer <= 0.0:
				heat_state = 1
				heat_time = 0.0
		1:
			if heat_time >= c.heat.warn:
				heat_state = 2
				heat_time = 0.0
				_heat_tick = 0.0
				game.emit_event({"type": "sfx", "id": "crash", "at": arena})
		2:
			_heat_tick -= dt
			if _heat_tick <= 0.0 and not p.dead and p.grounded and U.hdist(p.pos, arena) > c.heat.radiusIn:
				_heat_tick = c.heat.tick
				p.take_damage(c.heat.tickDamage, p.pos, false)
			if heat_time >= c.heat.hot:
				heat_state = 0
				_heat_timer = c.heat.every


## 胴の中に入り込んだプレイヤーを外へ押し出す（胴は 10 m あるので物理の柱だけでは足りない）
func _push_player_out() -> void:
	var c: Dictionary = game.tuning.boss
	var p = game.player
	if p.dead or state == "dead":
		return
	var cp := closest_point(p.pos + Vector3(0, 1.0, 0))
	var off := Vector3(p.pos.x - cp.x, 0.0, p.pos.z - cp.z)
	var need: float = c.bodyRadius + 0.5
	if off.length() >= need or p.pos.y > pos.y + 4.4:
		return
	if off.length() < 0.01:
		off = Vector3(-forward().z, 0.0, forward().x)
	var push := off.normalized() * (need - off.length())
	game.phys.move_character(p.body, push, Phys.TERRAIN)
	p.pos = game.phys.feet_of(p.body)


## 本体の物理の柱（プレイヤーを止める）は壁にぶつかるだけでよい
func _move_filter() -> int:
	return Phys.TERRAIN
