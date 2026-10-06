extends RefCounted
## 第 1 章 前半（オープニング〜夜の町、禁足扉まで）の通しのテスト。実際の content/world.json を読み、
## 会話は決定ボタンで送り、場所は目印・出口・トリガーの位置へ置いて進める（歩きの操作そのものは test_feel が見ている）。
## 確かめること：フラグが決まった順に立つ・ニコの救出・父の銃・遺構 B1 への入口が開く・全部屋が読み込める

var h: TestHelpers
var order: Array = []


func _init(helpers: TestHelpers) -> void:
	h = helpers


func _new_game() -> GameSim:
	var g := GameSim.new()
	var vp := SubViewport.new()
	vp.own_world_3d = true
	vp.render_target_update_mode = SubViewport.UPDATE_DISABLED
	vp.size = Vector2i(2, 2)
	h.tree.root.add_child(vp)
	vp.add_child(g)
	g.setup({"world": World.load_manifest("res://content/world.json"), "tuning": TestHelpers.default_tuning(), "seed": 1})
	g.god_mode = true
	order = []
	return g


## n 刻み進める。会話が出ている間は決定ボタンを送る。until が真になったら止めて true を返す
func _pump(g: GameSim, ticks: int, until: Callable = Callable(), kill := false) -> bool:
	for i in ticks:
		await h.tree.physics_frame
		if kill:
			_kill_all(g)
		var f := {}
		if g.story.blocking():
			f = {"jump": (i % 6) < 3}
		g.step(InputFrame.of(f))
		for e in g.drain_events():
			if e.type == "flagSet":
				order.append(e.name)
		if until.is_valid() and until.call():
			return true
	return false


## 倒せる敵（ボスと、倒せない演出の敵を除く）を全部倒す
func _kill_all(g: GameSim) -> void:
	for e in g.enemies.duplicate():
		if e.alive and not e.invulnerable and e != g.boss:
			g.damage_enemy(e, 99999.0, e.pos, {})


func _warp(g: GameSim, p: Vector3, yaw := 0.0) -> void:
	g.player.teleport(p, yaw)
	g.cam.yaw = yaw


## 調べるボタンを 1 回押す（接地を待ってから）
func _use(g: GameSim) -> void:
	await _pump(g, 6)
	await h.tree.physics_frame
	g.step(InputFrame.of({"jump": true}))
	await h.tree.physics_frame
	g.step(InputFrame.of({}))


func _in_order(names: Array) -> bool:
	var last := -1
	for n in names:
		var i := order.find(n)
		if i < 0 or i < last:
			return false
		last = i
	return true


func test_all_rooms_load() -> void:
	var g := _new_game()
	await h.settle()
	h.expect(g.room_id == "ch1.opening", "はじめからの最初の部屋はオープニング（%s）" % g.room_id)
	var ids := []
	for id in g.world.rooms:
		if String(id).begins_with("ch1."):
			ids.append(id)
	h.expect(ids.size() >= 29, "第 1 章の部屋が 29 以上ある（%d）" % ids.size())
	for i in range(1, 21):
		h.expect(g.world.has_room("ch1.r%02d" % i), "遺構の部屋 r%02d がある" % i)
	var bad := 0
	for id in ids:
		# 出口の行き先・出口の戻り目印・目印の存在を確かめる
		var r: Dictionary = g.world.room(id)
		var geo := g.world.geometry(id)
		for p in r.get("props", []):
			if p.type == "exit":
				var to := g.world.resolve(p.to, id)
				if not g.world.has_room(to) or not g.world.geometry(to).markers.has(p.get("spawn", "start")):
					bad += 1
					printerr("  出口の行き先が不正: %s → %s:%s" % [id, to, p.get("spawn")])
		for p in r.get("props", []):
			if p.type != "exit":
				continue
			var ex := RoomGeo.v3(p.pos)
			var sz := RoomGeo.v3(p.get("size", [3, 4, 1]))
			for mk in geo.markers:
				var mp: Vector3 = geo.markers[mk].pos
				if absf(mp.x - ex.x) <= sz.x / 2 and absf(mp.z - ex.z) <= sz.z / 2 and mp.y >= ex.y - 0.1 and mp.y <= ex.y + sz.y:
					bad += 1
					printerr("  目印が出口の範囲の中: %s %s / %s" % [id, mk, p.id])
		# 目印（出てくる位置）が箱の中に埋まっていない（埋まると動けずに詰む。2026-10-06 封印室で起きた）
		for mk in geo.markers:
			var mp: Vector3 = geo.markers[mk].pos
			for gd in r.get("geometry", []):
				if gd.get("t", "") != "box":
					continue
				var bp := RoomGeo.v3(gd.pos)
				var bs := RoomGeo.v3(gd.size)
				var top := bp.y + bs.y
				if absf(mp.x - bp.x) < bs.x / 2 + 0.45 and absf(mp.z - bp.z) < bs.z / 2 + 0.45 \
						and mp.y < top - 0.45 and mp.y + 1.8 > bp.y + 0.05:
					bad += 1
					printerr("  目印が箱に埋まっている: %s %s %s" % [id, mk, mp])
		if not geo.markers.has(r.get("playerStart", "start")):
			bad += 1
			printerr("  始まりの目印が無い: ", id)
		g.load_room(id, String(r.get("playerStart", "start")))
		await _pump(g, 4)
	h.expect(bad == 0, "全部の部屋が読み込めて、出口の行き先がそろっている")
	h.free_game(g)


func test_chapter1_part1_playthrough() -> void:
	var g := _new_game()
	await h.settle()
	await Ch1Run.new(h, TestDriver.new(h.tree, g)).play_part1(g)
	h.free_game(g)



## 実際に歩く：階段で段を登り降りして段へ移れること、訓練場の溝をダッシュジャンプで越えられること
func test_town_walking() -> void:
	var g := _new_game()
	await h.settle()
	# 下段の階段を登って中段へ
	g.load_room("ch1.lower", "start")
	await _pump(g, 6)
	_warp(g, Vector3(0, 0, 8), 0.0)
	var moved := await h.run_until(g, TestHelpers.seconds(20), {"move_y": 1.0}, func(): return g.room_id == "ch1.mid")
	h.expect(moved, "下段の階段を歩いて登ると中段へ移る（%s、y=%.1f）" % [g.room_id, g.player.pos.y])
	await _pump(g, 6)
	h.near(g.player.pos.y, -5.0, 0.3, "中段の階段の下に着く")
	# 中段の階段を登って床へ（踊り場から北へ）
	await h.run_until(g, TestHelpers.seconds(15), {"move_y": 1.0}, func(): return g.player.pos.y > -0.3)
	h.expect(g.room_id == "ch1.mid" and g.player.pos.y > -0.3 and g.player.pos.z > -16.0, "階段を登りきると中段の広場に出る（z=%.1f, y=%.1f）" % [g.player.pos.z, g.player.pos.y])
	# 南へ降りて下段へ
	_warp(g, Vector3(0, 0, -8), PI)
	await h.run_until(g, TestHelpers.seconds(20), {"move_y": 1.0}, func(): return g.room_id == "ch1.lower")
	h.expect(g.room_id == "ch1.lower", "中段の階段を降りると下段へ戻る（%s）" % g.room_id)
	# 訓練場の溝：ダッシュジャンプで越える
	g.set_flag("trigger.ch1.training.start")
	g.load_room("ch1.training", "start")
	await _pump(g, 6)
	_warp(g, Vector3(3, 0, 14), 0.0)
	var dashed := [false]
	await h.run(g, TestHelpers.seconds(4.0), func(i):
		var z: float = g.player.pos.z
		var d: bool = not dashed[0] and z > 22.4
		if d:
			dashed[0] = true
		return {"move_y": 1.0, "dash": d, "jump": z > 25.4})
	h.expect(g.player.pos.z > 32.0 and g.player.pos.y > -0.3, "溝（幅 6 m）をダッシュジャンプで越えられる（z=%.1f, y=%.1f）" % [g.player.pos.z, g.player.pos.y])
	# 溝に落ちても、南のスロープから戻れる
	_warp(g, Vector3(0, -1.5, 29), PI)
	await h.run(g, TestHelpers.seconds(5.0), {"move_y": 1.0})
	h.expect(g.player.pos.y > -0.3 and g.player.pos.z < 26.0, "溝に落ちても南のスロープから戻れる（z=%.1f, y=%.1f）" % [g.player.pos.z, g.player.pos.y])
	h.free_game(g)


## 第 1 章を最後まで：町 → 遺構 B1〜B4 → ボス → 再始動 → 翌朝の町（降下許可・ドリル開発・依頼 2 件）→ 隠し部屋 → 章末。
## 歩きの操作は他のテストが見ているので、場所は目印・出口・トリガーの位置へ置いて進める（敵は倒すか、ボスは HP を減らす確認用の手で倒す）
func test_chapter1_full_run() -> void:
	var g := _new_game()
	await h.settle()
	await Ch1Run.new(h, TestDriver.new(h.tree, g)).play_all(g)
	h.free_game(g)



## ナゴミは封印室のフレームとの適合で仲間になる。それまでの第 1 章の部屋ではハルについて来ない（見た目も隠れる）
func test_nagomi_joins_at_frame_fit() -> void:
	var g := _new_game()
	await h.settle()
	var view := NagomiView.new()
	h.tree.root.add_child(view)
	view.sync(g, Vector3(0, 2, 4), 1.0 / 60.0)
	h.expect(not g.nagomi_present() and not view.visible, "はじめから（オープニング）ではナゴミはいない")
	for id in ["ch1.training", "ch1.mid", "ch1.r01", "ch1.r08"]:
		g.load_room(id)
		await _pump(g, 2)
		view.sync(g, Vector3(0, 2, 4), 1.0 / 60.0)
		h.expect(not g.nagomi_present() and not view.visible, "適合の前の %s ではナゴミはいない" % id)
	g.set_flag(GameSim.NAGOMI_JOIN_FLAG)
	view.sync(g, Vector3(0, 2, 4), 1.0 / 60.0)
	h.expect(g.nagomi_present() and view.visible, "適合のあとはナゴミがいる")
	h.expect(view.global_position.distance_to(g.player.pos) < 2.0, "出てきたナゴミはハルのそばにいる（%.2f m）" % view.global_position.distance_to(g.player.pos))
	g.load_room("ch1.mid")
	await _pump(g, 2)
	h.expect(g.nagomi_present(), "適合のあとは町に戻ってもナゴミがいる")
	g.set_flag(GameSim.NAGOMI_JOIN_FLAG, false)
	g.load_room("sample.hub")
	await _pump(g, 2)
	h.expect(g.nagomi_present(), "見本の部屋では最初からナゴミがいる")
	view.queue_free()
	h.free_game(g)


## 再始動のあとの夜（セーブして中断した場合など）でも、ハルの家のベッドで休めば夜が明ける
func test_sleep_after_restart_brings_morning() -> void:
	var g := _new_game()
	await h.settle()
	for f in ["ch1.night", "ch1.ordo_stopped", "ch1.ordo_restarted", "ch1.debt_scene"]:
		g.set_flag(f)
	g.load_room("ch1.home", "from_lower")
	await _pump(g, 6)
	_warp(g, Vector3(-3, 0, 3.5))
	await _use(g)
	h.expect(await _pump(g, 3000, func(): return g.flag("ch1.morning") and not g.story.running_event()), "再始動のあとの夜は、ベッドで休むと朝になる")
	h.expect(not g.flag("ch1.night") and g.room_id == "ch1.home", "夜が明けてハルの家で目覚める")
	# 再始動の前の夜は、まだ眠れない
	var g2 := _new_game()
	await h.settle()
	for f in ["ch1.night", "ch1.ordo_stopped", "ch1.debt_scene"]:
		g2.set_flag(f)
	g2.load_room("ch1.home", "from_lower")
	await _pump(g2, 6)
	_warp(g2, Vector3(-3, 0, 3.5))
	await _use(g2)
	await _pump(g2, 120)
	h.expect(g2.flag("ch1.night") and not g2.flag("ch1.morning"), "再始動の前は眠れない")
	h.free_game(g)
	h.free_game(g2)


## 実際に歩く：整備通路（B1）の溝を、走ってジャンプで渡りきれること（溝 1.5〜3.5m・段 1.0m）
func test_ruins_walking_maintenance_corridor() -> void:
	var g := _new_game()
	await h.settle()
	g.set_flag("ch1.got_spark")
	g.load_room("ch1.r03", "from_r02")
	for t in g.triggers:
		t.fired = true
	await _pump(g, 6)
	var edges := [-13.0, -7.0, -0.5, 7.5, 13.5]
	var next := [0]
	var hold := [0]
	var fell := [false]
	await h.run(g, TestHelpers.seconds(14.0), func(i):
		var z: float = g.player.pos.z
		if g.player.pos.y < -1.0:
			fell[0] = true
		if next[0] < edges.size() and z >= edges[next[0]] - 0.5 and g.player.grounded:
			next[0] += 1
			hold[0] = 24
		var jump: bool = hold[0] > 0
		if hold[0] > 0:
			hold[0] -= 1
		return {"move_y": 1.0, "jump": jump})
	h.expect(not fell[0], "整備通路：走ってジャンプするだけで、溝に落ちずに渡れる")
	h.expect(g.room_id == "ch1.r04" or g.player.pos.z > 15.0, "整備通路を渡りきる（%s, z=%.1f）" % [g.room_id, g.player.pos.z])
	h.free_game(g)


## 実際に歩く：駆動回廊（B3）のピストンを、タイミングを見て跳び移って渡りきれること（動力が通った状態）
func test_ruins_walking_pistons() -> void:
	var g := _new_game()
	await h.settle()
	g.set_flag("ch1.drive_powered")
	g.load_room("ch1.r12", "from_r11")
	for t in g.triggers:
		t.fired = true
	await _pump(g, 6)
	var edges := [-10.4, -3.4, 4.6, 12.6]
	var targets := ["ch1.r12.p1", "ch1.r12.p2", "ch1.r12.p3", ""]
	var hop := [0]
	var hold := [0]
	var fell := [false]
	var reached := await h.run_until(g, 4000, func(i):
		var z: float = g.player.pos.z
		var y: float = g.player.pos.y
		if y < -3.0:
			fell[0] = true
		var inp := {}
		if hold[0] > 0:
			hold[0] -= 1
			return {"move_y": 1.0, "jump": true}
		if hop[0] >= edges.size():
			return {"move_y": 1.0}
		if z < edges[hop[0]] - 0.3:
			return {"move_y": 1.0}
		if g.player.grounded:
			var top := 0.0
			if targets[hop[0]] != "":
				var mv: Props.Mover = g.movers.filter(func(m): return m.id == targets[hop[0]])[0]
				top = mv.pos.y + mv.size.y
			if absf(top - y) <= 0.9:
				hop[0] += 1
				hold[0] = 26
				return {"move_y": 1.0, "jump": true}
		return inp, func(): return g.player.pos.z > 16.5 or fell[0])
	h.expect(reached and not fell[0], "駆動回廊：ピストンを見て跳び移れば渡りきれる（z=%.1f, 落下=%s）" % [g.player.pos.z, str(fell[0])])
	h.free_game(g)


## Ch1Run 用の運転役：物理の 1 刻みごとに game.step を呼ぶ（画面・音なし）
class TestDriver:
	extends RefCounted
	var tree: SceneTree
	var g: GameSim

	func _init(t: SceneTree, game: GameSim) -> void:
		tree = t
		g = game

	func tick(f: Dictionary) -> void:
		await tree.physics_frame
		g.step(InputFrame.of(f))
		g.drain_events()

	func shot(_name: String) -> void:
		pass

	func milestone(_name: String) -> void:
		pass

	func after_warp() -> void:
		pass
