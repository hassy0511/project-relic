class_name HaruPose
extends SkeletonModifier3D
## 動作の上から重ねる、手続きの姿勢。AnimationPlayer の結果に足して、動きに生気を出す。
## - 撃つ：右腕を照準へ向け、胸を少しひねる（上半身だけの重ね合わせ）
## - 走る：曲がるときに体を内側へ傾け、加速・減速で前後に傾ける
## - ロックオン：頭を対象へ向ける

## 照準の強さ（0〜1）と向き（キャラクターの座標系。+Z が正面）
var aim_weight := 0.0
var aim_local := Vector3(0, 0, 1)
## 体の傾き（ラジアン）。roll：左右、pitch：前後
var lean_roll := 0.0
var lean_pitch := 0.0
## 頭を向ける先（キャラクターの座標系）と強さ
var look_weight := 0.0
var look_local := Vector3(0, 0, 1)

var _bones := {}


func _bone(sk: Skeleton3D, name: String) -> int:
	if not _bones.has(name):
		_bones[name] = sk.find_bone(name)
	return _bones[name]


func _process_modification() -> void:
	var sk := get_skeleton()
	if sk == null:
		return
	# 体の傾き：背骨に分けて入れる
	var spine := _bone(sk, "spine")
	var chest := _bone(sk, "chest")
	if spine >= 0 and (absf(lean_roll) > 1e-4 or absf(lean_pitch) > 1e-4):
		_rotate_global(sk, spine, Quaternion(Vector3(0, 0, 1), lean_roll * 0.6) * Quaternion(Vector3(1, 0, 0), lean_pitch * 0.6))
		if chest >= 0:
			_rotate_global(sk, chest, Quaternion(Vector3(0, 0, 1), lean_roll * 0.4) * Quaternion(Vector3(1, 0, 0), lean_pitch * 0.4))

	# 撃つ：右腕を照準の向きへ。胸を照準の横方向へ少しひねる
	if aim_weight > 0.001:
		var yaw := atan2(aim_local.x, aim_local.z)
		if chest >= 0:
			_rotate_global(sk, chest, Quaternion(Vector3.UP, clampf(yaw, -1.0, 1.0) * 0.5 * aim_weight))
		var arm := _bone(sk, "upper_arm.R")
		var fore := _bone(sk, "forearm.R")
		if arm >= 0:
			# 上腕の骨の向き（肩→肘）を、照準の向きへ回す
			var g := sk.get_bone_global_pose(arm)
			var cur := (sk.get_bone_global_pose(fore).origin - g.origin).normalized() if fore >= 0 else -g.basis.y
			var want := aim_local.normalized()
			var q := _arc(cur, want)
			var full := Quaternion.IDENTITY.slerp(q, aim_weight)
			_rotate_global(sk, arm, full)
			if fore >= 0:
				# 肘はまっすぐ伸ばす（前腕を上腕と同じ向きに）
				var ga := sk.get_bone_global_pose(arm)
				var gf := sk.get_bone_global_pose(fore)
				var hand := _bone(sk, "hand.R")
				if hand >= 0:
					var fdir := (sk.get_bone_global_pose(hand).origin - gf.origin).normalized()
					var adir := (gf.origin - ga.origin).normalized()
					_rotate_global(sk, fore, Quaternion.IDENTITY.slerp(_arc(fdir, adir), aim_weight))

	# 頭を対象へ向ける
	if look_weight > 0.001:
		var head := _bone(sk, "head")
		if head >= 0:
			var yaw2 := clampf(atan2(look_local.x, look_local.z), -1.1, 1.1)
			var pitch2 := clampf(-atan2(look_local.y, Vector2(look_local.x, look_local.z).length()), -0.5, 0.5)
			_rotate_global(sk, head, Quaternion(Vector3.UP, yaw2 * 0.6 * look_weight) * Quaternion(Vector3(1, 0, 0), pitch2 * 0.5 * look_weight))


## 2 つの向きの間の回転
static func _arc(a: Vector3, b: Vector3) -> Quaternion:
	var axis := a.cross(b)
	var d := clampf(a.dot(b), -1.0, 1.0)
	if axis.length() < 1e-6:
		return Quaternion.IDENTITY
	return Quaternion(axis.normalized(), acos(d))


## 骨を、骨格の座標系での回転 q だけ回す（子の骨もいっしょに回る）
static func _rotate_global(sk: Skeleton3D, bone: int, q: Quaternion) -> void:
	var parent := sk.get_bone_parent(bone)
	var pg := sk.get_bone_global_pose(parent) if parent >= 0 else Transform3D.IDENTITY
	var g := sk.get_bone_global_pose(bone)
	var new_basis := Basis(q) * g.basis
	var local_basis := pg.basis.inverse() * new_basis
	sk.set_bone_pose_rotation(bone, local_basis.get_rotation_quaternion())
