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
	# 訓練場の溝：適合の前なのでダッシュは無い。走りジャンプで越える
	g.set_flag("trigger.ch1.training.start")
	g.load_room("ch1.training", "start")
	await _pump(g, 6)
	_warp(g, Vector3(3, 0, 14), 0.0)
	await h.run(g, TestHelpers.seconds(4.0), func(i):
		var z: float = g.player.pos.z
		return {"move_y": 1.0, "jump": z > 25.3 and z < 27.5})
	h.expect(g.player.pos.z > 31.0 and g.player.pos.y > -0.3, "溝（幅 4 m）を走りジャンプで越えられる（z=%.1f, y=%.1f）" % [g.player.pos.z, g.player.pos.y])
	# 溝に落ちても、南のスロープから戻れる
	_warp(g, Vector3(0, -1.5, 28.5), PI)
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


## 第 1 章の力は少しずつ使えるようになる：練習銃 → スパーク（夜）→ ロックオン（適合）→ 光刃（弁の間）→ ダッシュ（駆動回廊）
func test_abilities_unlock_in_stages() -> void:
	var g := _new_game()
	await h.settle()
	g.set_flag("trigger.ch1.training.start")
	g.load_room("ch1.training", "start")
	await _pump(g, 6)
	for a in ["spark", "lock_on", "sword", "dash"]:
		h.expect(not g.has_ability(a), "訓練場では %s はまだ使えない" % a)
	h.expect(g.gun_cfg().damage < g.tuning.gun.damage and g.gun_cfg().rate < g.tuning.gun.rate, "最初は練習銃（威力・連射がスパークより低い）")
	await h.run(g, 10, {"dash": true, "sword": true, "lock_on": true, "fire": true})
	h.expect(not g.input.dash and not g.input.sword and not g.input.lock_on and g.input.fire, "解放の前：ダッシュ・斬る・ロックオンは押していないことになる（撃つは使える）")
	h.expect(g.player.dash_time <= 0.0 and g.player.attack == null, "解放の前：ダッシュも斬りも出ない")
	g.set_flag("ch1.got_spark")
	h.expect(g.has_ability("spark") and g.gun_cfg().damage == g.tuning.gun.damage, "スパークを受け取ると普通の銃になる")
	g.set_flag("ch1.frame_fitted")
	h.expect(g.has_ability("lock_on") and not g.has_ability("sword") and not g.has_ability("dash"), "適合ではロックオンだけ")
	g.set_flag("ch1.blade_online")
	h.expect(g.has_ability("sword") and not g.has_ability("dash"), "籠手が目覚めると光刃")
	await _pump(g, 30)
	await h.run(g, 4, func(i): return {"sword": i < 2})
	h.expect(g.player.attack != null, "光刃が出る")
	await _pump(g, 60)
	await h.run(g, 3, {"dash": true, "move_y": 1.0})
	h.expect(g.player.dash_time <= 0.0, "ダッシュはまだ出ない")
	g.set_flag("ch1.drive_powered")
	await _pump(g, 30)
	await h.run(g, 3, {"dash": true, "move_y": 1.0})
	h.expect(g.player.dash_time > 0.0, "駆動回廊に動力が戻るとダッシュが出る")
	h.free_game(g)


## 部屋から始める確認用（後の本筋のフラグだけ立てる）でも、そこまでの力は使える
func test_abilities_implied_by_later_flags() -> void:
	var g := _new_game()
	await h.settle()
	g.load_room("ch1.r13")
	g.set_flag("ch1.drive_powered")
	for a in ["spark", "lock_on", "sword", "dash"]:
		h.expect(g.has_ability(a), "駆動回廊より後なら %s は使える" % a)
	g.load_room("sample.hub")
	g.set_flag("ch1.drive_powered", false)
	h.expect(g.has_ability("dash") and g.has_ability("sword"), "見本の部屋では最初から全部使える")
	h.free_game(g)


## 換気室（子番機 2 体）に、ハルが +Z（子番機の方）を向いて立ち、カメラは 90° 横を向いた状態にする
func _r04_facing_minis(fitted: bool) -> GameSim:
	var g := _new_game()
	await h.settle()
	g.set_flag("ch1.got_spark")
	if fitted:
		g.set_flag("ch1.frame_fitted")
	g.load_room("ch1.r04", "from_r03")
	for t in g.triggers:
		t.fired = true
	await _pump(g, 6)
	_warp(g, Vector3(0, 0, -5), 0.0)
	await _pump(g, 4)
	return g


## 適合の前：ロックオンのボタンを押すと、ロックオンはしないが、カメラがハルの向きの背後へ回る（押すたびに）。
## 背後のボタン（camera_reset。R3・C・タッチの「背後」）もそのまま使える
func test_lock_button_recenters_before_fitting() -> void:
	var g: GameSim = await _r04_facing_minis(false)
	h.expect(not g.has_ability("lock_on"), "適合の前はロックオンが使えない")
	h.expect(g.enemies.size() == 2 and g.enemies.all(func(e): return e.alive), "前に子番機が 2 体いる")
	g.cam.yaw = PI / 2
	await h.run(g, 30, {"lock_on": true})
	h.near(rad_to_deg(U.wrap_angle(g.cam.yaw - g.player.yaw)), 0.0, 2.0, "ロックオンのボタンでカメラがハルの背後へ回る")
	h.expect(g.lock_on.target == null and not g.input.lock_on, "適合の前はロックオンしない（前に敵がいても）")
	# 押し続けても、カメラを回せば回したまま（押した瞬間だけ背後へ回す）
	g.cam.yaw = -PI / 2
	await h.run(g, 20, {"lock_on": true})
	h.near(rad_to_deg(U.wrap_angle(g.cam.yaw + PI / 2)), 0.0, 0.5, "押し続けているだけでは何度も回らない")
	await h.run(g, 2, {})
	await h.run(g, 30, {"lock_on": true})
	h.near(rad_to_deg(U.wrap_angle(g.cam.yaw - g.player.yaw)), 0.0, 2.0, "押し直すと、また背後へ回る")
	await h.run(g, 2, {})
	g.cam.yaw = PI
	await h.run(g, 1, {"camera_reset": true})
	await h.run(g, 30, {})
	h.near(rad_to_deg(U.wrap_angle(g.cam.yaw - g.player.yaw)), 0.0, 2.0, "背後のボタンもそのまま使える")
	h.expect(g.lock_on.target == null, "ロックオンはしていない")
	# 横へ走りながら押しても、カメラは回り続けずにハルの背後で止まる（ハルはそのまま同じ向きへ走る）
	for btn in ["lock_on", "camera_reset"]:
		_warp(g, Vector3(0, 0, -5), 0.0)
		await h.run(g, 2, {})
		await h.run(g, 15, {"move_x": 1.0})
		var heading0 := U.dir_to_yaw(g.player.vel.x, g.player.vel.z)
		var turned := 0.0
		var prev := g.cam.yaw
		for i in 30:
			await h.run(g, 1, {"move_x": 1.0, btn: i == 0})
			turned += absf(U.wrap_angle(g.cam.yaw - prev))
			prev = g.cam.yaw
		h.expect(turned < 95.0 * U.DEG, "%s：横へ走りながら押しても、カメラは回り続けない（%.0f°）" % [btn, turned / U.DEG])
		h.near(rad_to_deg(U.wrap_angle(g.cam.yaw - g.player.yaw)), 0.0, 2.0, "%s：横へ走りながら押すと、カメラがハルの背後で止まる" % btn)
		h.near(rad_to_deg(U.wrap_angle(U.dir_to_yaw(g.player.vel.x, g.player.vel.z) - heading0)), 0.0, 2.0, "%s：ハルはそのまま同じ向きへ走る" % btn)
		h.expect(g.lock_on.target == null, "%s：ロックオンはしていない" % btn)
		await h.run(g, 15, {})
	# 会話の間は回らない
	g.cam.yaw = PI / 2
	g.story.start_event("ch1.r04.enter")
	await h.run(g, 1, {})
	h.expect(g.story.blocking(), "会話が出ている")
	await h.run(g, 1, {"lock_on": true})
	await h.run(g, 1, {})
	h.near(g.cam.yaw, PI / 2, 0.0001, "会話の間はロックオンのボタンでカメラが回らない")
	h.free_game(g)
	# 部屋に入った直後（物理の世界への反映を待つ 2 刻み）に押して離しても、待ちが明けたら背後へ回る
	var g2 := _new_game()
	await h.settle()
	g2.set_flag("ch1.got_spark")
	g2.load_room("ch1.r04", "from_r03")
	for t in g2.triggers:
		t.fired = true
	g2.cam.yaw = g2.player.yaw + PI / 2
	await h.run(g2, 1, {"lock_on": true})
	await h.run(g2, 40, {})
	h.near(rad_to_deg(U.wrap_angle(g2.cam.yaw - g2.player.yaw)), 0.0, 2.0, "部屋に入った直後に押しても背後へ回る")
	h.free_game(g2)


## 適合の前の換気室：カメラの方へ走りながらロックオンのボタンを押し、回している途中に左スティックを上へ倒し直しても、
## 回し終えてから倒し直したときと同じく、ハルはそのまま走り続け、カメラはハルの背後で止まる（CameraOrbit._hold_to）。
## 前はハルが U ターンし（+90° → −90°）、カメラは 236〜324° 回って、背中から 36〜124° 外れた所で止まったままだった（2026-10-08）
func test_lock_button_reaim_during_swing_before_fitting() -> void:
	for reaim_at in [6, 10, 14, 30]:
		var g: GameSim = await _r04_facing_minis(false)
		_warp(g, Vector3(0, 0, 0), PI / 2)
		g.cam.yaw = -PI / 2
		g.cam.follow = "weak"
		await h.run(g, 4, {})
		await h.run(g, 20, {"move_y": -1.0})
		var p: Player = g.player
		var heading0 := U.dir_to_yaw(p.vel.x, p.vel.z)
		h.near(U.wrap_angle(heading0 - PI / 2) / U.DEG, 0.0, 2.0, "カメラの方（+90°）へ走っている")
		var turned := 0.0
		var prev := g.cam.yaw
		var worst := 0.0
		for i in 60:
			var f := {"move_y": -1.0 if i < reaim_at else 1.0}
			if i == 0:
				f["lock_on"] = true
			await h.run(g, 1, f)
			turned += absf(U.wrap_angle(g.cam.yaw - prev))
			prev = g.cam.yaw
			worst = maxf(worst, absf(U.wrap_angle(U.dir_to_yaw(p.vel.x, p.vel.z) - heading0)))
		var what := "%d 刻み目に上へ倒し直す" % reaim_at
		h.expect(g.room_id == "ch1.r04" and g.lock_on.target == null, "%s：同じ部屋で、ロックオンはしていない" % what)
		h.expect(worst < 3.0 * U.DEG, "%s：ハルはそのまま走り続ける（最大 %.1f° ずれた）" % [what, worst / U.DEG])
		h.expect(turned < 182.0 * U.DEG, "%s：カメラは背後まで回るだけ（%.0f°）" % [what, turned / U.DEG])
		h.near(U.wrap_angle(p.yaw - g.cam.yaw) / U.DEG, 0.0, 1.0, "%s：カメラはハルの背後で止まる" % what)
		h.free_game(g)


## 左スティックをカメラの方（下・斜め下）へ倒したまま扉を通ると、ハルは新しい部屋でもそのまま奥へ進む（CameraOrbit.keep_heading）。
## 新しい部屋のカメラは入口から奥を向くので、新しいカメラから測り直すと「下」が「扉へ戻る」向きになる。
## 前は倒している間ずっと 2 つの部屋を行き来した（換気室と遺構 B1 の間で 4 秒に 17 回。中層の町と下層の町も。2026-10-08）
func test_door_with_stick_held_keeps_going() -> void:
	for c in [["ch1.r04", "from_r03", Vector2(0, -1)], ["ch1.r04", "from_r03", Vector2(0.5, -0.866)], ["ch1.r03", "from_r04", Vector2(0, -1)], ["ch1.mid", "", Vector2(0, -1)]]:
		var g := _new_game()
		await h.settle()
		g.set_flag("ch1.got_spark")
		g.set_flag("ch1.frame_fitted")
		g.load_room(c[0], c[1])
		for t in g.triggers:
			t.fired = true
		await _pump(g, 8)
		g.drain_events()
		var s: Vector2 = c[2]
		var room := g.room_id
		var changes := 0
		var into := []
		for i in 240:
			var f := {"move_x": s.x, "move_y": s.y}
			if g.story.blocking():
				f = {"jump": i % 6 < 3}
			await h.tree.physics_frame
			g.step(InputFrame.of(f))
			g.drain_events()
			if g.room_id != room:
				changes += 1
				room = g.room_id
				# 入口の目印の向き（読み込んだ直後のカメラの向き）
				into = [g.cam.yaw, i]
		var what := "%s（%s）で左スティック %s を 4 秒" % c
		h.expect(changes <= 1, "%s：部屋を行き来しない（移った回数 %d）" % [what, changes])
		if changes == 1 and 240 - into[1] > 30:
			var p: Player = g.player
			h.near(U.wrap_angle(U.dir_to_yaw(p.vel.x, p.vel.z) - into[0]) / U.DEG, 0.0, 3.0, "%s：移った部屋でも、そのまま奥へ進む" % what)
		h.free_game(g)


## 適合のあと：対象がいないときにロックオンのボタンを押すと、カメラが背後へ回る（これまでどおり）。対象がいればロックオンする
func test_lock_button_recenters_after_fitting_without_target() -> void:
	var g: GameSim = await _r04_facing_minis(true)
	h.expect(g.has_ability("lock_on"), "適合のあとはロックオンが使える")
	_kill_all(g)
	# 倒した直後の手応えの一時停止（ヒットストップ）の間に押しても、押した瞬間として扱う
	await _pump(g, 2)
	g.cam.yaw = PI / 2
	await h.run(g, 30, {"lock_on": true})
	h.near(rad_to_deg(U.wrap_angle(g.cam.yaw - g.player.yaw)), 0.0, 2.0, "対象がいないときは、ロックオンのボタンでカメラが背後へ回る")
	h.expect(g.lock_on.target == null, "対象がいなければロックオンしない")
	h.free_game(g)
	var g2: GameSim = await _r04_facing_minis(true)
	await h.run(g2, 2, {"lock_on": true})
	h.expect(g2.lock_on.target != null, "対象がいればロックオンする")
	h.free_game(g2)
	# 部屋に入った直後（読み込み待ち）に押して離し、続けてヒットストップ（倒した手応え）が入っても、明けたら背後へ回る
	var g3 := _new_game()
	await h.settle()
	g3.set_flag("ch1.got_spark")
	g3.set_flag("ch1.frame_fitted")
	g3.load_room("ch1.r04", "from_r03")
	for t in g3.triggers:
		t.fired = true
	_kill_all(g3)
	h.expect(g3.hitstop > 0.0, "倒した手応えの一時停止が入っている")
	g3.cam.yaw = g3.player.yaw + PI / 2
	await h.run(g3, 1, {"lock_on": true})
	await h.run(g3, 40, {})
	h.near(rad_to_deg(U.wrap_angle(g3.cam.yaw - g3.player.yaw)), 0.0, 2.0, "読み込み待ち・一時停止の間に押して離しても背後へ回る")
	h.expect(g3.lock_on.target == null, "対象がいなければロックオンしない")
	h.free_game(g3)


## 部屋の床（高さ floor_y）のうち、始まりの目印から歩いて行ける所（0.5m の升目。地形・壁・閉じた扉で区切る）
func _walkable_cells(g: GameSim, start: Vector3, floor_y: float, fits: Callable) -> Dictionary:
	var cell := 0.5
	var c0 := Vector2i(roundi(start.x / cell), roundi(start.z / cell))
	var seen := {c0: true}
	var queue := [c0]
	while not queue.is_empty() and seen.size() < 20000:
		var c: Vector2i = queue.pop_back()
		for dc in [Vector2i(1, 0), Vector2i(-1, 0), Vector2i(0, 1), Vector2i(0, -1)]:
			var n: Vector2i = c + dc
			if seen.has(n):
				continue
			var top := Vector3(n.x * cell, floor_y + 2.4, n.y * cell)
			var down := g.phys.raycast(top, Vector3.DOWN, 3.0, Phys.TERRAIN | Phys.BREAKABLE)
			if down.is_empty() or absf(down.point.y - floor_y) > 0.3 or not fits.call(down.point):
				seen[n] = false
				continue
			seen[n] = true
			queue.append(n)
	return seen


## 第 1 章の撃つスイッチ（"mode": "shoot" 全部）の部屋：{ 部屋 id: [スイッチ id...] }
func _ch1_shoot_switches() -> Dictionary:
	var world := World.load_manifest("res://content/world.json")
	var rooms := {}
	for rid in world.rooms:
		if not String(rid).begins_with("ch1."):
			continue
		for p in world.room(rid).get("props", []):
			if p.type == "switch" and String(p.get("mode", "shoot")) == "shoot":
				if not rooms.has(rid):
					rooms[rid] = []
				rooms[rid].append(p.id)
	return rooms


## スイッチの部屋を読み込み、敵を倒しておく（ふつうの順）。町（訓練場）は練習銃、遺構はスパークを受け取った後
func _shoot_switch_room(rid: String) -> GameSim:
	var g := _new_game()
	await h.settle()
	if not rid.begins_with("ch1.training"):
		g.set_flag("ch1.got_spark")
	g.load_room(rid)
	for t in g.triggers:
		t.fired = true
	await _pump(g, 6)
	_kill_all(g)
	await _pump(g, 6)
	return g


## 今の向きのまま撃って（カメラはわざと 90° 横）、スイッチが入るか
func _shoot_switch_from_here(g: GameSim, sw: Props.Switch) -> bool:
	sw.on = false
	g.set_flag("switch." + sw.id, false)
	g.player.gun_cooldown = 0.0
	g.cam.yaw = g.player.yaw + PI / 2
	await h.run(g, 1, {"fire": true})
	return await h.run_until(g, 45, {}, func(): return sw.on)


## 撃つと入るスイッチ（訓練場の的・換気室の弁・弁の間の輪・駆動回廊の動力の球など、第 1 章の "mode": "shoot" 全部）は、
## ふつうに立つ場所から、その方を向いて撃てば入る（カメラはわざと 90° 横へ向けておく。撃つ向きは体の向き）。
## 立つ場所：部屋の床（始まりの目印と同じ高さ）の上で、スイッチから水平に 1.1・1.3・1.6・2・3・5・7・9・11m、16 方向。
## 始まりの目印から歩いて行けて（閉じた扉の向こうは除く）、体（ハルのカプセル）が収まる所に立たせ、立った位置で
## 胸からスイッチの球のどこか（中心か、中心から半径の 0.6 倍だけ上下・東西・南北の点）まで視線が通り（地形にさえぎられない。
## 手前に別のスイッチが重なる所は除く）、射程の内にある所を全部試す。
## 台・箱・柱のすぐ脇（銃口が台にめり込む・銃口からだと柱の角に隠れる所）や、扉・箱の縁から球の一部だけ見える所も入る。
## 向きは真正面と ±8°（スティックで大まかに向けた程度）。部屋の敵は先に倒しておく
func test_all_shoot_switches_hittable() -> void:
	var rooms := _ch1_shoot_switches()
	var n_switches := 0
	for ids in rooms.values():
		n_switches += ids.size()
	h.expect(n_switches >= 8, "第 1 章の撃つスイッチ（%d 個：%s）" % [n_switches, rooms])
	var mask := Phys.TERRAIN | Phys.BREAKABLE
	for rid in rooms:
		var g: GameSim = await _shoot_switch_room(rid)
		var start: Vector3 = g.world.geometry(rid).markers[String(g.room.get("playerStart", "start"))].pos
		var floor_y := start.y
		var space := g.phys.get_world_3d().direct_space_state
		var cap := CapsuleShape3D.new()
		cap.radius = Player.RADIUS
		cap.height = Player.HEIGHT
		var cap_q := PhysicsShapeQueryParameters3D.new()
		cap_q.shape = cap
		cap_q.collision_mask = mask
		# 体（ハルのカプセル）が地形・壁・扉に埋まらない
		var fits := func(f: Vector3) -> bool:
			cap_q.transform = Transform3D(Basis(), f + Vector3(0, Player.HEIGHT * 0.5 + 0.08, 0))
			return space.intersect_shape(cap_q, 1).is_empty()
		var walk := _walkable_cells(g, start, floor_y, fits)
		var reach: float = g.gun_cfg().range - 0.5
		# 射程の内で、手前に別のスイッチ（弾が当たると入る）が重ならず（そちらに当たるのが正しい）、
		# 胸から球のどこか（中心か、中心から半径の 0.6 倍だけ上下・東西・南北の点。自動照準の狙う点とは別に決めた点）まで視線が通る。
		# 返り値：0＝見えない、1＝中心が見える、2＝中心は隠れていて一部だけ見える
		var sees := func(sw: Props.Switch, chest: Vector3) -> int:
			if chest.distance_to(sw.pos) > reach or Vector2(sw.pos.x - chest.x, sw.pos.z - chest.z).length() < 0.6:
				return 0
			if g.switches.any(func(o): return o != sw and o.mode == "shoot" and U.segment_sphere(chest, sw.pos, o.pos, o.radius + 0.3) >= 0.0):
				return 0
			for o in [Vector3.ZERO, Vector3.UP, Vector3.DOWN, Vector3.LEFT, Vector3.RIGHT, Vector3.FORWARD, Vector3.BACK]:
				var q: Vector3 = sw.pos + o * sw.radius * 0.6
				if g.phys.raycast(chest, (q - chest).normalized(), chest.distance_to(q), mask).is_empty():
					return 1 if o == Vector3.ZERO else 2
			return 0
		for sid in rooms[rid]:
			var sw: Props.Switch = g.switch_by_id(sid)
			var spots := []
			for d in [1.1, 1.3, 1.6, 2.0, 3.0, 5.0, 7.0, 9.0, 11.0]:
				for k in 16:
					var a := k * TAU / 16.0
					var top := Vector3(sw.pos.x + sin(a) * d, floor_y + 2.4, sw.pos.z + cos(a) * d)
					var down := g.phys.raycast(top, Vector3.DOWN, 3.0, mask)
					if down.is_empty() or absf(down.point.y - floor_y) > 0.3:
						continue
					var f: Vector3 = down.point
					if not fits.call(f) or not walk.get(Vector2i(roundi(f.x / 0.5), roundi(f.z / 0.5)), false) or g.exits.any(func(x): return x.contains(f)):
						continue
					if sees.call(sw, f + Vector3(0, Player.CHEST, 0)) > 0:
						spots.append(f)
			var tried := 0
			var near := 0
			var partly := 0
			var missed := []
			for f in spots:
				g.player.teleport(f, U.dir_to_yaw(sw.pos.x - f.x, sw.pos.z - f.z))
				await h.run(g, 3, {})
				var at := g.player.pos
				if not g.player.grounded:
					missed.append("%s（立てない）" % f)
					continue
				# 立った位置（体が押し戻されたらそこ）で、まだ見えているか
				var vis: int = sees.call(sw, g.player.chest())
				if vis == 0:
					continue
				for off in [0.0, 8.0, -8.0]:
					g.player.yaw = U.dir_to_yaw(sw.pos.x - at.x, sw.pos.z - at.z) + off * U.DEG
					tried += 1
					if Vector2(sw.pos.x - at.x, sw.pos.z - at.z).length() < 2.5:
						near += 1
					if vis == 2:
						partly += 1
					if not await _shoot_switch_from_here(g, sw):
						missed.append("%s %+.0f°%s" % [at, off, "（一部だけ見える）" if vis == 2 else ""])
					if g.player.pos.distance_to(at) > 0.05:
						missed.append("%s %+.0f°（撃ったあと動いた：%s）" % [at, off, g.player.pos])
						break
			h.expect(tried >= 12, "%s：ふつうに立って狙える場所がある（%d 回。うち 2.5m より近く %d 回、一部だけ見える所 %d 回）" % [sid, tried, near, partly])
			h.expect(missed.is_empty(), "%s：向いて撃てば入る（%d 回。外れ：%s）" % [sid, tried, missed])
		h.free_game(g)


## 台・箱・柱へまっすぐ歩いて寄って、止まった所でそのまま撃っても入る（銃口が台や箱にめり込む所。
## 換気室の弁の台は背より高く、すぐ脇からは弁の中心が台の縁に隠れて、上の方だけ見える）
func test_shoot_switches_after_walking_up() -> void:
	# [部屋, スイッチ, 歩き始める所, 歩く向き（yaw 度）]
	var cases := [
		["ch1.training", "ch1.tg1", Vector3(-8, 0, 12), 0.0],
		["ch1.training", "ch1.tg2", Vector3(0, 0, 14), 0.0],
		["ch1.training", "ch1.tg3", Vector3(8, 0, 12), 0.0],
		["ch1.r04", "ch1.r04.v1", Vector3(-7, 0, -2), 0.0],
		["ch1.r04", "ch1.r04.v1", Vector3(-3, 0, 3), -90.0],
		["ch1.r04", "ch1.r04.v1", Vector3(-7, 0, 7), 180.0],
		["ch1.r04", "ch1.r04.v2", Vector3(7, 0, -2), 0.0],
		["ch1.r04", "ch1.r04.v2", Vector3(3, 0, 3), 90.0],
		["ch1.r04", "ch1.r04.v2", Vector3(7, 0, 7), 180.0],
		["ch1.r10", "ch1.r10.valve", Vector3(-1.5, 0, -4), 0.0],
		["ch1.r10", "ch1.r10.valve", Vector3(0, 0, -4), 0.0],
		["ch1.r10", "ch1.r10.valve", Vector3(1, 0, -4), 0.0],
	]
	var games := {}
	for c in cases:
		if not games.has(c[0]):
			games[c[0]] = await _shoot_switch_room(c[0])
		var g: GameSim = games[c[0]]
		var sw: Props.Switch = g.switch_by_id(c[1])
		_warp(g, c[2], c[3] * U.DEG)
		await h.run(g, 140, {"move_y": 1.0})
		var before := g.player.pos
		await h.run(g, 10, {"move_y": 1.0})
		await h.run(g, 3, {})
		var at := g.player.pos
		var stopped := at.distance_to(before) < 0.05 and at.distance_to(c[2]) > 2.0
		h.expect(stopped and g.player.grounded, "%s：%s から歩いて、台・箱・柱に当たって止まる（%s）" % [c[1], c[2], at])
		h.expect(await _shoot_switch_from_here(g, sw), "%s：%s から歩いて寄り、止まった所（%s）でそのまま撃てば入る" % [c[1], c[2], at])
	for g in games.values():
		h.free_game(g)


## 球の一部だけ見えるスイッチ（中心は箱・台・閉じた扉の縁に隠れて、横・手前・上の方だけ見える）も、その方を向いて撃てば入る
func test_shoot_partly_hidden_switches() -> void:
	# [部屋, スイッチ, 立つ所]
	var cases := [
		["ch1.r04", "ch1.r04.v2", Vector3(2, 0, -4)],
		["ch1.r04", "ch1.r04.v2", Vector3(0, 0, -7)],
		["ch1.r04", "ch1.r04.v1", Vector3(-4, 0, -6)],
		["ch1.r10", "ch1.r10.valve", Vector3(9, 0, 6.6)],
	]
	var games := {}
	for c in cases:
		if not games.has(c[0]):
			games[c[0]] = await _shoot_switch_room(c[0])
		var g: GameSim = games[c[0]]
		var sw: Props.Switch = g.switch_by_id(c[1])
		var f: Vector3 = c[2]
		_warp(g, f, U.dir_to_yaw(sw.pos.x - f.x, sw.pos.z - f.z))
		sw.on = false
		g.set_flag("switch." + sw.id, false)
		await h.run(g, 4, {})
		var chest := g.player.chest()
		h.expect(g.player.grounded and not g.has_clear_shot(chest, sw.pos), "%s：%s から中心は隠れている" % [c[1], f])
		h.expect(not g.soft_aim(g.player.yaw).is_empty(), "%s：%s から一部が見えるので狙いが合う" % [c[1], f])
		h.expect(await _shoot_switch_from_here(g, sw), "%s：%s から撃てば入る" % [c[1], f])
	for g in games.values():
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
