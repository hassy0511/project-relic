class_name OpeningShots
## オープニングとオルドの停止の場面の確かめ（こま並べの画像と描画の回数）：Demo（--demo=<フォルダ>）から使う。
##   --opening_shots                  「はじめから」でオープニングを始め、決まった時刻（場面の始めからの秒）に撮る。続けて停止の場面
##                                    （ハルの家で眠る ch1.stop）を始め、決まった時刻に撮る
##   --opening_part=opening|stop      片方だけ（既定は両方）
##   --opening_times=0.8,3,…          オープニングを撮る時刻（秒。既定 OPENING_TIMES）。--stop_times=… は停止の場面
## 出力：<フォルダ>/op_<秒×10>.png・st_<秒×10>.png。撮るたびに「描画 op_…：draw 回・物・三角形」を出す。
## 会話（ハルのひと言・停止の会話）は、出しきってから 0.5 秒待って送る（撮る時刻に出ているように）。見た目の確かめだけ（ゲームの中身は変えない）

const OPENING_TIMES := [0.9, 3.0, 9.0, 12.4, 17.0, 23.0, 29.0, 32.3, 35.5, 39.5, 44.0, 49.0, 54.0, 59.0]
const STOP_TIMES := [1.0, 4.5, 6.0, 8.0, 10.0, 11.5, 13.0, 15.0, 17.0, 19.0, 21.5, 24.0]
## 停止の場面の前の本筋のフラグ（ツケの場面まで）
const BEFORE_STOP := ["ch1.opening_done", "ch1.chores_started", "ch1.t_move", "ch1.t_jump", "ch1.t_shoot", "ch1.t_dash", "ch1.nico_ran",
	"ch1.nico_rescued", "ch1.scolded", "ch1.debt_scene"]


static func steps(d) -> Array:
	var m = d.main
	var part := String(m.args.get("opening_part", "opening,stop"))
	var s := []
	if part.contains("opening"):
		s.append_array(_timeline(d, "op", _times(m, "opening_times", OPENING_TIMES), func():
			m.args.erase("mvp")
			m.args.erase("room")
			m.start_game(null)
			m.game.god_mode = true))
	if part.contains("stop"):
		s.append_array(_timeline(d, "st", _times(m, "stop_times", STOP_TIMES), func():
			var g: GameSim = m.game
			g.god_mode = true
			g.story.stop_all()
			g.player_locked = false
			for f in BEFORE_STOP:
				g.set_flag(f)
			g.load_room("ch1.home", "from_lower")
			for t in g.triggers:
				t.fired = true
			d._stand(Vector3(-3, 0, 3.5), Vector3(-6, 0, 3.5))
			g.story.start_event("ch1.stop")))
	return s


static func _times(m, key: String, def: Array) -> Array:
	if not m.args.has(key):
		return def
	return Array(String(m.args[key]).split(",", false)).map(func(x): return float(x))


## 始める（start）→ 時刻ごとに撮る。会話は出しきってから 0.5 秒で送る
static func _timeline(d, prefix: String, times: Array, start: Callable) -> Array:
	var m = d.main
	var s := []
	s.append({"ticks": 1, "setup": start})
	var at := 1
	for t in times:
		var tick := int(round(float(t) * 60.0))
		if tick > at:
			s.append({"ticks": tick - at, "input_fn": func(_i): return _auto_confirm(m)})
			at = tick
		var name := "%s_%03d" % [prefix, int(round(float(t) * 10.0))]
		s.append({"ticks": 1, "shot": name, "input": {}, "after": func():
			var g: GameSim = m.game
			print("描画 %s：draw %d・物 %d・三角形 %d（部屋 %s・黒帯 %s・字幕「%s」・会話 %s）" % [name,
				RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_DRAW_CALLS_IN_FRAME),
				RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_OBJECTS_IN_FRAME),
				RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_PRIMITIVES_IN_FRAME),
				g.room_id, g.cinematic(), m.hud.caption_text(), g.story.dialogue.get("id", "")])})
		at += 1
	# 場面の終わりまで送る
	s.append({"ticks": 900, "input_fn": func(_i): return _auto_confirm(m)})
	return s


## 会話を出しきって 0.5 秒たったら送る（それまでは何も押さない）
static func _auto_confirm(m) -> Dictionary:
	var dl: Dictionary = m.game.story.dialogue
	if dl.is_empty() or int(dl.shown) < String(dl.text).length():
		m.set_meta("op_hold", 0)
		return {}
	var n := int(m.get_meta("op_hold", 0)) + 1
	m.set_meta("op_hold", n)
	return {"confirm": n >= 30 and n % 6 < 3}
