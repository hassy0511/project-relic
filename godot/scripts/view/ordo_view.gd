class_name OrdoView
extends Node3D
## 巡礼機オルド（全長 400 m、町を背に載せて歩く機械）の見た目と、手続きの歩き方（閂と同じく、部品を毎フレーム回す。動作のクリップは無い）。
## モデル：ordo.glb（tools/blender/recon/ordo.py、npm run ordo:build）。結果の文書：docs/art_orders/W2_オルド3D化の結果.md。
## 座標（このノードの中）：原点 = 背の歩行面（町を載せる平らな面）の真ん中で y = 0、+Z が船首、+X が左舷、地面は y = -120。
##   背の面は |x| ≤ 56・z = -118〜+100 で平ら（町の約 180 × 90 m が載る）。旧遠景 ordo_far と同じ原点なので、町の中段の部屋では
##   ordo_far と同じ [0, -6.5, 0] に置けば、背の面が下の段の床の 1.5 m 下に来る。
## 部品（原点 = 回転の軸、ローカル +X = 軸。「元の姿勢 * Basis(RIGHT, 角度)」で回す）：
##   leg_<l|r><1..4>_roll（肩の横振り。軸 = 船首の向き）→ _shoulder（肩のピッチ。軸 +X）→ _knee → _ankle。
##   l = 左舷（+X）、r = 右舷（-X、昇降リフトの側）。1〜4 は船首から（取付は全長の 15・38・62・85 %）。
##   1・2 は膝が船尾へ、3・4 は船首へ曲がる（絵の側面図）。door（禁足扉）・lift_guide・lift_cage は下へ滑る（ローカル +X = 下）。
## 歩き方（spec_ordo_3d.md の「関節と歩行」）：右の列は 1 → 3 → 2 → 4 の順に足を振り出し、左の列は半周期ずらす。
##   1 周 cycle_s 秒（既定 80 秒。1 本の振り出しは swing_frac × 80 = 19.2 秒）。同時に浮く足は最大 2 本（右と左で 1 本ずつ）。
##   地面に着いている足は動かない：着いた所（地面の上の位置）を覚え、体から見た位置を毎回逆算して関節の角度を解く（2 節の IK）。
##   体は歩くあいだ crouch_m だけ低く、bob_m だけゆっくり上下する（振り出しの 4 拍ごとに 1 回）。
## 止まる：set_walking(false) で歩幅を 0 へ落とし、全部の足が肩の真下に着いたら体を元の高さへ戻す（停止の姿勢 = モデルの元の姿勢。
##   8 本とも接地、関節は全部 0 度）。第 1 章の停止の場面で最初から止まっているときは set_walking(false, true)。
## 見方は 2 つ：
##   body_fixed = false（既定）：地面が止まっていて体が進む。子の "ordo" が +Z へ travel だけ進み、上下する（遠くから見る場面）。
##   body_fixed = true ：体（町）が止まっていて地面が動く（町の縁から見下ろす場面）。地面に ground_offset() を足す。
## 軽さ：毎フレーム、脚 8 本 × 関節 4 つの Transform を置くだけ（三角関数が十数回）。

const MODEL_PATH := "res://assets/models/ordo.glb"
const LEGS := ["l1", "l2", "l3", "l4", "r1", "r2", "r3", "r4"]
## 振り出しを始める時刻（1 周の割合）。右の列：1 → 3 → 2 → 4、左の列は半周期ずらす
const PHASE := {"r1": 0.0, "r3": 0.25, "r2": 0.5, "r4": 0.75, "l1": 0.5, "l3": 0.75, "l2": 0.0, "l4": 0.25}
## 可動域（度。spec の暫定値）：肩のピッチ ±22、肩の横振り ±5、膝の曲げ 0〜35（元の姿勢から曲げる向きが +）、足首 ±16
const LIMITS := {"shoulder": 22.0, "roll": 5.0, "knee_min": 0.0, "knee_max": 35.0, "ankle": 16.0}
const GROUND_Y := -120.0
const ANKLE_SWING_MAX := 15.0    ## 浮いている足の足首の角の上限（度。可動域 ±16 の手前）

@export var cycle_s := 80.0      ## 1 周（8 本が 1 回ずつ振り出す）の秒数
@export var swing_frac := 0.24   ## 振り出しの長さ（1 周の割合。0.24 × 80 秒 = 19.2 秒。0.25 より小さいと、同時に浮くのは 2 本まで）
@export var step_m := 28.0       ## 着いている間に足が体に対して後ろへ動く距離（= 体の進む速さ × 接地の時間）
@export var lift_m := 6.0        ## 振り出しで足を上げる高さ
@export var roll_deg := 2.5      ## 振り出しで脚を外へ振る角（肩の横振り）
@export var toe_deg := 9.0       ## 振り出しの途中でつま先を下げる角
@export var crouch_m := 2.5      ## 歩くあいだ体を下げる高さ（膝を元の姿勢より曲げたまま歩く）
@export var bob_m := 0.5         ## 体の上下（片振幅）
@export var body_fixed := false
@export var walking := true

var model: Node3D
var body: Node3D
var travel := 0.0                ## 体が進んだ距離（m、+Z）
var phase := 0.0                 ## 歩きの周期の位置（0〜1）
var speed := 1.0                 ## 歩幅の割合（0 = 止まる、1 = 歩く）
var body_h := 0.0                ## 体の高さの元の姿勢からのずれ（m）
var parts := {}                  ## 部品の名前 → Node3D（door・lift_guide・lift_cage・body など）
var legs: Array = []             ## 脚ごとの辞書（_setup_leg）
var _crouch := 1.0
var _rest := {}


func _ready() -> void:
	if not ResourceLoader.exists(MODEL_PATH):
		push_warning("オルドのモデルが無い: %s" % MODEL_PATH)
		return
	model = (load(MODEL_PATH) as PackedScene).instantiate() as Node3D
	model.name = "ordo"
	add_child(model)
	body = model.find_child("body", true, false) as Node3D
	for n in model.find_children("*", "Node3D", true, false):
		_rest[n.name] = (n as Node3D).transform
	for nm in ["body", "door", "lift_guide", "lift_cage"]:
		parts[nm] = model.find_child(nm, true, false)
	for tag in LEGS:
		var leg := _setup_leg(tag)
		if not leg.is_empty():
			legs.append(leg)
	if walking:
		_init_gait()
	else:
		set_walking(false, true)
	_apply()


## 歩いている途中の姿勢から始める：各脚を、周期の今の位置の定常の歩きの位置に置く（振り出し中なら後ろ → 前の途中）
func _init_gait() -> void:
	speed = 1.0
	_crouch = 1.0
	for leg in legs:
		var p := fposmod(phase - float(leg.offset), 1.0)
		leg.p_prev = p
		leg.parked = false
		if p < swing_frac:
			leg.swinging = true
			leg["from"] = -0.5 * step_m
			leg.to = 0.5 * step_m
			var s := p / swing_frac
			leg.sigma = s
			leg.off = lerpf(-0.5 * step_m, 0.5 * step_m, s * s * (3.0 - 2.0 * s))
			leg.lift = lift_m * pow(sin(PI * s), 1.3)
		else:
			var tau := (p - swing_frac) / (1.0 - swing_frac)
			leg.swinging = false
			leg.off = 0.5 * step_m - step_m * tau
			leg.planted = travel + float(leg.off)
	body_h = -crouch_m + bob_m * sin(TAU * 4.0 * phase)


## 脚 1 本の情報：関節のノード・元の姿勢・体から見た関節の位置（肩 s0・膝 k0・足首 a0）・膝の曲がる向き
func _setup_leg(tag: String) -> Dictionary:
	var names := ["roll", "shoulder", "knee", "ankle"]
	var nodes := {}
	for k in names:
		var n := model.find_child("leg_%s_%s" % [tag, k], true, false) as Node3D
		if n == null:
			push_warning("オルドの脚の部品が無い: leg_%s_%s" % [tag, k])
			return {}
		nodes[k] = n
	var s0 := _in_body(nodes.shoulder)
	var k0 := _in_body(nodes.knee)
	var a0 := _in_body(nodes.ankle)
	var sa := _yz(a0 - s0)
	var sk := _yz(k0 - s0)
	var leg := {
		"tag": tag, "side": 1.0 if tag.begins_with("l") else -1.0, "nodes": nodes,
		"s0": s0, "k0": k0, "a0": a0,
		# 横から見た（YZ 面の）長さ。膝・足首は肩より外へ開いている（x）が、ピッチの軸は x に平行なので x は角度に効かない
		"l1": _yz(k0 - s0).length(), "l2": _yz(a0 - k0).length(),
		"knee_sign": signf(sa.angle_to(sk)),
		"inner0": _yz(s0 - k0).angle_to(_yz(a0 - k0)),
		"offset": PHASE[tag],
		"off": 0.0, "planted": 0.0, "swinging": false, "from": 0.0, "to": 0.0, "parked": false, "p_prev": 1.0,
		"lift": 0.0, "sigma": 0.0,
		"angles": {"roll": 0.0, "shoulder": 0.0, "knee": 0.0, "ankle": 0.0, "flex": 0.0},
	}
	return leg


## ノードの原点の位置（体のノードから見た座標。元の姿勢のとき）
func _in_body(n: Node3D) -> Vector3:
	var xf := Transform3D.IDENTITY
	var cur: Node = n
	while cur != null and cur != body:
		xf = (cur as Node3D).transform * xf
		cur = cur.get_parent()
	return xf.origin


static func _yz(v: Vector3) -> Vector2:
	return Vector2(v.y, v.z)


func _process(delta: float) -> void:
	if model == null:
		return
	advance(delta)


## 時間を進める（テスト・撮影はこれを直接呼ぶ）
func advance(dt: float) -> void:
	if legs.is_empty():
		return
	var target := 1.0 if walking else 0.0
	speed = move_toward(speed, target, dt / cycle_s)
	var t_stance := cycle_s * (1.0 - swing_frac)
	var v := speed * step_m / t_stance
	travel += v * dt
	var all_parked := true
	for leg in legs:
		all_parked = all_parked and leg.parked
	if not (all_parked and target == 0.0):
		phase = fposmod(phase + dt / cycle_s, 1.0)
	for leg in legs:
		_step_leg(leg)
	# 体の低さ：どれかの足がまだ動くなら歩きの高さ、全部の足が肩の真下で止まったら元の高さへ（8 秒で）
	var any_active := false
	for leg in legs:
		any_active = any_active or not leg.parked
	_crouch = move_toward(_crouch, 1.0 if (any_active or walking) else 0.0, dt / 8.0)
	body_h = -crouch_m * _crouch + bob_m * _crouch * sin(TAU * 4.0 * phase)
	_apply()


func _step_leg(leg: Dictionary) -> void:
	var p := fposmod(phase - float(leg.offset), 1.0)
	var started: bool = p < float(leg.p_prev) and p < swing_frac
	leg.p_prev = p
	var cur_off: float = (float(leg.planted) - travel) if not leg.swinging else float(leg.off)
	if started and not leg.swinging:
		var at_rest := absf(cur_off) < 0.05
		if walking or not at_rest:
			leg.swinging = true
			leg.parked = false
			leg["from"] = cur_off
			leg.to = 0.5 * step_m * speed
		else:
			leg.parked = true
	if leg.swinging and p < swing_frac:
		var s := p / swing_frac
		leg.sigma = s
		var e := s * s * (3.0 - 2.0 * s)
		leg.off = lerpf(float(leg["from"]), float(leg.to), e)
		leg.lift = lift_m * pow(sin(PI * s), 1.3)
	else:
		if leg.swinging:
			# 着いた：地面の上の位置を覚える
			leg.swinging = false
			leg.planted = travel + float(leg.to)
		leg.sigma = 0.0
		leg.lift = 0.0
		leg.off = float(leg.planted) - travel


## 関節の角度を解いて置く
func _apply() -> void:
	if body == null:
		return
	if body_fixed:
		model.position = Vector3.ZERO
	else:
		model.position = Vector3(0.0, body_h, travel)
	for leg in legs:
		_solve(leg)


func _solve(leg: Dictionary) -> void:
	var s0: Vector3 = leg.s0
	var a0: Vector3 = leg.a0
	var k0: Vector3 = leg.k0
	var l1: float = leg.l1
	var l2: float = leg.l2
	# 体から見た足首の目標：地面は体に対して -body_h だけずれる
	var a := a0 + Vector3(0.0, -body_h + float(leg.lift), float(leg.off))
	var d := _yz(a - s0)
	var dl := clampf(d.length(), absf(l1 - l2) + 0.01, l1 + l2 - 0.01)
	var al := acos(clampf((l1 * l1 + dl * dl - l2 * l2) / (2.0 * l1 * dl), -1.0, 1.0))
	var kdir := d.normalized().rotated(float(leg.knee_sign) * al)
	var k2 := _yz(s0) + kdir * l1
	var a2 := _yz(s0) + d.normalized() * dl
	var th_s := _yz(k0 - s0).angle_to(k2 - _yz(s0))
	var th_k := _yz(a0 - k0).angle_to(a2 - k2) - th_s
	var sig: float = leg.sigma
	var toe := -deg_to_rad(toe_deg) * sin(PI * sig) if leg.swinging else 0.0
	var th_a := toe - th_s - th_k
	if leg.swinging:
		# 浮いている足は、すねの振れを足首で全部は打ち消さない（可動域の手前で止め、足が少し傾く。絵の歩き方と同じ）。
		# 着く前に膝が戻るので、着くときは水平
		var lim := deg_to_rad(ANKLE_SWING_MAX)
		th_a = clampf(th_a, -lim, lim)
	var th_r := float(leg.side) * deg_to_rad(roll_deg) * pow(sin(PI * sig), 1.5) if leg.swinging else 0.0
	var inner := (_yz(s0) - k2).angle_to(a2 - k2)
	var flex := absf(float(leg.inner0)) - absf(inner)
	var n: Dictionary = leg.nodes
	_rot(n.roll, th_r)
	_rot(n.shoulder, th_s)
	_rot(n.knee, th_k)
	_rot(n.ankle, th_a)
	leg.angles = {"roll": rad_to_deg(th_r), "shoulder": rad_to_deg(th_s), "knee": rad_to_deg(th_k),
		"ankle": rad_to_deg(th_a), "flex": rad_to_deg(flex)}


func _rot(n: Node3D, ang: float) -> void:
	var r: Transform3D = _rest[n.name]
	n.transform = Transform3D(r.basis * Basis(Vector3.RIGHT, ang), r.origin)


## 歩く・止まる。immediate：すぐに停止の姿勢（全部の足が肩の真下に着いた元の姿勢）にする
func set_walking(on: bool, immediate := false) -> void:
	walking = on
	if immediate and not on:
		speed = 0.0
		_crouch = 0.0
		body_h = 0.0
		for leg in legs:
			leg.swinging = false
			leg.parked = true
			leg.planted = travel
			leg.off = 0.0
			leg.lift = 0.0
			leg.sigma = 0.0
		_apply()


## 止まっているか（全部の足が肩の真下に着き、体が元の高さ）
func is_stopped() -> bool:
	for leg in legs:
		if not leg.parked:
			return false
	return _crouch <= 0.0


## body_fixed のとき、地面に足すずれ（体から見て地面が後ろへ流れ、体の上下の逆に動く）
func ground_offset() -> Vector3:
	return Vector3(0.0, -body_h, -travel)


## 脚の関節の今の角度（度）：{ "roll", "shoulder", "knee", "ankle", "flex"（膝の曲げ。元の姿勢から +） }
func leg_angles(tag: String) -> Dictionary:
	for leg in legs:
		if leg.tag == tag:
			return leg.angles
	return {}


## 足が地面に着いているか（振り出しの途中でない）
func is_planted(tag: String) -> bool:
	for leg in legs:
		if leg.tag == tag:
			return not leg.swinging
	return false


## 禁足扉を開ける（0〜30 m 下へ）・リフトのガイドとかごを下ろす（m）
func set_door_open(m: float) -> void:
	_slide("door", clampf(m, 0.0, 30.0))


func set_lift(guide_m: float, cage_m: float) -> void:
	_slide("lift_guide", maxf(guide_m, 0.0))
	_slide("lift_cage", maxf(cage_m, 0.0))


func _slide(nm: String, m: float) -> void:
	var n := parts.get(nm) as Node3D
	if n == null:
		return
	var r: Transform3D = _rest[nm]
	n.transform = Transform3D(r.basis, r.origin + r.basis.x * m)


## 材質をキット（content/kits/<id>.json の "materials"）の同じ名前の材質に替える（ivory・graphite・brass・cloth・amber）。
## 汚れの層をあとで足すとき用（モデルの UV は部品の原点からの m）
func apply_kit(kit_id: String) -> int:
	var kit := RoomKit.load_kit(kit_id)
	var mats: Dictionary = kit.get("mats", {})
	var n := 0
	if model == null:
		return 0
	for mi in model.find_children("*", "MeshInstance3D", true, false):
		var m := (mi as MeshInstance3D).mesh
		for s in m.get_surface_count():
			var mat := m.surface_get_material(s)
			if mat != null and mats.has(mat.resource_name):
				(mi as MeshInstance3D).set_surface_override_material(s, mats[mat.resource_name])
				n += 1
	return n
