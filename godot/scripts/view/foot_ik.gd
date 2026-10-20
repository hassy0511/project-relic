class_name FootIK
extends SkeletonModifier3D
## 足の接地（見た目だけ。ゲームの中身のカプセル・物理は変えない）。
## 動作は平らな床（足の裏が y = 0）で作ってあるので、階段・坂・段の縁では片方の足が浮くか床に沈む。
## 立っている間（待機・その場の攻撃）だけ、各足の下の床の面（PlayerView.sync が部屋の当たりへ光線を撃って決め、なめらかにした面）に
## 足の裏を置く：
##   1. 足首を上下にだけ動かして、足の裏の中ほどが面に載る高さ t を求める（坂では足を面の傾きへ倒してから）
##   2. 腰を低いほうの足の t だけ下げる（伸ばせない脚を下の段へ届かせる。上の足は膝を曲げて上げる）
##   3. 脚ごとに 2 本の骨（太もも・すね）の解析的な IK で足首を目標へ。膝は今の曲がりの向き（無ければ足の前）へ
##   4. 足は動作の向きのまま、床の面の傾きへ倒す（MAX_TILT まで）
## 効き weight（0〜1）は PlayerView が決める（止まって立つ間 1、走る・跳ぶ・ダッシュ・倒れでは 0 へ）。

const LEGS := [["thigh.L", "shin.L", "foot.L"], ["thigh.R", "shin.R", "foot.R"]]
## 腰を下げる最大・上げる最大（m）。段は 0.35 m まで（42 章）なので、それより深い所は届かせない
const MAX_DROP := 0.36
const MAX_RISE := 0.05
## 足を動作の位置より上げる最大（m。膝の曲がりの限り）
const MAX_LIFT := 0.45
## 足を床の傾きへ倒す最大（ラジアン、約 30 度）
const MAX_TILT := 0.52
## 足の裏の点（足首の骨の基準の姿勢から：前・下。モデルの座標 = Blender の humanoid.FOOT_CONTACTS のつま先 0.22・かかと 0.06・下 0.09）。
## 光線を撃つのは母指球（前 0.14）・中ほど（前 0.07）・かかと（後ろ 0.05）
const SOLE_DOWN := 0.09
const SOLE_POINTS := [0.14, 0.07, -0.05]

## 効き（0〜1）
var weight := 0.0
## モデルの足もとの点（世界の座標。ゲームの中身のカプセルの底 = PlayerView の位置）。動作の足の裏はこの高さが床
var base_point := Vector3.ZERO
## 各足の床の面（世界の座標）：点と上向きの法線。valid が偽の足は動かさない（面が見つからない・深すぎる）
var plane_point: Array[Vector3] = [Vector3.ZERO, Vector3.ZERO]
var plane_normal: Array[Vector3] = [Vector3.UP, Vector3.UP]
var plane_valid: Array[bool] = [false, false]
## 動作のままの足の裏の点（骨格の座標。各足 SOLE_POINTS の順）。PlayerView が次の刻みの光線をここから撃つ
var sole_anim: Array = [[], []]
## 最後に使った腰の下げ・足の上げ（確かめ用、世界の m）
var last_drop := 0.0
var last_lift: Array[float] = [0.0, 0.0]

var _ids := []          # [[thigh, shin, foot], ...]
var _hips := -1
var _sole_local := []   # 足首の骨の座標での、足の裏の点（各足 SOLE_POINTS の順）
var _sole_mid_local := [Vector3.ZERO, Vector3.ZERO]


func _bind(sk: Skeleton3D) -> bool:
	if not _ids.is_empty():
		return true
	_hips = sk.find_bone("hips")
	var ids := []
	for leg in LEGS:
		var t := sk.find_bone(leg[0])
		var s := sk.find_bone(leg[1])
		var f := sk.find_bone(leg[2])
		if t < 0 or s < 0 or f < 0:
			return false
		ids.append([t, s, f])
	if _hips < 0:
		return false
	_ids = ids
	_sole_local = []
	for i in 2:
		var rest := sk.get_bone_global_rest(_ids[i][2])
		# 足の前：足首の骨の向き（つま先へ）を水平にしたもの
		var fwd := Vector3(rest.basis.y.x, 0.0, rest.basis.y.z).normalized()
		var pts := []
		for d in SOLE_POINTS:
			var p: Vector3 = rest.origin + fwd * float(d) + Vector3.DOWN * SOLE_DOWN
			pts.append(rest.affine_inverse() * p)
		_sole_local.append(pts)
		_sole_mid_local[i] = rest.affine_inverse() * (rest.origin + fwd * 0.07 + Vector3.DOWN * SOLE_DOWN)
	return true


func _process_modification() -> void:
	var sk := get_skeleton()
	if sk == null or not _bind(sk):
		return
	# 動作のままの足の裏の点（次の刻みの光線の元）
	for i in 2:
		var g := sk.get_bone_global_pose(_ids[i][2])
		var pts := []
		for lp in _sole_local[i]:
			pts.append(g * lp)
		sole_anim[i] = pts
	if weight <= 0.001 or not (plane_valid[0] or plane_valid[1]):
		last_drop = 0.0
		last_lift[0] = 0.0
		last_lift[1] = 0.0
		return
	var to_sk := sk.global_transform.affine_inverse()
	var up := (to_sk.basis * Vector3.UP)          # 世界の 1 m 上（骨格の座標。拡大を含む）
	var up_n := up.normalized()
	var unit := up.length()
	var base := to_sk * base_point
	# 1. 各足の高さ t（骨格の座標の上下、動作の足首から）と倒す回転。
	#    足を倒して足首を上下に動かし、足の裏の中ほどを床の面に載せる高さ ＋ 動作でその足が床から上がっている高さ
	#    （踏み込みでかかとを上げた足・上げた足は、新しい床から同じだけ上がったまま。平らな床では t = 0 で動作のまま）
	var t := [0.0, 0.0]
	var tilt := [Quaternion.IDENTITY, Quaternion.IDENTITY]
	var foot_g := []
	for i in 2:
		var g := sk.get_bone_global_pose(_ids[i][2])
		foot_g.append(g)
		if not plane_valid[i]:
			continue
		var n := (to_sk.basis * plane_normal[i]).normalized()
		var ang := up_n.angle_to(n)
		var q := Quaternion.IDENTITY
		if ang > 1e-4:
			q = Quaternion(up_n.cross(n).normalized(), minf(ang, MAX_TILT))
		tilt[i] = q
		var p := to_sk * plane_point[i]
		var anim_off: Vector3 = g.basis * _sole_mid_local[i]
		var anim_h := (g.origin + anim_off - base).dot(up_n)
		var mid_off: Vector3 = Basis(q) * anim_off
		var denom := up_n.dot(n)
		if denom < 0.2:
			continue
		t[i] = (p - g.origin - mid_off).dot(n) / denom + anim_h
	# 2. 腰の下げ（低いほうの足）。足の上げは腰を下げたあとの分
	var lo := INF
	for i in 2:
		if plane_valid[i]:
			lo = minf(lo, t[i])
	var drop := clampf(lo, -MAX_DROP * unit, MAX_RISE * unit) * weight
	last_drop = drop / unit
	var hp := sk.get_bone_global_pose(_hips)
	var parent := sk.get_bone_parent(_hips)
	var pg := sk.get_bone_global_pose(parent) if parent >= 0 else Transform3D.IDENTITY
	sk.set_bone_pose_position(_hips, pg.affine_inverse() * (hp.origin + up_n * drop))
	# 3. 脚ごとの IK
	for i in 2:
		var ids: Array = _ids[i]
		var lift := 0.0
		if plane_valid[i]:
			lift = clampf(t[i] * weight - drop, -MAX_DROP * unit, MAX_LIFT * unit)
		else:
			lift = -drop          # 面の無い足は動作の高さのまま（腰を下げた分だけ戻す）
		last_lift[i] = lift / unit
		var anim_ankle: Vector3 = (foot_g[i] as Transform3D).origin
		var target: Vector3 = anim_ankle + up_n * (drop + lift)
		_solve_leg(sk, ids, target, foot_g[i], Quaternion.IDENTITY.slerp(tilt[i], weight))


## 2 本の骨の IK：太もも ids[0]・すね ids[1] を回して、足首 ids[2] を target へ。足の向きは動作の向き foot_g に、tilt をかけたもの
func _solve_leg(sk: Skeleton3D, ids: Array, target: Vector3, foot_g: Transform3D, tilt: Quaternion) -> void:
	var th: int = ids[0]
	var sh: int = ids[1]
	var ft: int = ids[2]
	var H := sk.get_bone_global_pose(th).origin
	var K := sk.get_bone_global_pose(sh).origin
	var A := sk.get_bone_global_pose(ft).origin
	var a := H.distance_to(K)
	var b := K.distance_to(A)
	var ht := target - H
	var d := clampf(ht.length(), absf(a - b) + 1e-4, (a + b) * 0.9995)
	if ht.length() < 1e-5:
		return
	var dir := ht.normalized()
	# 膝の向き：今の膝の、腰 → 目標の線からの向き（まっすぐなら足の前）
	var pole := (K - H) - dir * (K - H).dot(dir)
	if pole.length() < 1e-3:
		var fwd := foot_g.basis.y
		pole = fwd - dir * fwd.dot(dir)
	pole = pole.normalized()
	var cos_a := clampf((a * a + d * d - b * b) / (2.0 * a * d), -1.0, 1.0)
	var sin_a := sqrt(maxf(0.0, 1.0 - cos_a * cos_a))
	var K2 := H + (dir * cos_a + pole * sin_a) * a
	var T2 := H + dir * d
	# 太もも：腰 → 膝の向きを K2 へ
	HaruPose._rotate_global(sk, th, HaruPose._arc((K - H).normalized(), (K2 - H).normalized()))
	# すね：膝 → 足首の向きを T2 へ（太ももを回したあとの位置で）
	var K1 := sk.get_bone_global_pose(sh).origin
	var A1 := sk.get_bone_global_pose(ft).origin
	HaruPose._rotate_global(sk, sh, HaruPose._arc((A1 - K1).normalized(), (T2 - K1).normalized()))
	# 足：動作の向きに床の傾きをかける（太もも・すねの回りを打ち消す）
	var sg := sk.get_bone_global_pose(sh)
	var want := Basis(tilt) * foot_g.basis
	sk.set_bone_pose_rotation(ft, (sg.basis.inverse() * want).get_rotation_quaternion())
