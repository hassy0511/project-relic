class_name CameraOrbit
extends RefCounted
## カメラの向き（yaw・pitch）。移動の向きに関わるのでゲームの中身が持つ。
## 実際のカメラ位置（壁の回避など）は見た目の側が決める。yaw は「カメラが見ている水平方向」。

var t: Dictionary
var yaw := PI
var pitch := 12.0 * U.DEG
var _idle_look := 0.0
var _recentering := 0.0


func _init(tuning: Dictionary) -> void:
	t = tuning
	pitch = t.camera.defaultPitch * U.DEG


func apply_look(input: InputFrame) -> void:
	var c: Dictionary = t.camera
	yaw = U.wrap_angle(yaw - input.look_x * c.sensitivityX)
	pitch = clampf(pitch + input.look_y * c.sensitivityY, c.minPitch * U.DEG, c.maxPitch * U.DEG)
	if input.look_active:
		_idle_look = 0.0
		_recentering = 0.0


## プレイヤーの背後へ素早く回す（ロックオン対象がないときのロックオンボタン、R3）
func request_recenter() -> void:
	_recentering = 0.35


func update(dt: float, player_pos: Vector3, player_yaw: float, player_speed: float, target) -> void:
	var c: Dictionary = t.camera
	_idle_look += dt
	if target != null:
		# ロックオン中：プレイヤーの後ろから対象を見る向きへ寄せる
		var want := U.dir_to_yaw(target.x - player_pos.x, target.z - player_pos.z)
		yaw = U.wrap_angle(yaw + U.wrap_angle(want - yaw) * U.damp(c.lockOnYawSpeed, dt))
		pitch += (c.defaultPitch * U.DEG - pitch) * U.damp(3.0, dt)
		return
	if _recentering > 0.0:
		_recentering -= dt
		yaw = U.wrap_angle(yaw + U.wrap_angle(player_yaw - yaw) * U.damp(14.0, dt))
		pitch += (c.defaultPitch * U.DEG - pitch) * U.damp(10.0, dt)
		return
	if _idle_look > c.autoRecenterDelay and player_speed > 2.0:
		# 操作がしばらくないときは、移動の向きの背後へゆっくり回る。
		# ただしプレイヤーの向きとの差が autoRecenterDeadzone（度）以内なら回らない。
		# （まっすぐ倒したつもりの数度のずれを追いかけると、向きが少しずれる → カメラが回る → 入力の基準が回る、
		# という繰り返しで進路が曲がっていく。大きく曲がったときだけ、不感帯の端まで寄せる）
		var dead: float = float(c.get("autoRecenterDeadzone", 25.0)) * U.DEG
		var diff := U.wrap_angle(player_yaw - yaw)
		var excess := absf(diff) - dead
		if excess > 0.0:
			var rate: float = c.autoRecenterSpeed * clampf(player_speed / 7.0, 0.0, 1.0) * dt
			yaw = U.wrap_angle(yaw + signf(diff) * minf(excess, rate))
