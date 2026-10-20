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
	for nm in ["door", "lift_guide", "lift_cage", "lift_landing"]:
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
	h.expect(names == ["amber", "brass", "cloth", "dark", "deck", "graphite", "ivory"], "材質は 7 つ（キットの名前）：%s" % [names])
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


## 町の部屋に置いたオルド（部屋の "ordo"、RoomView が作る）：体が止まり砂の床が流れる見方、描くのは 1 つのメッシュ（面は材質の数）で影なし。
## 上段には置かない（展望台の前の地平線を船首の頭が隠すため）
func test_ordo_in_town_rooms() -> void:
	var world := World.load_manifest("res://content/world.json")
	for rid in ["ch1.mid", "ch1.lower", "ch1.opening", "ch1.upper"]:
		var root := RoomView.build(world, rid)
		h.tree.root.add_child(root)
		var o := root.get_node_or_null("Ordo") as OrdoView
		if rid == "ch1.upper":
			h.expect(o == null, "上段にはオルドを置かない")
			root.free()
			continue
		h.expect(o != null and o.body_fixed, "%s にオルドがある（体が止まり地面が流れる見方）" % rid)
		if o == null:
			root.free()
			continue
		var surfaces := o.skin_mesh.mesh.get_surface_count() if o.skin_mesh != null else 99
		h.expect(surfaces <= 6, "%s：描くのは 1 つのメッシュ（面 %d）" % [rid, surfaces])
		h.expect(o.skin_mesh != null and o.skin_mesh.cast_shadow == GeometryInstance3D.SHADOW_CASTING_SETTING_OFF, "%s：影を落とさない" % rid)
		h.expect(not o.model.visible, "%s：部品のメッシュは描かない（骨組みだけ）" % rid)
		var ank := o.leg_angles("r2")
		h.expect(not ank.is_empty(), "%s：脚が動く" % rid)
		if rid == "ch1.opening":
			h.expect(o.ground_node == null, "夜明けの甲羅は砂の床を描かない（空のカメラの砂漠は空の絵）")
		else:
			h.expect(o.ground_node != null, "%s：砂の床がある" % rid)
			var p0 := o.body.global_transform.origin
			o.advance(30.0)
			var mat := o.ground_node.material_override as ShaderMaterial
			var travel := float(mat.get_shader_parameter("travel"))
			h.expect(travel > 5.0 and absf(travel - o.travel) < 0.01, "%s：床の模様が体の進みだけ流れる（%.1f m）" % [rid, travel])
			h.expect((o.body.global_transform.origin - p0).length() < 0.001, "%s：体（町）は動かない" % rid)
		root.free()


## 下段のリフトの踊り場の「見下ろす」：部屋の外のカメラ（台本の "eye"）になり、操作が止まる
func test_ordo_lookout_event() -> void:
	var world := World.load_manifest("res://content/world.json")
	var g := GameSim.new()
	var vp := SubViewport.new()
	vp.own_world_3d = true
	vp.render_target_update_mode = SubViewport.UPDATE_DISABLED
	vp.size = Vector2i(2, 2)
	h.tree.root.add_child(vp)
	vp.add_child(g)
	g.setup({"world": world, "tuning": TestHelpers.default_tuning(), "seed": 1})
	g.load_room("ch1.lower")
	var term := {}
	for p in g.room.get("props", []):
		if p.get("id", "") == "ch1.lower.lookout":
			term = p
	h.expect(not term.is_empty() and term.get("event", "") == "ch1.ordo_legs", "踊り場に「見下ろす」の端末がある")
	g.story.start_event("ch1.ordo_legs")
	for i in 10:
		g.step(InputFrame.of({}))
	h.expect(g.cam_eye != null and (g.cam_eye as Vector3).x > 100.0, "カメラが部屋の外（左舷の外）に出る")
	h.expect(g.player_locked, "見ている間は操作が止まる")
	vp.free()


## 大きくした足（52 × 34 m）：振り出しの途中でも足の裏の四隅が地面に潜らない、同じ舷の隣の足どうしが重ならない
func test_ordo_feet_clear() -> void:
	var o := _make()
	var half := Vector2(17.0, 26.0)        # 足の裏の半分（左右・前後）
	var rest := {}
	for leg in o.legs:
		rest[leg.tag] = (leg.nodes.ankle as Node3D).global_transform.basis
	var lowest := INF
	var gap := INF
	var dt := 0.25
	for i in int(2.0 * o.cycle_s / dt):
		o.advance(dt)
		var spans := {}
		for leg in o.legs:
			var ank: Node3D = leg.nodes.ankle
			var r: Basis = ank.global_transform.basis * (rest[leg.tag] as Basis).inverse()
			var zs: Array = []
			for sx in [-1.0, 1.0]:
				for sz in [-1.0, 1.0]:
					var c: Vector3 = ank.global_transform.origin + r * Vector3(sx * half.x, -14.0, sz * half.y)
					lowest = minf(lowest, c.y - OrdoView.GROUND_Y)
					zs.append(c.z)
			spans[leg.tag] = Vector2(zs.min(), zs.max())
		for side in ["l", "r"]:
			for k in [1, 2, 3]:
				var a: Vector2 = spans["%s%d" % [side, k]]
				var b: Vector2 = spans["%s%d" % [side, k + 1]]
				gap = minf(gap, a.x - b.y)    # 1 が船首側（z が大きい）
	print("オルドの足：最も低い隅 %.2f m・隣の足の最も近いすき間 %.1f m" % [lowest, gap])
	h.expect(lowest >= -0.3, "足の裏の四隅が地面に潜らない（最も低い所 %.2f m）" % lowest)
	h.expect(gap > 2.0, "同じ舷の隣の足が重ならない（最も近い所 %.1f m）" % gap)
	o.free()


## リフトの踊り場（2026-10-20）：下段は、オルドの部品 lift_landing と同じ形の飾り town/ordo_landing（キットの汚れの層・布の揺れつき）を
## オルドと同じ所に置き、オルドの部品は骨の大きさ 0 で隠す（同じ所に 2 つ描かない）。中段・夜明けの甲羅はオルドの部品のまま。
## 下段は板の床が当たり判定の床の箱の上の面に、望遠鏡は「見下ろす」の端末の箱の中に立ち、端末の箱は描かない
func test_ordo_landing_dress() -> void:
	var world := World.load_manifest("res://content/world.json")
	for rid in ["ch1.lower", "ch1.mid", "ch1.opening"]:
		var root := RoomView.build(world, rid)
		h.tree.root.add_child(root)
		var o := root.get_node_or_null("Ordo") as OrdoView
		var dressed: bool = rid == "ch1.lower"
		var bi := o.skeleton.find_bone("lift_landing") if o != null and o.skeleton != null else -1
		h.expect(bi >= 0, "%s：踊り場はオルドの 1 つのメッシュの骨（lift_landing）" % rid)
		if bi < 0:
			root.free()
			continue
		var sc := o.skeleton.get_bone_pose_scale(bi)
		h.expect(o.landing != dressed and sc.is_equal_approx(Vector3.ZERO if dressed else Vector3.ONE),
			"%s：オルドの踊り場は%s（骨の大きさ %s）" % [rid, "隠す" if dressed else "描く", sc])
		var gi := root.get_node_or_null("Dress/town_ordo_landing") as MeshInstance3D
		var aw := root.get_node_or_null("Dress/town_ordo_landing_awning") as MeshInstance3D
		h.expect((gi != null) == dressed and (aw != null) == dressed,
			"%s：踊り場の飾り town/ordo_landing・帆布 ordo_landing_awning は%s" % [rid, "ある" if dressed else "無い"])
		if gi == null or aw == null:
			root.free()
			continue
		h.expect(aw.cast_shadow == GeometryInstance3D.SHADOW_CASTING_SETTING_ON and gi.cast_shadow == GeometryInstance3D.SHADOW_CASTING_SETTING_OFF,
			"%s：影を落とすのは帆布だけ（影の描画を増やしすぎない）" % rid)
		# 飾りとオルドの部品は同じ形・同じ所（部屋の座標の広がりが 2 cm 以内で一致）
		var part := o.parts.get("lift_landing") as Node3D
		var a := AABB()
		var first := true
		for mi in [part] + part.find_children("*", "MeshInstance3D", false, false):
			if mi is MeshInstance3D:
				var b: AABB = (mi as MeshInstance3D).global_transform * (mi as MeshInstance3D).mesh.get_aabb()
				a = b if first else a.merge(b)
				first = false
		var d: AABB = (gi.global_transform * gi.mesh.get_aabb()).merge(aw.global_transform * aw.mesh.get_aabb())
		h.expect(a.position.distance_to(d.position) < 0.02 and a.end.distance_to(d.end) < 0.02,
			"%s：飾りはオルドの踊り場と同じ所（%s / %s）" % [rid, d, a])
		# 材質：板はキットの deck（板の絵と汚れの層）、布は揺れの重み（頂点の色のアルファ < 1）
		var kit := RoomKit.load_kit("town")
		var deck_ok := false
		var swaying := 0
		for s in gi.mesh.get_surface_count():
			var m := gi.mesh.surface_get_material(s)
			if m == kit.mats.get("deck"):
				deck_ok = (m as ShaderMaterial).get_shader_parameter("albedo_tex") != null
		for s in aw.mesh.get_surface_count():
			if aw.mesh.surface_get_material(s) == kit.mats.get("flat"):
				for c in (aw.mesh.surface_get_arrays(s)[Mesh.ARRAY_COLOR] as PackedColorArray):
					if c.a < 0.99:
						swaying += 1
		h.expect(deck_ok, "%s：板の床はキットの材質 deck（板の絵）" % rid)
		h.expect(swaying > 200, "%s：日よけの布は風で揺れる（重みのある頂点 %d）" % [rid, swaying])
		if rid == "ch1.lower":
			var room := world.room(rid)
			var floor_top := -INF
			for g in room.geometry:
				if g.get("t", "box") == "box" and absf(float(g.pos[0]) - 59.45) < 0.01 and absf(float(g.pos[2]) + 4.0) < 0.01:
					floor_top = float(g.pos[1]) + float(g.size[1])
			h.expect(absf(floor_top) < 0.001 and absf(gi.global_transform.origin.y + 1.5) < 0.001,
				"下段：踊り場の床の上の面（オルドの背の 1.5 m 上）が当たり判定の床の箱の上の面（%.2f）" % floor_top)
			var term := {}
			for p in room.props:
				if p.get("id", "") == "ch1.lower.lookout":
					term = p
			h.expect(term.get("hide", false), "下段：「見下ろす」の端末の箱は描かない（踊り場の望遠鏡）")
		root.free()


## 足が着いた・浮いた知らせ（映画のような場面の足音・砂ぼこり。CineDirector）：1 周で 8 本とも 1 回ずつ浮いて着く。
## 知らせの位置は足の裏の真ん中の地面（足首の真下、地面の高さ）で、そのとき足は着いている
func test_ordo_foot_events() -> void:
	# 周期の 0.245（どの足も振り出していない所）から 1 周
	var o := OrdoView.new()
	o.body_fixed = true
	o.phase = 0.245
	h.tree.root.add_child(o)
	var lifts := {}
	var plants := {}
	var bad := []
	o.foot_lifted.connect(func(tag: String, _at: Vector3): lifts[tag] = int(lifts.get(tag, 0)) + 1)
	o.foot_planted.connect(func(tag: String, at: Vector3):
		plants[tag] = int(plants.get(tag, 0)) + 1
		var ank: Vector3 = (o.legs.filter(func(l): return l.tag == tag)[0].nodes.ankle as Node3D).global_transform.origin
		if absf(at.y - o.ground_y()) > 0.01 or Vector2(at.x - ank.x, at.z - ank.z).length() > 0.01 or not o.is_planted(tag):
			bad.append("%s %s / %s" % [tag, at, ank]))
	var dt := 1.0 / 30.0
	for i in int(o.cycle_s / dt):
		o.advance(dt)
	h.expect(lifts.size() == 8 and lifts.values().all(func(n): return n == 1), "1 周で 8 本とも 1 回ずつ浮く（%s）" % lifts)
	h.expect(plants.size() == 8 and plants.values().all(func(n): return n == 1), "1 周で 8 本とも 1 回ずつ着く（%s）" % plants)
	h.expect(bad.is_empty(), "着いた知らせの位置は足首の真下の地面（%s）" % [bad])
	# 地面の高さ：体が止まる見方では、地面が体の上下の逆に動く（歩きの低さの分だけ上）
	h.near(o.ground_y(), OrdoView.GROUND_Y - o.body_h, 0.001, "地面の高さ = -120 − 体の上下")
	o.free()


## 動力が切れて止まる演出（cine_stop。停止の場面の外の舞台のオルド）：振り出していた足が STOP_DROP_S 秒で落ちて着き、着いている足は滑らない。
## 体はなめらかに止まり（もう進まない）、沈んで一度行き過ぎてから収まる。関節は可動域の中。ゲームの停止の姿勢（set_walking(false)）は前と同じ
func test_ordo_cine_stop() -> void:
	var o := _make(true, true)
	o.phase = 0.088
	o._init_gait()
	o.advance(4.5)
	var swinging := o.legs.filter(func(l): return l.swinging).map(func(l): return l.tag)
	h.expect(swinging.has("l2") and swinging.has("r1"), "止める前：左舷 l2・右舷 r1 が振り出しの途中（%s）" % [swinging])
	var landed := {}
	o.foot_planted.connect(func(tag: String, _at: Vector3): landed[tag] = o._stop_t)
	o.cine_stop()
	# 地面に固定した座標（体が止まる見方：地面は体に対して後ろへ travel、上下へ -body_h ずれる）で、着いた足が動かないか
	var anchor := {}
	var worst := 0.0
	var lim := {"roll": 0.0, "shoulder": 0.0, "ankle": 0.0, "flex_lo": INF, "flex_hi": -INF}
	var dt := 1.0 / 60.0
	var travel_mid := -1.0
	var sink_max := 0.0
	for i in int(8.0 / dt):
		o.advance(dt)
		for leg in o.legs:
			var g: Vector3 = (leg.nodes.ankle as Node3D).global_transform.origin + Vector3(0, o.body_h, o.travel)
			if not leg.swinging:
				if not anchor.has(leg.tag):
					anchor[leg.tag] = g
				worst = maxf(worst, (g - anchor[leg.tag] as Vector3).length())
			for k in ["roll", "shoulder", "ankle"]:
				lim[k] = maxf(lim[k], absf(float(leg.angles[k])))
			lim.flex_lo = minf(lim.flex_lo, float(leg.angles.flex))
			lim.flex_hi = maxf(lim.flex_hi, float(leg.angles.flex))
		if travel_mid < 0.0 and o._stop_t >= OrdoView.STOP_DECEL_S + 0.2:
			travel_mid = o.travel
		sink_max = maxf(sink_max, o._sink)
	h.expect(landed.has("l2") and landed.has("r1") and absf(float(landed.get("l2", 0.0)) - OrdoView.STOP_DROP_S) < 0.05,
		"振り出していた足は %.1f 秒で落ちて着く（%s）" % [OrdoView.STOP_DROP_S, landed])
	h.expect(o.legs.all(func(l): return not l.swinging and l.parked) and o.cine_stopping(), "8 本とも着いて止まる")
	h.expect(worst <= TOL, "着いた足は滑らない（最大 %.3f m）" % worst)
	h.expect(lim.shoulder <= 22.0 and lim.roll <= 5.0 and lim.ankle <= 16.0 and lim.flex_lo >= -0.5 and lim.flex_hi <= 35.0,
		"関節は可動域の中（肩 %.1f・横振り %.1f・足首 %.1f・膝の曲げ %.1f〜%.1f 度）" % [lim.shoulder, lim.roll, lim.ankle, lim.flex_lo, lim.flex_hi])
	h.expect(travel_mid >= 0.0 and absf(o.travel - travel_mid) < 0.001 and o.speed == 0.0, "体は %.1f 秒で止まり、もう進まない" % OrdoView.STOP_DECEL_S)
	h.expect(sink_max > OrdoView.STOP_SINK_M + 0.05 and absf(o._sink - OrdoView.STOP_SINK_M) < 0.03 and absf(o._sink_v) < 0.05,
		"体が沈み、一度行き過ぎてから収まる（最も深く %.2f m → %.2f m）" % [sink_max, o._sink])
	o.free()
	# ゲームの停止の姿勢は前のまま（肩の真下に 8 本・関節 0 度・元の高さ）
	var o2 := _make(false, true)
	var worst2 := 0.0
	for leg in o2.legs:
		for k in ["roll", "shoulder", "knee", "ankle"]:
			worst2 = maxf(worst2, absf(float(leg.angles[k])))
	h.expect(o2.is_stopped() and o2.body_h == 0.0 and worst2 < 0.3, "ゲームの停止の姿勢は前と同じ（関節 最大 %.2f 度）" % worst2)
	o2.free()


## 背の上の町の灯（TownLights）：町の影絵の壁から選んだ窓の灯と街灯・段の縁・塔の灯。町の上に収まり、描画は 1 回（MultiMesh）、
## 明るさ・消えた割合・ちらつきをシェーダーへ渡せる
func test_town_lights() -> void:
	var o := _make(true, true)
	var tl := o.add_town_lights()
	await h.tree.process_frame
	var pts := TownLights.points()
	h.expect(tl.count() == pts.size() and pts.size() >= 150, "町の灯は %d" % pts.size())
	var outside := pts.filter(func(p):
		var v: Vector3 = p[0]
		return absf(v.x) > 56.0 or v.z < -118.0 or v.z > 100.0 or v.y < 0.5 or v.y > 50.0)
	h.expect(outside.is_empty(), "灯は背の上の町の中（舷の外の縁 ±55 m の内。外：%d）" % outside.size())
	h.expect(tl.get_parent() == o.skeleton and tl.multimesh.instance_count == pts.size() and tl.material_override != null,
		"体の骨の子の 1 つの MultiMesh（描画 1 回）")
	tl.power = 0.7
	tl.out = 0.4
	tl.flicker = 0.3
	tl.apply()
	var m := tl.material_override as ShaderMaterial
	h.expect(is_equal_approx(float(m.get_shader_parameter("power")), 0.7) and is_equal_approx(float(m.get_shader_parameter("out_amount")), 0.4)
		and is_equal_approx(float(m.get_shader_parameter("flicker")), 0.3), "明るさ・消えた割合・ちらつきをシェーダーへ渡す")
	h.expect(o.add_town_lights() == tl, "2 回呼んでも 1 つ")
	o.free()

