extends RefCounted
## 部屋のキット（RoomKit）のテスト：キットの部屋が読める、無い部品・無いキットで落ちない、hide の形も当たり判定は残る、
## キットの無い部屋は今までどおり。書き方は docs/design/42_コンテンツの書き方.md 14 章。

var h: TestHelpers


func _init(helpers: TestHelpers) -> void:
	h = helpers


func _room(extra: Dictionary) -> Dictionary:
	var r := {
		"geometry": [
			{"t": "shell", "pos": [0, 0, 0], "size": [12, 6, 12], "ceiling": true},
			{"t": "box", "pos": [3, 0, 0], "size": [2, 1, 2]},
		],
		"markers": {"start": {"pos": [0, 0, -4], "yaw": 0}},
		"props": [], "triggers": [], "enemies": [], "checkpoints": [], "playerStart": "start",
	}
	r.merge(extra, true)
	return r


func _world(room: Dictionary) -> World:
	return World.from_dict({"start": {"room": "k.a", "spawn": "start"}, "areas": [{"id": "k", "name": "キット", "rooms": {"a": room}}]})


func _find(n: Node, cls: String) -> Array:
	var out := []
	if n.is_class(cls):
		out.append(n)
	for c in n.get_children():
		out.append_array(_find(c, cls))
	return out


func _verts(mi: MeshInstance3D) -> int:
	var n := 0
	for s in mi.mesh.get_surface_count():
		n += (mi.mesh.surface_get_arrays(s)[Mesh.ARRAY_VERTEX] as PackedVector3Array).size()
	return n


func test_kit_room_loads() -> void:
	var w := _world(_room({"kit": "ruins_b1", "dress": [
		{"part": "ruins/b1_pillar", "pos": [-5, 0, -5]},
		{"part": "ruins/b1_pillar", "pos": [-5, 0, 0], "count": 3, "step": [0, 0, 2]},
		{"part": "ruins/b1_wall", "pos": [0, 0, 6], "yaw": 180},
	]}))
	var root := RoomView.build(w, "k.a")
	h.expect(not root.has_meta("missing_kit"), "キット ruins_b1 が読める")
	var surf := root.get_node_or_null("KitSurfaces") as MeshInstance3D
	h.expect(surf != null and surf.mesh.get_surface_count() >= 4, "床・壁・天井・縁取りの面ができる（%d）" % (surf.mesh.get_surface_count() if surf else -1))
	if surf:
		var ok := true
		for s in surf.mesh.get_surface_count():
			ok = ok and surf.mesh.surface_get_material(s) is ShaderMaterial
		h.expect(ok, "面にキットの材質が付く")
	var missing: Array = root.get_meta("missing_parts", ["?"])
	h.expect(missing.is_empty(), "部品がそろっている（足りない：%s）" % [missing])
	var mm := _find(root, "MultiMeshInstance3D")
	h.expect(mm.size() == 1 and (mm[0] as MultiMeshInstance3D).multimesh.instance_count == 4, "同じ部品は 1 つの MultiMesh にまとまる（count・step を含めて 4 本）")
	var single := _find(root.get_node("Dress"), "MeshInstance3D")
	h.expect(single.size() == 1, "1 つだけの部品はふつうのメッシュ")
	# 同じキットの材質は部屋をまたいで共有（作り直さない）
	var root2 := RoomView.build(w, "k.a")
	var surf2 := root2.get_node("KitSurfaces") as MeshInstance3D
	h.expect(surf2.mesh.surface_get_material(0) == surf.mesh.surface_get_material(0), "キットの材質は共有される")
	root.free()
	root2.free()


func test_kit_unknown_parts_and_kit() -> void:
	var w := _world(_room({"kit": "no_such_kit", "dress": [
		{"part": "ruins/no_such_part", "pos": [0, 0, 0]},
		{"part": "../../etc", "pos": [0, 0, 0]},
	]}))
	var root := RoomView.build(w, "k.a")
	h.expect(root.get_meta("missing_kit", "") == "no_such_kit", "無いキットは記録され、落ちない")
	h.expect(root.get_node_or_null("KitSurfaces") != null, "無いキットでも地形は灰色で描く")
	var missing: Array = root.get_meta("missing_parts", [])
	h.expect("ruins/no_such_part" in missing and "../../etc" in missing, "無い部品の名前が報告される（%s）" % [missing])
	root.free()


func test_kit_hide_keeps_collision() -> void:
	# 出口の手前に hide の壁。見た目には無いが、通れない
	var room := _room({"kit": "ruins_b1"})
	room.geometry.append({"t": "box", "pos": [0, 0, 0], "size": [12, 4, 1], "hide": true})
	var w := _world(room)
	var vis := RoomView.build(w, "k.a")
	var plain := _room({"kit": "ruins_b1"})
	var vis_plain := RoomView.build(_world(plain), "k.a")
	h.expect(_verts(vis.get_node("KitSurfaces")) == _verts(vis_plain.get_node("KitSurfaces")), "hide の形は描かない")
	vis.free()
	vis_plain.free()
	h.expect(w.geometry("k.a").faces.size() == RoomGeo.build(plain).faces.size() + 1, "hide の形も当たり判定の面に入る")
	var g := h.make_world_game({"start": {"room": "k.a", "spawn": "start"}, "areas": [{"id": "k", "name": "キット", "rooms": {"a": room}}]})
	await h.settle()
	await h.run(g, TestHelpers.seconds(2.5), {"move_y": 1.0})
	h.expect(g.player.pos.z < -0.3, "hide の壁で止まる（z = %.2f）" % g.player.pos.z)
	h.free_game(g)


## "cam": false の形（体だけを止める。細い柱など）：体は止まり、上に立てる。カメラの壁よけ・弾の線は通る
func test_kit_body_only_shape() -> void:
	var room := _room({})
	room.geometry.append({"t": "box", "pos": [0, 0, 0], "size": [0.2, 3, 0.2], "hide": true, "cam": false})
	room.geometry.append({"t": "box", "pos": [-3, 0, -3], "size": [2, 0.3, 2], "hide": true, "cam": false})
	var w := _world(room)
	var geo := w.geometry("k.a")
	h.expect(geo.prop.size() == 2 and geo.faces.size() == RoomGeo.build(_room({})).faces.size(), "cam: false の形は体だけの当たり判定（prop）に分かれる")
	var g := h.make_world_game({"start": {"room": "k.a", "spawn": "start"}, "areas": [{"id": "k", "name": "キット", "rooms": {"a": room}}]})
	await h.settle()
	await h.run(g, TestHelpers.seconds(2.0), {"move_y": 1.0})
	h.expect(g.player.pos.z < -0.4 and g.player.pos.z > -0.6, "細い柱で体が止まる（z = %.2f）" % g.player.pos.z)
	var cam_hit: Dictionary = g.phys.raycast(Vector3(0, 1.4, -2), Vector3(0, 0, 1), 4.0, Phys.TERRAIN | Phys.BREAKABLE)
	var body_hit: Dictionary = g.phys.raycast(Vector3(0, 1.4, -2), Vector3(0, 0, 1), 4.0, Phys.PROP)
	h.expect(cam_hit.is_empty() and not body_hit.is_empty(), "カメラ・弾の線は細い柱を通る（体だけの層には当たる）")
	g.player.teleport(Vector3(-3, 1.0, -3), 0.0)
	await h.run(g, TestHelpers.seconds(1.0), {})
	h.expect(g.player.grounded and absf(g.player.pos.y - 0.3) < 0.05, "体だけの箱の上にも立てる（y = %.2f）" % g.player.pos.y)
	h.free_game(g)


func test_room_without_kit_unchanged() -> void:
	var w := _world(_room({}))
	var root := RoomView.build(w, "k.a")
	var meshes := _find(root, "MeshInstance3D")
	h.expect(meshes.size() == 1 and root.get_node_or_null("KitSurfaces") == null, "キットの無い部屋は今までの 1 つのメッシュ")
	var mat = (meshes[0] as MeshInstance3D).mesh.surface_get_material(0)
	h.expect(mat is ShaderMaterial and (mat as ShaderMaterial).shader == LevelLoader.GRID, "灰色の格子の材質のまま")
	root.free()


## 足場の箱（中心・大きさ）だけの地形（下は奈落）
func _ledges(boxes: Array) -> Dictionary:
	var faces := []
	for b in boxes:
		faces.append(TestHelpers.box_faces(b[0], b[1]))
	return {"faces": faces, "markers": {"start": {"pos": Vector3(0, 0, 0), "yaw": 0.0}}}


func test_fall_camera_holds_over_void() -> void:
	# 足場の端から奈落へ歩いて落ちる：カメラは縁の高さに止まって見下ろし（ハルについて部屋の下まで下がらない）、
	# 4 m 落ちるまでに画面が真っ暗になる。直前の足場に戻ると、暗いうちにカメラも戻ってから明るくなる
	var g := h.make_game({"geometry": _ledges([[Vector3(0, -0.5, 0), Vector3(6, 1, 6)]])})
	await h.settle()
	var cam := CameraRig.new()
	h.tree.root.add_child(cam)
	var dt := 1.0 / 60.0
	var hold_y := INF
	var dark_at_4 := -1.0
	var lowest := 0.0
	var cam_moved := 0.0
	var respawned := false
	var after := 0
	for i in 400:
		await h.tree.physics_frame
		g.step(InputFrame.of({"move_y": 1.0 if i < 60 else 0.0}))
		cam.sync(g, g.player.pos, dt, 0.0)
		var y := g.player.pos.y
		if i < 20:
			h.expect(cam.fall_dark == 0.0, "立っているあいだは暗くしない")
		if not respawned:
			if y < -1.0 and hold_y == INF:
				hold_y = cam.global_position.y
			if hold_y != INF and y < -0.5:
				cam_moved = maxf(cam_moved, absf(cam.global_position.y - hold_y))
			if y < -4.0 and dark_at_4 < 0.0:
				dark_at_4 = cam.fall_dark
			lowest = minf(lowest, y)
			if lowest < -20.0 and y > -0.5:
				respawned = true
				h.expect(cam.global_position.y > y + 1.0 and cam.global_position.distance_to(y * Vector3.UP + Vector3(g.player.pos.x, 0, g.player.pos.z)) < 7.5,
					"足場に戻った刻みにカメラもハルの後ろへ戻る（%s）" % cam.global_position)
				h.expect(cam.fall_dark > 0.9, "戻った刻みはまだ暗い（%.2f）" % cam.fall_dark)
		else:
			after += 1
			if after == 45:
				h.expect(cam.fall_dark == 0.0, "戻って 0.75 秒で明るい（%.2f）" % cam.fall_dark)
				break
	h.expect(hold_y != INF and hold_y > 1.0, "落ち始めのカメラは縁より上（%.2f）" % hold_y)
	h.expect(cam_moved < 0.01, "落ちているあいだカメラは下がらない（動き %.3f m）" % cam_moved)
	h.expect(dark_at_4 > 0.95, "4 m 落ちるまでに真っ暗（%.2f）" % dark_at_4)
	h.expect(respawned, "奈落から直前の足場に戻る")
	cam.queue_free()
	h.free_game(g)


func test_fall_camera_not_on_gap_jump() -> void:
	# 穴を跳び越す・段を飛び降りる（下に床がある）ときは、カメラを止めず暗くもしない
	var g := h.make_game({"geometry": _ledges([[Vector3(0, -0.5, 0), Vector3(6, 1, 6)], [Vector3(0, -1.5, 8.5), Vector3(6, 1, 6)],
		[Vector3(0, -4.5, 16), Vector3(6, 1, 6)]])})
	await h.settle()
	var cam := CameraRig.new()
	h.tree.root.add_child(cam)
	var worst := 0.0
	var jumped := false
	for i in 200:
		await h.tree.physics_frame
		var p := g.player.pos
		var jump := not jumped and p.z > 2.4 and g.player.grounded
		jumped = jumped or jump
		g.step(InputFrame.of({"move_y": 1.0 if p.z < 15.0 else 0.0, "jump": jump}))
		cam.sync(g, g.player.pos, 1.0 / 60.0, 0.0)
		worst = maxf(worst, cam.fall_dark)
	h.expect(g.player.pos.z > 14.0 and g.player.pos.y > -4.1, "跳び越して、段を飛び降りて下の床に着く（%s）" % g.player.pos)
	h.expect(worst == 0.0, "下に床があるあいだは暗くしない（%.2f）" % worst)
	cam.queue_free()
	h.free_game(g)


# ---------------------------------------------------------------- 飾りの当たり判定（"solid"）

## 当たり判定の箱が要る部品（歩ける所に立つ、手で触れる大きさの物）。solid の箱か、前からある描かない箱の中に立つこと
const SOLID_CLASS := ["ruins/b1_crate", "ruins/b1_crate_cloth", "town/crate", "town/barrel", "town/chest", "town/planter", "town/planter_big",
	"town/bench", "town/stall_table", "town/junk_pile", "town/tool_rack", "town/water_tower", "town/clothesline", "town/pipes",
	"town/lamp_post", "town/lamp_tall"]
## 飾りのある部屋（キットの部屋）
const DRESSED := ["ch1.r02", "ch1.r03", "ch1.mid"]
## 足した箱と、出口・トリガーの箱の間（m）／目印・チェックポイント・敵の出る所から／調べる物・拾う物・住人から（tools/dress_solid.py と同じ）
const CLEAR_BOX := 0.1
const CLEAR_MARK := 0.6
const CLEAR_PROP := 0.5


## 形の床の上の広がり：[中心 x, 中心 z, 半幅 x, 半幅 z, yaw（ラジアン）, 下の y, 上の y]
static func _foot(g: Dictionary) -> Array:
	var p := RoomGeo.v3(g.pos)
	var s := RoomGeo.v3(g.size)
	return [p.x, p.z, s.x / 2.0, s.z / 2.0, float(g.get("yaw", 0.0)) * U.DEG, p.y, p.y + s.y]


## 点 (x, z) から形の床の上の広がりまでの距離（中なら 0）
static func _dist(g: Dictionary, x: float, z: float) -> float:
	var f := _foot(g)
	var l := Basis(Vector3.UP, -float(f[4])) * Vector3(x - f[0], 0.0, z - f[1])
	return Vector2(maxf(absf(l.x) - f[2], 0.0), maxf(absf(l.z) - f[3], 0.0)).length()


## 形が軸にそろった箱（底の中心 pos・大きさ size）に clear まで近いか。高さはトリガーと同じく上へ 1 m のゆとり。分離軸で調べる
static func _near_box(g: Dictionary, pos: Vector3, size: Vector3, clear: float) -> bool:
	var f := _foot(g)
	if f[6] < pos.y - clear or f[5] > pos.y + size.y + 1.0 + clear:
		return false
	var d := Vector2(pos.x - f[0], pos.z - f[1])
	var ax := Vector2(cos(f[4]), -sin(f[4]))
	var az := Vector2(sin(f[4]), cos(f[4]))
	for axis in [Vector2(1, 0), Vector2(0, 1), ax, az]:
		var rg: float = absf(ax.dot(axis)) * f[2] + absf(az.dot(axis)) * f[3]
		var rb: float = absf(axis.x) * size.x / 2.0 + absf(axis.y) * size.z / 2.0
		if absf(d.dot(axis)) >= rg + rb + clear:
			return false
	return true


## 足した箱が、出口・トリガー・目印・チェックポイント・敵・調べる物・拾う物・住人をふさいでいないか（ふさいでいる物の一覧）
static func _blocking(room: Dictionary, added: Array) -> Array:
	var points := []
	var mk: Dictionary = room.get("markers", {})
	for n in mk:
		points.append([n, RoomGeo.v3(mk[n].pos), CLEAR_MARK])
	for c in room.get("checkpoints", []):
		points.append([c.id, RoomGeo.v3(c.pos), CLEAR_MARK])
	for e in room.get("enemies", []):
		if e.has("pos"):
			points.append([str(e.get("id", e.get("kind", "敵"))), RoomGeo.v3(e.pos), CLEAR_MARK])
	var boxes := []
	for t in room.get("triggers", []):
		if t.has("pos") and t.has("size"):
			boxes.append([t.id, RoomGeo.v3(t.pos), RoomGeo.v3(t.size)])
	for p in room.get("props", []):
		if p.get("type", "") == "sign":
			continue
		if p.get("size") is Array:
			boxes.append([str(p.get("id", p.type)), RoomGeo.v3(p.pos), RoomGeo.v3(p.size)])
		elif p.has("pos"):
			points.append([str(p.get("id", p.type)), RoomGeo.v3(p.pos), CLEAR_PROP])
	var bad := []
	for g in added:
		var f := _foot(g)
		for q in points:
			var at: Vector3 = q[1]
			if f[6] > at.y - 0.2 and f[5] < at.y + 1.6 and _dist(g, at.x, at.z) < q[2]:
				bad.append("%s が %s に近い" % [str(g.pos), q[0]])
		for b in boxes:
			if _near_box(g, b[1], b[2], CLEAR_BOX):
				bad.append("%s が %s に掛かる" % [str(g.pos), b[0]])
	return bad


## キットの部屋の飾りの当たり判定：solid の飾りには描かない箱があり、箱・樽・鉢植えなどはどれも当たり判定の箱の中に立ち、
## 足した箱は出口・トリガー・目印・調べる物・住人をふさがない。整備通路の跳ぶ所（溝の縁から 1.5 m）には箱を置かない
func test_dress_solid_props() -> void:
	var w := World.load_manifest("res://content/world.json")
	for rid in DRESSED:
		var room := w.room(rid)
		var geo: Array = room.get("geometry", [])
		var dress: Array = room.get("dress", [])
		var added := geo.filter(func(g): return g.has("dress"))
		h.expect(added.size() > 0 and added.all(func(g): return g.get("hide", false)),
			"%s：飾りの当たり判定の箱がある（%d 個）、どれも描かない" % [rid, added.size()])
		var lacking := []
		for i in dress.size():
			var d: Dictionary = dress[i]
			if d.get("solid", false) and added.filter(func(g): return int(g.dress) == i).size() < int(d.get("count", 1)):
				lacking.append(d.part)
		h.expect(lacking.is_empty(), "%s：solid の飾りに当たり判定の箱がある（無い：%s）" % [rid, lacking])
		var loose := []
		var n := 0
		for d in dress:
			if not d.part in SOLID_CLASS:
				continue
			for k in maxi(1, int(d.get("count", 1))):
				var p := RoomGeo.v3(d.pos) + RoomGeo.v3(d.get("step", [0, 0, 0])) * k + Vector3(0, 0.25, 0)
				n += 1
				if not geo.any(func(g): return g.get("t", "box") == "box" and _dist(g, p.x, p.z) == 0.0 and p.y >= g.pos[1] and p.y <= g.pos[1] + g.size[1]):
					loose.append("%s %s" % [d.part, p])
		h.expect(n > 0 and loose.is_empty(), "%s：箱・樽・鉢植えなど %d 個に当たり判定がある（無い：%s）" % [rid, n, loose])
		var bad := _blocking(room, added)
		h.expect(bad.is_empty(), "%s：当たり判定の箱が出口・トリガー・目印・調べる物・住人から離れている（%s）" % [rid, bad])
	var on_jump := []
	for g in w.room("ch1.r03").geometry:
		if not g.has("dress"):
			continue
		var f := _foot(g)
		var ez: float = absf(f[2] * sin(f[4])) + absf(f[3] * cos(f[4]))
		for edge in [-13.0, -11.5, -7.0, -4.5, -0.5, 3.0, 7.5, 10.5, 13.5, 16.0]:
			if absf(f[1] - edge) < ez + 1.5:
				on_jump.append("%s（溝の縁 z=%.1f）" % [str(g.pos), edge])
	h.expect(on_jump.is_empty(), "整備通路：溝の縁から 1.5 m（着地・踏み切りの所）に当たり判定の箱が無い（%s）" % [on_jump])


func _ch1_game() -> GameSim:
	var g := GameSim.new()
	var vp := SubViewport.new()
	vp.own_world_3d = true
	vp.render_target_update_mode = SubViewport.UPDATE_DISABLED
	vp.size = Vector2i(2, 2)
	h.tree.root.add_child(vp)
	vp.add_child(g)
	g.setup({"world": World.load_manifest("res://content/world.json"), "tuning": TestHelpers.default_tuning(), "seed": 1})
	g.god_mode = true
	return g


## 実際に歩く：箱・樽・鉢植え・ベンチ・大型ファンに向かって歩くと、当たって止まる（体が箱に入らない。前は頭だけ出して中に立てた）
func test_dress_solid_walk() -> void:
	var g := _ch1_game()
	await h.settle()
	var cases := [
		["ch1.r02", "from_r01", Vector3(9.4, 0, 9.4), Vector2(1, 1), "遺構 B1 の北東の角の箱"],
		["ch1.r02", "from_r01", Vector3(-9.4, 0, -9.4), Vector2(-1, -1), "南西の角の箱"],
		["ch1.r02", "from_r01", Vector3(-9.8, 0, 9.8), Vector2(-1, 1), "北西の角の箱"],
		["ch1.r02", "from_r01", Vector3(9.8, 0, -9.8), Vector2(1, -1), "南東の角の箱"],
		["ch1.r02", "from_r01", Vector3(-10.5, 0, 0.5), Vector2(-1, 0), "西の壁の大型ファン"],
		["ch1.r03", "from_r02", Vector3(0.3, 0, -16.7), Vector2(1, 0), "整備通路の扉の前の箱（東）"],
		["ch1.r03", "from_r02", Vector3(-0.3, 0, -16.7), Vector2(-1, 0), "整備通路の扉の前の箱（西）"],
		["ch1.mid", "start", Vector3(19.4, 0, 2.2), Vector2(0, 1), "雑貨屋の西の端の樽"],
		["ch1.mid", "start", Vector3(-25.8, 0, -1.9), Vector2(0, 1), "食堂の西の角の木箱"],
		["ch1.mid", "start", Vector3(-7.4, 0, 5.0), Vector2(-1, 0), "広場のベンチ"],
		["ch1.mid", "start", Vector3(-10.0, 0, -11.0), Vector2(0, -1), "胸壁の前の鉢植え"],
	]
	for c in cases:
		if g.room_id != c[0]:
			g.load_room(c[0], c[1])
			for t in g.triggers:
				t.fired = true
			await h.run(g, 4, {})
		var dir: Vector2 = (c[3] as Vector2).normalized()
		var yaw := atan2(dir.x, dir.y)
		g.player.teleport(c[2], yaw)
		g.cam.yaw = yaw
		await h.run(g, 2, {})
		var start := g.player.pos
		var added: Array = g.room.geometry.filter(func(s): return s.has("dress"))
		var worst := INF
		for i in TestHelpers.seconds(2.0):
			await h.run(g, 1, {"move_y": 1.0})
			var p := g.player.pos
			for s in added:
				var f := _foot(s)
				if f[6] > p.y + 0.05 and f[5] < p.y + Player.HEIGHT:
					worst = minf(worst, _dist(s, p.x, p.z))
		var moved := Vector2(g.player.pos.x - start.x, g.player.pos.z - start.z).dot(dir)
		h.expect(worst <= Player.RADIUS + 0.05 and moved > 0.3, "%s：歩いて行って箱に当たる（%.2f m 進んで、箱との間 %.2f m）" % [c[4], moved, worst])
		h.expect(worst >= Player.RADIUS - 0.06, "%s：体が箱に入らない（箱との間 %.2f m）" % [c[4], worst])
		h.expect(g.room_id == c[0] and absf(g.player.pos.y - start.y) < 0.2 and g.player.grounded,
			"%s：床の上に立ったまま（%s, y=%.2f）" % [c[4], g.room_id, g.player.pos.y])
	h.free_game(g)
