class_name LockOn
extends RefCounted
## ロックオンの状態と、対象の選び方（docs/design/20_ゲームシステム設計.md 5 章）

var game
var target = null  # Enemy
var _sight_lost := 0.0
var _scan_time := 0.0
## 解析済みの敵の種類（弱点を表示できる）
var scanned := {}
## この距離（m）より近い敵は、カメラの向きに関係なく候補にする（すぐ横・後ろの敵も捉えられるように）
const NEAR_ANY_ANGLE := 8.0


func _init(g) -> void:
	game = g


func active() -> bool:
	return target != null


## pressed：ボタンを押した瞬間（GameSim が生の入力から拾い、読み込み待ち・ヒットストップの間の分も持ち越して渡す）
func update(dt: float, pressed: bool) -> void:
	var g = game
	var input: InputFrame = g.input
	var cfg: Dictionary = g.tuning.lockOn
	# まだ使えない間（第 1 章の適合の前）：押した瞬間にカメラをハルの背後へ回すだけ（捉えない・対象を切り替えない）
	if not g.has_ability("lock_on"):
		release()
		if pressed:
			g.recenter_camera()
		return
	var down: bool = g.edges.down("lock_on")
	if pressed:
		# 押した瞬間：いちばんよい対象を捉える。誰もいなければカメラをハルの背後へ回す
		target = _pick_best(null)
		_scan_time = 0.0
		if target == null:
			g.recenter_camera()
	if not down:
		release()
		return
	if not pressed and target == null:
		# 押し続けている間（タッチは入れている間）は、捉えられる敵が見えた刻みで捉える。
		# （押した瞬間に誰もいない・対象が離れた・見えなくなったあとでも、押し直さずに捉え直す）
		target = _pick_best(null)
		_scan_time = 0.0
	if target == null:
		return

	# 対象を失う条件：倒した、離れすぎた、見えない時間が続いた
	var t = target
	var dist: float = t.center().distance_to(g.player.chest())
	if not t.alive or dist > cfg.loseRange:
		target = _pick_best(null) if not t.alive else null
		_scan_time = 0.0
		return
	if _has_line_of_sight(t):
		_sight_lost = 0.0
	else:
		_sight_lost += dt
	if _sight_lost > cfg.loseSightTime:
		release()
		return

	if input.switch_left or input.switch_right:
		var nxt = _pick_side(1 if input.switch_right else -1)
		if nxt != null:
			target = nxt
			_scan_time = 0.0

	_scan_time += dt
	if _scan_time >= cfg.scanTime:
		scanned[target.kind] = true


func release() -> void:
	target = null
	_sight_lost = 0.0
	_scan_time = 0.0


## 解析の進み具合（0〜1）
func scan_progress() -> float:
	if target == null:
		return 0.0
	if scanned.has(target.kind):
		return 1.0
	return minf(1.0, _scan_time / game.tuning.lockOn.scanTime)


## 候補の敵（射程内で、視線が通っていて、カメラの前方にいる）
func candidates() -> Array:
	var g = game
	var cfg: Dictionary = g.tuning.lockOn
	var chest: Vector3 = g.player.chest()
	var out := []
	for e in g.enemies:
		if not e.alive:
			continue
		var c: Vector3 = e.center()
		var dist := c.distance_to(chest)
		if dist > cfg.range:
			continue
		var rel := absf(U.wrap_angle(U.dir_to_yaw(c.x - chest.x, c.z - chest.z) - g.cam.yaw))
		if rel > 75.0 * U.DEG and dist > NEAR_ANY_ANGLE:
			continue
		if _has_line_of_sight(e):
			out.append(e)
	return out


func _pick_best(exclude):
	var g = game
	var cfg: Dictionary = g.tuning.lockOn
	var chest: Vector3 = g.player.chest()
	var best = null
	var best_score := -INF
	for e in candidates():
		if e == exclude:
			continue
		var c: Vector3 = e.center()
		var rel := absf(U.wrap_angle(U.dir_to_yaw(c.x - chest.x, c.z - chest.z) - g.cam.yaw))
		var score: float = cfg.centerWeight * (1.0 - rel / (75.0 * U.DEG)) + cfg.distanceWeight * (1.0 - c.distance_to(chest) / cfg.range)
		if score > best_score:
			best_score = score
			best = e
	return best


## 画面上で今の対象の右（side=1）または左（side=-1）にいる、最も近い敵
func _pick_side(side: int):
	var g = game
	var chest: Vector3 = g.player.chest()
	var cur = target
	if cur == null:
		return null
	var cc: Vector3 = cur.center()
	var cur_yaw := U.dir_to_yaw(cc.x - chest.x, cc.z - chest.z)
	var best = null
	var best_delta := INF
	for e in candidates():
		if e == cur:
			continue
		var c: Vector3 = e.center()
		# yaw が小さくなる方向が画面の右
		var delta := -U.wrap_angle(U.dir_to_yaw(c.x - chest.x, c.z - chest.z) - cur_yaw) * side
		if delta > 0.0 and delta < best_delta:
			best_delta = delta
			best = e
	return best


## 視線が通っているか：敵の狙う点（中心か頭。Enemy.aim_points）のどれかが胸から見えればよい
## （低い壁・柱の陰から体の一部が見えている敵も捉える。弱い自動照準と同じ点・同じ判定。GameSim.enemy_aim_point）。
## ロックオン中に撃つ弾も、その見えている点へ向ける（Player.aim_plan）ので、捉えた敵には撃てば当たる
func _has_line_of_sight(e) -> bool:
	return game.enemy_aim_point(e) != null
