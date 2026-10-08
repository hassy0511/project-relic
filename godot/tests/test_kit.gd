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
