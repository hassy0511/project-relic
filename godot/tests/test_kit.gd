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
