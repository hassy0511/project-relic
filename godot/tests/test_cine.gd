extends RefCounted
## 映画のような場面（CineDirector・台本の shot と caption・外の舞台・オルドの足音と砂ぼこり・町の灯）のテスト。
## 書き方は docs/design/42_コンテンツの書き方.md 6.1、結果は docs/art_orders/W2_オルド3D化の結果.md 11 章。
## ・オープニング：最初のカメラは船の外の遠く（オルド全体が画面に入る）、部屋（台）は隠れ、霞が薄い。32 秒に左舷の足が着いて足音と砂ぼこり。
##   最後の道筋はふだんの遊びのカメラ（台のハルの後ろ）とちょうど同じ所で終わる（ハルの所へなめらかに渡す）。終わると霞・部屋・オルドの時計が戻る
## ・停止：家の中で外の舞台（夜のオルド）が出て、部屋が隠れ、夜の空になる。動力が切れて足が落ちて着き、町の灯が消える。家へ戻ると全部戻る
## ・スキップ：どこで飛ばしても、カメラ・舞台・霞・部屋の表示・オルドの時計・風が元に戻る
## ・語りの字幕（HUD）：黒帯の場面の下の帯のすぐ上に出て、時間で消える

var h: TestHelpers

const DT := 1.0 / 60.0


func _init(helpers: TestHelpers) -> void:
	h = helpers


## main.gd の代わり（CineDirector が使う物だけ）：部屋の見た目（RoomView）・カメラ・太陽と環境・Fx・音
class FakeMain extends Node3D:
	var game: GameSim
	var level: Node3D
	var camera: CameraRig
	var sun: DirectionalLight3D
	var fx: Fx
	var audio: GameAudio
	var player_view = null
	var nagomi_view = null
	var props_view = null
	var enemy_view = null
	var moods: Array = []

	func _ordo() -> OrdoView:
		if level == null or not is_instance_valid(level):
			return null
		return level.get_node_or_null("Ordo") as OrdoView

	## main._apply_mood と同じ（部屋の雰囲気・キットの空と光）
	func _apply_mood() -> void:
		var r: Dictionary = game.room
		var mood := String(r.get("mood", "day"))
		if mood == "outdoor" or mood == "day":
			mood = "night" if game.flag("ch1.night") else "day"
		EnvironmentSetup.apply_mood(sun, mood)
		var o := _ordo()
		if o != null:
			o.set_mood(mood)
		if r.has("kit"):
			var kd: Dictionary = RoomKit.load_kit(String(r.kit)).get("data", {})
			EnvironmentSetup.apply_sky(sun, String(kd.get("sky", {}).get(mood, "")), kd.get("light", {}).get(mood, {}))
		moods.append(mood)

	func rebuild() -> void:
		if level != null and is_instance_valid(level):
			level.free()
		level = RoomView.build(game.world, game.room_id)
		add_child(level)
		_apply_mood()


## 画面のある小さな世界（1600×900 の SubViewport）に、ゲームと main の代わりと CineDirector を作る
func _setup() -> Array:
	var vp := SubViewport.new()
	vp.own_world_3d = true
	vp.size = Vector2i(1600, 900)
	vp.render_target_update_mode = SubViewport.UPDATE_DISABLED
	h.tree.root.add_child(vp)
	var m := FakeMain.new()
	vp.add_child(m)
	var g := GameSim.new()
	m.add_child(g)
	g.setup({"world": World.load_manifest("res://content/world.json"), "tuning": TestHelpers.default_tuning(), "seed": 1})
	m.game = g
	m.sun = EnvironmentSetup.build(m)
	m.camera = CameraRig.new()
	m.add_child(m.camera)
	m.camera.current = true
	m.fx = Fx.new()
	m.add_child(m.fx)
	m.audio = GameAudio.new()
	m.add_child(m.audio)
	m.rebuild()
	var cd := CineDirector.new(m)
	m.add_child(cd)
	await h.settle()
	return [vp, m, cd]


## 1 刻み：ゲーム → 出来事（Fx・CineDirector、部屋の移動は作り直し）→ カメラ → 場面のカメラ（main._physics_process と同じ順）
func _tick(m: FakeMain, cd: CineDirector, input := {}) -> Array:
	await h.tree.physics_frame
	var g := m.game
	g.step(InputFrame.of(input))
	var evs := g.drain_events()
	for e in evs:
		m.fx.handle(e)
		cd.handle(e)
		if e.type == "roomChanged" and not e.first:
			m.rebuild()
	m.camera.sync(g, g.player.pos, DT, m.fx.shake)
	cd.sync(DT)
	m.fx.vfx.step(DT)
	return evs


func _env(m: FakeMain) -> Environment:
	return m.sun.get_meta("env")


## 会話は出しきってから送る（オープニングのハルのひと言・停止の会話）
static func _confirm(g: GameSim, i: int) -> Dictionary:
	var d: Dictionary = g.story.dialogue
	if d.is_empty():
		return {}
	return {"confirm": i % 6 < 3}


func test_cine_opening() -> void:
	var made: Array = await _setup()
	var m: FakeMain = made[1]
	var cd: CineDirector = made[2]
	var g := m.game
	h.expect(g.room_id == "ch1.opening", "はじめから：夜明けの甲羅（%s）" % g.room_id)
	var fog0 := _env(m).fog_density
	var o := m._ordo()
	h.expect(o != null and o.ground_node == null, "部屋のオルドは砂の床なし（ふだんの部屋の見た目は前のまま）")
	# 始まり：最初の道筋
	for i in 6:
		await _tick(m, cd)
	h.expect(g.cinematic() and not cd.shot.is_empty() and cd.ordo() == o, "オープニングは黒帯の場面で、最初の道筋がオルドの座標で始まる")
	var cam := m.camera
	var center := o.global_position + Vector3(0, -50, 0)
	h.expect(cam.global_position.distance_to(center) > 600.0, "カメラは船の外の遠く（オルドの真ん中から %.0f m）" % cam.global_position.distance_to(center))
	var corners := [Vector3(0, 30, 200), Vector3(0, 22, -204), Vector3(88, -118, 150), Vector3(-88, -118, 150), Vector3(88, -118, -150), Vector3(0, 48, 0)]
	var seen := corners.filter(func(c): return cam.is_position_in_frustum(o.global_position + c))
	h.expect(seen.size() == corners.size(), "オルドの全体（船首・船尾・前後の足・背の町の塔）が画面に入る（%d / %d）" % [seen.size(), corners.size()])
	h.expect(_env(m).fog_density < fog0 * 0.25, "遠景の霞は薄い（%.5f、ふだん %.4f）" % [_env(m).fog_density, fog0])
	h.expect(o.ground_node != null and o.ground_node.visible and o.town_lights != null, "砂の床と背の町の灯を出す")
	h.expect(not o.is_processing(), "場面の間は、オルドの時計を場面が進める（足が着く時刻が台本と同じ時計）")
	var hidden := m.level.get_children().filter(func(c): return c.name != "Ordo" and c is Node3D and (c as Node3D).visible)
	h.expect(hidden.is_empty(), "遠景では台（部屋の地形・飾り・明かり）を描かない（見えている物 %d）" % hidden.size())
	h.expect(m.audio.ambience == "amb_wind", "風の音")
	# 32 秒：左舷の脚 l2 の足が着く（足もとの低いカメラ）
	var heard := {}
	var at_plant := {}
	o.foot_planted.connect(func(tag: String, at: Vector3):
		heard[tag] = true
		if tag == "l2":
			at_plant["cam"] = cam.global_position
			at_plant["foot"] = at)
	var t := 6
	while t < 34 * 60:
		await _tick(m, cd)
		t += 1
	h.expect(heard.has("l2") and heard.has("r1"), "32 秒に左舷の l2・右舷の r1 が着く（%s）" % [heard.keys()])
	h.expect(cd.steps_heard >= 4 and cd.dust_puffs >= 40, "足音（%d 回）と砂ぼこり（%d 粒）" % [cd.steps_heard, cd.dust_puffs])
	var cp: Vector3 = at_plant.get("cam", Vector3.ZERO)
	var fp: Vector3 = at_plant.get("foot", Vector3(0, 1e6, 0))
	h.expect(cp.distance_to(fp) < 110.0 and cp.y - fp.y < 6.0,
		"足が着くとき、カメラは足もとの低い所（足まで %.0f m、地面から %.1f m）" % [cp.distance_to(fp), cp.y - fp.y])
	# 終わり：最後の道筋はふだんの遊びのカメラ（台のハルの後ろ）で終わる
	var last_gap := INF
	var shown_room := false
	while t < 75 * 60:
		var before_eye := Vector3.ZERO
		var d: Dictionary = g.story.dialogue
		if d.get("id", "") == "ch1.opening" and int(d.shown) >= String(d.text).length():
			# ハルのひと言：カメラはふだんの所（場面のカメラを当てる前の、CameraRig が決めた所）と同じ
			await h.tree.physics_frame
			g.step(InputFrame.new())
			for e in g.drain_events():
				cd.handle(e)
			cam.sync(g, g.player.pos, DT, 0.0)
			before_eye = cam.global_position
			cd.sync(DT)
			last_gap = cam.global_position.distance_to(before_eye)
			shown_room = m.level.get_children().all(func(c): return not (c is Node3D) or (c as Node3D).visible)
			break
		await _tick(m, cd, _confirm(g, t))
		t += 1
	h.expect(last_gap < 0.02, "ハルのひと言のとき、カメラはふだんの遊びのカメラと同じ所（差 %.3f m）" % last_gap)
	h.expect(shown_room, "台（部屋）は見えている")
	while t < 80 * 60 and g.room_id != "ch1.training":
		await _tick(m, cd, _confirm(g, t))
		t += 1
	h.expect(g.room_id == "ch1.training" and g.flag("ch1.opening_done"), "オープニングのあと訓練場へ（%.1f 秒）" % (t / 60.0))
	h.expect(cd.shot.is_empty() and cd.ordo() == null and absf(_env(m).fog_density - fog0) < 1e-6, "場面が終わると道筋・霞が戻る")
	await _tick(m, cd)
	h.expect(m.audio.ambience == "", "風は止まる")
	h.free_game(g)
	made[0].queue_free()


func test_cine_stop_stage() -> void:
	var made: Array = await _setup()
	var m: FakeMain = made[1]
	var cd: CineDirector = made[2]
	var g := m.game
	for f in ["ch1.opening_done", "ch1.chores_started", "ch1.t_move", "ch1.nico_rescued", "ch1.scolded", "ch1.debt_scene"]:
		g.set_flag(f)
	g.load_room("ch1.home", "from_lower")
	for tr in g.triggers:
		tr.fired = true
	m.rebuild()
	for i in 4:
		await _tick(m, cd)
	var fog0 := _env(m).fog_density
	g.player.teleport(Vector3(-3, 0, 3.5), deg_to_rad(270.0))
	g.story.start_event("ch1.stop")
	var t := 0
	var stage_seen := false
	var night_sky := false
	var stopped := false
	var landed := {"n": 0}
	var lights_out := 0.0
	var hidden_ok := true
	while t < 40 * 60:
		await _tick(m, cd, _confirm(g, t))
		t += 1
		if cd.stage != null and is_instance_valid(cd.stage):
			if not stage_seen:
				stage_seen = true
				cd.stage.foot_planted.connect(func(_tag: String, _at: Vector3): landed.n += 1)
				night_sky = _env(m).sky.sky_material is PanoramaSkyMaterial and m.moods.size() > 0
			hidden_ok = hidden_ok and not m.level.visible
			stopped = stopped or cd.stage.cine_stopping()
			if cd.stage.town_lights != null:
				lights_out = maxf(lights_out, cd.stage.town_lights.out)
		if g.flag("ch1.ordo_stopped") and not g.story.running_event():
			break
	h.expect(stage_seen and night_sky, "家の中の場面で、外の舞台（夜のオルドと空の絵）を出す")
	h.expect(hidden_ok, "外の舞台の間は家（部屋）を隠す")
	h.expect(stopped and int(landed.n) >= 2, "動力が切れて、振り出していた足が落ちて着く（着いた足 %d）" % int(landed.n))
	h.expect(lights_out > 0.99, "町の灯が順に消える（%.2f）" % lights_out)
	h.expect(g.flag("ch1.ordo_stopped") and g.flag("ch1.night") and g.room_id == "ch1.home", "フラグと部屋は前と同じ（夜・停止・家）")
	h.expect(cd.stage == null and m.level.visible and cd.shot.is_empty() and absf(_env(m).fog_density - fog0) < 1e-6,
		"家へ戻ると、舞台を片付け、部屋を出し、霞を戻す")
	h.expect(String(m.moods.back()) == "interior", "空と光は家（interior）に戻る（%s）" % m.moods.back())
	h.expect(g.player.pos.distance_to(Vector3(-2, 0, 1.5)) < 0.3, "ハルはベッドの所（%s）" % g.player.pos)
	h.free_game(g)
	made[0].queue_free()


## どこで飛ばしても、場面のカメラ・舞台・霞・部屋の表示・オルドの時計・風が元に戻る
func test_cine_skip_restores() -> void:
	for when in [3.0, 30.0, 50.0]:
		var made: Array = await _setup()
		var m: FakeMain = made[1]
		var cd: CineDirector = made[2]
		var g := m.game
		var fog0 := _env(m).fog_density
		var o := m._ordo()
		for i in int(when * 60.0):
			await _tick(m, cd)
		h.expect(not cd.shot.is_empty(), "%.0f 秒：道筋の途中" % when)
		g.story.begin_skip()
		for i in 8:
			await _tick(m, cd)
		h.expect(cd.shot.is_empty() and absf(_env(m).fog_density - fog0) < 1e-6 and g.room_id == "ch1.training",
			"%.0f 秒で飛ばす：道筋を終え、霞を戻し、訓練場へ" % when)
		h.expect(not is_instance_valid(o) or o.is_processing(), "%.0f 秒で飛ばす：オルドの時計を返す" % when)
		h.expect(m.audio.ambience == "", "%.0f 秒で飛ばす：風を止める" % when)
		h.free_game(g)
		made[0].queue_free()
	# 停止の場面の途中（外の舞台）で飛ばす
	var made2: Array = await _setup()
	var m2: FakeMain = made2[1]
	var cd2: CineDirector = made2[2]
	var g2 := m2.game
	for f in ["ch1.opening_done", "ch1.chores_started", "ch1.nico_rescued", "ch1.scolded", "ch1.debt_scene"]:
		g2.set_flag(f)
	g2.load_room("ch1.home", "from_lower")
	for tr in g2.triggers:
		tr.fired = true
	m2.rebuild()
	for i in 4:
		await _tick(m2, cd2)
	g2.story.start_event("ch1.stop")
	var t := 0
	while t < 20 * 60 and (cd2.stage == null or not cd2.stage.cine_stopping()):
		await _tick(m2, cd2)
		t += 1
	h.expect(cd2.stage != null, "停止の場面：外の舞台の途中")
	g2.story.begin_skip()
	for i in 8:
		await _tick(m2, cd2)
	h.expect(cd2.stage == null and m2.level.visible and cd2.shot.is_empty() and g2.flag("ch1.ordo_stopped") and g2.room_id == "ch1.home",
		"飛ばすと舞台を片付け、家を出す（フラグ・部屋は見たときと同じ）")
	h.free_game(g2)
	made2[0].queue_free()


## 台本の shot・caption：shot は黒帯の場面を始め、time 秒待つ（wait: false なら待たない）。{"shot": {}} は道筋を終える知らせ。
## caption は待たない。スキップ中は shot・caption の知らせを出さない。shot を含むイベントは「カメラを使う」イベント
func test_shot_and_caption_steps() -> void:
	var line := func(who: String, text: String) -> Dictionary: return {"who": who, "face": "normal", "text": text}
	var room := {"name": "t", "playerStart": "start", "geometry": [{"t": "box", "pos": [0, -1, 0], "size": [60, 1, 60]}],
		"markers": {"start": {"pos": [0, 0, 0], "yaw": 0}}, "props": [], "enemies": [], "checkpoints": [], "triggers": []}
	var g := h.make_world_game({"start": {"room": "t.r", "spawn": "start"}, "areas": [{"id": "t", "name": "t", "rooms": {"r": room}}],
		"dialogues": {"t.a": {"lines": [line.call("ハル", "よし")]}},
		"events": {"t.film": {"steps": [{"freeze": true}, {"shot": {"time": 1.0, "eye": [[0, 5, -10]], "look": [[0, 0, 0]]}},
			{"caption": "語り", "time": 3.0}, {"shot": {"time": 2.0, "eye": [[0, 5, 10]], "look": [[0, 0, 0]], "wait": false}},
			{"flag": "t.mid"}, {"wait": 0.5}, {"shot": {}}, {"say": "t.a"}, {"freeze": false}, {"flag": "t.end"}]}}})
	await h.settle()
	h.expect(g.story.event_uses_camera("t.film"), "shot を含むイベントは、台本がカメラを使うイベント（黒帯の場面）")
	g.story.start_event("t.film")
	var evs: Array = []
	for i in 3:
		await h.tree.physics_frame
		g.step(InputFrame.new())
		evs.append_array(g.drain_events())
	var shots := evs.filter(func(e): return e.type == "shot")
	h.expect(g.cinematic() and shots.size() == 1 and float(shots[0].shot.time) == 1.0, "shot：黒帯の場面になり、道筋の知らせを出す")
	h.expect(not g.flag("t.mid"), "shot は time 秒（1 秒）待つ")
	for i in 60:
		await h.tree.physics_frame
		g.step(InputFrame.new())
		evs.append_array(g.drain_events())
	var caps := evs.filter(func(e): return e.type == "caption")
	h.expect(caps.size() == 1 and caps[0].text == "語り" and is_equal_approx(float(caps[0].time), 3.0), "caption：語りの字幕の知らせ（文と秒）")
	h.expect(g.flag("t.mid"), "wait: false の shot は待たない")
	for i in 40:
		await h.tree.physics_frame
		g.step(InputFrame.new())
		evs.append_array(g.drain_events())
	shots = evs.filter(func(e): return e.type == "shot")
	h.expect(shots.size() == 3 and (shots[2].shot as Dictionary).is_empty() and g.cinematic(), "{\"shot\": {}} で道筋を終える知らせ（黒帯は操作が戻るまで続く）")
	h.free_game(g)
	# スキップ中は出さない
	g = h.make_world_game({"start": {"room": "t.r", "spawn": "start"}, "areas": [{"id": "t", "name": "t", "rooms": {"r": room}}],
		"dialogues": {"t.a": {"lines": [line.call("ハル", "よし")]}},
		"events": {"t.film": {"cutscene": true, "steps": [{"freeze": true}, {"say": "t.a"}, {"shot": {"time": 5.0, "eye": [[0, 5, -10]], "look": [[0, 0, 0]]}},
			{"caption": "語り", "time": 3.0}, {"shot": {}}, {"freeze": false}, {"flag": "t.end"}]}}})
	await h.settle()
	g.story.start_event("t.film")
	for i in 3:
		await h.tree.physics_frame
		g.step(InputFrame.new())
	g.drain_events()
	g.story.begin_skip()
	await h.tree.physics_frame
	g.step(InputFrame.new())
	var types: Array = g.drain_events().map(func(e): return String(e.type))
	h.expect(g.flag("t.end") and not types.has("shot") and not types.has("caption") and types.has("skipped"),
		"スキップ中は道筋・字幕の知らせを出さない（%s）" % [types])
	h.free_game(g)


## 語りの字幕（HUD）：出し入れは 0.7 秒、time 秒で消える。下の黒帯のすぐ上（帯に掛からない）。スマホの配置でも画面の中
func test_caption_hud() -> void:
	for compact in [false, true]:
		var vp := SubViewport.new()
		vp.size = Vector2i(1920, 1080) if not compact else Vector2i(1824, 843)
		h.tree.root.add_child(vp)
		var hud := Hud.new()
		vp.add_child(hud)
		hud.compact = compact
		var cam := Camera3D.new()
		vp.add_child(cam)
		await h.tree.process_frame
		var g := h.make_game()
		g.story.cutscene = true
		for i in 30:
			hud.sync(g, cam, DT)
		hud.show_caption("夜明け。赤い砂の大地を、山のような影がゆっくりと歩いていく。", 3.0)
		for i in 60:
			hud.sync(g, cam, DT)
		await h.tree.process_frame
		var vs: Vector2 = hud._root.size
		var r: Rect2 = hud._caption.get_global_rect()
		h.expect(hud.caption_text() != "" and hud._caption.modulate.a > 0.99, "%s：字幕が出る" % ("スマホ" if compact else "PC"))
		h.expect(r.end.y <= vs.y - hud.cinema_bar(vs) + 0.5 and r.position.y > vs.y * 0.5 and r.position.x >= 0.0 and r.end.x <= vs.x,
			"%s：下の黒帯のすぐ上、画面の中（%s / 帯 %.0f）" % ["スマホ" if compact else "PC", r, hud.cinema_bar(vs)])
		for i in 130:
			hud.sync(g, cam, DT)
		h.expect(hud.caption_text() == "", "%s：time 秒で消える" % ("スマホ" if compact else "PC"))
		hud.show_caption("x", 5.0)
		hud.clear_caption()
		h.expect(hud.caption_text() == "", "clear_caption ですぐ消える（スキップ・部屋の移動）")
		h.free_game(g)
		vp.queue_free()
