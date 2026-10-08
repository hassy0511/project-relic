class_name CameraOrbit
extends RefCounted
## カメラの向き（yaw・pitch）。移動の向きに関わるのでゲームの中身が持つ。
## 実際のカメラ位置（壁の回避など）は見た目の側が決める。yaw は「カメラが見ている水平方向」。

var t: Dictionary
## カメラが見ている水平方向。外から書き換える（部屋の読み込み・復活・台本の teleport・セーブの読み込み）と、
## 背後へ回している途中の回転と、止めている左スティックの基準をやめる（_end_swing）。
## 回転の続きが残ると、新しい向きから基準なしで回り出し、回るカメラにつられて進む向きが回り、カメラが回り続ける
## （部屋の出口の手前で押すと、新しい部屋でハルが扉へ走り戻った。基準だけ戻すのでは足りない。2026-10-08）。
## カメラの中の書き換えは _yaw へ直に入れる
var yaw: float:
	get:
		return _yaw
	set(v):
		_yaw = v
		_end_swing()
var _yaw := PI
var pitch := 12.0 * U.DEG
var _idle_look := 0.0
## 移動に合わせた自動の回り込み："off"＝回らない（右スティック・マウス・背後のボタンだけ）、
## "weak"＝前寄り（カメラの前方 ±FORWARD_ONLY 度以内）へ進むときだけゆっくり、"normal"＝横・後ろへ進んでも回る。
## 設定画面の「カメラの自動回り込み」（PadConfig.cam_follow）を main が毎刻み入れる
var follow := "normal"
const FORWARD_ONLY := 50.0
var _recentering := 0.0
## 左スティックの「前」の基準（移動の向きの基準）を止めているときの yaw。null なら止めていない（基準＝カメラの向き yaw）。
## 背後へ回す（request_recenter）と、左スティックを倒したまま自動で回り込むとき（update）に止める。止めないと、回るカメラにつられて
## ハルの進む向きが回り、それをカメラが追ってまた回る、を繰り返してカメラが回り続ける（横へ走りながら押すと 1 周近く回って横のまま止まった。
## 「弱い」の回り込みで斜め前へ倒し続けると、1 秒に 43° ずつ回り続けてハルが輪を描いた。2026-10-08）
var _hold = null
## 回し終えたときの左スティックの向き（単位ベクトル。倒していなければ 0）。ここから倒す向きを変えた分だけ、基準をカメラへ戻していく
var _hold_stick := Vector2.ZERO
## 止めた基準を、左スティックの向きを変えた分だけカメラの方へ戻した量（ラジアン。move_yaw = _hold + これ）
var _hold_shift := 0.0
## この刻みの左スティック（apply_look で受け取る。自動の回り込みで基準を止めるかどうかに使う）
var _stick := Vector2.ZERO
## 止めた基準とカメラの差がこれ（度）より大きい（ほぼ真後ろ）ときは、左スティックをどちらへ回しても、ハルがまっすぐ進むように戻す
const HOLD_EITHER_WAY := 170.0
## 左スティックを倒していないとみなす大きさ（Player._move_input と同じ）
const STICK_DEAD := 0.15
## 背後へ回している途中の回転をやめさせる、1 刻みのカメラ操作の大きさ（ラジアン。マウスで約 4 ピクセル、右スティックを半分ほど倒した量）
const LOOK_CANCEL := 0.01


func _init(tuning: Dictionary) -> void:
	t = tuning
	pitch = t.camera.defaultPitch * U.DEG


## 背後へ回している途中の回転と、止めている左スティックの基準をやめる（基準はカメラに戻る）
func _end_swing() -> void:
	_recentering = 0.0
	_hold = null
	_hold_shift = 0.0
	_hold_stick = Vector2.ZERO


func apply_look(input: InputFrame) -> void:
	var c: Dictionary = t.camera
	var turn: float = -input.look_x * c.sensitivityX
	_yaw = U.wrap_angle(_yaw + turn)
	if _hold != null:
		# 右スティック・マウスで回した分は、止めている基準も一緒に回す（ふだんと同じく、カメラを回すと進む向きも回る）
		_hold = U.wrap_angle(_hold + turn)
	pitch = clampf(pitch + input.look_y * c.sensitivityY, c.minPitch * U.DEG, c.maxPitch * U.DEG)
	if input.look_active:
		_idle_look = 0.0
		# 背後へ回している途中は、はっきり回したときだけやめる（右クリック中のマウスの小さな揺れで止まらないように）
		if absf(turn) > LOOK_CANCEL or absf(input.look_y) > LOOK_CANCEL:
			_recentering = 0.0
	_stick = Vector2(input.move_x, input.move_y)
	_update_hold(_stick)


## プレイヤーの背後へ素早く回す（ロックオン対象がないときのロックオンボタン、R3・C・タッチの「背後」）。
## player_yaw：ハルの体の向き。stick：今の左スティック（move_x, move_y）。
## 回している間と、そのあと左スティックを倒し続けている間は、左スティックの基準を止める（move_yaw。_update_hold）：
## 倒していれば押す前のカメラの向きのまま（ハルはそのまま同じ向きへ走り続け、カメラだけが背後へ回る）、
## 倒していなければ背後の向き（＝ハルの向き。回している途中で倒しても、カメラが向かう先が「前」）
func request_recenter(player_yaw: float, stick: Vector2) -> void:
	_recentering = 0.35
	if _hold != null:
		# すでに止めている（続けて押した）：今の基準（戻した分も含めて）をそのまま止め直す。進む向きは変わらない
		_hold = U.wrap_angle(_hold + _hold_shift)
		_hold_shift = 0.0
		if stick.length() >= STICK_DEAD:
			_hold_stick = stick.normalized()
		return
	_hold_shift = 0.0
	if stick.length() >= STICK_DEAD:
		_hold = _yaw
		_hold_stick = stick.normalized()
	else:
		_hold = player_yaw
		_hold_stick = Vector2.ZERO


## 左スティックの「前」の基準（yaw）。ふつうはカメラの向き。背後へ回している間などは止めた向き（request_recenter）
func move_yaw() -> float:
	return _yaw if _hold == null else U.wrap_angle(_hold + _hold_shift)


## 左スティックの向き（前＝0、右＝−90°。基準の yaw に足すと進む向きの yaw になる）
static func _stick_yaw(v: Vector2) -> float:
	return atan2(-v.x, v.y)


## 止めた基準をカメラへ戻していく：
## ・背後へ回している間は止めたまま（左スティックの向きを覚え直すだけ）。
## ・回し終えたら、左スティックの向きを変えた分だけ基準をカメラの方へ戻す。カメラに合わせて倒し直す向き（横へ走りながら押して、
##   そのあと前へ倒し直す）なら、戻した分と倒し直した分が打ち消し合って、ハルはまっすぐ走り続ける。逆の向きなら 2 倍の速さで向きを変える。
##   戻しきったら止めるのをやめる。向きを覚えておいた所から測るので、指の小さな揺れが積もって進路がずれていくことはない。
## ・左スティックを離したら、止めるのをやめる
func _update_hold(stick: Vector2) -> void:
	if _hold == null:
		return
	var held := stick.length() >= STICK_DEAD
	if _recentering > 0.0:
		if held:
			_hold_stick = stick.normalized()
		_hold_shift = 0.0
		return
	if not held or _hold_stick == Vector2.ZERO:
		_hold = null
		return
	var o := U.wrap_angle(_yaw - _hold)
	var turned := U.wrap_angle(_stick_yaw(stick) - _stick_yaw(_hold_stick))
	var shift := -turned
	if signf(shift) != signf(o) and absf(o) < HOLD_EITHER_WAY * U.DEG:
		shift = signf(o) * absf(turned)
	if absf(shift) >= absf(o):
		_hold = null
	else:
		_hold_shift = shift


func update(dt: float, player_pos: Vector3, player_yaw: float, player_speed: float, target) -> void:
	var c: Dictionary = t.camera
	_idle_look += dt
	if target != null:
		# ロックオン中：プレイヤーの後ろから対象を見る向きへ寄せる（左スティックの基準はカメラに戻す）。
		# 背後へ回している途中に捉えたら、回すのはやめる（残すと、外れたあとに基準なしで回り出して、カメラが回り続ける）
		_end_swing()
		var want := U.dir_to_yaw(target.x - player_pos.x, target.z - player_pos.z)
		_yaw = U.wrap_angle(_yaw + U.wrap_angle(want - _yaw) * U.damp(c.lockOnYawSpeed, dt))
		pitch += (c.defaultPitch * U.DEG - pitch) * U.damp(3.0, dt)
		return
	if _recentering > 0.0:
		# ハルの体の向きの背後へ。左スティックの基準は止めてあるので、カメラが回ってもハルの進む向きは回らない
		_recentering -= dt
		_yaw = U.wrap_angle(_yaw + U.wrap_angle(player_yaw - _yaw) * U.damp(14.0, dt))
		pitch += (c.defaultPitch * U.DEG - pitch) * U.damp(10.0, dt)
		return
	if follow != "off" and _idle_look > c.autoRecenterDelay and player_speed > 2.0:
		# 操作がしばらくないときは、移動の向きの背後へゆっくり回る。
		# ただしプレイヤーの向きとの差が autoRecenterDeadzone（度）以内なら回らない。
		# （まっすぐ倒したつもりの数度のずれを追いかけると、向きが少しずれる → カメラが回る → 入力の基準が回る、
		# という繰り返しで進路が曲がっていく。大きく曲がったときだけ、不感帯の端まで寄せる）
		var dead: float = float(c.get("autoRecenterDeadzone", 25.0)) * U.DEG
		var diff := U.wrap_angle(player_yaw - _yaw)
		var excess := absf(diff) - dead
		# 弱い：横や後ろへ進むときは回らない（左スティックを横に倒しただけでカメラが回らないように）
		if follow == "weak" and absf(diff) > FORWARD_ONLY * U.DEG:
			excess = 0.0
		if excess > 0.0:
			var rate: float = c.autoRecenterSpeed * clampf(player_speed / 7.0, 0.0, 1.0) * dt
			if follow == "weak":
				rate *= 0.5
			if _hold == null and _stick.length() >= STICK_DEAD:
				# 左スティックを倒したまま回り込む：基準は回り込む前のカメラの向きに止める（背後へ回すときと同じ。_update_hold）。
				# ハルはまっすぐ走り続け、カメラは進む向きとの差が不感帯の端になった所で止まる（左スティックでカメラが回り続けない）
				_hold = _yaw
				_hold_stick = _stick.normalized()
				_hold_shift = 0.0
			_yaw = U.wrap_angle(_yaw + signf(diff) * minf(excess, rate))
