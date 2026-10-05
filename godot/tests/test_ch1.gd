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
func _pump(g: GameSim, ticks: int, until: Callable = Callable()) -> bool:
	for i in ticks:
		await h.tree.physics_frame
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
	h.expect(ids.size() >= 11, "第 1 章の部屋が 11 以上ある（%d）" % ids.size())
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
	# 1 オープニング：自動で進み、訓練場へ
	h.expect(await _pump(g, 1800, func(): return g.room_id == "ch1.training"), "オープニングのあと訓練場に移る")
	h.expect(g.flag("ch1.opening_done"), "オープニングが終わる")
	# 2 見習いの仕事
	h.expect(await _pump(g, 1800, func(): return g.flag("ch1.chores_started") and not g.story.running_event()), "バートンに仕事を言いつけられる")
	_warp(g, Vector3(0, 0, -8))
	await _pump(g, 20)
	h.expect(g.flag("ch1.t_move"), "歩く練習の床で案内が進む")
	_warp(g, Vector3(0, 1.8, 6))
	await _pump(g, 20)
	h.expect(g.flag("ch1.t_jump"), "跳ぶ練習の段で案内が進む")
	for id in ["ch1.tg1", "ch1.tg2", "ch1.tg3"]:
		g.activate_switch(g.switch_by_id(id))
	await _pump(g, 20)
	h.expect(g.flag("ch1.t_shoot"), "的を 3 つ撃つと案内が進む")
	_warp(g, Vector3(0, 0, 22))
	await _pump(g, 20)
	_warp(g, Vector3(0, 0, 35))
	await _pump(g, 20)
	h.expect(g.flag("ch1.t_dash"), "溝を越えると案内が進む")
	h.expect(g.npcs.any(func(n): return n.id == "npc_nico"), "訓練場にニコがいる")
	# 残骸を片付けるとニコが禁足扉へ走る
	g.activate_switch(g.switch_by_id("ch1.w1"))
	h.expect(await _pump(g, 1800, func(): return g.flag("ch1.nico_ran") and not g.story.running_event()), "ニコが禁足扉へ走っていく")
	h.expect(not g.npcs.any(func(n): return n.id == "npc_nico"), "走り去ったニコは訓練場から消える")
	h.expect(g.flag("ch1.gate_open"), "禁足扉が開く")
	# 町の下段へ。禁足扉が自動で開く
	g.go_to("ch1.lower", "from_training")
	await _pump(g, 30)
	h.expect(g.room_id == "ch1.lower", "訓練場の出口から下段へ")
	var gate = g.door_by_id("ch1.lower.gate")
	h.expect(gate != null and gate.is_open, "ニコが入ったあと禁足扉は開いている")
	# 3 ニコの救出（初めての戦闘）
	_warp(g, Vector3(-46.5, 0, 0), 270)
	await _pump(g, 40)
	h.expect(g.room_id == "ch1.r01", "禁足扉から前室に入る（%s）" % g.room_id)
	var b1 = g.exits.filter(func(x): return x.id == "ch1.r01.to_r02")[0]
	h.expect(not Cond.eval(b1.lock, g), "ニコを救うまで・銃をもらうまで、遺構 B1 への入口は閉じている")
	_warp(g, Vector3(0, 0, -6))
	h.expect(await _pump(g, 600, func(): return g.enemies.size() > 0), "小さな番機が現れる")
	h.expect(g.enemies[0].kind == "mini" and g.npcs.any(func(n): return n.id == "npc_nico"), "子番機とニコ")
	await _pump(g, 120)
	for e in g.enemies:
		g.damage_enemy(e, 9999.0, e.pos, {})
	h.expect(await _pump(g, 2400, func(): return g.flag("ch1.nico_rescued") and g.room_id == "ch1.lower"), "倒すとニコを連れて町へ戻る（%s）" % g.room_id)
	await _pump(g, 10)
	gate = g.door_by_id("ch1.lower.gate")
	h.expect(gate != null and not gate.is_open, "町へ戻ると禁足扉は閉じている")
	# 4 昼の町：下段→中段→上段の階段、ギルドで説教
	_warp(g, Vector3(0, 5, 33))
	await _pump(g, 30)
	h.expect(g.room_id == "ch1.mid", "下段の階段で中段へ（%s）" % g.room_id)
	h.near(g.player.pos.y, -5.0, 0.5, "階段の下の踊り場に着く")
	_warp(g, Vector3(0, 5, 33))
	await _pump(g, 30)
	h.expect(g.room_id == "ch1.upper", "中段の階段で上段へ（%s）" % g.room_id)
	_warp(g, Vector3(20, 0, 5.2))
	await _pump(g, 30)
	h.expect(g.room_id == "ch1.guild", "上段からギルドへ（%s）" % g.room_id)
	h.expect(await _pump(g, 3000, func(): return g.flag("ch1.scolded") and not g.story.running_event()), "ギルドで叱られる")
	# ツケの場面
	g.load_room("ch1.workshop", "from_mid")
	h.expect(await _pump(g, 3000, func(): return g.flag("ch1.debt_scene") and not g.story.running_event()), "工房でツケの場面（選択肢つき）")
	# 5 停止：家で休む
	g.load_room("ch1.home", "from_lower")
	await _pump(g, 6)
	_warp(g, Vector3(-3, 0, 3.5))
	await _use(g)
	h.expect(await _pump(g, 3000, func(): return g.flag("ch1.ordo_stopped") and not g.story.running_event()), "休むと夜、オルドが止まる")
	h.expect(g.flag("ch1.night") and g.room_id == "ch1.home", "夜になる")
	# 広場：町長の話
	g.load_room("ch1.mid", "start")
	await _pump(g, 6)
	_warp(g, Vector3(0, 0, 3))
	h.expect(await _pump(g, 3000, func(): return g.flag("ch1.plaza_done") and not g.story.running_event()), "広場で町長の話を聞く")
	h.expect(g.cells == 300, "見舞金 300 セルをもらう（%d）" % g.cells)
	# 雑貨屋で補修パックを買う
	var heals := g.player.heals
	var r := Economy.buy(g, "zakka", "consumable.repair")
	h.expect(r.ok and g.player.heals == heals + 1 and g.cells == 150, "夜の町で補修パックを買える")
	# 6 禁足扉：ヤーナから父の銃
	g.load_room("ch1.lower", "start")
	await _pump(g, 6)
	h.expect(g.npcs.any(func(n): return n.id == "npc_yana"), "夜の禁足扉にヤーナがいる")
	_warp(g, Vector3(-37, 0, 0), 90)
	h.expect(await _pump(g, 3000, func(): return g.flag("ch1.got_spark") and not g.story.running_event()), "禁足扉でヤーナが父の銃を渡す")
	h.expect(g.has_item("weapon.spark"), "スパークを手に入れる")
	await _pump(g, 30)
	gate = g.door_by_id("ch1.lower.gate")
	h.expect(gate != null and gate.is_open, "夜の禁足扉が開く")
	# 遺構 B1 への入口
	_warp(g, Vector3(-46.5, 0, 0), 270)
	await _pump(g, 40)
	h.expect(g.room_id == "ch1.r01", "禁足扉から前室へ")
	b1 = g.exits.filter(func(x): return x.id == "ch1.r01.to_r02")[0]
	h.expect(Cond.eval(b1.lock, g), "遺構 B1 への入口が開いている")
	_warp(g, Vector3(0, 0, 13))
	await _pump(g, 40)
	h.expect(g.room_id == "ch1.r02", "入口から遺構 B1 へ（%s）" % g.room_id)
	# フラグの立つ順（30 の 4.6 の表）
	h.expect(_in_order(["ch1.chores_started", "ch1.nico_rescued", "ch1.scolded", "ch1.debt_scene", "ch1.ordo_stopped", "ch1.got_spark"]),
		"フラグが決まった順に立つ（%s）" % str(order.filter(func(n): return n.begins_with("ch1.") and not n.begins_with("ch1.t_"))))
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
