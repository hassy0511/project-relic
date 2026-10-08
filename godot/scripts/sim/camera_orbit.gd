class_name CameraOrbit
extends RefCounted
## カメラの向き（yaw・pitch）。移動の向きに関わるのでゲームの中身が持つ。
## 実際のカメラ位置（壁の回避など）は見た目の側が決める。yaw は「カメラが見ている水平方向」。
##
## 左スティックの「前」（移動の基準。move_yaw）は、ふつうはカメラの向き。ただしカメラが自分で回る間（背後へ回す・自動の回り込み・
## ロックオンで捉えた直後）は、基準を止める（_hold）。止めないと、回るカメラにつられてハルの進む向きが回り、それをカメラが追って
## また回る（カメラが回り続ける）。止めた基準は、左スティックを倒し直した分だけ「カメラが向かう先」（_hold_to）へ戻し、
## 戻しきってカメラもそこに着いたら止めるのをやめる。基準を決めるのは左スティックと右スティック・マウスだけで、
## カメラが自分で回った分では動かない（docs/design/20_ゲームシステム設計.md 3 章「背後へ回すときの左スティック」）

var t: Dictionary
## カメラが見ている水平方向。外から書き換える（部屋の読み込み・復活・台本の teleport・セーブの読み込み）と、
## 背後へ回している途中の回転と、止めている左スティックの基準をやめる（_clear）。
## 回転の続きが残ると、新しい向きから基準なしで回り出し、回るカメラにつられて進む向きが回り、カメラが回り続ける
## （部屋の出口の手前で押すと、新しい部屋でハルが扉へ走り戻った。基準だけ戻すのでは足りない。2026-10-08）。
## 出口を通って部屋を移ったときは、そのあと GameSim が keep_heading で基準を止め直す。カメラの中の書き換えは _yaw へ直に入れる
var yaw: float:
	get:
		return _yaw
	set(v):
		_yaw = v
		_clear()
var _yaw := PI
var pitch := 12.0 * U.DEG
var _idle_look := 0.0
## 移動に合わせた自動の回り込み："off"＝回らない（右スティック・マウス・背後のボタンだけ）、
## "weak"＝前寄り（カメラの前方 ±FORWARD_ONLY 度以内）へ進むときだけゆっくり、"normal"＝横・後ろへ進んでも回る。
## 設定画面の「カメラの自動回り込み」（PadConfig.cam_follow）を main が毎刻み入れる
var follow := "normal"
const FORWARD_ONLY := 50.0
## 背後へ回している間は正（回す時間の上限の残り。ふつうは先（_hold_to）に着いた刻みで 0 になる）
var _recentering := 0.0
const SWING_MAX := 1.0
## 背後へ回す速さ：残りの角度に比例（14／秒）。ただし最後はこれ（度／秒）より遅くしない（だらだら近づかずに、先でぴたりと止まる）
const SWING_MIN_SPEED := 30.0
## 止めている左スティックの基準の yaw（倒し直した分は _hold_shift）。null なら止めていない（基準＝カメラの向き yaw）
var _hold = null
## カメラが向かう先：背後へ回す先（押したときにハルが向かう向き）、自動の回り込みが止まる所（不感帯の端）。
## 止めた基準はここまでしか戻さない。カメラが自分で回るのはここまでで、着いたら回らない（先は止めたときに決めて、そのあと動かさない）
var _hold_to := 0.0
## 止めたとき（または測り直したとき）の左スティックの向き（単位ベクトル。倒していなければ 0）。ここから倒す向きを変えた分だけ、基準を _hold_to へ戻す
var _hold_stick := Vector2.ZERO
## 止めた基準を、左スティックの向きを変えた分だけ _hold_to の方へ戻した量（ラジアン。move_yaw = _hold + これ）
var _hold_shift := 0.0
## この刻みの左スティック（apply_look で受け取る）
var _stick := Vector2.ZERO
## 今の倒し方（倒してから離すまで）で、自動の回り込みがもう基準を止めたか。回り込みで基準を止めるのは、1 回倒すごとに 1 度だけ。
## 何度も止め直すと、倒したまま指が揺れるたびに（基準がカメラに戻る → また回り込む）回った分が積もり、カメラが回り続けた（2026-10-08）
var _follow_used := false
## 前の刻みでロックオン（または演出の注視）の向きへ寄せていたか
var _locked := false
## 止めた基準と _hold_to の差がこれ（度）より大きい（ほぼ真後ろ）ときは、左スティックをどちらへ回しても、ハルがまっすぐ進むように戻す
const HOLD_EITHER_WAY := 170.0
## 左スティックを倒していないとみなす大きさ（Player._move_input と同じ）
const STICK_DEAD := 0.15
## 背後へ回している途中の回転をやめさせる、1 刻みのカメラ操作の大きさ（ラジアン。マウスで約 4 ピクセル、右スティックを半分ほど倒した量）
const LOOK_CANCEL := 0.01
## ロックオンで捉えたあと、止めた基準がカメラにこれ（ラジアン）より近づいたら止めるのをやめる
const LOCK_HOLD_DONE := 0.003


func _init(tuning: Dictionary) -> void:
	t = tuning
	pitch = t.camera.defaultPitch * U.DEG


## 外から向きを書き換えたとき：背後へ回している途中の回転と、止めている基準をやめる（基準はカメラに戻る）
func _clear() -> void:
	_recentering = 0.0
	_end_hold()


## 止めている基準をやめる（基準はカメラに戻る）
func _end_hold() -> void:
	_hold = null
	_hold_shift = 0.0
	_hold_stick = Vector2.ZERO


## 今の基準（倒し直した分も含めて）のまま止め直し、今の左スティックから測り直す。カメラが向かう先は to
func _rebase(to: float) -> void:
	_hold = move_yaw()
	_hold_shift = 0.0
	_hold_stick = _stick.normalized() if _stick.length() >= STICK_DEAD else Vector2.ZERO
	_hold_to = to


func apply_look(input: InputFrame) -> void:
	var c: Dictionary = t.camera
	var turn: float = -input.look_x * c.sensitivityX
	_yaw = U.wrap_angle(_yaw + turn)
	if _hold != null:
		# 右スティック・マウスで回した分は、止めている基準も向かう先も一緒に回す（ふだんと同じく、カメラを回すと進む向きも回る）
		_hold = U.wrap_angle(_hold + turn)
		_hold_to = U.wrap_angle(_hold_to + turn)
	pitch = clampf(pitch + input.look_y * c.sensitivityY, c.minPitch * U.DEG, c.maxPitch * U.DEG)
	_stick = Vector2(input.move_x, input.move_y)
	if input.look_active:
		_idle_look = 0.0
		# 背後へ回している途中は、はっきり回したときだけやめる（右クリック中のマウスの小さな揺れで止まらないように）。
		# カメラは今の向きで止まり、基準は跳ばさずに止め直す（倒し直すと、今のカメラへ戻る）
		if _recentering > 0.0 and (absf(turn) > LOOK_CANCEL or absf(input.look_y) > LOOK_CANCEL):
			_recentering = 0.0
			if _hold != null:
				_rebase(_yaw)
	_update_hold(_stick)


## プレイヤーの背後へ素早く回す（ロックオン対象がないときのロックオンボタン、R3・C・タッチの「背後」）。
## player_yaw：ハルの体の向き。stick：今の左スティック（move_x, move_y）。
## 回す先（_hold_to）は押したときに決める：倒していればハルが向かう向き（今の基準で倒している向き。体がまだ向きを変えている途中でも、
## 向き終わる先）、倒していなければ体の向き。回している途中で先を動かさない（ハルの向きを追い続けると、回している途中で倒し直したとき、
## 向きを変えたハルを追ってカメラが戻り、背中から外れた所で止まった。2026-10-08）。
## 左スティックの基準は止める：倒していれば今の基準のまま（ハルはそのまま同じ向きへ走り続け、カメラだけが背後へ回る）、
## 倒していなければ回す先（回している途中で倒しても、カメラが向かう先が「前」）。続けて押しても、進む向きは変わらない
func request_recenter(player_yaw: float, stick: Vector2) -> void:
	_recentering = SWING_MAX
	if stick.length() >= STICK_DEAD:
		var b := move_yaw()
		_hold = b
		_hold_shift = 0.0
		_hold_stick = stick.normalized()
		_hold_to = U.wrap_angle(b + _stick_yaw(stick))
	else:
		_hold = player_yaw
		_hold_shift = 0.0
		_hold_stick = Vector2.ZERO
		_hold_to = player_yaw


## 出口を通って部屋を移ったとき（GameSim._do_pending_room）：左スティックを倒したままなら、ハルはそのまま新しい部屋の奥
## （heading：入口の目印の向き。カメラもその向き）へ進むように、基準を止める。倒し直すとカメラ（＝部屋の奥）へ戻り、離すとやめる。
## 前は新しいカメラから測り直したので、カメラの方へ倒して扉を通ると、新しい部屋ではそれが「扉へ戻る」向きになり、
## 倒している間ずっと 2 つの部屋を行き来した（2026-10-08）
func keep_heading(heading: float, stick: Vector2) -> void:
	if stick.length() < STICK_DEAD:
		return
	_recentering = 0.0
	_hold = U.wrap_angle(heading - _stick_yaw(stick))
	_hold_shift = 0.0
	_hold_stick = stick.normalized()
	_hold_to = _yaw


## 左スティックの「前」の基準（yaw）。ふつうはカメラの向き。止めている間は止めた向き（request_recenter・keep_heading・自動の回り込み）
func move_yaw() -> float:
	return _yaw if _hold == null else U.wrap_angle(_hold + _hold_shift)


## 左スティックの向き（前＝0、右＝−90°。基準の yaw に足すと進む向きの yaw になる）
static func _stick_yaw(v: Vector2) -> float:
	return atan2(-v.x, v.y)


## 止めた基準を、左スティックの倒し直しに合わせてカメラが向かう先（_hold_to）へ戻していく：
## ・倒し直した分だけ戻す。先に合わせて倒し直す向き（横へ走りながら押して、そのあと前へ倒し直す）なら、戻した分と倒し直した分が
##   打ち消し合って、ハルはまっすぐ走り続ける。逆の向きなら 2 倍の速さで向きを変える。回している途中でも、回し終えたあとでも同じ
##   （先は押したときに決めてあるので、途中で倒し直しても、ハルの向きもカメラの止まる所も、回し終えてから倒し直したときと同じ）。
##   止めたときの向きから測るので、指の小さな揺れが積もって進路がずれていくことはない。
## ・戻しきって、カメラも先に着いたら、止めるのをやめる（基準＝カメラ）。
## ・左スティックを離したら、止めるのをやめる（背後へ回している途中なら、基準は回す先。次に倒した向きから測る）
func _update_hold(stick: Vector2) -> void:
	var held := stick.length() >= STICK_DEAD
	if not held:
		_follow_used = false
	if _hold == null:
		return
	if not held:
		if _recentering > 0.0:
			_hold = _hold_to
			_hold_shift = 0.0
			_hold_stick = Vector2.ZERO
		else:
			_end_hold()
		return
	if _locked or _hold_stick == Vector2.ZERO:
		# ロックオンの向きへ基準を寄せている間（update）と、止めてから初めて倒したときは、今の向きから測る
		_hold = move_yaw()
		_hold_shift = 0.0
		_hold_stick = stick.normalized()
		return
	var o := U.wrap_angle(_hold_to - _hold)
	var turned := U.wrap_angle(_stick_yaw(stick) - _stick_yaw(_hold_stick))
	var shift := -turned
	if signf(shift) != signf(o) and absf(o) < HOLD_EITHER_WAY * U.DEG:
		shift = signf(o) * absf(turned)
	if absf(shift) >= absf(o) - 0.00001:
		shift = o
		if _recentering <= 0.0 and absf(U.wrap_angle(_yaw - _hold_to)) < 0.00001:
			_end_hold()
			return
	_hold_shift = shift


func update(dt: float, player_pos: Vector3, player_yaw: float, player_speed: float, target) -> void:
	var c: Dictionary = t.camera
	_idle_look += dt
	if target != null:
		# ロックオン中（演出の注視も）：プレイヤーの後ろから対象を見る向きへ寄せる。背後へ回している途中なら回すのはやめる
		# （残すと、外れたあとに基準なしで回り出して、カメラが回り続ける）。
		# 止めていた基準は、カメラと同じ向きへ同じ割合で寄せていき、カメラに追いついたらやめる。
		# 一度にカメラへ戻すと、捉えた刻みにハルの進む向きが大きく（横へ走りながらで 40〜90°）跳んだ（2026-10-08）
		_recentering = 0.0
		var want := U.dir_to_yaw(target.x - player_pos.x, target.z - player_pos.z)
		var k := U.damp(c.lockOnYawSpeed, dt)
		_yaw = U.wrap_angle(_yaw + U.wrap_angle(want - _yaw) * k)
		pitch += (c.defaultPitch * U.DEG - pitch) * U.damp(3.0, dt)
		if _hold != null:
			var b := move_yaw()
			_hold = U.wrap_angle(b + U.wrap_angle(want - b) * k)
			_hold_shift = 0.0
			_hold_to = _yaw
			if absf(U.wrap_angle(_hold - _yaw)) < LOCK_HOLD_DONE:
				_end_hold()
		_locked = true
		return
	_locked = false
	if _recentering > 0.0 and _hold != null:
		# 背後（押したときに決めた先）へ。左スティックの基準は止めてあるので、カメラが回ってもハルの進む向きは回らない
		_recentering -= dt
		var gap := U.wrap_angle(_hold_to - _yaw)
		var step := maxf(absf(gap) * U.damp(14.0, dt), SWING_MIN_SPEED * U.DEG * dt)
		if step >= absf(gap) or _recentering <= 0.0:
			_yaw = _hold_to
			_recentering = 0.0
		else:
			_yaw = U.wrap_angle(_yaw + signf(gap) * step)
		pitch += (c.defaultPitch * U.DEG - pitch) * U.damp(10.0, dt)
		return
	_recentering = 0.0
	if follow == "off" or _idle_look <= c.autoRecenterDelay or player_speed <= 2.0:
		return
	# 操作がしばらくないときは、移動の向きの背後へゆっくり回る
	var rate: float = c.autoRecenterSpeed * clampf(player_speed / 7.0, 0.0, 1.0) * dt
	if follow == "weak":
		rate *= 0.5
	if _hold != null:
		# 基準を止めている間は、止めたときに決めた所（_hold_to）までしか回らない（左スティックでカメラが回り続けない）
		_yaw = U.wrap_angle(U.approach_angle(_yaw, _hold_to, rate))
		return
	# ハルが向かう向き：倒していればその向き（体がまだ向きを変えている途中でも、向き終わる先）、倒していなければ体の向き。
	# 差が autoRecenterDeadzone（度）以内なら回らない（まっすぐ倒したつもりの数度のずれを追いかけると、向きが少しずれる →
	# カメラが回る → 入力の基準が回る、という繰り返しで進路が曲がっていく。大きく曲がったときだけ、不感帯の端まで寄せる）
	var held := _stick.length() >= STICK_DEAD
	var heading := U.wrap_angle(_yaw + _stick_yaw(_stick)) if held else player_yaw
	var dead: float = float(c.get("autoRecenterDeadzone", 25.0)) * U.DEG
	var diff := U.wrap_angle(heading - _yaw)
	var excess := absf(diff) - dead
	# 弱い：横や後ろへ進むときは回らない（左スティックを横に倒しただけでカメラが回らないように）
	if follow == "weak" and absf(diff) > FORWARD_ONLY * U.DEG:
		excess = 0.0
	if excess <= 0.0:
		return
	var to := U.wrap_angle(_yaw + signf(diff) * excess)
	if held:
		# 左スティックを倒したまま回り込む：基準は回り込む前のカメラの向きに止め、回るのは今の不感帯の端（to）まで（背後へ回すときと同じ）。
		# ハルはまっすぐ走り続け、カメラは不感帯の端で止まる。この倒し方の間は、もう回り込まない（_follow_used）
		if _follow_used:
			return
		_follow_used = true
		_hold = _yaw
		_hold_shift = 0.0
		_hold_stick = _stick.normalized()
		_hold_to = to
	_yaw = U.wrap_angle(U.approach_angle(_yaw, to, rate))
