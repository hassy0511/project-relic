class_name HaruSway
extends SkeletonModifier3D
## 髪の房のまとまりと、帯から下がるポーチの揺れ（2 次の動き。見た目だけ）。
## 骨はモデルの側（tools/blender/recon/sway.py、ai_character.py --sway-bones）：髪のまとまりごとに 1 本（親 head）、
## ポーチごとに 1 本（親 hips）。重みは房の先ほど大きく、土台・生え際・ゴーグル・ヒモのまわりは 0（揺れても顔・ゴーグル・
## ヒモを突き抜けない）。
##
## 揺れ方：骨ごとに、根のまわりに回る振り子（向き d・角速度 ω、世界の座標）。物理の刻みごとに：
##   ・ばね：動作のままの向き d0 へ戻す（stiffness、1/秒²）と、回る速さの減衰（damping、1/秒）
##   ・慣性：根の世界の加速度（刻みごとの位置の 2 階の差。なめらかにして大きさを制限）の逆向きに房の先を押す（inertia）：
##     走り出すと後ろへ、止まると前へ振れ、落ちる間は少し浮き、着地で下へ打ってから戻る。待機の息・攻撃のひねりでも根が動くので揺れる
##   ・風：走る速さ（水平）の逆向きに少し（wind。髪だけ）
##   ・振り向き：d は世界に残るので、頭が回ると遅れてから追いつく
##   ・角度の上限 limit：d0 から limit より開かない（顔・頭・体へ深く入らない）。ポーチは体の外向きの軸のまわりだけ（前後）に回る
## 刻みの速さに左右されない：揺れは骨格の更新のうち物理の刻みのもの（delta > 0。PlayerView.load_model で骨格の変形を
## 物理の刻みで進める）でだけ進め、親の骨の座標での回転として持つ。描画のこまの更新（delta = 0）では、その回転を今の姿勢に
## 置き直すだけ（--fixed-fps 30・60・144 で同じ動き）。
## SpringBoneSimulator3D（Godot 4.5）は使わなかった：delta = 0 の更新でも速さの項で 1 歩進むので、動作を描画のこまで進める
## このゲームでは描画の速さで揺れ方が変わる。世界に対する減衰のため走る速さで房が 60〜110 度なびき、跳び始めの速い沈みで
## 150 度めくれた。角度の上限も無い（W1_ハル再構築の結果.md 8 章）。
## 調整：CHAINS（固さ・減衰・慣性・風・角度の上限）、ACCEL_*（加速度のなめらかさと上限）。

## 骨の名前 → 揺れ方。stiffness：戻す強さ（1/秒²。√ が 1 秒あたりの振れの角速度。250 で約 2.5 回/秒）。damping：回る速さを
## 減らす（1/秒。2√stiffness で振れずに止まる）。inertia：加速度 1 m/秒² あたりの押し（ラジアン/秒²）。wind：走る速さ
## 1 m/秒あたりの後ろへの押し。limit：d0 からの角度の上限（ラジアン）。axis "out"：体の外向きの軸のまわりだけ回す
const CHAINS := {
	"hair.front": {"stiffness": 260.0, "damping": 11.0, "inertia": 2.6, "wind": 2.4, "limit": 0.50},
	"hair.top": {"stiffness": 200.0, "damping": 9.0, "inertia": 3.2, "wind": 3.2, "limit": 0.62},
	"hair.back.L": {"stiffness": 180.0, "damping": 8.0, "inertia": 3.4, "wind": 3.6, "limit": 0.62},
	"hair.back.R": {"stiffness": 180.0, "damping": 8.0, "inertia": 3.4, "wind": 3.6, "limit": 0.62},
	"hair.nape": {"stiffness": 220.0, "damping": 10.0, "inertia": 2.8, "wind": 2.8, "limit": 0.50},
	"hair.side.L": {"stiffness": 200.0, "damping": 9.0, "inertia": 2.8, "wind": 3.0, "limit": 0.45},
	"hair.side.R": {"stiffness": 200.0, "damping": 9.0, "inertia": 2.8, "wind": 3.0, "limit": 0.45},
	"pouch.L": {"stiffness": 150.0, "damping": 6.5, "inertia": 2.6, "wind": 0.0, "limit": 0.42, "axis": "out"},
	"pouch.R": {"stiffness": 150.0, "damping": 6.5, "inertia": 2.6, "wind": 0.0, "limit": 0.42, "axis": "out"},
}
## 加速度をなめらかにする速さ（1/秒）と大きさの上限（m/秒²）。着地・跳び始めの 1 刻みの大きな加速度を数刻みへ広げ、
## 動作の速い沈み（跳び始めに頭が 2 刻みで 17 cm 下がる）でも房が上限に張りつかないように
const ACCEL_SMOOTH := 20.0
const ACCEL_MAX := 60.0

var bones: PackedInt32Array = []
## 最後の物理の刻みの、揺れの角度の最大（ラジアン。確かめ用）
var last_max := 0.0
## 計測（HaruMotionShots の --haru_secondary_bench）：真の間、この修飾にかかった時間（マイクロ秒）と呼ばれた回数を足していく
static var profile := false
static var prof_usec := 0
static var prof_calls := 0
var _e: Array = []           ## 骨ごとの設定と状態（Dictionary）


## 骨格に揺れの骨があれば揺れを組み立てて骨格の子にする（無いモデルでは null）
static func attach(sk: Skeleton3D) -> HaruSway:
	var names: Array[String] = []
	for n in CHAINS:
		if sk.find_bone(n) >= 0:
			names.append(n)
	if names.is_empty():
		return null
	var s := HaruSway.new()
	s.name = "HaruSway"
	sk.add_child(s)
	for n in names:
		var b := sk.find_bone(n)
		var pb := sk.get_bone_parent(b)
		var c: Dictionary = CHAINS[n]
		var e := {"b": b, "pb": pb, "rest": sk.get_bone_rest(b), "c": c, "axis": Vector3.ZERO,
			"d": Vector3.UP, "w": Vector3.ZERO, "pos": Vector3.ZERO, "vel": Vector3.ZERO, "acc": Vector3.ZERO,
			"q": Quaternion.IDENTITY, "fresh": true}
		if c.get("axis", "") == "out":
			# 体の縦の軸から外向き（水平）を、親の骨（腰）の座標へ直して持つ
			var rest := sk.get_bone_global_rest(b)
			var out := Vector3(rest.origin.x, 0.0, rest.origin.z).normalized()
			e.axis = (sk.get_bone_global_rest(pb).basis.inverse() * out).normalized()
		s._e.append(e)
		s.bones.append(b)
	return s


## 入れる・切る（PlayerView.set_secondary）
func set_enabled(on: bool) -> void:
	active = on
	last_max = 0.0
	reset()


## 揺れを止めて置き直す（読み込み・部屋の移動・復活。次の更新の姿勢から始める）
func reset() -> void:
	for e in _e:
		e.fresh = true


func _process_modification_with_delta(delta: float) -> void:
	var sk := get_skeleton()
	if sk == null:
		return
	var t0 := Time.get_ticks_usec() if profile else 0
	var S := sk.global_transform
	var sb := S.basis.orthonormalized()
	var mx := 0.0
	for e in _e:
		var rest: Transform3D = e.rest
		if delta > 0.0 or e.fresh:
			var pg := sk.get_bone_global_pose(e.pb)
			var g0 := pg * rest
			var pivot: Vector3 = S * g0.origin
			var d0: Vector3 = (sb * g0.basis.y).normalized()
			if e.fresh:
				e.fresh = false
				e.d = d0
				e.w = Vector3.ZERO
				e.pos = pivot
				e.vel = Vector3.ZERO
				e.acc = Vector3.ZERO
				e.q = Quaternion.IDENTITY
			else:
				_step(e, pg, sb, pivot, d0, delta)
				mx = maxf(mx, d0.angle_to(e.d))
		sk.set_bone_pose_rotation(e.b, (e.q as Quaternion) * rest.basis.get_rotation_quaternion())
	if delta > 0.0:
		last_max = mx
	if profile:
		prof_usec += Time.get_ticks_usec() - t0
		prof_calls += 1


## 1 刻み進める（物理の刻み）。e.q：揺れの回転を親の骨の座標で（描画のこまでは今の親の姿勢にそのまま載る）
func _step(e: Dictionary, pg: Transform3D, sb: Basis, pivot: Vector3, d0: Vector3, dt: float) -> void:
	var c: Dictionary = e.c
	var v: Vector3 = (pivot - (e.pos as Vector3)) / dt
	var a: Vector3 = (v - (e.vel as Vector3)) / dt
	e.acc = ((e.acc as Vector3).lerp(a, 1.0 - exp(-ACCEL_SMOOTH * dt))).limit_length(ACCEL_MAX)
	e.vel = v
	e.pos = pivot
	var d: Vector3 = e.d
	var w: Vector3 = e.w
	# 先を押す向き：加速度の逆向き＋走る速さの逆向きの風
	var push: Vector3 = -(e.acc as Vector3) * float(c.inertia) - Vector3(v.x, 0.0, v.z) * float(c.wind)
	var alpha: Vector3 = d.cross(d0) * float(c.stiffness) - w * float(c.damping) + d.cross(push)
	w += alpha * dt
	w -= d * d.dot(w)              # 骨の軸まわりのねじれは持たない
	var pw := (sb * pg.basis).orthonormalized()
	var axis := Vector3.ZERO
	if e.axis != Vector3.ZERO:
		axis = (pw * (e.axis as Vector3)).normalized()
		w = axis * axis.dot(w)
	var ang := w.length() * dt
	if ang > 1e-7:
		d = Quaternion(w.normalized(), ang) * d
	if axis != Vector3.ZERO:
		d = d - axis * axis.dot(d)
	d = d.normalized()
	# 角度の上限：それより開く向きの回る速さは捨てる
	var lim := float(c.limit)
	var open := d0.angle_to(d)
	if open > lim:
		d = d0.slerp(d, lim / open).normalized()
		var out := d0.cross(d)
		if out.length() > 1e-6:
			out = out.normalized()
			w -= out * maxf(0.0, out.dot(w))
	e.d = d
	e.w = w
	# 揺れの回転（世界の d0 → d）を親の骨の座標へ：q = Pw⁻¹ · A · Pw
	var A := HaruPose._arc(d0, d)
	var pq := pw.get_rotation_quaternion()
	e.q = pq.inverse() * A * pq


## 揺れの骨の、今の向き（揺れのあと）と揺れない向き（親の今の姿勢 × 基準の姿勢）の角度（ラジアン）。
## 確かめ・調整用：骨格の更新の直後（Skeleton3D.skeleton_updated）に読む
func deflection(sk: Skeleton3D) -> Dictionary:
	var out := {}
	for b in bones:
		var cur := sk.get_bone_global_pose(b).basis.y.normalized()
		var base := (sk.get_bone_global_pose(sk.get_bone_parent(b)) * sk.get_bone_rest(b)).basis.y.normalized()
		out[sk.get_bone_name(b)] = cur.angle_to(base)
	return out
