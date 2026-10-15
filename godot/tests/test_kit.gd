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


## 汚れ・傷みの層（材質の "detail"。42 章 14.2）：層の無い材質は前のシェーダーのまま、層のある材質は層つきのシェーダーと値。
## キットの面と部品のメッシュには、足元・上の端の汚れのための UV2（下の端からの高さ, 上の端までの深さ）が付く
func test_kit_detail_materials() -> void:
	var base := {"albedo": "res://assets/kit/tex/ruins_aged_ivory.jpg", "uv_m": 3.0, "color": "#f1e7d2", "roughness": 0.72}
	var plain := RoomKit.make_material(base) as ShaderMaterial
	h.expect(plain.shader == RoomKit.SHADER, "層の無い材質は前のシェーダー（kit_surface.gdshader）のまま")
	var with_layers := base.duplicate()
	with_layers["detail"] = [
		{"mask": "grime", "uv_m": 3.0, "cover": 0.4, "color": "#a47c60", "mode": "multiply", "amount": 0.6},
		{"mask": "streaks", "uv_m": [1.6, 2.6], "cover": 0.5, "top": [0.0, 1.8], "color": "#9b5a3c", "gate": {"cover": 0.6, "uv_m": 6.0}},
	]
	var dm := RoomKit.make_material(with_layers) as ShaderMaterial
	h.expect(dm.shader == RoomKit.SHADER_DETAIL, "層のある材質は層つきのシェーダー（kit_surface_detail.gdshader）")
	h.expect(int(dm.get_shader_parameter("detail_count")) == 2, "層の数が入る（%s）" % [dm.get_shader_parameter("detail_count")])
	h.expect(dm.get_shader_parameter("detail_tex") is Texture2D and dm.get_shader_parameter("detail_tex2") is Texture2D, "型の絵が 2 枚とも読める")
	var pick: PackedVector4Array = dm.get_shader_parameter("d_pick")
	var feet: PackedVector4Array = dm.get_shader_parameter("d_feet")
	var shape: PackedVector4Array = dm.get_shader_parameter("d_shape")
	var gate: PackedVector4Array = dm.get_shader_parameter("d_gate")
	h.expect(pick.size() == RoomKit.DETAIL_MAX and pick[0] == Vector4(1, 0, 0, 0) and pick[1] == Vector4(0, 0, 0, 1), "型の選び（汚れの斑・縦の筋）")
	h.expect(is_equal_approx(shape[0].x, 0.4) and shape[0].z == 1.0 and shape[0].w == 0.0, "覆う割合・掛ける塗り方・全部の面（%s）" % [shape[0]])
	h.expect(shape[1].w == 2.0 and is_equal_approx(feet[1].w, 1.8), "上の端の層は縦の面だけ（%s・%s）" % [shape[1], feet[1]])
	h.expect(is_equal_approx(gate[1].z, 0.6) and is_equal_approx(gate[1].w, 1.0 / 6.0), "大きな斑の中だけ（%s）" % [gate[1]])
	for k in ["color", "uv_m", "roughness_value", "albedo_tex"]:
		h.expect(dm.get_shader_parameter(k) == plain.get_shader_parameter(k), "層を足しても元の値（%s）は同じ" % k)
	# 1 つの層は辞書のままでもよい。4 つを超える分は使わない
	var one := base.duplicate()
	one["detail"] = {"mask": "chips", "cover": 0.2}
	h.expect(int((RoomKit.make_material(one) as ShaderMaterial).get_shader_parameter("detail_count")) == 1, "1 つの層は辞書でも書ける")
	var many := base.duplicate()
	many["detail"] = [{}, {}, {}, {}, {}]
	h.expect(int((RoomKit.make_material(many) as ShaderMaterial).get_shader_parameter("detail_count")) == RoomKit.DETAIL_MAX, "層は %d つまで" % RoomKit.DETAIL_MAX)
	var faded := with_layers.duplicate()
	faded["near_fade"] = [0.8, 1.5]
	var fm := RoomKit.make_material(faded) as ShaderMaterial
	h.expect(fm.shader == (RoomKit.SHADER_DETAIL if RenderingServer.get_current_rendering_method() == "gl_compatibility" else RoomKit.SHADER_DETAIL_FADE),
		"近くを網目に消す材質にも層が付く")
	# キットの材質：層を書いた物は層つきのシェーダー、書いていない物は前のまま
	for id in ["ruins_b1", "town"]:
		var data: Dictionary = U.load_json(RoomKit.KIT_PATH % id)
		var kit := RoomKit.load_kit(id)
		var ok := true
		var n := 0
		for group in [["surfaces", "surf"], ["materials", "mats"]]:
			for k in data.get(group[0], {}):
				var def: Dictionary = data[group[0]][k]
				var m: Material = kit[group[1]][k]
				if def.get("blend", "") == "add":
					continue
				var sh: Shader = (m as ShaderMaterial).shader
				var has: bool = sh == RoomKit.SHADER_DETAIL or sh == RoomKit.SHADER_DETAIL_FADE
				ok = ok and has == def.has("detail")
				n += 1 if has else 0
		h.expect(ok and n > 0, "キット %s：層を書いた材質（%d）だけが層つきのシェーダー" % [id, n])
	# 面の UV2：形の下の端からの高さと、上の端までの深さ
	var root := RoomView.build(_world(_room({"kit": "ruins_b1", "dress": [{"part": "ruins/b1_crate", "pos": [-4, 0, -4]}]})), "k.a")
	var surf := root.get_node("KitSurfaces") as MeshInstance3D
	var uv_ok := true
	for s in surf.mesh.get_surface_count():
		var arr := surf.mesh.surface_get_arrays(s)
		var verts: PackedVector3Array = arr[Mesh.ARRAY_VERTEX]
		var uv2 = arr[Mesh.ARRAY_TEX_UV2]
		if not (uv2 is PackedVector2Array) or (uv2 as PackedVector2Array).size() != verts.size():
			uv_ok = false
			continue
		for i in verts.size():
			# 部屋の箱（shell）は y 0〜6、中の箱は y 0〜1
			var hgt: float = (uv2 as PackedVector2Array)[i].x
			var depth: float = (uv2 as PackedVector2Array)[i].y
			uv_ok = uv_ok and absf(hgt - verts[i].y) < 1e-3 and (absf(hgt + depth - 6.0) < 1e-3 or absf(hgt + depth - 1.0) < 1e-3)
	h.expect(uv_ok, "部屋の面の UV2 は（形の下の端からの高さ, 上の端までの深さ）")
	var crate := RoomKit.part_mesh("ruins/b1_crate", RoomKit.load_kit("ruins_b1"))
	var carr := crate.surface_get_arrays(0)
	var cuv2 = carr[Mesh.ARRAY_TEX_UV2]
	var cy := (carr[Mesh.ARRAY_VERTEX] as PackedVector3Array)
	var aabb := crate.get_aabb()
	h.expect(cuv2 is PackedVector2Array and (cuv2 as PackedVector2Array).size() == cy.size() and absf((cuv2 as PackedVector2Array)[0].x - (cy[0].y - aabb.position.y)) < 1e-3,
		"部品のメッシュにも UV2（部品の下の端からの高さ）")
	root.free()


## キットの "base"・"detail_scale"（部屋ごとの汚れの強さ）と、汚れの斑の板（"blend": "decal"）。42 章 14.2.1（2026-10-15）
func test_kit_inherit_and_decal() -> void:
	var town: Dictionary = U.load_json(RoomKit.KIT_PATH % "town")
	var tidy := RoomKit.load_kit("town_tidy")
	var worn := RoomKit.load_kit("town_worn")
	h.expect(not tidy.is_empty() and tidy.data.get("sky", {}) == town.get("sky", {}) and tidy.surf.has("floor") and tidy.mats.has("flat"),
		"元のキット（town）の空・面・材質を受け継ぐ")
	var a0 := float(town.surfaces.floor.detail[1].amount)
	var c0 := float(town.surfaces.floor.detail[1].cover)
	var at := float(tidy.data.surfaces.floor.detail[1].amount)
	var aw := float(worn.data.surfaces.floor.detail[1].amount)
	h.expect(is_equal_approx(at, a0 * 0.55) and is_equal_approx(float(tidy.data.surfaces.floor.detail[1].cover), c0 * 0.8),
		"detail_scale が汚れの層の強さ・覆う割合に掛かる（%.3f → %.3f）" % [a0, at])
	h.expect(is_equal_approx(aw, minf(1.0, a0 * 1.2)) and float(worn.data.materials.flat.detail[0].amount) <= 1.0, "強くしても 1 まで（%.3f）" % aw)
	h.expect(float(town.surfaces.floor.detail[1].amount) == a0, "元のキットの JSON は変わらない")
	var dm := RoomKit.make_material({"blend": "decal", "color": "#9c8466", "amount": 0.5, "cover": 0.7, "uv_m": 4.0}) as ShaderMaterial
	h.expect(dm.shader == RoomKit.DECAL and is_equal_approx(float(dm.get_shader_parameter("cover")), 0.7) and dm.get_shader_parameter("detail_tex") is Texture2D,
		"汚れの斑の材質は半透明の汚れのシェーダー（kit_decal.gdshader）")
	var patch := RoomKit.part_mesh("town/grime_patch", RoomKit.load_kit("town"))
	h.expect(patch != null and (patch.surface_get_material(0) as ShaderMaterial).shader == RoomKit.DECAL, "汚れの斑の板（town/grime_patch）はキットの grime_decal で描く")


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
## （洗濯綱は洗濯物が頭の上の高さで、2 本の柱の間は歩いて通れる。柱だけに箱がある）
const SOLID_CLASS := ["ruins/b1_crate", "ruins/b1_crate_cloth", "town/crate", "town/barrel", "town/chest", "town/planter", "town/planter_big",
	"town/bench", "town/stall_table", "town/junk_pile", "town/tool_rack", "town/water_tower", "town/pipes",
	"town/lamp_post", "town/lamp_tall", "town/tank", "town/stool", "town/pipe_bend", "town/bollard", "ruins/b1_post_lamp",
	"town/sacks", "cc0/cask", "cc0/plank_box"]
## 飾りのある部屋（キットの部屋）
const DRESSED := ["ch1.r02", "ch1.r03", "ch1.mid"]
## 足した箱と、出口・トリガーの箱の間（m）／目印・チェックポイント・敵の出る所から／調べる物・拾う物・住人から（tools/dress_solid.py と同じ）
const CLEAR_BOX := 0.1
const CLEAR_MARK := 0.6
const CLEAR_PROP := 0.5
## 壁の帯（"wall": true）が出口・トリガーの箱に掛かってよい深さ（dress_solid.WALL_REACH）
const WALL_REACH := 1.0
## 両辺がこれより広いトリガーは「場所」（広場など）。その中には床の上の広がりが SMALL より小さい箱は立ててよい（dress_solid.AREA・SMALL）
const AREA := 4.0
const SMALL := 0.5
## 跳んで届く高さ（tuning の jumpHeight 2.2）と、乗れない柱（"nogo"）の上の端に要るゆとり。届く所を探す横の距離
const JUMP_UP := 2.2
const NOGO_MARGIN := 0.1
const JUMP_ACROSS := 6.5
## 整備通路の溝（z の範囲）と、壁の帯の面（|x|）
const R03_PITS := [[-13.0, -11.5], [-7.0, -4.5], [-0.5, 3.0], [7.5, 10.5], [13.5, 16.0]]
const R03_LINER := 2.64
## 町の残りの 9 部屋（2026-10-15 の町の展開、tools/dress_town.py。42 章 14.7）。test_dress_solid_props で DRESSED と一緒に確かめる
const DRESSED_TOWN := ["ch1.opening", "ch1.training", "ch1.lower", "ch1.upper", "ch1.home", "ch1.workshop", "ch1.guild", "ch1.mayor", "ch1.r01"]


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


## 壁の帯が、出口・トリガーの箱に壁ぎわの WALL_REACH までしか掛かっていないか（重なりの幅か奥行きのどちらかが WALL_REACH 以下）
static func _wall_edge_only(g: Dictionary, pos: Vector3, size: Vector3) -> bool:
	var f := _foot(g)
	var ox: float = minf(f[0] + f[2], pos.x + size.x / 2.0) - maxf(f[0] - f[2], pos.x - size.x / 2.0) + 2.0 * CLEAR_BOX
	var oz: float = minf(f[1] + f[3], pos.z + size.z / 2.0) - maxf(f[1] - f[3], pos.z - size.z / 2.0) + 2.0 * CLEAR_BOX
	return minf(ox, oz) <= WALL_REACH


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
			var ts := RoomGeo.v3(t.size)
			boxes.append([t.id, RoomGeo.v3(t.pos), ts, ts.x >= AREA and ts.z >= AREA])
	for p in room.get("props", []):
		if p.get("type", "") == "sign":
			continue
		if p.get("size") is Array:
			boxes.append([str(p.get("id", p.type)), RoomGeo.v3(p.pos), RoomGeo.v3(p.size), false])
		elif p.has("pos"):
			points.append([str(p.get("id", p.type)), RoomGeo.v3(p.pos), CLEAR_PROP])
	var bad := []
	for g in added:
		var f := _foot(g)
		for q in points:
			var at: Vector3 = q[1]
			if f[6] > at.y - 0.2 and f[5] < at.y + 1.6 and _dist(g, at.x, at.z) < q[2]:
				bad.append("%s が %s に近い" % [str(g.pos), q[0]])
		var small: bool = f[2] * 2.0 <= SMALL and f[3] * 2.0 <= SMALL
		for b in boxes:
			if b[3] and small:
				continue      # 場所のトリガーの中の小さい箱
			if _near_box(g, b[1], b[2], CLEAR_BOX) and not (g.get("wall", false) and _wall_edge_only(g, b[1], b[2])):
				bad.append("%s が %s に掛かる" % [str(g.pos), b[0]])
	return bad


## 箱の床の上の範囲 [x0, x1, z0, z1]（軸にそろった形だけ。回した形は囲む範囲）
static func _rect(g: Dictionary) -> Array:
	var f := _foot(g)
	var ex: float = absf(f[2] * cos(f[4])) + absf(f[3] * sin(f[4]))
	var ez: float = absf(f[2] * sin(f[4])) + absf(f[3] * cos(f[4]))
	return [f[0] - ex, f[0] + ex, f[1] - ez, f[1] + ez]


static func _rect_gap(a: Array, b: Array) -> float:
	return Vector2(maxf(0.0, maxf(a[0] - b[1], b[0] - a[1])), maxf(0.0, maxf(a[2] - b[3], b[2] - a[3]))).length()


## 上の面に立てる箱か（乗れない柱は除く）：上の面の点のどれかで、体の中心を置ける（その点から 0.33 m 以内に、上の面より上へ伸びる
## ほかの箱が無い。壁ぎわの薄い箱・頭の上がふさがった箱には立てない）。i は geo の番号
static func _standable(i: int, geo: Array, rects: Array) -> bool:
	var g: Dictionary = geo[i]
	if g.get("t", "box") != "box" or g.get("nogo", false):
		return false
	var r: Array = rects[i]
	if r[1] - r[0] < 0.05 or r[3] - r[2] < 0.05:
		return false
	var top: float = float(g.pos[1]) + float(g.size[1])
	var near := []
	for j in geo.size():
		var o: Dictionary = geo[j]
		var y0: float = float(o.pos[1])
		if j != i and y0 < top + 1.55 and y0 + float(o.size[1]) > top + 0.05 and _rect_gap(rects[j], [r[0] - 0.33, r[1] + 0.33, r[2] - 0.33, r[3] + 0.33]) == 0.0:
			near.append(rects[j])
	for a in 3:
		for b in 3:
			var x: float = r[0] + (r[1] - r[0]) * (0.1 + 0.4 * a)
			var z: float = r[2] + (r[3] - r[2]) * (0.1 + 0.4 * b)
			if near.all(func(ro): return _rect_gap(ro, [x, x, z, z]) >= 0.33):
				return true
	return false


## 乗れない柱（"nogo"）の上には、跳んで届かない：近くの立てる面（床 0 m と、床から順に跳んで届く箱の上）から JUMP_UP 跳んでも、
## 上の端に NOGO_MARGIN 足りない。上にほかの箱が続いている柱は、その箱の上で見る
func _nogo_reach(room: Dictionary) -> Array:
	var geo: Array = room.get("geometry", []).filter(func(g): return g.get("t", "box") == "box")
	var rects := geo.map(func(g): return _rect(g))
	var tops := geo.map(func(g): return float(g.pos[1]) + float(g.size[1]))
	var stand := []
	for i in geo.size():
		if tops[i] > 0.05 and tops[i] < 8.0 and _standable(i, geo, rects):
			stand.append(i)
	var reached := {}      # 届く立てる箱の番号
	var changed := true
	while changed:
		changed = false
		for i in stand:
			if reached.has(i):
				continue
			var ok: bool = tops[i] <= JUMP_UP
			if not ok:
				for a in reached:
					if tops[a] + JUMP_UP >= tops[i] and _rect_gap(rects[a], rects[i]) <= JUMP_ACROSS:
						ok = true
						break
			if ok:
				reached[i] = true
				changed = true
	var bad := []
	for k in geo.size():
		if not geo[k].get("nogo", false):
			continue
		var r: Array = rects[k]
		var cx: float = (r[0] + r[1]) / 2.0
		var cz: float = (r[2] + r[3]) / 2.0
		var above := false
		for j in geo.size():
			var ro: Array = rects[j]
			if j != k and absf(float(geo[j].pos[1]) - tops[k]) < 0.02 and cx >= ro[0] and cx <= ro[1] and cz >= ro[2] and cz <= ro[3]:
				above = true
				break
		if above:
			continue      # 上に続く箱がある
		var best := JUMP_UP
		for a in reached:
			if _rect_gap(rects[a], r) <= JUMP_ACROSS:
				best = maxf(best, tops[a] + JUMP_UP)
		if tops[k] < best + NOGO_MARGIN:
			bad.append("%s（上の端 %.2f、届く %.2f）" % [str(geo[k].pos), tops[k], best])
	return bad


## キットの部屋の飾りの当たり判定：solid の飾りには描かない箱があり、箱・樽・鉢植えなどはどれも当たり判定の箱の中に立ち、
## 足した箱は出口・トリガー・目印・調べる物・住人をふさがない（壁の帯は壁ぎわだけ可）。乗れない柱の上には跳んで届かない。
## 整備通路の溝と、溝の縁から 1.5 m（着地・踏み切り・跳んでいる所）では、頭の届く高さに壁の帯より前へ出た箱が無い
func test_dress_solid_props() -> void:
	var w := World.load_manifest("res://content/world.json")
	for rid in DRESSED + DRESSED_TOWN:
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
		h.expect(added.filter(func(g): return g.get("nogo", false) and g.get("cam", true)).is_empty(), "%s：乗れない柱はどれも体だけの箱（cam: false）" % rid)
		var high := _nogo_reach(room)
		h.expect(high.is_empty(), "%s：乗れない柱の上には跳んで届かない（届く：%s）" % [rid, high])
	var on_jump := []
	for g in w.room("ch1.r03").geometry:
		if not g.has("dress"):
			continue
		var f := _foot(g)
		var r := _rect(g)
		if f[5] >= 3.9 or (r[0] >= R03_LINER - 0.005 or r[1] <= -R03_LINER + 0.005):
			continue      # 頭の上の管・梁、壁の帯の内の物
		for pit in R03_PITS:
			if r[3] > pit[0] - 1.5 and r[2] < pit[1] + 1.5:
				on_jump.append("%s（溝 %s）" % [str(g.pos), str(pit)])
	h.expect(on_jump.is_empty(), "整備通路：溝と溝の縁から 1.5 m に、壁の帯より前へ出た当たり判定の箱が無い（%s）" % [on_jump])


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
		["ch1.r02", "from_r01", Vector3(12.0, 0, -9.0), Vector2(0, -1), "南東の角の箱"],
		["ch1.r02", "from_r01", Vector3(11.0, 0, -9.5), Vector2(1, 0), "遺構 B1 の東の壁（板の継ぎ目の柱の前。体は壁の帯で止まる）"],
		["ch1.r03", "from_r02", Vector3(1.0, 0, -10.0), Vector2(1, 0), "整備通路の東の壁"],
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


## 縁の角に体の丸い底だけで載ったら（体の中心が縁の外）、縁から滑り落ちて床に立つ。前は接地しないまま縁の上で止まり、
## 跳べないまま宙に浮いて見えた（箱の縁・溝の縁）。体の中心が縁の内なら、縁に立ったまま
func test_edge_slides_off() -> void:
	var g := h.make_game({"boxes": [[Vector3(0, 0.5, 0), Vector3(2, 1, 2)]]})
	await h.settle()
	g.player.teleport(Vector3(1.15, 1.0, 0), 0.0)
	await h.run(g, TestHelpers.seconds(0.8), {})
	h.expect(g.player.grounded and g.player.pos.y < 0.05 and g.player.pos.x > 1.3,
		"中心が縁の 0.15 m 外：縁から床へ落ちて立つ（%.2f, %.2f）" % [g.player.pos.x, g.player.pos.y])
	g.player.teleport(Vector3(0.9, 1.0, 0), 0.0)
	await h.run(g, TestHelpers.seconds(0.8), {})
	h.expect(g.player.grounded and absf(g.player.pos.y - 1.0) < 0.02 and absf(g.player.pos.x - 0.9) < 0.02,
		"中心が縁の 0.1 m 内：縁に立ったまま（%.2f, %.2f）" % [g.player.pos.x, g.player.pos.y])
	h.free_game(g)


## 箱の上から角・壁ぎわへ歩いて（跳んで）下りても、宙に浮いたまま止まらない。前は遺構 B1 の角の箱と壁の間のすき間（0.3〜0.6 m）に落ちて、
## 両側の角に体が引っかかり、立てず跳べず出られなくなった（食堂の卓とベンチの間も同じ）。止まったあと接地していて、部屋の真ん中へ戻れる
func test_dress_no_hang() -> void:
	var g := _ch1_game()
	await h.settle()
	var cases := [
		# [部屋, 目印, 始めの位置（箱の上）, 歩く向き, 説明]
		["ch1.r02", "from_r01", Vector3(-12.0, 1.02, -11.9), Vector2(-1, -1), "遺構 B1 の南西の角の箱の上から角へ"],
		["ch1.r02", "from_r01", Vector3(-10.8, 1.06, -12.0), Vector2(0, -1), "南西の布の箱の上から南の壁へ"],
		["ch1.r02", "from_r01", Vector3(-12.0, 1.02, -10.9), Vector2(-1, 0), "南西の箱の上から西の壁へ"],
		["ch1.r02", "from_r01", Vector3(11.9, 1.06, 12.0), Vector2(1, 1), "北東の角の布の箱の上から角へ"],
		["ch1.r02", "from_r01", Vector3(10.8, 1.02, 12.1), Vector2(0, 1), "北東の箱の上から北の壁へ"],
		["ch1.r02", "from_r01", Vector3(12.1, 1.02, 10.9), Vector2(1, 0), "北東の箱の上から東の壁へ"],
		["ch1.r02", "from_r01", Vector3(-12.0, 1.02, 12.0), Vector2(-1, 1), "北西の角の箱の上から角へ"],
		["ch1.r02", "from_r01", Vector3(12.0, 1.06, -11.9), Vector2(1, -1), "南東の角の布の箱の上から角へ"],
		["ch1.mid", "start", Vector3(-24.6, 0.82, -3.6), Vector2(-1, 0), "食堂の西の卓の上から西のベンチへ"],
		["ch1.mid", "start", Vector3(-24.6, 0.82, -3.6), Vector2(1, 0), "食堂の西の卓の上から東のベンチへ"],
		["ch1.mid", "start", Vector3(-15.4, 0.82, -3.6), Vector2(-1, 0), "食堂の東の卓の上から西のベンチへ"],
		["ch1.mid", "start", Vector3(-15.4, 0.82, -3.6), Vector2(1, 0), "食堂の東の卓の上から東のベンチへ"],
		["ch1.mid", "start", Vector3(10.0, 1.47, -13.2), Vector2(0, -1), "胸壁の前の鉢植えの上から胸壁の上へ"],
		["ch1.mid", "start", Vector3(-20.0, 1.47, -13.2), Vector2(0, -1), "胸壁の前の鉢植えの上から胸壁の上へ（西）"],
		["ch1.mid", "start", Vector3(2.6, 1.75, 13.8), Vector2(1, 1), "北の階段の横の大きな鉢植えの上から角の棟の扉の方へ"],
		["ch1.mid", "start", Vector3(-2.6, 1.75, 13.8), Vector2(-1, 1), "北の階段の横の大きな鉢植えの上から角の棟の扉の方へ（西）"],
		["ch1.mid", "start", Vector3(-19.7, 1.14, 10.1), Vector2(1, 0), "食堂の裏の木箱の上から裏口の日よけの方へ"],
		["ch1.mid", "start", Vector3(28.9, 1.02, 5.2), Vector2(-1, -1), "雑貨屋の収納箱の上から台の端の方へ"],
		["ch1.mid", "start", Vector3(-19.64, 1.08, 10.1), Vector2(-1, 0), "食堂の裏の木箱の上から裏の窓の雨戸の方へ"],
		["ch1.mid", "start", Vector3(5.5, 1.22, -14.3), Vector2(0, 1), "胸壁の上から南の階段の上り口の背の高い外灯の方へ"],
		["ch1.mid", "start", Vector3(-5.5, 1.22, -14.3), Vector2(0, 1), "胸壁の上から背の高い外灯の方へ（西）"],
		["ch1.mid", "start", Vector3(12.0, 2.96, 9.5), Vector2(-1, 0), "広場の外灯の腕の上から灯の先へ"],
	]
	for c in cases:
		if g.room_id != c[0]:
			g.load_room(c[0], c[1])
			for t in g.triggers:
				t.fired = true
			g.exits = []
			await h.run(g, 4, {})
		for mode in ["walk", "jump"]:
			var dir: Vector2 = (c[3] as Vector2).normalized()
			var yaw := atan2(dir.x, dir.y)
			g.player.teleport(c[2], yaw)
			g.cam.yaw = yaw
			await h.run(g, 3, {})
			for i in TestHelpers.seconds(1.5):
				g.cam.yaw = yaw
				await h.run(g, 1, {"move_y": 1.0, "jump": mode == "jump" and i < 10})
			await h.run(g, TestHelpers.seconds(0.8), {})
			var p := g.player.pos
			h.expect(g.player.grounded, "%s（%s）：止まったとき接地している（%.2f, %.2f, %.2f）" % [c[4], mode, p.x, p.y, p.z])
			# 部屋の真ん中へ戻れる
			var back := atan2(-p.x, -p.z)
			for i in TestHelpers.seconds(1.5):
				g.cam.yaw = back
				await h.run(g, 1, {"move_y": 1.0, "jump": i % 30 < 8})
			await h.run(g, TestHelpers.seconds(0.6), {})
			var q := g.player.pos
			h.expect(Vector2(q.x - p.x, q.z - p.z).length() > 1.0 and g.player.grounded,
				"%s（%s）：そこから部屋の真ん中へ歩いて戻れる（%.2f m）" % [c[4], mode, Vector2(q.x - p.x, q.z - p.z).length()])
	h.free_game(g)


## 跳んで乗れない所：露店の奥の柱・洗濯綱の柱の上（前は 1.2 m の低い箱で、柱の途中の宙に立てた）、工具棚 → 給水塔 → 露店の屋根
## （前は屋根の上を歩けて、靴が帆布の下へ抜けた）、配膳台から食堂の日よけの上
func test_dress_no_ledges() -> void:
	var g := _ch1_game()
	await h.settle()
	g.load_room("ch1.mid", "start")
	for t in g.triggers:
		t.fired = true
	await h.run(g, 4, {})
	var posts := [Vector3(20.2, 0, 8.75), Vector3(27.8, 0, 8.75), Vector3(34.2, 0, 8.75), Vector3(41.8, 0, 8.75), Vector3(30.0, 0, 11.5), Vector3(32.0, 0, 11.5)]
	var stood := []
	for p in posts:
		for a in 8:
			var ang := a * TAU / 8.0
			var start := Vector3(p.x + sin(ang) * 1.4, 0.02, p.z + cos(ang) * 1.4)
			if not _clear(g, start):
				continue
			g.player.teleport(start, ang + PI)
			await h.run(g, 3, {})
			for i in 90:
				var q := g.player.pos
				var d := Vector2(p.x - q.x, p.z - q.z).length()
				g.cam.yaw = atan2(p.x - q.x, p.z - q.z)
				await h.run(g, 1, {"move_y": 1.0 if (d > 0.12 and (q.y > 1.3 or i > 2)) else 0.0, "jump": i < 24})
			await h.run(g, 30, {})
			var q := g.player.pos
			if g.player.grounded and q.y > 0.9 and Vector2(p.x - q.x, p.z - q.z).length() < 0.3:
				stood.append("%s から %d°：(%.2f, %.2f, %.2f)" % [str(p), a * 45, q.x, q.y, q.z])
	h.expect(stood.is_empty(), "露店の奥の柱・洗濯綱の柱の上に立てない（立てた：%s）" % [stood])
	# 工具棚 → 給水塔 → 露店の屋根（実際の操作：跳んで、足が目当ての上より上に来てから向きを入れる）。給水塔の上から屋根へも跳ぶ
	var on_roof := []
	var tower_top := 0.0
	for start in [Vector3(31, 0, 8.2), Vector3(31, 3.25, 13.6)]:
		g.player.teleport(start, 0.0)
		await h.run(g, 20, {})
		if start.y > 1.0:
			tower_top = g.player.pos.y if g.player.grounded else -1.0
		var legs := [[Vector3(31, 1.75, 9.0), 24, 50, false], [Vector3(31, 3.19, 13.6), 24, 80, true], [Vector3(30.2, 3.19, 12.8), 0, 40, false]] if start.y < 1.0 else []
		legs += [[Vector3(27.2, 3.45, 8.2), 24, 90, true], [Vector3(21.0, 3.45, 5.0), 0, 90, false]]
		for leg in legs:
			var to: Vector3 = leg[0]
			var up: bool = int(leg[1]) > 0
			for i in int(leg[2]):
				var q := g.player.pos
				g.cam.yaw = atan2(to.x - q.x, to.z - q.z)
				var d := Vector2(to.x - q.x, to.z - q.z).length()
				var mv := 0.0
				if leg[3] or not up or q.y > to.y + 0.15 or (g.player.grounded and i > 3 and absf(q.y - to.y) < 0.1):
					mv = 1.0 if d > 0.25 else 0.0
				await h.run(g, 1, {"move_y": mv, "jump": up and i < int(leg[1])})
				var r := g.player.pos
				if g.player.grounded and r.y > 3.2 and ((r.x > 19.9 and r.x < 28.1) or (r.x > 33.9 and r.x < 42.1)) and r.z > 3.5 and r.z < 9.1:
					on_roof.append("(%.2f, %.2f, %.2f)" % [r.x, r.y, r.z])
	h.expect(tower_top > 3.0, "給水塔の上には立てる（%.2f）" % tower_top)
	h.expect(on_roof.is_empty(), "工具棚・給水塔から露店の屋根の上へは行けない（%s）" % [on_roof.slice(0, 3)])
	# 配膳台の上から食堂の日よけへ跳ぶ
	var high := 0.0
	for a in [-0.6, 0.0, 0.6]:
		g.player.teleport(Vector3(-20.0 + a * 2.0, 1.02, -0.25), PI)
		await h.run(g, 3, {})
		for i in 80:
			g.cam.yaw = PI + a
			await h.run(g, 1, {"move_y": 1.0 if i > 4 else 0.0, "jump": i < 24})
			if g.player.grounded:
				high = maxf(high, g.player.pos.y)
	h.expect(high < 1.1, "配膳台の上から食堂の日よけの上に乗れない（立った高さ %.2f）" % high)
	h.free_game(g)


## 体（カプセル）が置ける所か（地形・壊せる物・体だけの箱に重ならない）
func _clear(g: GameSim, feet: Vector3) -> bool:
	var q := PhysicsShapeQueryParameters3D.new()
	var cap := CapsuleShape3D.new()
	cap.radius = Player.RADIUS
	cap.height = Player.HEIGHT
	q.shape = cap
	q.transform = Transform3D(Basis(), feet + Vector3(0, Player.HEIGHT / 2.0 + 0.01, 0))
	q.collision_mask = Phys.TERRAIN | Phys.BREAKABLE | Phys.PROP
	return g.phys.get_world_3d().direct_space_state.intersect_shape(q, 1).is_empty()
