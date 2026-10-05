class_name Ch1Run
extends RefCounted
## 第 1 章の通し（「はじめから」から「第 1 章 クリア」まで）の台本。自動テスト（tests/test_ch1.gd）と、実際のゲームの中で動かす自動操作
## （--demo=… --ch1_full、debug/demo.gd）の両方が使う。会話は決定ボタンで送り、歩きが不安定な場所は目印・出口・トリガーへ置いて進める。
## driver：tick(frame: Dictionary)（1 刻み進める・コルーチン）、shot(name)（画面を撮る・コルーチン）、after_warp()、milestone(name) を持つ。

var h
var driver


func _init(helpers, drv) -> void:
	h = helpers
	driver = drv


func _pump(g: GameSim, ticks: int, until: Callable = Callable(), kill := false, hold := {}) -> bool:
	for i in ticks:
		if kill:
			_kill_all(g)
		var f := hold
		if g.story.blocking():
			f = {"jump": (i % 6) < 3}
		await driver.tick(f)
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
	driver.after_warp()


## 調べるボタンを 1 回押す（接地を待ってから）
func _use(_g: GameSim) -> void:
	await _pump(_g, 6)
	await driver.tick({"jump": true})
	await driver.tick({})


## フラグが立った順（story.flags は入れた順を保つ）
func flag_order(g: GameSim) -> Array:
	return g.story.flags.keys().filter(func(k): return g.story.flags[k])


func _in_order(g: GameSim, names: Array) -> bool:
	var order := flag_order(g)
	var last := -1
	for n in names:
		var i := order.find(n)
		if i < 0 or i < last:
			return false
		last = i
	return true


## 最初から最後まで
func play_all(g: GameSim) -> void:
	await play_part1(g)
	await play_part2(g)


## 第 1 章 前半（オープニング〜遺構 B1 の入口）を最後まで進める。終わると遺構 B1（ch1.r02）にいる
func play_part1(g: GameSim) -> void:
	# 1 オープニング：自動で進み、訓練場へ
	h.expect(await _pump(g, 1800, func(): return g.room_id == "ch1.training"), "オープニングのあと訓練場に移る")
	h.expect(g.flag("ch1.opening_done"), "オープニングが終わる")
	await driver.milestone("01_opening")
	# 2 見習いの仕事
	h.expect(await _pump(g, 1800, func(): return g.flag("ch1.chores_started") and not g.story.running_event()), "バートンに仕事を言いつけられる")
	# ここだけは本当に歩く（前へ押し続ける）。ほかは目印へ置いて進める
	h.expect(await _pump(g, 900, func(): return g.flag("ch1.t_move"), false, {"move_y": 1.0}), "歩く練習の床まで歩くと案内が進む")
	_warp(g, Vector3(0, 1.8, 6))
	await _pump(g, 20)
	h.expect(g.flag("ch1.t_jump"), "跳ぶ練習の段で案内が進む")
	for id in ["ch1.tg1", "ch1.tg2", "ch1.tg3"]:
		g.activate_switch(g.switch_by_id(id))
	await _pump(g, 20)
	h.expect(g.flag("ch1.t_shoot"), "的を 3 つ撃つと案内が進む")
	await driver.milestone("02_training_dummy")
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
	await driver.milestone("03_guild")
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
	await driver.milestone("04_spark")
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
	h.expect(_in_order(g, ["ch1.chores_started", "ch1.nico_rescued", "ch1.scolded", "ch1.debt_scene", "ch1.ordo_stopped", "ch1.got_spark"]),
		"フラグが決まった順に立つ（%s）" % str(flag_order(g).filter(func(n): return n.begins_with("ch1.") and not n.begins_with("ch1.t_"))))



## 第 1 章の後半（遺構 B1 から章末まで）。part1 の終わり（遺構 B1 の入口）から続ける
func play_part2(g: GameSim) -> void:
	g.god_mode = true
	h.expect(g.room_id == "ch1.r02", "B1 の入口から始まる（%s）" % g.room_id)
	# ---- B1 外殻層
	_warp(g, Vector3(0, 0, -8))
	await _pump(g, 400, func(): return g.objective.contains("遺構の奥") and not g.story.running_event())
	h.expect(g.objective.contains("遺構の奥"), "ジャンク溜まりで目的が出る")
	var cells0 := g.cells
	_warp(g, Vector3(-8.5, 1.85, -3.4))
	await _use(g)
	h.expect(g.flag("chest.ch1.r02.chest1") and g.cells == cells0 + 50, "ジャンクの山の宝箱（50 セル）")
	_warp(g, Vector3(7.2, 1.9, 5.2))
	await _pump(g, 10)
	h.expect(g.relics.has("relic.old_gear"), "山の上の遺物を拾える")
	_warp(g, Vector3(0, 0, 12))
	await _pump(g, 40)
	h.expect(g.room_id == "ch1.r03", "整備通路へ（%s）" % g.room_id)
	_warp(g, Vector3(0, 0, -15))
	await _pump(g, 60)
	_warp(g, Vector3(0, 0, 18.4))
	await _pump(g, 40)
	h.expect(g.room_id == "ch1.r04", "換気室へ（%s）" % g.room_id)
	h.expect(g.enemies.size() == 2 and g.enemies[0].kind == "mini", "換気室に子番機 2 体")
	_warp(g, Vector3(0, 0, -7))
	await _pump(g, 400, func(): return not g.story.running_event())
	await _pump(g, 6, Callable(), true)
	var door = g.door_by_id("ch1.r04.door")
	h.expect(door != null and not door.is_open, "弁が詰まっている間、換気室の扉は閉じている")
	g.activate_switch(g.switch_by_id("ch1.r04.v1"))
	g.activate_switch(g.switch_by_id("ch1.r04.v2"))
	await _pump(g, 30)
	h.expect(g.door_by_id("ch1.r04.door").is_open, "弁を 2 つ撃つと扉が開く")
	_warp(g, Vector3(0, 0, 11))
	await _pump(g, 40)
	h.expect(g.room_id == "ch1.r05", "崩落床の部屋へ（%s）" % g.room_id)
	# ---- 崩落 → B2
	_warp(g, Vector3(0, 0, 3))
	h.expect(await _pump(g, 1800, func(): return g.room_id == "ch1.r06" and g.flag("ch1.fell_to_b2") and not g.story.running_event()), "床が崩れて B2 の落下地点へ（%s）" % g.room_id)
	h.expect(g.player.hp > 0.0, "落下してもやられない")
	_warp(g, Vector3(-8, 0, 11))
	await _use(g)
	h.expect(g.player.heals >= 1 and g.flag("chest.ch1.r06.chest1"), "落下地点の宝箱（補修パック）")
	_warp(g, Vector3(0, 0, 14))
	await _pump(g, 40)
	h.expect(g.room_id == "ch1.r07", "追跡通路へ（%s）" % g.room_id)
	# 追跡：倒せない歩哨型が 2 体
	_warp(g, Vector3(0, 0, -12))
	h.expect(await _pump(g, 600, func(): return g.enemies.size() >= 2 and not g.story.blocking()), "歩哨型に追われる")
	var chasers := g.enemies.filter(func(e): return e.kind == "sentry")
	h.expect(chasers.size() == 2 and chasers.all(func(e): return e.invulnerable), "追ってくる歩哨型 2 体は倒せない")
	g.damage_enemy(chasers[0], 9999.0, chasers[0].pos, {})
	h.expect(chasers[0].alive, "撃っても倒せない")
	var exit_b: Props.Exit = g.exits.filter(func(x): return x.id == "ch1.r07.to_r08")[0]
	h.expect(not Cond.eval(exit_b.lock, g), "行き止まりの間は、奥の壁が閉じている")
	_warp(g, Vector3(0, 0, 14))
	h.expect(await _pump(g, 900, func(): return g.flag("ch1.r07.seal_open") and not g.story.running_event()), "行き止まりで壁がハルに反応して開く")
	_warp(g, Vector3(0, 0, 18.6))
	await _pump(g, 40)
	h.expect(g.room_id == "ch1.r08", "封印室へ（%s）" % g.room_id)
	h.expect(not g.enemies.any(func(e): return e.alive), "封印室に追っ手は入ってこない")
	# ---- フレームとの適合・ナゴミ起動・訓練
	_warp(g, Vector3(0, 0, -4))
	h.expect(await _pump(g, 3000, func(): return g.flag("ch1.frame_fitted") and not g.story.blocking()), "フレームとの適合が起きる")
	h.expect(g.has_item("frame.vestige"), "フレーム〈ヴェスティージ〉を手に入れる")
	h.expect(await _pump(g, 6000, func(): return g.flag("ch1.r08.trained") and not g.story.running_event(), true), "ロックオン・ダッシュ・光刃の練習が終わる")
	_warp(g, Vector3(0, 0, 10))
	await _pump(g, 40)
	h.expect(g.room_id == "ch1.r09", "配管広間へ（%s）" % g.room_id)
	# ---- 配管広間：歩哨型 3 → 突撃型 1
	h.expect(g.enemies.filter(func(e): return e.kind == "sentry").size() == 3, "配管広間：歩哨型 3 体")
	h.expect(not g.door_by_id("ch1.r09.door").is_open, "戦闘中は奥の扉が閉じている")
	h.expect(await _pump(g, 3000, func(): return g.enemies.any(func(e): return e.kind == "charger") or g.flag("ch1.r09.cleared"), true), "歩哨型を倒すと突撃型が出る")
	h.expect(await _pump(g, 3000, func(): return g.flag("ch1.r09.cleared") and not g.story.running_event(), true), "突撃型も倒すと広間を制圧")
	await _pump(g, 20)
	h.expect(g.door_by_id("ch1.r09.door").is_open, "制圧すると扉が開く")
	_warp(g, Vector3(0, 0, 11))
	await _pump(g, 40)
	h.expect(g.room_id == "ch1.r10", "弁の間へ（%s）" % g.room_id)
	h.expect(g.enemies.any(func(e): return e.kind == "shield"), "弁の間：盾型がいる")
	await _pump(g, 6000, func(): return g.group_cleared("r10_w1"), true)
	h.expect(g.group_cleared("r10_w1"), "盾型と歩哨型を倒す")
	g.activate_switch(g.switch_by_id("ch1.r10.valve"))
	await _pump(g, 30)
	h.expect(g.door_by_id("ch1.r10.door").is_open, "弁の輪を撃つと扉が開く")
	_warp(g, Vector3(9, 0, -8.5))
	await _use(g)
	h.expect(g.flag("chest.ch1.r10.chest1"), "弁の間の宝箱")
	_warp(g, Vector3(0, 0, 11))
	await _pump(g, 40)
	h.expect(g.room_id == "ch1.r11", "縦坑へ（%s）" % g.room_id)
	h.near(g.player.pos.y, 21.0, 0.5, "縦坑の上の足場から始まる")
	_warp(g, Vector3(0, 0, 0.8))
	await _use(g)
	h.expect(await _pump(g, 600, func(): return g.flag("ch1.first_beacon") and not g.story.running_event()), "縦坑の底に最初のセーブビーコン")
	_warp(g, Vector3(0, 0, 5))
	await _pump(g, 40)
	h.expect(g.room_id == "ch1.r12", "駆動回廊へ（%s）" % g.room_id)
	# ---- B3 駆動層：動力を流す
	_warp(g, Vector3(0, 0, -15))
	await _pump(g, 400, func(): return not g.story.running_event())
	var mv: Props.Mover = g.movers.filter(func(m): return m.id == "ch1.r12.p1")[0]
	var y0: float = mv.pos.y
	await _pump(g, 60)
	h.near(mv.pos.y, y0, 0.01, "動力が通る前、ピストンは止まっている")
	g.activate_switch(g.switch_by_id("ch1.r12.s1"))
	g.activate_switch(g.switch_by_id("ch1.r12.s2"))
	h.expect(await _pump(g, 900, func(): return g.flag("ch1.drive_powered") and not g.story.running_event()), "動力の球を 2 つ撃つと駆動層に動力が戻る")
	var lo := mv.pos.y
	var hi := mv.pos.y
	for i in 400:
		await _pump(g, 1)
		lo = minf(lo, mv.pos.y)
		hi = maxf(hi, mv.pos.y)
	h.expect(hi - lo > 2.0, "動力が戻るとピストンが往復する（y %.2f〜%.2f）" % [lo, hi])
	var to14: Props.Exit = g.exits.filter(func(x): return x.id == "ch1.r12.to_r14")[0]
	h.expect(not Cond.eval(to14.lock, g), "ひび割れた壁の奥（隠し部屋）は、まだ入れない")
	# 近道のエレベーター（B3 の内側から開ける）
	_warp(g, Vector3(7.2, 0, -14))
	await _pump(g, 40)
	h.expect(g.room_id == "ch1.r17", "近道の部屋へ（%s）" % g.room_id)
	var to02: Props.Exit = g.exits.filter(func(x): return x.id == "ch1.r17.to_r02")[0]
	h.expect(not Cond.eval(to02.lock, g), "レバーを引く前、エレベーターは動かない")
	_warp(g, Vector3(0, 0, -3.4))
	await _use(g)
	h.expect(await _pump(g, 600, func(): return g.flag("ch1.shortcut_open") and not g.story.running_event()), "レバーを引くと近道が開く")
	_warp(g, Vector3(-4.6, 0, -3))
	await _pump(g, 40)
	h.expect(g.room_id == "ch1.r02" and g.player.pos.x > 7.0, "エレベーターで外殻層のジャンク溜まりへ（%s）" % g.room_id)
	_warp(g, Vector3(12, 0, 0))
	await _pump(g, 40)
	h.expect(g.room_id == "ch1.r17", "外殻層からもエレベーターで B3 へ戻れる（%s）" % g.room_id)
	_warp(g, Vector3(4.6, 0, 3))
	await _pump(g, 40)
	h.expect(g.room_id == "ch1.r12", "近道の部屋から駆動回廊へ（%s）" % g.room_id)
	_warp(g, Vector3(0, 0, 18))
	await _pump(g, 40)
	h.expect(g.room_id == "ch1.r13", "歯車の間へ（%s）" % g.room_id)
	h.expect(g.enemies.filter(func(e): return e.kind == "floater").size() == 3, "歯車の間：浮遊型 3 体")
	h.expect(await _pump(g, 3000, func(): return g.flag("ch1.r13.cleared"), true), "浮遊型を倒す")
	_warp(g, Vector3(0, 4.1, 10.2))
	await _use(g)
	h.expect(g.flag("chest.ch1.r13.chest1"), "張り出しの宝箱")
	_warp(g, Vector3(0, 0, 14))
	await _pump(g, 40)
	h.expect(g.room_id == "ch1.r15", "伝導路へ（%s）" % g.room_id)
	h.expect(await _pump(g, 6000, func(): return g.flag("ch1.r15.cleared") and not g.story.running_event(), true), "伝導路の混戦を制圧")
	_warp(g, Vector3(9, 0, 9))
	await _use(g)
	h.expect(g.has_item("chip.charge"), "伝導路の宝箱：チップ「チャージ化」")
	_warp(g, Vector3(0, 0, 11))
	await _pump(g, 40)
	h.expect(g.room_id == "ch1.r16", "中央縦坑へ（%s）" % g.room_id)
	_warp(g, Vector3(0, 20.3, 0.4))
	await _pump(g, 400)
	h.expect(g.player.pos.y < 8.0, "リフトに乗ると下へ降りる（y=%.1f）" % g.player.pos.y)
	await _pump(g, 3000, func(): return g.flag("ch1.r16.cleared"), true)
	h.expect(g.flag("ch1.r16.cleared"), "待ち伏せの突撃型 2 体を倒す")
	_warp(g, Vector3(0, 0, 5))
	await _pump(g, 40)
	h.expect(g.room_id == "ch1.r18", "心臓部前室へ（%s）" % g.room_id)
	# ---- B4 診断・ボス
	var to19: Props.Exit = g.exits.filter(func(x): return x.id == "ch1.r18.to_r19")[0]
	h.expect(not Cond.eval(to19.lock, g), "診断の前は、心臓部の扉が開かない")
	_warp(g, Vector3(0, 0, -3))
	h.expect(await _pump(g, 3000, func(): return g.flag("ch1.diagnosis") and not g.story.running_event()), "ナゴミの診断")
	_warp(g, Vector3(-5, 0, 2))
	await _use(g)
	await _pump(g, 400, func(): return not g.story.running_event())
	_warp(g, Vector3(0, 0, 11))
	await _pump(g, 40)
	h.expect(g.room_id == "ch1.r19", "心臓部（ボス部屋）へ（%s）" % g.room_id)
	h.expect(await _pump(g, 3000, func(): return g.flag("ch1.boss_intro") and not g.story.running_event()), "戦闘前の会話")
	h.expect(g.boss != null and g.boss.alive, "ボス「閂」がいる")
	await driver.milestone("05_boss_room")
	_warp(g, Vector3(0, 0, 6), PI)
	await _pump(g, 400, func(): return not g.boss_status().is_empty())
	h.expect(not g.boss_status().is_empty(), "戦闘が始まり、体力バーが出る")
	await driver.milestone("06_boss_fight")
	# 確認用：段階 3・核を開けて、1 撃ずつ削って倒す（戦闘そのものは test_boss が見ている）
	g.boss.debug_set_phase(3)
	await _pump(g, 30)
	g.boss.core_open = true
	var guard := 0
	while g.boss.alive and guard < 200:
		g.damage_enemy(g.boss, 60.0, g.player.pos, {"melee": true, "at": g.boss.axis_center()})
		guard += 1
	h.expect(not g.boss.alive and g.flag("ch1.boss_defeated"), "閂を倒すとフラグが立つ")
	h.expect(await _pump(g, 1200, func(): return g.material_count("core.kannuki") == 1 and not g.story.running_event()), "閂のコアを手に入れる")
	await driver.milestone("07_core")
	h.expect(g.door_by_id("ch1.r19.furnace").is_open, "炉心の扉が開く")
	# 倒したボスは、入り直しても出ない
	g.load_room("ch1.r19", "from_r18")
	await _pump(g, 20)
	h.expect(g.boss == null or not g.boss.alive, "倒したあとの心臓部に、閂は戻らない")
	_warp(g, Vector3(0, 0, -14.3))
	await _pump(g, 40)
	h.expect(g.room_id == "ch1.r20", "炉心へ（%s）" % g.room_id)
	# ---- 再始動 → ノードの記憶 → 歓声 → 夜明け
	h.expect(g.flag("ch1.night"), "再始動の前はまだ夜")
	_warp(g, Vector3(0, 0, -5))
	h.expect(await _pump(g, 6000, func(): return g.flag("ch1.morning") and g.room_id == "ch1.home" and not g.story.running_event()), "再始動 → 歓声 → 翌朝、ハルの家で目覚める（%s）" % g.room_id)
	h.expect(g.flag("ch1.ordo_restarted"), "オルドが再び歩き出した")
	await driver.milestone("08_restarted")
	h.expect(not g.flag("ch1.night"), "夜が明けて、フラグ ch1.night が消える")
	# ---- 翌朝の町
	g.load_room("ch1.guild", "from_upper")
	await _pump(g, 6)
	_warp(g, Vector3(0, 0, 3.4))
	await _use(g)
	h.expect(await _pump(g, 3000, func(): return g.flag("ch1.descent_permit") and not g.story.running_event()), "ギルドで降下許可をもらう")
	h.expect(g.mark == "降下許可", "回収屋の印が「降下許可」になる（%s）" % g.mark)
	h.expect(Economy.accept_request(g, "ch1.req.marble").ok and Economy.accept_request(g, "ch1.req.parcel").ok, "依頼板の 2 件の依頼を受けられる")
	g.load_room("ch1.workshop", "from_mid")
	await _pump(g, 6)
	_warp(g, Vector3(3, 0, 1.4))
	await _use(g)
	await _pump(g, 1500, func(): return not g.story.running_event())
	h.expect(not g.has_item("special.drill"), "工房で話しただけでは、ドリルは手に入らない")
	var cr := Economy.craft(g, "yana", "drill")
	h.expect(cr.ok and g.has_item("special.drill") and g.material_count("core.kannuki") == 0, "工房で閂のコアからブレイクドリルを開発する")
	h.expect(await _pump(g, 1500, func(): return g.flag("ch1.drill_developed") and not g.story.running_event()), "ヤーナがドリルの使い道を話す")
	# サブ依頼 1：ニコのビー玉
	g.load_room("ch1.r02", "from_r01")
	await _pump(g, 6)
	_warp(g, Vector3(-9, 1.5, 7))
	await _pump(g, 20)
	h.expect(g.has_item("quest.marble"), "ジャンク溜まりでビー玉を見つける")
	g.load_room("ch1.lower", "from_home")
	await _pump(g, 6)
	h.expect(g.npcs.any(func(n): return n.id == "npc_nico"), "朝の下段にニコがいる")
	_warp(g, Vector3(14, 0, 1.4))
	await _use(g)
	await _pump(g, 1500, func(): return g.flag("ch1.marble_returned") and not g.story.running_event())
	var c1 := g.cells
	h.expect(Economy.complete_request(g, "ch1.req.marble").ok and g.cells == c1 + 200, "ビー玉を返して依頼を達成（セル +200）")
	# サブ依頼 2：雑貨屋の配達
	g.load_room("ch1.mid", "start")
	await _pump(g, 6)
	_warp(g, Vector3(24, 0, 3.4))
	await _use(g)
	await _pump(g, 1500, func(): return g.flag("ch1.parcel_taken") and not g.story.running_event())
	h.expect(g.flag("ch1.parcel_taken"), "雑貨屋の荷物を預かる")
	g.load_room("ch1.lower", "start")
	await _pump(g, 6)
	_warp(g, Vector3(30, 0, 1.4))
	await _use(g)
	await _pump(g, 1500, func(): return g.flag("ch1.parcel_delivered") and not g.story.running_event())
	h.expect(Economy.complete_request(g, "ch1.req.parcel").ok, "荷物を届けて依頼を達成")
	h.expect(g.guild_points == 20, "ギルドポイント +20（%d）" % g.guild_points)
	# ---- 再訪：B3 のひび割れた壁をドリルで壊す
	g.load_room("ch1.r12", "from_r11")
	await _pump(g, 6)
	var cr_wall = g.breakables.filter(func(b): return b.id == "ch1.r12.crack")[0]
	g.drill_breakable(cr_wall, 5.0)
	await _pump(g, 6)
	h.expect(cr_wall.broken, "ドリルでひび割れた壁を壊す")
	_warp(g, Vector3(-7.2, 0, -14))
	await _pump(g, 40)
	h.expect(g.room_id == "ch1.r14", "壊した壁の奥の隠し部屋へ（%s）" % g.room_id)
	var hp0 := g.player.max_hp
	_warp(g, Vector3(0, 0.9, 0))
	await _pump(g, 20)
	h.expect(g.has_item("item.lifecore") and g.player.max_hp == hp0 + 20.0, "隠し部屋のライフコア（最大 HP +20）")
	# ---- 章末
	g.load_room("ch1.upper", "start")
	await _pump(g, 6)
	_warp(g, Vector3(0, 0, 22.6))
	await _use(g)
	h.expect(await _pump(g, 3000, func(): return g.flag("ch1.complete") and not g.story.running_event()), "展望台で章末の演出が走る")
	await driver.milestone("09_ending")
	# 17 個のフラグが決まった順に立つ（30 の 4.6）
	var names := ["ch1.chores_started", "ch1.nico_rescued", "ch1.scolded", "ch1.debt_scene", "ch1.ordo_stopped", "ch1.got_spark", "ch1.fell_to_b2",
		"ch1.frame_fitted", "ch1.first_beacon", "ch1.drive_powered", "ch1.shortcut_open", "ch1.diagnosis", "ch1.boss_defeated",
		"ch1.ordo_restarted", "ch1.descent_permit", "ch1.drill_developed", "ch1.complete"]
	for n in names:
		h.expect(g.flag(n), "フラグ %s が立っている" % n)
	h.expect(_in_order(g, names), "第 1 章のフラグ 17 個が決まった順に立つ（%s）" % str(flag_order(g).filter(func(n): return names.has(n))))

