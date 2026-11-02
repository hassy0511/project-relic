extends RefCounted
## 町で感じるオルドの歩み（OrdoSteps。30 章 4.2.1）と設定の「画面の揺れ」（20 章 22 節）のテスト。
## ・時計：OrdoView と同じ周期・同じ時刻に足が着く（2 本ずつ 20 秒ごと）
## ・歩いている間は部屋ごとの足音が鳴り、画面がごく小さく揺れ、布・吊り灯の材質に揺れが入る。屋内は器が鳴り、天井から砂がこぼれる
## ・停止の夜（ch1.ordo_stopped）から再始動（ch1.ordo_restarted）までは鳴らない。再始動の刻みから restart_first_s 秒で重い 1 歩が戻る
## ・部屋を移っても同じリズム（オルドのいない部屋 → オルドのいる部屋 → オルドのいない部屋で、足の時刻がずれない）
## ・遺構（再始動のあとに行ける）は重い音。吊り灯には揺れの重みが入る。「画面の揺れ」は場面・Fx・足音の揺れのどれにも掛かる

var h: TestHelpers

const DT := 1.0 / 60.0


func _init(helpers: TestHelpers) -> void:
	h = helpers


## 鳴らした音を覚える GameAudio。本当には鳴らさない（[id, dB, 高さ, 音の素材がある]）：鳴ったまま次のテスト・終わりへ進むと、
## 音の側（AudioServer）が止めた再生を外すのが間に合わず、終わりに「resources still in use at exit」が出ることがあった（16 回に 3 回）
class RecAudio extends GameAudio:
	var log: Array = []

	func play_gain(id: String, gain_db := 0.0, pitch := 1.0) -> void:
		log.append([id, gain_db, pitch, ResourceLoader.exists("res://assets/audio/%s.ogg" % id)])


## main.gd の代わり（OrdoSteps が使う物だけ）
class FakeMain extends Node3D:
	var game: GameSim
	var level: Node3D
	var camera: CameraRig
	var sun: DirectionalLight3D
	var fx: Fx
	var audio: RecAudio
	var cine = null
	var power = null
	var state := "playing"

	func _ordo() -> OrdoView:
		if level == null or not is_instance_valid(level):
			return null
		return level.get_node_or_null("Ordo") as OrdoView

	func rebuild() -> void:
		if level != null and is_instance_valid(level):
			level.free()
		level = RoomView.build(game.world, game.room_id)
		add_child(level)
		var o := _ordo()
		if o != null:
			o.set_process(false)
			if not OrdoSteps.walk_flag(game):
				o.set_walking(false, true)
		fx.ambient.build(game.room_id, game.room)


func _setup(room: String, flags: Array = []) -> Array:
	var vp := SubViewport.new()
	vp.own_world_3d = true
	vp.size = Vector2i(320, 180)
	vp.render_target_update_mode = SubViewport.UPDATE_DISABLED
	h.tree.root.add_child(vp)
	var m := FakeMain.new()
	vp.add_child(m)
	var g := GameSim.new()
	m.add_child(g)
	g.setup({"world": World.load_manifest("res://content/world.json"), "tuning": TestHelpers.default_tuning(), "seed": 1,
		"start": {"room": room, "spawn": ""}})
	for f in flags:
		g.set_flag(f)
	m.game = g
	m.sun = EnvironmentSetup.build(m)
	m.camera = CameraRig.new()
	m.add_child(m.camera)
	m.camera.current = true
	m.fx = Fx.new()
	m.add_child(m.fx)
	m.audio = RecAudio.new()
	m.add_child(m.audio)
	m.rebuild()
	var st := OrdoSteps.new(m)
	m.add_child(st)
	await h.settle()
	return [vp, m, st]


## 1 刻み：（ゲームは止めたまま）カメラ → 部屋のオルド → 足音（main._physics_process と同じ順）。部屋の移動は呼ぶ側
func _tick(m: FakeMain, st: OrdoSteps) -> void:
	m.camera.sync(m.game, m.game.player.pos, DT, 0.0)
	var o := m._ordo()
	if o != null:
		o.advance(DT)
	st.sync(DT)
	m.fx.vfx.step(DT)


## n 刻み進めて、足音の鳴った時刻（st.time）を返す
func _run(m: FakeMain, st: OrdoSteps, ticks: int) -> Array:
	var at := []
	for i in ticks:
		var n := st.steps_heard
		_tick(m, st)
		if st.steps_heard > n:
			at.append(st.time)
	return at


func _go(m: FakeMain, st: OrdoSteps, room: String) -> void:
	m.game.load_room(room, "")
	m.rebuild()
	m.game.drain_events()


## 片付け：鳴っている音（足音は RecAudio が鳴らさない。ほかの音があれば）を先に止め、止めた再生を音の側（AudioServer。混ぜる回は
## 約 12 ms ごと）が外すのを待ってから消す（main.quit と同じ）
func _free(vp: SubViewport) -> void:
	for n in vp.get_children():
		if n is FakeMain and (n as FakeMain).audio != null:
			(n as FakeMain).audio.stop_all()
	OS.delay_msec(20)
	await h.tree.process_frame
	vp.queue_free()
	await h.tree.process_frame


func test_steps_clock_matches_ordo() -> void:
	var o := OrdoView.new()
	h.expect(is_equal_approx(o.cycle_s, OrdoSteps.CYCLE_S) and is_equal_approx(o.swing_frac, OrdoSteps.SWING_FRAC),
		"時計の周期・振り出しの長さが OrdoView の既定と同じ（%.0f 秒・%.2f）" % [o.cycle_s, o.swing_frac])
	o.free()
	var all := OrdoSteps.plants_between(0.0, 1.0)
	h.expect(all.size() == 8, "1 周で 8 本とも 1 回ずつ着く（%d）" % all.size())
	h.expect(OrdoSteps.plants_between(0.2, 0.25) == ["l2", "r1"], "周期 0.24 で 左 2・右 1 が一緒に着く（%s）" % str(OrdoSteps.plants_between(0.2, 0.25)))
	h.expect(OrdoSteps.plants_between(0.95, 1.05) == ["l3", "r4"], "周期の終わりをまたいでも数える（%s）" % str(OrdoSteps.plants_between(0.95, 1.05)))
	h.near(OrdoSteps.to_next_plant(0.0), 0.24, 1e-6, "次に足が着くまで（周期 0 から 0.24）")
	h.near(OrdoSteps.to_next_plant(0.24), 0.25, 1e-6, "着いた直後は次の組まで 0.25（20 秒）")
	# 本物のオルド（部品を毎刻み動かす）と同じ時刻に着く
	var w := OrdoView.new()
	w.merged = false
	h.tree.root.add_child(w)
	await h.tree.process_frame
	w.set_process(false)
	var real := []
	var t := [0.0]
	w.foot_planted.connect(func(tag, _at): real.append([snappedf(t[0], 0.001), tag]))
	var clock := []
	var p := w.phase
	for i in int(85.0 / DT):
		t[0] += DT
		w.advance(DT)
		for tag in OrdoSteps.plants_between(p, p + DT / OrdoSteps.CYCLE_S):
			clock.append([snappedf(t[0], 0.001), tag])
		p = fposmod(p + DT / OrdoSteps.CYCLE_S, 1.0)
	real.sort()
	clock.sort()
	h.expect(real.size() >= 8 and real == clock, "OrdoView の足が着く刻みと時計の刻みが同じ（%d 本：%s …）" % [real.size(), str(real.slice(0, 4))])
	w.queue_free()


## 家の中（オルドのいない部屋）：20 秒ごとにこもった足音。器が鳴る・天井から砂・画面のごく小さな揺れ・材質の揺れ
func test_steps_walking_interior() -> void:
	var made: Array = await _setup("ch1.home")
	var m: FakeMain = made[1]
	var st: OrdoSteps = made[2]
	_tick(m, st)
	h.expect(st.place_name == "interior" and st.walking, "家の中は interior（歩いている）")
	st.phase = OrdoSteps.plant_phase("l2") - 1.0 / OrdoSteps.CYCLE_S
	var at := _run(m, st, int(42.0 / DT))
	h.expect(at.size() == 3, "42 秒で 3 歩（%d）" % at.size())
	if at.size() >= 2:
		h.near(at[1] - at[0], 20.0, 0.05, "足音の間は 20 秒")
	var thuds := m.audio.log.filter(func(e): return e[0] == "ordo_thud_in")
	h.expect(thuds.size() == at.size(), "家の中の足音はこもった音 ordo_thud_in（%d）" % thuds.size())
	var rattles := m.audio.log.filter(func(e): return String(e[0]).begins_with("ordo_rattle"))
	h.expect(rattles.size() >= 1 and rattles.size() <= thuds.size(), "器が小さく鳴る（%d 回）" % rattles.size())
	var missing := m.audio.log.filter(func(e): return not e[3]).map(func(e): return e[0])
	h.expect(missing.is_empty(), "鳴らす音の素材がどれもある（無い：%s）" % str(missing))
	for e in thuds:
		h.between(float(e[1]), -20.0, -2.0, "足音の大きさ（%.1f dB）" % float(e[1]))
	# 次の足音の直後：画面のずれ、材質の揺れ、天井からの砂
	st.phase = OrdoSteps.plant_phase("l4") - 0.5 / OrdoSteps.CYCLE_S
	_run(m, st, 29)
	var moved := 0.0
	var mats: Array = OrdoSteps.jolt_materials(m.game.room)
	var jolt_w := 0.0
	for i in 40:
		m.camera.sync(m.game, m.game.player.pos, DT, 0.0)
		var p0 := m.camera.global_position
		st.sync(DT)
		moved = maxf(moved, m.camera.global_position.distance_to(p0))
		for mt in mats:
			jolt_w = maxf(jolt_w, (mt.get_shader_parameter("jolt") as Vector4).w)
		m.fx.vfx.step(DT)
	h.expect(st.steps_heard == 4, "4 歩目が鳴った（%d）" % st.steps_heard)
	h.between(moved, 0.002, 0.06, "画面のずれは小さい（最大 %.1f mm。場面の揺れ（Fx の揺れ 0.6 で 9 cm）より小さい）" % (moved * 1000.0))
	h.expect(not mats.is_empty() and jolt_w > 0.0, "揺れの重みを使う材質に足音の揺れが入る（%d 材質、幅 %.3f m）" % [mats.size(), jolt_w])
	h.expect(m.fx.vfx.count() > 0, "天井から砂がこぼれる（粒 %d）" % m.fx.vfx.count())
	# 揺れは数秒で収まり、材質は 0 に戻る
	_run(m, st, int(7.0 / DT))
	var rest := 0.0
	for mt in mats:
		rest = maxf(rest, (mt.get_shader_parameter("jolt") as Vector4).w)
	h.expect(rest == 0.0, "7 秒後には材質の揺れは 0（%.3f）" % rest)
	await _free(made[0])


## 停止の夜から再始動まで鳴らない。再始動すると restart_first_s 秒で重い 1 歩、そのあと 20 秒ごと
func test_steps_stop_and_restart() -> void:
	var made: Array = await _setup("ch1.home", ["ch1.night"])
	var m: FakeMain = made[1]
	var st: OrdoSteps = made[2]
	_tick(m, st)
	h.expect(st.walking, "停止の前の夜は歩いている")
	# 停止の場面の「動力が切れる」合図から、フラグが立つ前も鳴らさない
	st.handle({"type": "fx", "id": "ordo_stop"})
	st.phase = OrdoSteps.plant_phase("r1") - 1.0 / OrdoSteps.CYCLE_S
	var at := _run(m, st, int(5.0 / DT))
	h.expect(at.is_empty() and not st.walking, "動力が切れる合図のあとは鳴らない（%d 歩）" % at.size())
	m.game.set_flag("ch1.ordo_stopped")
	at = _run(m, st, int(40.0 / DT))
	h.expect(at.is_empty() and m.audio.log.filter(func(e): return String(e[0]).begins_with("ordo_")).is_empty(),
		"止まっている間は足音が無い（40 秒で %d 歩）" % at.size())
	var t0 := st.time
	m.game.set_flag("ch1.ordo_restarted")
	at = _run(m, st, int(25.0 / DT))
	var first := float(OrdoSteps.config().get("restart_first_s", 2.5))
	h.expect(at.size() >= 2, "再始動のあと足音が戻る（25 秒で %d 歩）" % at.size())
	if at.size() >= 2:
		h.near(at[0] - t0, first, 0.05, "再始動から %.1f 秒で最初の 1 歩" % first)
		h.near(at[1] - at[0], 20.0, 0.05, "そのあとは 20 秒ごと")
	var thuds := m.audio.log.filter(func(e): return e[0] == "ordo_thud_in")
	h.expect(thuds.size() >= 2 and float(thuds[0][2]) < 0.9 and float(thuds[1][2]) >= 0.9, "最初の 1 歩は重く低い（高さ %.2f、次は %.2f）" % [
		float(thuds[0][2]) if thuds.size() > 0 else 0.0, float(thuds[1][2]) if thuds.size() > 1 else 0.0])
	await _free(made[0])


## 再始動のあとの歓声：町の電気が戻る波（TownPower）の間に足が着いたら、波が終わってから鳴る（灯が戻る → いつもの揺れ、の順。
## 重ねない）。次の足は時計どおり
func test_steps_wait_for_power_wave() -> void:
	var made: Array = await _setup("ch1.home", ["ch1.night", "ch1.ordo_stopped", "ch1.ordo_restarted"])
	var m: FakeMain = made[1]
	var st: OrdoSteps = made[2]
	var tp := TownPower.new(m)
	m.add_child(tp)
	tp.set_process(false)
	m.power = tp
	tp.begin_room(m.game)
	tp.room_built(m.level)
	_tick(m, st)
	# 歓声の前：町の電気はまだ消えたまま。足が着く 0.5 秒前に、戻る波を始める
	tp.level = 0.0
	st.phase = OrdoSteps.plant_phase("l2") - 0.5 / OrdoSteps.CYCLE_S
	tp.power_on(Vector3(0, -6, 2))
	var end := tp.wave_end
	h.expect(tp.wave_dir > 0 and end > 1.0, "電気が戻る波が始まる（%.1f 秒）" % end)
	var t0 := st.time
	var at := []
	for i in int((end + 21.0) / DT):
		var n := st.steps_heard
		tp._process(DT)
		_tick(m, st)
		if st.steps_heard > n:
			at.append(snappedf(st.time - t0, 0.01))
	h.expect(at.size() == 2, "波の間に着いた足は 1 歩、そのあと時計どおりにもう 1 歩（%s 秒）" % str(at))
	if at.size() == 2:
		h.between(float(at[0]), end - 0.02, end + 0.05, "波の間は鳴らさず、波が終わってから鳴る（%.2f 秒。波は %.2f 秒）" % [at[0], end])
		h.near(float(at[1]), 20.5, 0.05, "次の足は着いた刻みから 20 秒（%.2f 秒）" % at[1])
	await _free(made[0])


## 部屋を移っても同じリズム：家（時計）→ 中段（部屋のオルドの足の知らせ）→ 家。どの足音も最初の足音から 20 秒の倍数
func test_steps_continuous_across_rooms() -> void:
	var made: Array = await _setup("ch1.home")
	var m: FakeMain = made[1]
	var st: OrdoSteps = made[2]
	_tick(m, st)
	st.phase = OrdoSteps.plant_phase("l2") - 1.0 / OrdoSteps.CYCLE_S
	var at := _run(m, st, int(6.0 / DT))
	h.expect(at.size() == 1, "家で 1 歩（%d）" % at.size())
	_go(m, st, "ch1.mid")
	_tick(m, st)
	var o := m._ordo()
	h.expect(o != null and st.place_name == "town", "中段は部屋のオルドがいる屋外")
	if o != null:
		h.near(o.phase, st.phase, 1e-4, "中段のオルドに時計の位置を渡す（%.4f と %.4f）" % [o.phase, st.phase])
	at.append_array(_run(m, st, int(30.0 / DT)))
	_go(m, st, "ch1.home")
	at.append_array(_run(m, st, int(26.0 / DT)))
	h.expect(at.size() == 4, "家・中段・家で 4 歩（%d）" % at.size())
	var bad := []
	for t in at:
		var k: float = (float(t) - float(at[0])) / 20.0
		if absf(k - roundf(k)) * 20.0 > 0.05:
			bad.append(snappedf(t - at[0], 0.01))
	h.expect(bad.is_empty() and at.size() == 4, "部屋を移っても足音は 20 秒ごと（最初からの秒：%s）" % str(at.map(func(t): return snappedf(t - at[0], 0.01))))
	var sounds := m.audio.log.filter(func(e): return String(e[0]).begins_with("ordo_thud")).map(func(e): return e[0])
	h.expect(sounds == ["ordo_thud_in", "ordo_thud", "ordo_thud_in", "ordo_thud_in"], "中段は屋外の足音、家はこもった足音（%s）" % str(sounds))
	await _free(made[0])


## 脚ごとの大きさ：近い脚の組ほど大きい（中段の真ん中で、前後の組の差が数 dB）
func test_steps_leg_loudness() -> void:
	var place: Dictionary = OrdoSteps.config().places.town
	var at := Vector3(0, 6.5, 0)
	var near := OrdoSteps.leg_db(place, "l2", at)
	var far := OrdoSteps.leg_db(place, "l1", at)
	h.expect(near > far + 2.0, "中段の真ん中では、真ん中寄りの脚（l2 %.1f dB）が船首の脚（l1 %.1f dB）より大きい" % [near, far])
	var stern := Vector3(0, 1.5, -60)
	h.expect(OrdoSteps.leg_db(place, "r4", stern) > OrdoSteps.leg_db(place, "r1", stern) + 4.0, "船尾の側では船尾の脚が大きい")


## 遺構（オルドの体の中）：再始動のあとは重い音。止まっている間（停止の夜の遺構）は鳴らない
func test_steps_ruins() -> void:
	var made: Array = await _setup("ch1.r12", ["ch1.ordo_stopped", "ch1.ordo_restarted"])
	var m: FakeMain = made[1]
	var st: OrdoSteps = made[2]
	_tick(m, st)
	h.expect(st.place_name == "ruins", "遺構は ruins（%s）" % st.place_name)
	st.phase = OrdoSteps.plant_phase("l3") - 1.0 / OrdoSteps.CYCLE_S
	_run(m, st, 90)
	h.expect(st.steps_heard == 1 and st.last.get("sound", "") == "ordo_thud_deep", "遺構の足音は重い ordo_thud_deep（%s）" % st.last.get("sound", ""))
	m.game.set_flag("ch1.ordo_restarted", false)
	st.phase = OrdoSteps.plant_phase("l3") - 1.0 / OrdoSteps.CYCLE_S
	_run(m, st, 90)
	h.expect(st.steps_heard == 1, "止まっている間の遺構は鳴らない")
	await _free(made[0])


## 灯の揺れの重み：外灯の灯（芯と籠）だけに重みが入り、柱・腕は動かない。置いた携行灯（停電の夜の灯油ランプも）は底から上へ。
## 芯の材質（amber・flame）にも布と同じ風の揺れが入り、足音の揺れの材質に入る。中段の布の下の端
func test_steps_lantern_weights() -> void:
	var kit := RoomKit.load_kit("town")
	var mesh := RoomKit.part_mesh("town/lamp_post", kit)
	h.expect(mesh != null, "外灯の部品を読める")
	if mesh == null:
		return
	var weighted := 0
	var post_moving := 0
	var max_w := 0.0
	for s in mesh.get_surface_count():
		var arr := mesh.surface_get_arrays(s)
		var vs: PackedVector3Array = arr[Mesh.ARRAY_VERTEX]
		var col = arr[Mesh.ARRAY_COLOR]
		if not (col is PackedColorArray) or (col as PackedColorArray).is_empty():
			continue
		for i in vs.size():
			var w := 1.0 - (col as PackedColorArray)[i].a
			if w > 0.01:
				weighted += 1
				max_w = maxf(max_w, w)
				if absf(vs[i].x) < 0.3:
					post_moving += 1
	h.expect(weighted > 20 and post_moving == 0, "外灯の灯に揺れの重み（%d 頂点、最大 %.2f）、柱は動かない（%d）" % [weighted, max_w, post_moving])
	h.between(max_w, 0.3, 0.75, "灯の下の端の重み")
	var mats: Dictionary = kit.mats
	h.expect(mats.amber.get_shader_parameter("sway_amp") == mats.metal.get_shader_parameter("sway_amp"), "芯（amber）にも籠と同じ風の揺れ")
	# 置いた携行灯（芯は油の灯 flame。停電の夜だけ置く灯油ランプも同じ部品）：台の底は動かず、上ほど重い（小さく傾ぐ）
	var hand := RoomKit.part_mesh("town/hand_lantern", kit)
	var base_w := 0.0
	var top_w := 0.0
	for s in hand.get_surface_count():
		var arr := hand.surface_get_arrays(s)
		var vs: PackedVector3Array = arr[Mesh.ARRAY_VERTEX]
		var col = arr[Mesh.ARRAY_COLOR]
		if not (col is PackedColorArray) or (col as PackedColorArray).is_empty():
			continue
		for i in vs.size():
			var w := 1.0 - (col as PackedColorArray)[i].a
			if vs[i].y < 0.05:
				base_w = maxf(base_w, w)
			elif vs[i].y > 0.55:
				top_w = maxf(top_w, w)
	h.expect(base_w < 0.02 and top_w > 0.12 and top_w <= 0.25, "携行灯は底が動かず、上ほど重い（底 %.2f・提げ手 %.2f）" % [base_w, top_w])
	h.expect(mats.flame.get_shader_parameter("sway_amp") == mats.metal.get_shader_parameter("sway_amp"), "芯（flame）にも籠と同じ風の揺れ")
	var world := World.load_manifest("res://content/world.json")
	var room: Dictionary = world.rooms.get("ch1.mid", {})
	var jm := OrdoSteps.jolt_materials(room)
	h.expect(jm.has(mats.amber) and jm.has(mats.flame) and jm.has(mats.metal), "足音の揺れが入る材質に、灯の芯（amber・flame）と金物がある（%d 材質）" % jm.size())
	# 停電の夜の中段：停電の間だけの灯油ランプが増え、どれも重みを足した携行灯の部品で描く
	var count_hand := func(dark: bool) -> int:
		var root := RoomView.build(world, "ch1.mid", dark)
		var n := 0
		for g in root.find_children("*", "GeometryInstance3D", true, false):
			if g is MultiMeshInstance3D and (g as MultiMeshInstance3D).multimesh.mesh == hand:
				n += (g as MultiMeshInstance3D).multimesh.instance_count
			elif g is MeshInstance3D and (g as MeshInstance3D).mesh == hand:
				n += 1
		root.free()
		return n
	var lit: int = count_hand.call(false)
	var blackout: int = count_hand.call(true)
	h.expect(blackout >= lit + 4, "停電の夜の中段の灯油ランプも、揺れの重みのある携行灯（%d → %d）" % [lit, blackout])
	var pts := OrdoSteps.puff_points(room)
	h.expect(pts.size() >= 10, "中段の日よけ・洗濯物の下の端から砂ぼこりを出せる（%d か所）" % pts.size())
	# 船着き場（下段）：吊り灯の部品の中で、木箱の上に置いた灯油ランプは置いた灯（底は動かない）。吊った灯は吊り灯のまま
	var land := RoomKit.part_mesh("town/ordo_landing", kit)
	var lw := {"bottom": 0.0, "top": 0.0, "hung": 0.0}   # ラムダの中から書けるように辞書で
	_each_vertex(land, func(v: Vector3, w: float):
		if Vector2(v.x - 57.52, v.z + 19.8).length() < 0.2:
			if v.y < 3.087 - 0.2:
				lw.bottom = maxf(lw.bottom, w)
			elif v.y > 3.087 + 0.3:
				lw.top = maxf(lw.top, w)
		elif Vector2(v.x - 57.75, v.z + 14.68).length() < 0.2 and v.y < 6.916 - 0.12:
			lw.hung = maxf(lw.hung, w))
	h.expect(lw.bottom < 0.03 and lw.top > 0.12 and lw.top <= 0.25,
		"船着き場の木箱の上の灯油ランプは底が動かず、上ほど重い（底 %.2f・提げ手 %.2f）" % [lw.bottom, lw.top])
	h.expect(lw.hung > 0.4, "船着き場の吊り灯は下の端が重い振り子のまま（%.2f）" % lw.hung)
	# ギルドの十字の吊り灯：天井からの 1 つの振り子（十字の腕の端・鎖にも重み。4 つの灯の下の端は同じ重み）
	var guild := RoomKit.part_mesh("town/guild_set", kit)
	var gw := {"bar": [], "chain": 0.0, "lamps": [0.0, 0.0, 0.0, 0.0]}
	var offs := [Vector2(-0.6, 0.0), Vector2(0.6, 0.0), Vector2(0.0, -0.6), Vector2(0.0, 0.6)]
	_each_vertex(guild, func(v: Vector3, w: float):
		var rel := Vector2(v.x - signf(v.x) * 5.0, v.z)
		if absf(absf(v.x) - 5.0) > 0.9 or absf(v.z) > 0.9:
			return
		if absf(v.y - 4.95) < 0.04 and absf(rel.length() - 0.6) < 0.02 and minf(absf(rel.x), absf(rel.y)) < 0.04:
			gw.bar.append(w)
		elif rel.length() < 0.05 and v.y > 5.3 and v.y < 5.7:
			gw.chain = maxf(gw.chain, w)
		elif v.y < 4.68 and v.x > 0.0:
			for k in 4:
				if (rel - offs[k]).length() < 0.15:
					gw.lamps[k] = maxf(gw.lamps[k], w))
	var bar: Array = gw.bar
	bar.sort()
	var lamps: Array = gw.lamps
	h.expect(not bar.is_empty() and bar[0] > 0.2 and bar[-1] - bar[0] < 0.03 and gw.chain > 0.05 and gw.chain < bar[0],
		"ギルドの吊り灯：十字の腕の端はどれも同じ重み（腕の太さの分だけ違う：%.2f〜%.2f）、鎖（%.2f）も揺れる" % [
			bar[0] if not bar.is_empty() else 0.0, bar[-1] if not bar.is_empty() else 0.0, gw.chain])
	h.expect(lamps.min() > 0.4 and lamps.max() - lamps.min() < 0.02, "4 つの灯の下の端は同じ重み（%s）" % str(lamps))
	# 壁に掛けた垂れ幕（食堂の壁）：足音の揺れを弱めた材質の写し（風の揺れは同じ）。足音の揺れの材質に入り、幅は 0.3 倍
	var wall := RoomKit.part_mesh("town/goods_cloth_wall", kit)
	var soft = null
	for i in wall.get_surface_count():
		var mt := wall.surface_get_material(i)
		if mt != null and mt.has_meta("jolt_scale"):
			soft = mt
	h.expect(soft != null and is_equal_approx(float(soft.get_meta("jolt_scale")), 0.3)
		and soft.get_shader_parameter("sway_amp") == mats.flat.get_shader_parameter("sway_amp"),
		"壁の垂れ幕は足音の揺れを 0.3 倍にした材質の写し（風の揺れは同じ）")
	h.expect(soft != null and OrdoSteps.jolt_materials(room).has(soft), "弱めた写しも足音の揺れの材質に入る")


## 部品の頂点ごとに f(位置, 揺れの重み)
func _each_vertex(mesh: Mesh, f: Callable) -> void:
	if mesh == null:
		return
	for s in mesh.get_surface_count():
		var arr := mesh.surface_get_arrays(s)
		var vs: PackedVector3Array = arr[Mesh.ARRAY_VERTEX]
		var col = arr[Mesh.ARRAY_COLOR]
		var has_col: bool = col is PackedColorArray and (col as PackedColorArray).size() == vs.size()
		for i in vs.size():
			f.call(vs[i], 1.0 - (col as PackedColorArray)[i].a if has_col else 0.0)


## 部屋を出る直前の足音のあとに遅れて出すもの（天井の砂・器の音）は、移った部屋では出さない
func test_steps_delayed_stay_in_room() -> void:
	var made: Array = await _setup("ch1.home")
	var m: FakeMain = made[1]
	var st: OrdoSteps = made[2]
	_tick(m, st)
	st.phase = OrdoSteps.plant_phase("l2") - 0.1 / OrdoSteps.CYCLE_S
	var guard := 0
	while st.steps_heard == 0 and guard < 30:
		_tick(m, st)
		guard += 1
	h.expect(st.steps_heard == 1 and not st._later.is_empty(), "家で 1 歩：天井の砂（と器の音）が少し遅れて出る予定（%d 件）" % st._later.size())
	_go(m, st, "ch1.mid")
	var n := m.audio.log.size()
	_run(m, st, 60)
	var rattles := m.audio.log.slice(n).filter(func(e): return String(e[0]).begins_with("ordo_rattle"))
	h.expect(rattles.is_empty() and m.fx.vfx.count() == 0, "中段へ出たら、家の天井の砂・器の音は出ない（器 %d・粒 %d）" % [rattles.size(), m.fx.vfx.count()])
	await _free(made[0])


## 再始動の重い最初の 1 歩は、炉心の場面の最後の行「巨大な足が、地を踏みしめる。」と一緒に来る：フラグはその行の直前に立ち、
## restart_first_s（行の文字が出始めてすぐ）で鳴る
func test_steps_restart_on_last_line() -> void:
	var ev: Dictionary = U.load_json("res://content/events/ch1_ruins.json")
	var steps: Array = ev.get("ch1.restart", {}).get("steps", [])
	var at := -1
	for i in steps.size():
		if String(steps[i].get("flag", "")) == "ch1.ordo_restarted":
			at = i
	var next: Dictionary = steps[at + 1] if at >= 0 and at + 1 < steps.size() else {}
	var dlg: Dictionary = U.load_json("res://content/dialogue/ch1_ruins.json")
	var lines: Array = dlg.get(String(next.get("say", "")), {}).get("lines", [])
	h.expect(at > 0 and String(steps[at - 1].get("say", "")) == "ch1.restart.b" and lines.size() == 1
		and String(lines[0].text).begins_with("巨大な足が、地を踏みしめる"),
		"再始動のフラグは「巨大な足が、地を踏みしめる。」の行の直前（%s）" % str(next))
	var first := float(OrdoSteps.config().get("restart_first_s", 2.5))
	h.between(first, 0.2, 1.0, "フラグから重い 1 歩まで %.1f 秒（行の文字が出始めてすぐ）" % first)


## 足音の砂ぼこり：布の縁から砂粒が落ち、小さな砂ぼこりが下へ流れる（上がらない）。近い脚・重い 1 歩ほど大きく、夜・停電は暗い。
## 粒はカメラまでの距離の 1/4 より大きくならない
func test_steps_dust_falls() -> void:
	var made: Array = await _setup("ch1.home")
	var m: FakeMain = made[1]
	var amb: AmbientFx = m.fx.ambient
	var vfx: Vfx = m.fx.vfx
	var spots := PackedVector3Array()
	for i in 8:
		spots.append(Vector3(-2.0 + 0.5 * i, 3, 6 + i))
	# [粒の大きさの平均 m, 最大, 色の赤の最大, 上がる粒の数, 砂粒の数, 砂ぼこりの数]
	var measure := func(strength: float, light: float, pts: PackedVector3Array, n: int) -> Array:
		for l in vfx._layers:
			l.parts.clear()
		amb.puffs = pts
		amb.step_puffs(vfx, Vector3.ZERO, Vector3(0, 0, 1), n, strength, light)
		var sum := 0.0
		var most := 0.0
		var lum := 0.0
		var rising := 0
		var dust: Array = vfx._layers[Vfx.DUST].parts
		for q in dust:
			sum += q.s1
			most = maxf(most, q.s1)
			lum = maxf(lum, q.col.r)
			if q.vel.y > 0.0 or q.grav <= 0.0:
				rising += 1
		return [sum / maxf(1.0, dust.size()), most, lum, rising, vfx._layers[Vfx.DOT].parts.size(), dust.size()]
	var far: Array = measure.call(0.95, 1.0, spots, 8)
	var near: Array = measure.call(1.85, 1.0, spots, 8)
	var night: Array = measure.call(1.0, 0.35, spots, 8)
	var close: Array = measure.call(1.85, 1.0, PackedVector3Array([Vector3(0, 0.5, 2.4)]), 1)
	h.expect(far[5] >= 16 and far[4] >= 32 and far[3] == 0, "砂粒 %d と小さな砂ぼこり %d が落ちる（上がる粒 %d）" % [far[4], far[5], far[3]])
	h.expect(near[0] > far[0] * 1.2, "近い脚の組ほど砂ぼこりが大きい（平均 %.2f m と %.2f m）" % [near[0], far[0]])
	h.between(far[1], 0.2, 0.6, "砂ぼこりは小さい（最大 %.2f m）" % far[1])
	h.expect(night[2] < far[2] * 0.6, "夜は暗い（赤 %.3f と %.3f）" % [night[2], far[2]])
	var close_d := Vector3(0, 0.5, 2.4).length()
	h.expect(close[5] > 0 and close[1] <= close_d * 0.25 + 1e-4, "カメラのすぐ近くでは大きくしない（%.2f m で %.3f m）" % [close_d, close[1]])
	await _free(made[0])


## 設定の「画面の揺れ」：Fx の揺れ（CameraRig）・場面の揺れ（CineDirector）・足音の揺れ（OrdoSteps）に掛かる。切なら動かない
func test_shake_scale_applies() -> void:
	var made: Array = await _setup("ch1.home")
	var m: FakeMain = made[1]
	var st: OrdoSteps = made[2]
	_tick(m, st)
	# CameraRig：Fx の揺れ
	var offs := []
	for sc in [1.0, 0.5, 0.0]:
		m.camera.shake_scale = sc
		var d := 0.0
		for i in 30:
			m.camera.sync(m.game, m.game.player.pos, DT, 0.0)
			var p0 := m.camera.global_position
			m.camera.sync(m.game, m.game.player.pos, 0.0, 0.6)
			d = maxf(d, m.camera.global_position.distance_to(p0))
		offs.append(d)
	h.expect(offs[0] > 0.02 and absf(offs[1] - offs[0] * 0.5) < offs[0] * 0.1 and offs[2] == 0.0,
		"Fx の揺れ：標準 %.3f m・弱め %.3f m・切 %.3f m" % offs)
	# CineDirector：道筋の揺れ（"shake"）
	var cd := CineDirector.new(m)
	m.add_child(cd)
	m.cine = cd
	var cine_offs := []
	for sc in [1.0, 0.0]:
		m.camera.shake_scale = sc
		cd.start_shot({"time": 2.0, "frame": "room", "eye": [[0, 2, -6], [0, 2, -6]], "look": [[0, 1.5, 0], [0, 1.5, 0]], "shake": 0.8})
		var d := 0.0
		for i in 40:
			m.camera.sync(m.game, m.game.player.pos, DT, 0.0)
			cd.sync(DT)
			d = maxf(d, m.camera.global_position.distance_to(Vector3(0, 2, -6)))
		cine_offs.append(d)
		cd.reset()
	h.expect(cine_offs[0] > 0.01 and cine_offs[1] < 1e-4, "場面の揺れ：標準 %.3f m・切 %.5f m" % cine_offs)
	m.cine = null
	cd.queue_free()
	# OrdoSteps：足音の揺れ
	var step_offs := []
	for sc in [1.0, 0.0]:
		m.camera.shake_scale = sc
		st.phase = OrdoSteps.plant_phase("r3") - 0.5 / OrdoSteps.CYCLE_S
		var d := 0.0
		for i in 90:
			m.camera.sync(m.game, m.game.player.pos, DT, 0.0)
			var p0 := m.camera.global_position
			st.sync(DT)
			d = maxf(d, m.camera.global_position.distance_to(p0))
		step_offs.append(d)
	h.expect(step_offs[0] > 0.0005 and step_offs[1] == 0.0, "足音の揺れ：標準 %.4f m・切 %.4f m" % step_offs)
	await _free(made[0])
