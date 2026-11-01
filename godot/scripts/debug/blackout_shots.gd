class_name BlackoutShots
## 停電の夜（オルドの停止 ch1.ordo_stopped から再始動 ch1.ordo_restarted まで）の町の見た目の確かめ：Demo（--demo=<フォルダ>）から使う。
##   --blackout_shots               目覚めの家・広場の集まり・市場の雑貨屋・禁足扉への道・ギルド・工房・上段・再始動の歓声を撮る
##   --blackout_view=plaza,market   一部だけ
##   --blackout_bench=90            撮ったあと、その向きのまま描き続けて、描画の回数とこまの時間を測る（こまの数。0 で測らない）
## 出力：<フォルダ>/bo_<名前>.png（歓声は bo_cheer_<秒×10>.png）。撮るたびに「描画 bo_…：draw 回・物・三角形」、測ると「計測 bo_…」を出す。
## 見た目の確かめだけ（イベントの手順は走らせない。歓声だけは ch1.cheer を始める）

## 本筋のフラグ（立つ順。test_cutscene.gd の TIMELINE の前半）
const LINE := ["ch1.opening_done", "ch1.chores_started", "ch1.t_move", "ch1.t_jump", "ch1.t_shoot", "ch1.t_dash", "ch1.nico_ran",
	"ch1.nico_rescued", "ch1.scolded", "ch1.debt_scene", "ch1.night", "ch1.ordo_stopped", "ch1.plaza_done", "ch1.got_spark",
	"ch1.fell_to_b2", "ch1.chase_seen", "ch1.r07.seal_open", "ch1.frame_fitted", "ch1.r08.trained", "ch1.blade_online",
	"ch1.first_beacon", "ch1.drive_powered", "ch1.shortcut_open", "ch1.diagnosis", "ch1.boss_intro", "ch1.boss_defeated",
	"ch1.ordo_restarted"]
## [名前, 部屋, 立つ所, 見る所, 見下ろす角度（度）, ここまでのフラグ]
const VIEWS := [
	["home", "ch1.home", Vector3(2.4, 0, -3.2), Vector3(-4.0, 0, 3.0), 16.0, "ch1.ordo_stopped"],
	["plaza", "ch1.mid", Vector3(0, 0, -5), Vector3(0, 0, 8), 12.0, "ch1.ordo_stopped"],
	["market", "ch1.mid", Vector3(18.5, 0, -3), Vector3(27, 0, 7), 10.0, "ch1.ordo_stopped"],
	["gate", "ch1.lower", Vector3(-24, 0, -1.5), Vector3(-45, 0, 1), 10.0, "ch1.plaza_done"],
	["guild", "ch1.guild", Vector3(1.5, 0, -3.5), Vector3(-6, 0, 5), 14.0, "ch1.ordo_stopped"],
	["workshop", "ch1.workshop", Vector3(-1.5, 0, -3.5), Vector3(4, 0, 4), 14.0, "ch1.ordo_stopped"],
	["upper", "ch1.upper", Vector3(0, 0, 4), Vector3(0, 0, 22), 10.0, "ch1.ordo_stopped"],
]
## 歓声の場面を撮る時刻（ch1.cheer を始めてからの秒）
const CHEER_TIMES := [0.3, 1.2, 2.0, 3.5]


static func steps(d) -> Array:
	var m = d.main
	var want: Array = Array(String(m.args.get("blackout_view", "")).split(",", false))
	var bench := int(m.args.get("blackout_bench", "0"))
	var s := []
	for v in VIEWS:
		if not want.is_empty() and not want.has(v[0]):
			continue
		s.append({"ticks": 2, "setup": func():
			var g: GameSim = m.game
			g.god_mode = true
			g.story.stop_all()
			g.player_locked = false
			_flags(g, String(v[5]))
			g.load_room(String(v[1]), "")
			for t in g.triggers:
				t.fired = true
			d._stand(v[2], v[3])
			g.cam.pitch = float(v[4]) * U.DEG
			m.snap_views()})
		s.append({"ticks": 60, "input": {}})
		s.append(_shot(d, "bo_" + String(v[0])))
		if bench > 0:
			s.append_array(_bench(d, "bo_" + String(v[0]), bench))
	if want.is_empty() or want.has("cheer"):
		s.append_array(_cheer(d, bench))
	return s


## flag まで（flag も入れて）の本筋のフラグを立て、あとのものは消す。夜は再始動のあとも立てたまま（朝で消える）
static func _flags(g: GameSim, upto: String) -> void:
	var n := LINE.find(upto) + 1
	for i in LINE.size():
		g.set_flag(LINE[i], i < n)
	g.set_flag("ch1.morning", false)


static func _shot(d, name: String) -> Dictionary:
	return {"ticks": 1, "shot": name, "input": {}, "after": func():
		print("描画 %s：draw %d・物 %d・三角形 %d" % [name,
			RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_DRAW_CALLS_IN_FRAME),
			RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_OBJECTS_IN_FRAME),
			RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_PRIMITIVES_IN_FRAME)])}


## その向きのまま n こま描き続けて、描画の回数とこまの時間（実時間）を測る
static func _bench(d, name: String, n: int) -> Array:
	var st := {"draws": [], "us": [], "last": 0}
	return [
		{"ticks": 1, "setup": func():
			RenderingServer.render_loop_enabled = true
			st.last = Time.get_ticks_usec()},
		{"ticks": n, "input_fn": func(i):
			var now := Time.get_ticks_usec()
			if i > 4:
				st.draws.append(RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_DRAW_CALLS_IN_FRAME))
				st.us.append(now - int(st.last))
			st.last = now
			return {}},
		{"ticks": 1, "setup": func():
			RenderingServer.render_loop_enabled = false
			var dr: Array = st.draws
			var us: Array = st.us
			if dr.is_empty():
				return
			var sum := 0
			var mx := 0
			for x in dr:
				sum += int(x)
				mx = maxi(mx, int(x))
			var t := 0
			for x in us:
				t += int(x)
			var ms := float(t) / us.size() / 1000.0
			print("計測 %s（%s）：draw 平均 %.1f・最大 %d／こま %.1f ms（%.1f fps）" % [name, RenderingServer.get_current_rendering_method(),
				float(sum) / dr.size(), mx, ms, 1000.0 / maxf(ms, 0.001)])},
	]


## 再始動の歓声：遺構（炉心の間）で再始動のフラグを立ててから中段へ移り（本番と同じ順）、ch1.cheer を始めて決まった時刻に撮る
static func _cheer(d, bench: int) -> Array:
	var m = d.main
	var s := []
	s.append({"ticks": 2, "setup": func():
		var g: GameSim = m.game
		g.god_mode = true
		g.story.stop_all()
		g.player_locked = false
		_flags(g, "ch1.boss_defeated")
		g.load_room("ch1.r20", "")
		for t in g.triggers:
			t.fired = true})
	s.append({"ticks": 10, "input": {}})
	s.append({"ticks": 2, "setup": func():
		var g: GameSim = m.game
		g.set_flag("ch1.ordo_restarted")
		g.load_room("ch1.mid", "start")
		for t in g.triggers:
			t.fired = true
		d._stand(Vector3(0, 0, -5), Vector3(0, 0, 8))
		g.cam.pitch = 12.0 * U.DEG
		m.snap_views()})
	s.append({"ticks": 40, "input": {}})
	s.append(_shot(d, "bo_cheer_before"))
	s.append({"ticks": 1, "setup": func(): m.game.story.start_event("ch1.cheer")})
	var at := 1
	for t in CHEER_TIMES:
		var tick := int(round(float(t) * 60.0))
		if tick > at:
			s.append({"ticks": tick - at, "input": {}})
			at = tick
		s.append(_shot(d, "bo_cheer_%02d" % int(round(float(t) * 10.0))))
		at += 1
	if bench > 0:
		s.append_array(_bench(d, "bo_cheer", bench))
	return s
