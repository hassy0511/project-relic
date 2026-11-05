extends RefCounted
## 町の電気（停電の夜）のテスト：docs/design/42_コンテンツの書き方.md 14.8。
## ・正本 GameSim.powered：町の部屋は、オルドの停止（ch1.ordo_stopped）から再始動（ch1.ordo_restarted）まで電気が来ない。遺構はいつも来る。
##   セーブから戻しても・停止の場面をスキップしても同じ
## ・部屋の見た目（RoomView・RoomKit）：明かり・材質に電気の出所（electric・oil）が付き、停電の間だけの灯油ランプは暗く作ったときだけ置く
## ・TownPower（見た目）：停電の部屋では電気の灯が消え（描かない）、油の灯は灯る。再始動を町の外で迎えると、町の部屋に戻っても消えたままで、
##   歓声の合図（fx: town_power_on）で波のように点く。スキップはすぐ終わりの姿。部屋にいる間に止まると、ちらついて消える。
##   画面なしでは材質の値を読み返せないので、最後に入れた値（last_params）も見る

var h: TestHelpers

const STOPPED := ["ch1.opening_done", "ch1.chores_started", "ch1.nico_rescued", "ch1.scolded", "ch1.debt_scene", "ch1.night", "ch1.ordo_stopped"]
const TOWN := ["ch1.mid", "ch1.lower", "ch1.upper", "ch1.home", "ch1.workshop", "ch1.guild", "ch1.mayor", "ch1.training"]


func _init(helpers: TestHelpers) -> void:
	h = helpers


func _game(flags: Array = [], room := "ch1.mid") -> GameSim:
	var g := GameSim.new()
	var vp := SubViewport.new()
	vp.own_world_3d = true
	vp.render_target_update_mode = SubViewport.UPDATE_DISABLED
	vp.size = Vector2i(2, 2)
	h.tree.root.add_child(vp)
	vp.add_child(g)
	g.setup({"world": World.load_manifest("res://content/world.json"), "tuning": TestHelpers.default_tuning(), "seed": 1,
		"start": {"room": room, "spawn": ""}})
	for f in flags:
		g.set_flag(f)
	g.drain_events()
	return g


## 部屋の明かり（Light3D）のうち、出所が src のもの
static func _lights(root: Node, src: String) -> Array:
	return root.find_children("*", "Light3D", true, false).filter(func(l): return String(l.get_meta("source", "")) == src)


static func _dress_count(root: Node, part: String) -> int:
	var n := 0
	for gi in root.find_children("*", "GeometryInstance3D", true, false):
		if String(gi.name) == part.replace("/", "_"):
			n += (gi as MultiMeshInstance3D).multimesh.instance_count if gi is MultiMeshInstance3D else 1
	return n


# ---------------------------------------------------------------- 正本（フラグだけから）

func test_power_follows_flags() -> void:
	var g := _game()
	await h.settle()
	for r in TOWN:
		h.expect(g.powered(r), "停止の前は町に電気が来る（%s）" % r)
	h.expect(String(g.world.room("ch1.mid").get("grid", "")) == "town", "町の部屋は電気の網 town に乗る")
	g.set_flag("ch1.night")
	h.expect(g.powered(), "夜になっただけでは電気は切れない")
	g.set_flag("ch1.ordo_stopped")
	for r in TOWN:
		h.expect(not g.powered(r), "オルドが止まると町の電気が切れる（%s）" % r)
	for r in ["ch1.r01", "ch1.r02", "ch1.r20"]:
		h.expect(g.powered(r), "遺構は電気の網に乗らない（%s。自分の古い灯）" % r)
	h.expect(not g.powered(), "今の部屋（中段）も切れている")
	h.expect(g.grid_powered("") and g.grid_powered("nowhere"), "網の無い部屋・知らない網はいつも電気が来る")
	g.set_flag("ch1.ordo_restarted")
	for r in TOWN:
		h.expect(g.powered(r), "再始動で町の電気が戻る（%s）" % r)
	g.set_flag("ch1.morning")
	g.set_flag("ch1.night", false)
	h.expect(g.powered(), "朝も電気が来ている")
	h.free_game(g)


func test_power_survives_save_and_load() -> void:
	var g := _game(STOPPED, "ch1.home")
	await h.settle()
	h.expect(not g.powered(), "停電の夜の家（セーブの前）")
	var sv = GameSim.parse_save(JSON.stringify(g.to_save()))
	h.free_game(g)
	var g2 := GameSim.new()
	var vp := SubViewport.new()
	vp.own_world_3d = true
	vp.render_target_update_mode = SubViewport.UPDATE_DISABLED
	h.tree.root.add_child(vp)
	vp.add_child(g2)
	g2.setup({"world": World.load_manifest("res://content/world.json"), "tuning": TestHelpers.default_tuning(), "seed": 1, "save": sv})
	await h.settle()
	h.expect(g2.room_id == "ch1.home" and not g2.powered(), "セーブから戻しても、停電のまま（%s）" % g2.room_id)
	var tp := TownPower.new()
	h.expect(tp.begin_room(g2), "セーブから戻した部屋は暗く作る")
	tp.free()
	g2.set_flag("ch1.ordo_restarted")
	h.expect(g2.powered(), "戻したあとで再始動すれば電気が来る")
	g2.get_parent().queue_free()


## 停止の場面（ch1.stop）：見たときと、始まってすぐスキップしたときで、終わりに電気が切れている（見た目も暗く作る）
func test_power_after_stop_scene_and_skip() -> void:
	for skip in [false, true]:
		var g := _game(["ch1.opening_done", "ch1.chores_started", "ch1.nico_rescued", "ch1.scolded", "ch1.debt_scene"], "ch1.home")
		await h.settle()
		for t in g.triggers:
			t.fired = true
		g.story.start_event("ch1.stop")
		var done := await h.run_until(g, 4000, func(i):
			if skip and g.story.skippable():
				g.story.begin_skip()
			return {"confirm": i % 6 < 3} if not g.story.dialogue.is_empty() and not g.story.skipping else {},
			func(): return g.flag("ch1.ordo_stopped") and not g.story.running_event() and g.story.dialogue.is_empty() and not g.story.skipping)
		h.expect(done, "停止の場面が終わる（%s）" % ("スキップ" if skip else "見る"))
		h.expect(not g.powered() and g.room_id == "ch1.home", "停止の場面のあと、家は停電（%s）" % ("スキップ" if skip else "見る"))
		var tp := TownPower.new()
		h.expect(tp.begin_room(g), "停止の場面のあとに作る家は暗い（%s）" % ("スキップ" if skip else "見る"))
		tp.free()
		h.free_game(g)


# ---------------------------------------------------------------- データ（キット・部屋）

func test_power_data_marks_sources() -> void:
	var kit := RoomKit.load_kit("town")
	h.expect(String(kit.mats.amber.get_meta("source", "")) == "electric", "町のキットの琥珀の灯（amber）は電気の灯")
	h.expect(String(kit.mats.flame.get_meta("source", "")) == "oil", "油の灯の芯（flame）は油")
	h.expect(String(kit.mats.skyglass.get_meta("source", "")) == "electric", "屋内の明るい窓（skyglass）は電気で消える")
	h.near(float(kit.mats.skyglass.get_shader_parameter("power_floor")), 0.12, 0.001, "消えた窓に月明かりが少し残る（off）")
	var worn := RoomKit.load_kit("town_worn")
	h.expect(String(worn.mats.amber.get_meta("source", "")) == "electric", "元のキットを継いだキット（town_worn）も同じ")
	var ruins := RoomKit.load_kit("ruins_b1")
	h.expect(not ruins.mats.amber.has_meta("source") and not ruins.mats.flame.has_meta("source"), "遺構のキットの灯は町の電気に関係しない")
	var mesh := RoomKit.part_mesh("town/hand_lantern", kit)
	var names := []
	for s in mesh.get_surface_count():
		names.append(mesh.surface_get_material(s).get_meta("source", "") if mesh.surface_get_material(s).has_meta("source") else "")
	h.expect(names.has("oil") and not names.has("electric"), "携行灯の芯は油の灯（%s）" % [names])
	var home := RoomKit.part_mesh("town/home_set", kit)
	var both := {}
	for s in home.get_surface_count():
		both[String(home.surface_get_material(s).get_meta("source", ""))] = true
	h.expect(both.has("oil") and both.has("electric"), "ハルの家の組は、ベッドの携行灯が油・天井や壁の灯が電気（%s）" % [both.keys()])
	h.expect(RoomKit.electric_materials().has(kit.mats.amber), "電気の材質の一覧に入る")
	# 部屋の明かり：中段の街灯は電気、停電の間だけの灯油ランプは暗く作ったときだけ
	var w := World.load_manifest("res://content/world.json")
	var lit := RoomView.build(w, "ch1.mid", false)
	var dark := RoomView.build(w, "ch1.mid", true)
	h.expect(_lights(lit, "electric").size() >= 6, "中段の街灯・室内灯は電気の灯（%d）" % _lights(lit, "electric").size())
	h.expect(_lights(lit, "oil").is_empty() and _lights(dark, "oil").size() >= 3, "灯油ランプの本物の光は停電の間だけ（%d → %d）" % [
		_lights(lit, "oil").size(), _lights(dark, "oil").size()])
	h.expect(_lights(dark, "oil").size() <= 4, "灯油ランプの本物の光は数個だけ（スマホの描き方の重さ。%d）" % _lights(dark, "oil").size())
	var n_lit := _dress_count(lit, "town/hand_lantern")
	var n_dark := _dress_count(dark, "town/hand_lantern")
	h.expect(n_dark >= n_lit + 4, "停電の間だけ、人のいる所に携行灯を置く（%d → %d）" % [n_lit, n_dark])
	h.expect(dark.find_child("OilGlow", true, false) != null and lit.find_child("OilGlow", true, false) == null,
		"灯油ランプのにじみ・床の輪（描画 1 回）は停電の間だけ")
	var home_room := RoomView.build(w, "ch1.home", false)
	h.expect(_lights(home_room, "oil").size() == 1 and _lights(home_room, "electric").size() == 1, "ハルの家：ベッドの携行灯は油、天井の灯は電気")
	var r02 := RoomView.build(w, "ch1.r02", false)
	h.expect(_lights(r02, "electric").is_empty() and _lights(r02, "oil").is_empty(), "遺構の明かりには出所を付けない（町の電気に関係しない）")
	for n in [lit, dark, home_room, r02]:
		n.free()


# ---------------------------------------------------------------- 見た目（TownPower）

## 停電の中段を作る：電気の灯は描かない、油の灯は灯る、電気の材質は消えた値、空と光は停電の夜
func test_town_power_blackout_room() -> void:
	var g := _game(STOPPED)
	await h.settle()
	var tp := TownPower.new()
	var dark := tp.begin_room(g)
	h.expect(dark, "停電の中段は暗く作る")
	var root := RoomView.build(g.world, g.room_id, dark)
	h.tree.root.add_child(root)
	tp.room_built(root)
	var el := _lights(root, "electric")
	h.expect(not el.is_empty() and el.all(func(l): return not l.visible), "電気の灯はすべて消える（描かない。%d）" % el.size())
	var oil := _lights(root, "oil")
	h.expect(not oil.is_empty() and oil.all(func(l): return l.visible and l.light_energy > 0.5), "灯油ランプは灯る")
	var st: Vector4 = tp.last_params.get("power_state", Vector4.ONE)
	h.near(st.x, 0.0, 0.001, "電気の材質に「消えた」を入れる（最後に入れた値）")
	h.near(st.y, 0.0, 0.001, "波は無い")
	var amber: ShaderMaterial = RoomKit.load_kit("town").mats.amber
	var v = amber.get_shader_parameter("power_state")
	if v != null:
		h.near((v as Vector4).x, 0.0, 0.001, "材質の値も消えた")
	h.expect(tp.light_key(g, "night") == "night_blackout", "外の空と光は停電の夜（night_blackout）")
	var kd: Dictionary = RoomKit.load_kit("town").data
	h.expect(not tp.light_for(g, "night", kd.light).is_empty(), "町のキットに停電の夜の光がある")
	g.load_room("ch1.home", "bed")
	h.expect(tp.light_key(g, "interior") == "interior_blackout" and kd.light.has("interior_blackout"), "停電の屋内（interior_blackout）")
	# 揺らぎ：油の灯の明るさは時間で少し変わる（元の 0.76〜1 倍）
	var e0: float = oil[0].light_energy
	var es := []
	for i in 30:
		tp._process(0.05)
		es.append(oil[0].light_energy)
	h.expect(es.max() - es.min() > 0.01 and es.min() >= float(oil[0].get_meta("energy")) * 0.75, "油の灯はゆっくり揺らぐ（%.2f〜%.2f、元 %.2f）" % [es.min(), es.max(), e0])
	root.queue_free()
	tp.free()
	h.free_game(g)


## 夜の屋内（電気あり）：T5「屋内は夜も明るい」→ interior_night
func test_town_power_interior_night() -> void:
	var g := _game(["ch1.night"], "ch1.home")
	await h.settle()
	var tp := TownPower.new()
	h.expect(not tp.begin_room(g), "停止の前の夜は暗く作らない")
	h.expect(tp.light_key(g, "interior") == "interior_night", "夜の屋内は interior_night（%s）" % tp.light_key(g, "interior"))
	g.set_flag("ch1.night", false)
	h.expect(tp.light_key(g, "interior") == "interior", "昼の屋内は今までどおり")
	tp.free()
	h.free_game(g)


## 再始動を遺構で迎える → 中段に戻っても消えたまま → 歓声の合図で波のように点く。スキップならすぐ
func test_town_power_restart_wave() -> void:
	for skip in [false, true]:
		var g := _game(STOPPED + ["ch1.plaza_done", "ch1.boss_defeated"], "ch1.r20")
		await h.settle()
		var tp := TownPower.new()
		tp.begin_room(g)
		g.set_flag("ch1.ordo_restarted")
		for e in g.drain_events():
			tp.handle(e)
		h.expect(g.powered("ch1.mid") and tp.pending.get("town", false), "遺構で再始動：町の電気は戻ったが、まだ見せていない")
		g.load_room("ch1.mid", "start")
		var dark := tp.begin_room(g)
		h.expect(dark, "中段に戻っても、歓声までは消えたまま（暗く作る）")
		var root := RoomView.build(g.world, g.room_id, dark)
		h.tree.root.add_child(root)
		tp.room_built(root)
		var el := _lights(root, "electric")
		h.expect(el.all(func(l): return not l.visible), "戻った直後は電気の灯が消えている")
		tp.handle({"type": "fx", "id": "town_power_on", "at": Vector3(0, -6, 2), "skipped": skip})
		h.expect(not tp.pending.get("town", false), "合図で見せた")
		if skip:
			h.expect(tp.wave_dir == 0 and tp.level == 1.0 and el.all(func(l): return l.visible), "スキップ：すぐ全部点く")
		else:
			h.expect(tp.wave_dir == 1, "波が始まる")
			var seen_partial := false
			var steps := 0
			while tp.wave_dir != 0 and steps < 400:
				tp._process(1.0 / 60.0)
				steps += 1
				var on := el.filter(func(l): return l.visible).size()
				if on > 0 and on < el.size():
					seen_partial = true
			h.expect(seen_partial, "点く途中がある（近い灯から順に）")
			h.between(steps / 60.0, 1.0, 4.5, "波は数秒で終わる")
			h.expect(tp.level == 1.0 and el.all(func(l): return l.visible and l.light_energy > 0.5), "波のあとは全部点いている")
		h.near((tp.last_params.power_state as Vector4).x, 1.0, 0.001, "電気の材質は「点いた」")
		h.expect(tp.light_key(g, "night") == "night", "空と光も電気のある夜に戻る")
		root.queue_free()
		tp.free()
		h.free_game(g)


## 中段にいる間に電気が切れる（確かめ用）：灯がちらついて消える。逆に戻るとその場で点く
func test_town_power_live_change() -> void:
	var g := _game(["ch1.night"])
	await h.settle()
	var tp := TownPower.new()
	tp.begin_room(g)
	var root := RoomView.build(g.world, g.room_id, false)
	h.tree.root.add_child(root)
	tp.room_built(root)
	var el := _lights(root, "electric")
	h.expect(el.all(func(l): return l.visible), "停止の前は点いている")
	g.set_flag("ch1.ordo_stopped")
	for e in g.drain_events():
		tp.handle(e)
	h.expect(tp.wave_dir == -1, "部屋にいる間に止まると、消えていく")
	var steps := 0
	while tp.wave_dir != 0 and steps < 400:
		tp._process(1.0 / 60.0)
		steps += 1
	h.between(steps / 60.0, 0.5, 2.5, "1〜2 秒でちらついて消える（%.2f 秒）" % (steps / 60.0))
	h.expect(el.all(func(l): return not l.visible) and tp.dark(), "消えたあとは描かない")
	g.set_flag("ch1.ordo_restarted")
	for e in g.drain_events():
		tp.handle(e)
	h.expect(tp.wave_dir == 1, "部屋にいる間に戻ると、その場で点いていく")
	tp.handle({"type": "skipped"})
	h.expect(tp.wave_dir == 0 and not tp.dark(), "スキップで終わりの姿")
	root.queue_free()
	tp.free()
	h.free_game(g)


## 背の上の遠くの町の窓（部屋のオルドの遠景。OrdoView.set_back_lights）も町の電気に従う：
## 停電の部屋では消え、歓声の波で消えた順の逆にちらつきながら戻り、波のあとは灯る。場面の途中は場面の値のまま。電気の網の無い部屋は触らない
class _FakeCine:
	var on := false
	func active() -> bool:
		return on


class _FakeMain extends Node:
	var o := OrdoView.new()
	var cine := _FakeCine.new()
	var state := "playing"
	func _ordo() -> OrdoView:
		return o


func test_town_power_back_windows() -> void:
	var g := _game(STOPPED + ["ch1.plaza_done", "ch1.boss_defeated"], "ch1.r20")
	await h.settle()
	var m := _FakeMain.new()
	var tp := TownPower.new(m)
	tp.begin_room(g)
	tp.room_built(null)
	h.near(m.o.back_power, 0.0, 0.001, "電気の網の無い部屋（遺構）では遠景の窓を触らない")
	g.set_flag("ch1.ordo_restarted")
	for e in g.drain_events():
		tp.handle(e)
	g.load_room("ch1.mid", "start")
	h.expect(tp.begin_room(g), "中段は歓声までは暗く作る")
	tp.room_built(null)
	h.expect(m.o.back_power > 0.5 and is_equal_approx(m.o.back_out, 1.0), "停電の間は遠景の窓も全部消えている（out %.2f）" % m.o.back_out)
	tp.handle({"type": "fx", "id": "town_power_on", "at": Vector3(0, -6, 2), "skipped": false})
	var partial := false
	var flick := false
	var steps := 0
	while tp.wave_dir != 0 and steps < 400:
		tp._process(1.0 / 60.0)
		steps += 1
		partial = partial or (m.o.back_out > 0.01 and m.o.back_out < 0.99)
		flick = flick or m.o.back_flicker > 0.0
	h.expect(partial and flick, "波の間は遠景の窓がちらつきながら順に戻る")
	h.expect(is_equal_approx(m.o.back_power, 1.0) and is_equal_approx(m.o.back_out, 0.0) and is_equal_approx(m.o.back_flicker, 0.0),
		"波のあとは遠景の窓が灯っている")
	# 場面の途中（停止の場面など）は場面（CineDirector）が決めた値を上書きしない
	m.o.set_back_lights(0.7, 0.3, 0.9)
	m.cine.on = true
	tp.begin_room(g)
	tp.room_built(null)
	h.expect(is_equal_approx(m.o.back_out, 0.9) and is_equal_approx(m.o.back_power, 0.7), "場面の途中は場面の値のまま")
	# 場面が終わったら、町の電気の値に戻す（場面の値のまま残さない）
	tp._process(1.0 / 60.0)
	m.cine.on = false
	tp._process(1.0 / 60.0)
	h.expect(is_equal_approx(m.o.back_out, 0.0) and is_equal_approx(m.o.back_power, 1.0) and is_equal_approx(m.o.back_flicker, 0.0),
		"場面が終わると、遠景の窓は町の電気の値に戻る（out %.2f）" % m.o.back_out)
	tp.free()
	m.o.free()
	m.free()
	h.free_game(g)


## 停止の場面の終わり（家の中で電気が切れる）：空と光は、波の間に夜の屋内（interior_night）から停電の屋内（interior_blackout）へ
## 少しずつ移る（波の終わりに 1 こまで青く跳ねない）。歓声の波は逆（停電の夜 → 夜）
func test_town_power_light_blends_over_wave() -> void:
	var g := _game(["ch1.night"], "ch1.home")
	await h.settle()
	var tp := TownPower.new()
	tp.begin_room(g)
	var root := RoomView.build(g.world, g.room_id, false)
	h.tree.root.add_child(root)
	tp.room_built(root)
	var table: Dictionary = RoomKit.load_kit("town").data.light
	var lit: Dictionary = EnvironmentSetup.resolve_light(table.interior_night)
	var dark: Dictionary = EnvironmentSetup.resolve_light(table.interior_blackout)
	h.near(float(tp.light_for(g, "interior", table).ambient_energy), float(lit.ambient_energy), 0.001, "切れる前は夜の屋内の光")
	g.set_flag("ch1.ordo_stopped")
	for e in g.drain_events():
		tp.handle(e)
	h.expect(tp.wave_dir == -1, "家の中で電気が切れる（消えていく波）")
	var prev := float(tp.light_for(g, "interior", table).ambient_energy)
	h.near(prev, float(lit.ambient_energy), 0.02, "波の始めは夜の屋内の光のまま")
	var mids := 0
	var max_jump := 0.0
	var steps := 0
	while tp.wave_dir != 0 and steps < 400:
		tp._process(1.0 / 60.0)
		steps += 1
		var a := float(tp.light_for(g, "interior", table).ambient_energy)
		max_jump = maxf(max_jump, absf(a - prev))
		prev = a
		if a > float(lit.ambient_energy) + 0.05 and a < float(dark.ambient_energy) - 0.05:
			mids += 1
	h.expect(mids > 20, "波の間は環境光が 2 つの間を移る（間の値のこま %d）" % mids)
	h.near(prev, float(dark.ambient_energy), 0.001, "波のあとは停電の屋内の光")
	h.expect(max_jump < 0.05, "1 こまで跳ねない（いちばん大きな変わり %.3f）" % max_jump)
	var c: Color = Color(tp.light_for(g, "interior", table).ambient_color)
	h.expect(c.is_equal_approx(Color(dark.ambient_color)), "色も停電の屋内の色で終わる")
	root.queue_free()
	tp.free()
	h.free_game(g)


## 光の上書きの混ぜ方と、スマホ・ブラウザ版の描き方だけの値（"compat"）
func test_light_blend_and_compat() -> void:
	var b := TownPower.blend_light({"ambient_energy": 0.5, "ambient_color": "#000000", "only_a": 1.0},
		{"ambient_energy": 1.0, "ambient_color": Color.WHITE, "only_b": 2.0}, 0.5)
	h.near(float(b.ambient_energy), 0.75, 0.001, "数は直線で混ぜる")
	h.near((b.ambient_color as Color).r, 0.5, 0.01, "色は色で混ぜる（\"#…\" と Color のどちらでも）")
	h.expect(b.only_a == 1.0 and b.only_b == 2.0, "片方にしか無い項目はそのまま")
	var l := {"ambient_energy": 0.5, "compat": {"ambient_energy": 0.9, "char_fill": 0.6}}
	var r := EnvironmentSetup.resolve_light(l)
	h.expect(not r.has("compat") and l.has("compat"), "compat は外して返す（元は変えない）")
	if EnvironmentSetup.is_compat():
		h.near(float(r.ambient_energy), 0.9, 0.001, "スマホ・ブラウザ版の描き方では compat の値")
	else:
		h.expect(is_equal_approx(float(r.ambient_energy), 0.5) and not r.has("char_fill"), "ほかの描き方では元の値（compat の値を使わない）")
	var kl: Dictionary = RoomKit.load_kit("town").data.light
	for k in ["night", "night_blackout", "interior_night", "interior_blackout"]:
		h.expect(kl[k].has("compat") and kl[k].compat.has("char_fill"), "夜の光（%s）にはスマホ版の環境光と人物の照らしがある" % k)
	for pair in [["night", "night_blackout"], ["interior_night", "interior_blackout"]]:
		var ka: Array = EnvironmentSetup.resolve_light(kl[pair[0]]).keys()
		var kb: Array = EnvironmentSetup.resolve_light(kl[pair[1]]).keys()
		ka.sort()
		kb.sort()
		h.expect(ka == kb, "%s と %s は同じ項目を持つ（波の間に混ぜて、終わりに跳ねない）" % pair)


## 灯ごとのばらつきは部品の置き場所から：家の天井の灯の光は家の部品（home_set、原点）と同じ乱数、飾りの部品の明かりはその部品の置き場所。
## 波は電気の材質の窓（明かりの無い窓）まで届く
func test_town_power_seeds_and_reach() -> void:
	var g := _game(["ch1.night"], "ch1.home")
	await h.settle()
	var tp := TownPower.new()
	tp.begin_room(g)
	var root := RoomView.build(g.world, g.room_id, false)
	h.tree.root.add_child(root)
	tp.room_built(root)
	var ceiling: Array = tp._lights.filter(func(l): return l[2] == "electric")
	h.expect(not ceiling.is_empty(), "家に電気の明かりがある")
	h.near(float(ceiling[0][3]), TownPower.seed_hash(Vector3.ZERO), 0.0001, "天井の灯の光は家の部品の置き場所の乱数（灯の芯と一緒に消える）")
	h.expect(not is_equal_approx(TownPower.seed_hash(Vector3.ZERO), TownPower.seed_hash((ceiling[0][0] as Node3D).position)),
		"（自分の位置の升の乱数とは違う）")
	root.queue_free()
	tp.free()
	h.free_game(g)
	g = _game(["ch1.night"], "ch1.mid")
	await h.settle()
	tp = TownPower.new()
	tp.begin_room(g)
	root = RoomView.build(g.world, g.room_id, false)
	h.tree.root.add_child(root)
	tp.room_built(root)
	var tagged := 0
	for l in tp._lights:
		if l[2] == "electric" and (l[0] as Node).has_meta("power_at"):
			tagged += 1
			var at: Vector3 = TownPower._xform(l[0].get_parent()) * (l[0].get_meta("power_at") as Vector3)
			h.near(float(l[3]), TownPower.seed_hash(at), 0.0001, "飾りの明かりは部品の置き場所の乱数")
	h.expect(tagged > 0, "中段に飾りの部品の電気の明かりがある（%d）" % tagged)
	var origin := Vector3(0, -6, 2)
	var far_lights := 0.0
	for l in tp._lights:
		if l[2] == "electric":
			far_lights = maxf(far_lights, (l[0] as Node3D).global_position.distance_to(origin))
	h.expect(tp.far_from(origin) > far_lights + 5.0, "波は明かりの無い電気の窓まで届く（明かり %.1f m、窓まで %.1f m）" % [far_lights, tp.far_from(origin)])
	root.queue_free()
	tp.free()
	h.free_game(g)


## オルドの体を置かない上段の背の上の町（BackTownView。部屋の "back_town"）の窓も、町の電気に従う（停電の間は消え、戻ると灯る）
class _FakeMainUp extends Node:
	var b := BackTownView.new()
	var cine := _FakeCine.new()
	var state := "playing"
	func _ordo() -> OrdoView:
		return null
	func _back_town() -> BackTownView:
		return b


func test_town_power_back_town_upper() -> void:
	var g := _game(STOPPED + ["ch1.plaza_done"], "ch1.upper")
	await h.settle()
	h.expect(g.room.has("back_town") and not g.room.has("ordo"), "上段は背の上の町だけ（オルドの体は置かない）")
	var m := _FakeMainUp.new()
	var tp := TownPower.new(m)
	h.expect(tp.begin_room(g), "上段は停電の間は暗く作る")
	tp.room_built(null)
	h.expect(m.b.back_power > 0.5 and is_equal_approx(m.b.back_out, 1.0), "停電の間は上段の下の町の窓も消えている（out %.2f）" % m.b.back_out)
	g.set_flag("ch1.ordo_restarted")
	for e in g.drain_events():
		tp.handle(e)
	tp.power_on(null, true)
	h.expect(is_equal_approx(m.b.back_out, 0.0) and is_equal_approx(m.b.back_power, 1.0), "電気が戻ると窓が灯る（out %.2f）" % m.b.back_out)
	tp.free()
	m.b.free()
	m.free()
	h.free_game(g)
