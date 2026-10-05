class_name CameraRig
extends Camera3D
## カメラの実際の位置を決める。向き（yaw・pitch）はゲームの中身が持ち、
## ここでは壁への衝突回避、ロックオン時の画面の収め方、揺れを担当する。

var _dist := 5.5
var _pivot := Vector3.ZERO
var _initialized := false
var _time := 0.0


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

	var back := Vector3(-sin(yaw) * cos(pitch), sin(pitch), -cos(yaw) * cos(pitch))
	var want: float = c.distance
	if t != null:
		want += minf(2.0, _pivot.distance_to(target) * 0.1)
	# 壁の手前にカメラを寄せる
	var hit: Dictionary = game.phys.raycast(_pivot, back, want + 0.3, Phys.TERRAIN | Phys.BREAKABLE)
	if not hit.is_empty():
		want = maxf(c.minDistance, hit.distance - 0.3)
	# 近づくのは素早く、離れるのはゆっくり
	_dist += (want - _dist) * (1.0 if want < _dist else U.damp(4.0, dt))

	var p := _pivot + back * _dist
	if shake > 0.0:
		p.x += sin(_time * 73.0) * shake * 0.15
		p.y += sin(_time * 91.0) * shake * 0.15
	global_position = p
	look_at(_pivot, Vector3.UP)
	fov = c.fov


## カメラの正面方向
func forward_dir() -> Vector3:
	return -global_transform.basis.z
