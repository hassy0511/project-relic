extends RefCounted
## 巡礼機オルド（OrdoView・ordo.glb）のテスト：モデルが読める（材質はキットの名前）、歩くあいだ関節が可動域（spec の暫定値）の中、
## 着いている足が地面の上で動かない（許す ±5 cm）、止めると 8 本とも肩の真下に着いた停止の姿勢になる、体が止まって地面が動く見方。

var h: TestHelpers

const TOL := 0.05   # 着いている足の動き（m）


func _init(helpers: TestHelpers) -> void:
	h = helpers


func _make(walking := true, body_fixed := false) -> OrdoView:
	var o := OrdoView.new()
	o.walking = walking
	o.body_fixed = body_fixed
	h.tree.root.add_child(o)
	return o


func test_ordo_model_loads() -> void:
	var o := _make()
	h.expect(o.model != null and o.body != null, "ordo.glb が読める（body がある）")
	h.expect(o.legs.size() == 8, "脚が 8 本（%d）" % o.legs.size())
	for nm in ["door", "lift_guide", "lift_cage"]:
		h.expect(o.parts.get(nm) != null, "部品 %s がある" % nm)
	var tri := 0
	var mats := {}
	for mi in o.model.find_children("*", "MeshInstance3D", true, false):
		var m := (mi as MeshInstance3D).mesh
		for s in m.get_surface_count():
			tri += (m.surface_get_arrays(s)[Mesh.ARRAY_INDEX] as PackedInt32Array).size() / 3
			var mat := m.surface_get_material(s)
			mats[mat.resource_name if mat else "?"] = true
	h.expect(tri > 10000 and tri <= 60000, "三角形が 6 万以内（%d）" % tri)
	var names := mats.keys()
	names.sort()
	h.expect(names == ["amber", "brass", "cloth", "graphite", "ivory"], "材質は 5 つ（キットの名前）：%s" % [names])
	# 材質の名前が町のキットと同じなので、全部の面をキットの材質（あとで汚れの層を足す所）に替えられる
	var surfaces := 0
	for mi in o.model.find_children("*", "MeshInstance3D", true, false):
		surfaces += (mi as MeshInstance3D).mesh.get_surface_count()
	var swapped := o.apply_kit("town")
	h.expect(swapped == surfaces, "全部の面をキット town の同じ名前の材質に替えられる（%d / %d）" % [swapped, surfaces])
	# 元の姿勢：足の裏が地面（y = -120）、肩の軸が地面から 85 m
	var leg: Dictionary = o.legs[0]
	h.expect(absf(float(leg.s0.y) - (OrdoView.GROUND_Y + 85.0)) < 0.01, "肩の軸が地面から 85 m（%.2f）" % (float(leg.s0.y) - OrdoView.GROUND_Y))
	o.free()


## 2 周歩かせて、関節の角度の最大・最小を調べる
func test_ordo_walk_within_limits() -> void:
	var o := _make()
	var mx := {"roll": 0.0, "shoulder": 0.0, "ankle": 0.0}
	var flex_lo := INF
	var flex_hi := -INF
	var dt := 0.25
	var steps := int(2.0 * o.cycle_s / dt)
	var swings := 0
	var max_swinging := 0
	for i in steps:
		o.advance(dt)
		var n_sw := 0
		for leg in o.legs:
			var a: Dictionary = leg.angles
			for k in mx:
				mx[k] = maxf(mx[k], absf(float(a[k])))
			flex_lo = minf(flex_lo, float(a.flex))
			flex_hi = maxf(flex_hi, float(a.flex))
			if leg.swinging:
				n_sw += 1
		max_swinging = maxi(max_swinging, n_sw)
		swings += n_sw
	var L := OrdoView.LIMITS
	h.expect(mx.shoulder <= L.shoulder, "肩のピッチが ±%d 度の中（最大 %.1f）" % [L.shoulder, mx.shoulder])
	h.expect(mx.roll <= L.roll, "肩の横振りが ±%d 度の中（最大 %.1f）" % [L.roll, mx.roll])
	h.expect(mx.ankle <= L.ankle, "足首が ±%d 度の中（最大 %.1f）" % [L.ankle, mx.ankle])
	h.expect(flex_lo >= L.knee_min - 0.01 and flex_hi <= L.knee_max, "膝の曲げが %d〜%d 度の中（%.1f〜%.1f）" % [L.knee_min, L.knee_max, flex_lo, flex_hi])
	h.expect(swings > 0 and max_swinging <= 2, "足を振り出す（同時に浮くのは 2 本まで：%d）" % max_swinging)
	h.expect(o.travel > 50.0, "前へ進む（2 周で %.1f m）" % o.travel)
	o.free()


## 地面が止まっている見方で、着いている足（足首の円板の中心）が動かない
func test_ordo_planted_feet_stay() -> void:
	var o := _make()
	var anchor := {}
	var worst := 0.0
	var worst_tag := ""
	var dt := 0.2
	var planted_frames := 0
	for i in int(1.5 * o.cycle_s / dt):
		o.advance(dt)
		for leg in o.legs:
			var tag: String = leg.tag
			var ank: Node3D = leg.nodes.ankle
			var p := ank.global_transform.origin
			if o.is_planted(tag):
				planted_frames += 1
				if not anchor.has(tag):
					anchor[tag] = p
				var d := (p - anchor[tag] as Vector3).length()
				if d > worst:
					worst = d
					worst_tag = tag
			else:
				anchor.erase(tag)
	h.expect(planted_frames > 1000, "着いている足を調べた（%d こま）" % planted_frames)
	h.expect(worst <= TOL, "着いている足が動かない（最大 %.3f m、%s）" % [worst, worst_tag])
	# 足の裏の高さ：着いている足首の円板の中心は、元の姿勢と同じ高さ（地面から 14 m）
	var dy := 0.0
	for leg in o.legs:
		if o.is_planted(leg.tag):
			dy = maxf(dy, absf((leg.nodes.ankle as Node3D).global_transform.origin.y - float(leg.a0.y)))
	h.expect(dy <= TOL, "着いている足は地面の高さ（ずれ %.3f m）" % dy)
	o.free()


## 止めると、足を 1 本ずつ肩の真下へ置き直して、停止の姿勢（関節が全部 0 度、体が元の高さ）になる
func test_ordo_stop_pose() -> void:
	var o := _make()
	o.advance(13.0)
	o.set_walking(false)
	var dt := 0.25
	var t := 0.0
	while t < 4.0 * o.cycle_s and not o.is_stopped():
		o.advance(dt)
		t += dt
	h.expect(o.is_stopped(), "止まる（%.0f 秒）" % t)
	var worst := 0.0
	for leg in o.legs:
		for k in ["roll", "shoulder", "knee", "ankle"]:
			worst = maxf(worst, absf(float(leg.angles[k])))
	h.expect(worst < 0.3, "停止の姿勢は関節が全部ほぼ 0 度（最大 %.2f 度）" % worst)
	h.expect(absf(o.body_h) < 0.01, "体が元の高さ（%.3f m）" % o.body_h)
	var still := o.travel
	o.advance(10.0)
	h.expect(absf(o.travel - still) < 0.001, "止まったら進まない")
	# すぐに停止の姿勢
	var o2 := _make(false)
	h.expect(o2.is_stopped() and o2.body_h == 0.0, "最初から止まった姿勢にできる")
	o.free()
	o2.free()


## 体が止まって地面が動く見方（町の縁から見下ろす場面）：体は動かず、地面のずれが進んだ距離と逆
func test_ordo_body_fixed() -> void:
	var o := _make(true, true)
	var p0 := o.body.global_transform.origin
	for i in 100:
		o.advance(0.5)
	h.expect((o.body.global_transform.origin - p0).length() < 0.001, "体が動かない")
	var g := o.ground_offset()
	h.expect(g.z < -10.0 and absf(g.z + o.travel) < 0.001, "地面が後ろへ流れる（%.1f m）" % g.z)
	o.free()
