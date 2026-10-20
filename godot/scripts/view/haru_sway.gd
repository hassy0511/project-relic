class_name HaruSway
extends SkeletonModifier3D
## 髪の房のまとまりと、帯から下がるポーチの揺れ（2 次の動き。見た目だけ）。
## 骨はモデルの側（tools/blender/recon/sway.py、ai_character.py --sway-bones）：髪のまとまりごとに 1 本（親 head）、
## ポーチごとに 1 本（親 hips）。重みは房の先ほど大きく、土台・生え際・ゴーグル・ヒモのまわりは 0（揺れても顔・ゴーグル・
## ヒモを突き抜けない）。
##
## 揺れ方：骨ごとに、根のまわりに回る振り子（向き d・角速度 ω、世界の座標）。物理の刻みごとに：
##   ・ばね：動作のままの向き d0 へ戻す（stiffness、1/秒²）と、回る速さの減衰（damping、1/秒）
##   ・慣性：根の世界の加速度（2 刻みの間の速さの差。なめらかにして大きさを制限）の逆向きに房の先を押す（inertia）：
##     走り出すと後ろへ、止まると前へ振れ、落ちる間は少し浮き、着地で下へ打ってから戻る。待機の息・攻撃のひねりでも根が動くので揺れる
##   ・風：走る速さ（水平）の逆向きに少し（wind。髪だけ）
##   ・振り向き：d は世界に残るので、頭が回ると遅れてから追いつく
##   ・角度の上限 limit：d0 から limit より開かない（顔・頭・体へ深く入らない）。ポーチは体の外向きの軸のまわりだけ（前後）に回る
## 刻みの速さに左右されない：揺れは骨格の更新のうち物理の刻みのもの（delta > 0。PlayerView.set_secondary で骨格の変形を
## 物理の刻みで進める）でだけ進め、親の骨の座標での回転として持つ。描画のこまの更新（delta = 0）では、その回転を今の姿勢に
## 置き直すだけ。根の速さは 2 刻みの間の位置の差から取る：描画が 30 こま/秒だと動作の姿勢は 2 刻みに 1 回しか変わらないが、
## 2 刻みの間には必ず 1 回入るので、速さ・加速度が刻みごとに跳ねない（1 刻みの差だと、動作の動きが 1 刻みおきに 2 倍・0 になる）。
## SpringBoneSimulator3D（Godot 4.5）は使わなかった：delta = 0 の更新でも速さの項で 1 歩進むので、動作を描画のこまで進める
## このゲームでは描画の速さで揺れ方が変わる。世界に対する減衰のため走る速さで房が 60〜110 度なびき、跳び始めの速い沈みで
## 150 度めくれた。角度の上限も無い（W1_ハル再構築の結果.md 8 章）。
## 調整：CHAINS（固さ・減衰・慣性・風・角度の上限）、ACCEL_*（加速度のなめらかさと上限）。
## 軽さ：骨ごとの状態は型つきの配列に持ち、親の骨の姿勢は親ごとに 1 回だけ読む。描画のこまの更新は回転を置くだけ。

## 骨の名前 → 揺れ方。stiffness：戻す強さ（1/秒²。√ が 1 秒あたりの振れの角速度。250 で約 2.5 回/秒）。damping：回る速さを
## 減らす（1/秒。2√stiffness で振れずに止まる）。inertia：加速度 1 m/秒² あたりの押し（ラジアン/秒²）。wind：走る速さ
## 1 m/秒あたりの後ろへの押し。limit：d0 からの角度の上限（ラジアン）。axis "out"：体の外向きの軸のまわりだけ回す。
## 同じ親の骨は続けて並べる（親の姿勢を 1 回だけ読む）
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

## 揺れの骨（CHAINS の順）
var bones: PackedInt32Array = []
## 最後の物理の刻みの、揺れの角度の最大（ラジアン。確かめ用）
var last_max := 0.0
## 計測（HaruMotionShots の --haru_secondary_bench）：真の間、この修飾にかかった時間（マイクロ秒）と呼ばれた回数を足していく
static var profile := false
static var prof_usec := 0
static var prof_calls := 0

# 骨ごとの設定（bones と同じ順）
var _parent: PackedInt32Array = []
var _rest: Array[Transform3D] = []
var _rest_rot: Array[Quaternion] = []
var _stiff: PackedFloat32Array = []
var _damp: PackedFloat32Array = []
var _inertia: PackedFloat32Array = []
var _wind: PackedFloat32Array = []
var _limit: PackedFloat32Array = []
var _axis: PackedVector3Array = []     # 親の骨の座標での回る軸（ZERO = どの向きにも回る）
# 骨ごとの状態：向き d・角速度 w（世界）、根の位置・速さ・なめらかにした加速度（世界）、揺れの回転（親の骨の座標）、置く回転
var _d: PackedVector3Array = []
var _w: PackedVector3Array = []
var _pos: PackedVector3Array = []
var _pos2: PackedVector3Array = []    # 2 刻み前の根の位置
var _vel: PackedVector3Array = []
var _acc: PackedVector3Array = []
var _q: Array[Quaternion] = []
var _out: Array[Quaternion] = []
var _fresh := true
var _warm := 0                          # 置き直しのあと、速さだけを取る刻みの残り（加速度の跳ねを出さない）


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
		var rest := sk.get_bone_rest(b)
		var axis := Vector3.ZERO
		if c.get("axis", "") == "out":
			# 体の縦の軸から外向き（水平）を、親の骨（腰）の座標へ直して持つ
			var g := sk.get_bone_global_rest(b)
			var out := Vector3(g.origin.x, 0.0, g.origin.z).normalized()
			axis = (sk.get_bone_global_rest(pb).basis.inverse() * out).normalized()
		s.bones.append(b)
		s._parent.append(pb)
		s._rest.append(rest)
		s._rest_rot.append(rest.basis.get_rotation_quaternion())
		s._stiff.append(float(c.stiffness))
		s._damp.append(float(c.damping))
		s._inertia.append(float(c.inertia))
		s._wind.append(float(c.wind))
		s._limit.append(float(c.limit))
		s._axis.append(axis)
		s._d.append(Vector3.UP)
		s._w.append(Vector3.ZERO)
		s._pos.append(Vector3.ZERO)
		s._pos2.append(Vector3.ZERO)
		s._vel.append(Vector3.ZERO)
		s._acc.append(Vector3.ZERO)
		s._q.append(Quaternion.IDENTITY)
		s._out.append(s._rest_rot[-1])
	return s


## 入れる・切る（PlayerView.set_secondary）
func set_enabled(on: bool) -> void:
	active = on
	last_max = 0.0
	reset()


## 揺れを止めて置き直す（読み込み・部屋の移動・復活。次の更新の姿勢から始める）
func reset() -> void:
	_fresh = true


func _process_modification_with_delta(delta: float) -> void:
	var sk := get_skeleton()
	if sk == null:
		return
	var t0 := Time.get_ticks_usec() if profile else 0
	if delta > 0.0 or _fresh:
		_advance(sk, delta)
	# 揺れの回転を置く（描画のこまの更新では、親の今の姿勢にそのまま載る）
	for i in bones.size():
		sk.set_bone_pose_rotation(bones[i], _out[i])
	if profile:
		prof_usec += Time.get_ticks_usec() - t0
		prof_calls += 1


## 1 刻み進める（物理の刻み。_fresh なら今の姿勢から始める）。_q：揺れの回転を親の骨の座標で
func _advance(sk: Skeleton3D, dt: float) -> void:
	var S := sk.global_transform
	var sb := S.basis.orthonormalized()
	var fresh := _fresh
	_fresh = false
	if fresh:
		_warm = 2
	var warm := _warm > 0 and not fresh
	if warm:
		_warm -= 1
	var k_acc := 1.0 - exp(-ACCEL_SMOOTH * dt)
	var mx := 0.0
	var cur_pb := -2
	var pg := Transform3D.IDENTITY
	var pw := Basis.IDENTITY
	var pq := Quaternion.IDENTITY
	for i in bones.size():
		if _parent[i] != cur_pb:
			cur_pb = _parent[i]
			pg = sk.get_bone_global_pose(cur_pb)
			pw = (sb * pg.basis).orthonormalized()
			pq = pw.get_rotation_quaternion()
		var g0 := pg * _rest[i]
		var pivot := S * g0.origin
		var d0 := (sb * g0.basis.y).normalized()
		if fresh:
			_d[i] = d0
			_w[i] = Vector3.ZERO
			_pos[i] = pivot
			_pos2[i] = pivot
			_vel[i] = Vector3.ZERO
			_acc[i] = Vector3.ZERO
			_q[i] = Quaternion.IDENTITY
			_out[i] = _rest_rot[i]
			continue
		var v := (pivot - _pos2[i]) / (2.0 * dt)
		var acc := _acc[i]
		if not warm:
			acc = acc.lerp((v - _vel[i]) / dt, k_acc).limit_length(ACCEL_MAX)
		_acc[i] = acc
		_vel[i] = v
		_pos2[i] = _pos[i]
		_pos[i] = pivot
		var d := _d[i]
		var w := _w[i]
		# 先を押す向き：加速度の逆向き＋走る速さの逆向きの風
		var push := -acc * _inertia[i] - Vector3(v.x, 0.0, v.z) * _wind[i]
		w += (d.cross(d0) * _stiff[i] - w * _damp[i] + d.cross(push)) * dt
		w -= d * d.dot(w)              # 骨の軸まわりのねじれは持たない
		var axis := _axis[i]
		if axis != Vector3.ZERO:
			axis = (pw * axis).normalized()
			w = axis * axis.dot(w)
		var ang := w.length() * dt
		if ang > 1e-7:
			d = Quaternion(w / (ang / dt), ang) * d
		if axis != Vector3.ZERO:
			d -= axis * axis.dot(d)
		d = d.normalized()
		# 角度の上限：それより開く向きの回る速さは捨てる
		var open := d0.angle_to(d)
		if open > _limit[i]:
			d = d0.slerp(d, _limit[i] / open).normalized()
			var out := d0.cross(d)
			if out.length() > 1e-6:
				out = out.normalized()
				w -= out * maxf(0.0, out.dot(w))
		_d[i] = d
		_w[i] = w
		mx = maxf(mx, d0.angle_to(d))
		# 揺れの回転（世界の d0 → d）を親の骨の座標へ：q = Pw⁻¹ · A · Pw
		var q := pq.inverse() * HaruPose._arc(d0, d) * pq
		_q[i] = q
		_out[i] = q * _rest_rot[i]
	if dt > 0.0:
		last_max = mx


## 揺れの骨の、今の向き（揺れのあと）と揺れない向き（親の今の姿勢 × 基準の姿勢）の角度（ラジアン）。
## 確かめ・調整用：骨格の更新の直後（Skeleton3D.skeleton_updated）に読む
func deflection(sk: Skeleton3D) -> Dictionary:
	var out := {}
	for b in bones:
		var cur := sk.get_bone_global_pose(b).basis.y.normalized()
		var base := (sk.get_bone_global_pose(sk.get_bone_parent(b)) * sk.get_bone_rest(b)).basis.y.normalized()
		out[sk.get_bone_name(b)] = cur.angle_to(base)
	return out
