class_name CameraRig
extends Camera3D
## カメラの実際の位置を決める。向き（yaw・pitch）はゲームの中身が持ち、
## ここでは壁への衝突回避、ロックオン時の画面の収め方、揺れを担当する。

var _dist := 5.5
var _pivot := Vector3.ZERO
var _initialized := false
var _time := 0.0
## 壁に寄って立ったときにカメラを上へ回す角度（ラジアン。なめらかに戻す）
var _lift := 0.0
const LIFT_STEP := 0.26     # 15 度ずつ試す
const LIFT_STEPS := 8     # 下向き（-35 度）からでも 75 度まで届く数
const LIFT_MAX := 1.31      # 75 度まで

## 奈落へ落ちるとき：最後に立った高さより FALL_HOLD 下で、足の下（今の横の速さで少し先も）に何も無ければ、落ちきるとみなす。
## そのあいだカメラは縁に止まって見下ろし（ハルについて下がらない）、落ちた深さに合わせて画面を暗くする。
## 前はハルについて部屋の下まで下がり、縦穴の底より下の何も無い霧・町の下の段の床の裏・遠くの柱に乗った広場が映った。
## 直前の足場へ戻ったら（Player.KILL_Y）、暗いうちにカメラを戻してから明るくする
const FALL_HOLD := 0.8
const FALL_DARK := Vector2(0.8, 4.0)    # 立った高さからの深さ：暗くし始め・真っ暗（町の胸壁 1.2 m から下の段の屋根 -2 m では 9 割暗い）
const FALL_AHEAD: Array[float] = [0.0, 0.15, 0.3, 0.5]   # 今の横の速さで、この秒数だけ先の足元も調べる（穴を跳び越すときは止めない）
## 画面の暗さ（0〜1。カメラの下の幕の不透明度）
var fall_dark := 0.0
var _fall_hold := false
var _hold_pos := Vector3.ZERO
var _hold_w := 0.0
var _ground_y := 0.0
var _last_player := Vector3.ZERO
var _veil: ColorRect


func _ready() -> void:
	# 落ちるときの暗い幕（HUD の下。HP などは見えたまま）
	var layer := CanvasLayer.new()
	layer.layer = 0
	_veil = ColorRect.new()
	_veil.color = Color(0, 0, 0, 0)
	_veil.set_anchors_preset(Control.PRESET_FULL_RECT)
	_veil.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_veil.visible = false
	layer.add_child(_veil)
	add_child(layer)


func sync(game: GameSim, player_pos: Vector3, dt: float, shake: float) -> void:
	_time += dt
	var c: Dictionary = game.tuning.camera
	var yaw: float = game.cam.yaw
	var pitch: float = game.cam.pitch
	var snap := _update_fall(game, player_pos, dt)

	var want_pivot := player_pos + Vector3(0, c.pivotHeight, 0)
	var t = game.lock_on.target
	var target := Vector3.ZERO
	if t != null:
		target = t.center()
		# プレイヤーと対象の中間より、少しプレイヤー寄りを注視する
		want_pivot = want_pivot.lerp(target, 0.3)
		want_pivot.y = minf(want_pivot.y, player_pos.y + c.pivotHeight + 1.0)
	elif game.cam_focus != null:
		# イベントの注視点：プレイヤーと注視点のあいだ、注視点寄りを見る
		want_pivot = want_pivot.lerp(game.cam_focus, 0.65)
	if not _initialized or snap:
		_pivot = want_pivot
		_initialized = true
	_pivot = _pivot.lerp(want_pivot, U.damp(14.0, dt))

	var back := _dir(yaw, pitch)
	var want: float = c.distance
	if t != null:
		want += minf(2.0, _pivot.distance_to(target) * 0.1)
	# 壁の手前にカメラを寄せる。壁より向こうには置かない（前は最短 minDistance まで下がったので、壁に寄って立つとカメラが
	# 家・遺構の壁の中に入り、壁が消えて中が透けた）。壁が minDistance より近いときは、カメラを上へ回して頭の上から見る
	var room := _room(game, back, want)
	var lift_want := 0.0
	if room < c.minDistance:
		var best := room
		for k in range(1, LIFT_STEPS + 1):
			var p2 := minf(pitch + LIFT_STEP * k, LIFT_MAX)
			var r2 := _room(game, _dir(yaw, p2), want)
			if r2 > best + 0.05:
				best = r2
				lift_want = p2 - pitch
			if r2 >= c.minDistance or p2 >= LIFT_MAX:
				break
	# 上へ回すのは素早く（頭のすぐ後ろにいる時間を短く）、戻すのはゆっくり
	_lift += (lift_want - _lift) * U.damp(14.0 if lift_want > _lift else 5.0, dt)
	if _lift > 0.001:
		back = _dir(yaw, pitch + _lift)
		room = _room(game, back, want)
	want = minf(want, room)
	# 近づくのは素早く、離れるのはゆっくり（minDistance より近い窮屈な所からは早めに離れる）
	_dist += (want - _dist) * (1.0 if want < _dist or snap else U.damp(4.0 if _dist >= c.minDistance else 12.0, dt))

	var p := _pivot + back * _dist
	if _hold_w > 0.0:
		p = p.lerp(_hold_pos, _hold_w)
	if shake > 0.0:
		p.x += sin(_time * 73.0) * shake * 0.15
		p.y += sin(_time * 91.0) * shake * 0.15
	global_position = p
	var to := _pivot - p
	if to.length_squared() > 1e-6 and absf(to.normalized().y) < 0.999:
		look_at(_pivot, Vector3.UP)
	fov = c.fov
	if _veil != null:
		_veil.visible = fall_dark > 0.002
		_veil.color.a = fall_dark


## 奈落へ落ちているか（FALL_HOLD の説明）を調べ、カメラを止める重み・画面の暗さを進める。
## 戻り値：カメラを今の場所へすぐ移すか（暗いうちに直前の足場へ戻ったとき）
func _update_fall(game: GameSim, player_pos: Vector3, dt: float) -> bool:
	var pl: Player = game.player
	# 足場へ戻す・部屋に入る・撮影の構えなどで一気に動いた
	var teleported := not _initialized or dt >= 0.5 or player_pos.distance_to(_last_player) > 3.0
	_last_player = player_pos
	var was_hold := _fall_hold
	if teleported or pl.grounded:
		_ground_y = player_pos.y
		_fall_hold = false
	elif not _fall_hold and pl.vel.y < 0.0 and player_pos.y < _ground_y - FALL_HOLD and _nothing_below(game, player_pos, pl.vel):
		_fall_hold = true
		_hold_pos = global_position
	var snap := teleported and (was_hold or fall_dark > 0.5)
	if _fall_hold:
		_hold_w = 1.0
		fall_dark = maxf(fall_dark, smoothstep(FALL_DARK.x, FALL_DARK.y, _ground_y - player_pos.y))
	else:
		_hold_w = 0.0 if snap or teleported else move_toward(_hold_w, 0.0, dt / 0.35)
		fall_dark = move_toward(fall_dark, 0.0, dt / 0.5)
	return snap


## 足の下（と、今の横の速さで少し先の足の下）に、奈落の高さまで何も無いか
static func _nothing_below(game: GameSim, at: Vector3, vel: Vector3) -> bool:
	var flat := Vector3(vel.x, 0.0, vel.z)
	for t in FALL_AHEAD:
		var o := at + flat * t + Vector3(0, 0.2, 0)
		var hit: Dictionary = game.phys.raycast(o, Vector3.DOWN, o.y - Player.KILL_Y + 1.0, Phys.TERRAIN | Phys.BREAKABLE)
		if not hit.is_empty():
			return false
	return true


## yaw・pitch のときの、注視点からカメラへの向き
static func _dir(yaw: float, pitch: float) -> Vector3:
	return Vector3(-sin(yaw) * cos(pitch), sin(pitch), -cos(yaw) * cos(pitch))


## 注視点から dir の向きに、カメラを置ける距離（壁の 0.3 m 手前。壁がごく近いときは壁までの半分。壁を越えない）
func _room(game: GameSim, dir: Vector3, want: float) -> float:
	var hit: Dictionary = game.phys.raycast(_pivot, dir, want + 0.3, Phys.TERRAIN | Phys.BREAKABLE)
	if hit.is_empty():
		return want
	return maxf(hit.distance - 0.3, hit.distance * 0.5)


## カメラの正面方向
func forward_dir() -> Vector3:
	return -global_transform.basis.z
