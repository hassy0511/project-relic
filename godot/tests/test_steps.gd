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


## 鳴らした音を覚える GameAudio
class RecAudio extends GameAudio:
	var log: Array = []

	func play_gain(id: String, gain_db := 0.0, pitch := 1.0) -> void:
		log.append([id, gain_db, pitch])
		super(id, gain_db, pitch)


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


func _free(vp: SubViewport) -> void:
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
	var rattles := m.audio.log.filter(func(e): return e[0] == "ordo_rattle")
	h.expect(thuds.size() == at.size(), "家の中の足音はこもった音 ordo_thud_in（%d）" % thuds.size())
	h.expect(rattles.size() >= 1 and rattles.size() <= thuds.size(), "器が小さく鳴る（%d 回）" % rattles.size())
	for e in thuds:
		h.between(float(e[1]), -20.0, -4.0, "足音の大きさ（%.1f dB）" % float(e[1]))
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
	h.between(moved, 0.0005, 0.03, "画面のずれはごく小さい（最大 %.1f mm。場面の揺れより小さい）" % (moved * 1000.0))
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
