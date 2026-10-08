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
const LIFT_STEPS := 4
const LIFT_MAX := 1.31      # 75 度まで


func sync(game: GameSim, player_pos: Vector3, dt: float, shake: float) -> void:
	_time += dt
	var c: Dictionary = game.tuning.camera
	var yaw: float = game.cam.yaw
	var pitch: float = game.cam.pitch

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
	if not _initialized:
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
	_lift += (lift_want - _lift) * U.damp(6.0, dt)
	if _lift > 0.001:
		back = _dir(yaw, pitch + _lift)
		room = _room(game, back, want)
	want = minf(want, room)
	# 近づくのは素早く、離れるのはゆっくり
	_dist += (want - _dist) * (1.0 if want < _dist else U.damp(4.0, dt))

	var p := _pivot + back * _dist
	if shake > 0.0:
		p.x += sin(_time * 73.0) * shake * 0.15
		p.y += sin(_time * 91.0) * shake * 0.15
	global_position = p
	look_at(_pivot, Vector3.UP)
	fov = c.fov


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
