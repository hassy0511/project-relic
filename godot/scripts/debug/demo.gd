class_name Demo
extends Node
## 自動の見本：決まった入力でゲームを進め、場面ごとに画面を撮って終了する。
## 画面の確認と、起動から一通り遊べることの確認（通しのテスト）に使う。
## 起動 → ヤーナと会話 → 奥の部屋で戦闘 → 光刃 → ひび割れた壁をドリルで壊す
## → 試しの部屋（Arena）で 子番機・盾型・浮遊型・ボス「閂」（段階の移り変わり・核の露出・撃破）を順に確かめる
## 進み方はゲームの刻み（1/60 秒）で数える（描画が遅い環境でも同じ場面になるように）

var main
var out_dir: String
var _steps: Array = []
var _step := 0
var _tick := 0
var _cur := {}
var _pending_shot := ""
var _started := false
var _shooting := false
var failures: Array = []
var _seen := {}
## 通しの自動操作（--ch1_full）：Ch1Run が tick() で 1 刻みずつ入力を渡す
var _bot_active := false
var _bot_frame := {}
var _bot_consumed := false
var bot_ticks := 0
var shots_taken := 0
var _ui_shots := 0
## 何刻みごとに撮るか（1800 刻み = ゲーム内の 30 秒）
var bot_shot_every := 1800
signal bot_ticked
signal bot_shot_done


func _init(m, dir: String) -> void:
	main = m
	out_dir = dir


func _ready() -> void:
	DirAccess.make_dir_recursive_absolute(out_dir)
	# 画面あり（xvfb など）のときは、撮る間だけ描く（描かない刻みは速く進む。通しの自動操作が現実的な時間で終わる）
	if DisplayServer.get_name() != "headless":
		RenderingServer.render_loop_enabled = false
	_steps = [
		# F2 の見た目の切り替え（行って戻る）
		{"ticks": 2, "setup": func(): main.toggle_haru()},
		{"ticks": 1, "check": func():
			return _check(main.haru_path.ends_with("haru_a.glb") and main.player_view.model != null, "ハルの見た目を切り替えられる")},
		{"ticks": 2, "setup": func(): main.toggle_haru()},
		{"ticks": 1, "check": func():
			return _check(main.haru_path.ends_with("haru_r.glb") and main.player_view.model != null, "元の見た目に戻せる")},
		{"ticks": 60, "input": {"move_y": 1.0}},
		{"ticks": 1, "shot": "02_run"},
		{"ticks": 2, "setup": func(): _stand(Vector3(1.95, 0, -4.5), Vector3(2.5, 0, -3))},
		{"ticks": 2, "input": {"jump": true}},
		{"ticks": 40, "input": {}},
		{"ticks": 1, "shot": "03_dialogue", "check": func(): return _check(not main.game.story.dialogue.is_empty(), "ヤーナとの会話が始まる")},
		# 会話が出ている間だけ送る（終わったあとに押すと、また話しかけてしまう）
		{"ticks": 600, "input_fn": func(i): return {"jump": i % 20 < 2 and not main.game.story.dialogue.is_empty()}},
		{"ticks": 1, "check": func(): return _check(main.game.has_item("special.drill"), "会話でドリルを受け取る")},
		{"ticks": 2, "setup": func(): _stand(Vector3(0, 0, 47), Vector3(0, 0, 56))},
		{"ticks": 30, "input": {}},
		{"ticks": 60, "input_fn": func(i): return {"lock_on": true, "fire": i % 10 < 5}},
		{"ticks": 1, "shot": "04_lock_on", "input": {"lock_on": true}, "check": func():
			return _check(main.game.lock_on.target != null, "ロックオンできる")},
		{"ticks": 120, "input_fn": func(i): return {"lock_on": true, "fire": i % 10 < 5}},
		{"ticks": 2, "setup": func(): _stand(Vector3(0, 0, 57.6), Vector3(0, 0, 60))},
		{"ticks": 13, "input_fn": func(i): return {"sword": i % 8 < 2}},
		{"ticks": 1, "shot": "05_slash"},
		{"ticks": 90, "input_fn": func(i): return {"sword": i % 8 < 2}},
		{"ticks": 2, "setup": func():
			# 番機が壁の前に入り込むとドリルが番機に当たるので、先に片付ける
			for e in main.game.enemies:
				main.game.damage_enemy(e, 9999.0, e.pos, {})
			_stand(Vector3(0, 0, 63.1), Vector3(0, 0, 64.5))},
		{"ticks": 40, "input": {}},
		{"ticks": 30, "input": {"special": true}},
		{"ticks": 1, "shot": "06_drill"},
		{"ticks": 60, "input": {"special": true}},
		{"ticks": 30, "input": {}},
		{"ticks": 1, "shot": "07_after_drill", "check": func(): return _check(main.game.breakables[0].broken, "ドリルで壁を壊せる")},
	]
	# 引数 --arena_only：試しの部屋の場面だけ（画面の確認を早く撮るため）
	if main.args.has("arena_only") or main.args.has("world_only") or main.args.has("ch1_shots") or main.args.has("ruins_shots") or main.args.has("ch1b_shots") or main.args.has("cp2d_shots") or main.args.has("pad_shots") or main.args.has("ui_shots") or main.args.has("town_shots"):
		_steps.clear()
	if main.args.has("ch1_full"):
		_steps.clear()
	elif main.args.has("pad_shots"):
		_steps.append_array(_pad_steps())
	elif main.args.has("ui_shots"):
		_steps.append_array(_ui_steps())
	elif main.args.has("cp2d_shots"):
		_steps.clear()
		_steps.append_array(_cp2d_steps())
	elif main.args.has("ch1_shots"):
		_steps.append_array(_ch1_steps())
	elif main.args.has("ruins_shots"):
		_steps.append_array(_ruins_survey_steps())
	elif main.args.has("ch1b_shots"):
		_steps.append_array(_ch1b_steps())
	elif main.args.has("town_shots"):
		_steps.append_array(_town_steps())
	else:
		if not main.args.has("world_only"):
			_steps.append_array(_arena_steps())
		_steps.append_array(_world_steps())
		_steps.append_array(_cp2d_steps())
		_steps.append_array(_pad_steps())
		_steps.append_array(_ui_steps())
	if not main.args.has("ch1_full"):
		_steps.append({"ticks": 1, "done": true})


## 試しの部屋の見本：新しい試合を始め、決まった場面を作って確かめる（やられないように god_mode）
func _arena_start(kind: String) -> void:
	main.load_arena(kind)
	main.game.god_mode = true
	_seen.clear()


## 世界と進行の見本（動作確認用の小エリア sample）：鍵つきの扉・宝箱・動力の仕掛け・部屋の移動・セーブからの復帰
func _world_steps() -> Array:
	var shoot := func(target: Vector3):
		main.game.spawn_player_shot({"origin": target + Vector3(0, 0, -6), "dir": Vector3(0, 0, 1), "speed": 40.0, "range": 30.0, "damage": 5.0, "radius": 0.2, "pierce": false, "kind": "normal"})
	return [
		{"ticks": 2, "setup": func():
			main.arena_kind = ""
			main.args["room"] = "sample.hub"
			main.start_game(null)
			main.game.god_mode = true
			_stand(Vector3(-6.4, 0, 8), Vector3(-8, 0, 8))},
		{"ticks": 20, "input": {}},
		{"ticks": 1, "shot": "20_world_hub", "input": {}},
		{"ticks": 2, "input": {"jump": true}},
		{"ticks": 2, "input": {}},
		{"ticks": 1, "check": func(): return _check(main.game.has_item("key.sample") and main.game.flag("chest.sample.key_chest"), "宝箱から鍵が手に入る（開けたことが記録される）")},
		{"ticks": 2, "setup": func(): _stand(Vector3(0, 0, 10.4), Vector3(0, 0, 13))},
		{"ticks": 20, "input": {}},
		{"ticks": 2, "input": {"jump": true}},
		{"ticks": 40, "input": {}},
		{"ticks": 1, "shot": "21_world_door", "check": func(): return _check(main.game.doors[0].is_open, "鍵で施錠された扉が開く")},
		{"ticks": 150, "input": {"move_y": 1.0}},
		{"ticks": 20, "input": {}},
		{"ticks": 1, "shot": "22_world_vault", "check": func(): return _check(main.game.room_id == "sample.vault", "開いた扉の奥の部屋に移る")},
		{"ticks": 2, "setup": func(): main.game.go_to("gym", "from_hub")},
		{"ticks": 30, "input": {}},
		{"ticks": 1, "shot": "23_world_gym", "check": func(): return _check(main.game.room_id == "sample.gym", "別の部屋へ移れる")},
		{"ticks": 2, "setup": func():
			shoot.call(Vector3(-6, 1.5, 12))
			shoot.call(Vector3(6, 1.5, 12))},
		{"ticks": 20, "input": {}},
		{"ticks": 1, "check": func(): return _check(main.game.flag("switch.s1") and main.game.flag("switch.s2"), "動力の球を撃つと動力が通る")},
		{"ticks": 2, "setup": func(): _stand(Vector3(0, 0.5, 9), Vector3(0, 0, 16))},
		{"ticks": 150, "input": {}},
		{"ticks": 1, "shot": "24_world_lift", "check": func(): return _check(main.game.player.pos.y > 3.5, "上がる足場がハルを運ぶ")},
		{"ticks": 2, "setup": func():
			var save = JSON.parse_string(JSON.stringify(main.game.to_save()))
			main.start_game(save)},
		{"ticks": 20, "input": {}},
		{"ticks": 1, "check": func():
			return _check(main.game.room_id == "sample.gym" and main.game.flag("switch.s1") and main.game.movers[0].pos.y > 3.9, "セーブから復帰すると部屋・フラグ・足場の状態が戻る")},
	]


## 第 1 章 前半の画面の確認（--ch1_shots）：町の 3 段・訓練場・ニコの戦闘・夜の町・ヤーナが銃を渡す場面
func _ch1_steps() -> Array:
	var go := func(room: String, spawn: String, at: Vector3, look: Vector3, flags: Array = []):
		var g: GameSim = main.game
		g.god_mode = true
		for f in flags:
			g.set_flag(f)
		g.load_room(room, spawn)
		_stand(at, look)
	# 会話を決定ボタンで送る代わりに、直接送る（撮影を速くするため）。n 回
	var skip := func(n: int):
		for i in n:
			if main.game.story.blocking():
				main.game.story.confirm()
	var night := ["ch1.night", "ch1.ordo_stopped", "ch1.scolded", "ch1.debt_scene", "ch1.nico_rescued"]
	return [
		{"ticks": 230, "input": {}},
		{"ticks": 1, "shot": "ch1_01_opening", "input": {}},
		{"ticks": 2, "setup": func(): skip.call(30)},
		{"ticks": 60, "input": {}},
		{"ticks": 1, "check": func(): return _check(main.game.room_id == "ch1.training" and main.game.flag("ch1.opening_done"), "オープニングのあと訓練場へ")},
		{"ticks": 2, "setup": func(): skip.call(30)},
		{"ticks": 2, "setup": func():
			go.call("ch1.training", "start", Vector3(0, 0, -6), Vector3(0, 0, 30), ["ch1.chores_started", "ch1.t_move", "trigger.ch1.training.start"])
			main.hud.set_hint({"kb": "Space でジャンプ（長押しで高く）　② の段に登ってみよう", "pad": "", "touch": ""})},
		{"ticks": 50, "input": {}},
		{"ticks": 1, "shot": "ch1_02_training", "input": {}},
		{"ticks": 2, "setup": func():
			main.hud.set_hint("")
			go.call("ch1.lower", "start", Vector3(-14, 0, -9), Vector3(14, 0, 8))},
		{"ticks": 50, "input": {}},
		{"ticks": 1, "shot": "ch1_03_lower", "input": {}},
		{"ticks": 2, "setup": func(): go.call("ch1.mid", "start", Vector3(-6, 0, -9), Vector3(10, 0, 8))},
		{"ticks": 50, "input": {}},
		{"ticks": 1, "shot": "ch1_04_mid", "input": {}},
		{"ticks": 2, "setup": func(): go.call("ch1.upper", "start", Vector3(-6, 0, -9), Vector3(4, 0, 18))},
		{"ticks": 50, "input": {}},
		{"ticks": 1, "shot": "ch1_05_upper", "input": {}},
		{"ticks": 2, "setup": func(): go.call("ch1.r01", "from_town", Vector3(0, 0, -6), Vector3(0, 0, 8), ["ch1.nico_ran", "ch1.chores_started"])},
		{"ticks": 50, "input": {}},
		{"ticks": 1, "shot": "ch1_06_nico_dialogue", "input": {}},
		{"ticks": 2, "setup": func(): skip.call(8)},
		{"ticks": 50, "input": {}},
		{"ticks": 1, "shot": "ch1_07_nico_fight", "check": func(): return _check(not main.game.enemies.is_empty() and main.game.enemies[0].kind == "mini", "ニコの救出で子番機が出る")},
		{"ticks": 2, "setup": func():
			for e in main.game.enemies:
				main.game.damage_enemy(e, 9999.0, e.pos, {})},
		{"ticks": 60, "input": {}},
		{"ticks": 2, "setup": func(): skip.call(30)},
		{"ticks": 40, "input": {}},
		{"ticks": 2, "setup": func(): skip.call(30)},
		{"ticks": 60, "input": {}},
		{"ticks": 1, "check": func(): return _check(main.game.flag("ch1.nico_rescued") and main.game.room_id == "ch1.lower", "ニコを救出して町へ戻る")},
		{"ticks": 2, "setup": func(): go.call("ch1.mid", "start", Vector3(-2, 0, -4), Vector3(0, 0, 8), night)},
		{"ticks": 70, "input": {"move_y": 1.0}},
		{"ticks": 2, "setup": func(): skip.call(4)},
		{"ticks": 50, "input": {}},
		{"ticks": 1, "shot": "ch1_08_night_plaza", "input": {}},
		{"ticks": 2, "setup": func(): skip.call(30)},
		{"ticks": 60, "input": {}},
		{"ticks": 2, "setup": func(): skip.call(30)},
		{"ticks": 2, "setup": func(): _stand(Vector3(20, 0, -2), Vector3(28, 0, 8))},
		{"ticks": 50, "input": {}},
		{"ticks": 1, "shot": "ch1_09_night_market", "input": {}},
		{"ticks": 2, "setup": func():
			go.call("ch1.lower", "start", Vector3(-26, 0, 0), Vector3(-45, 0, 0), night + ["ch1.plaza_done"])
			main.game.player.teleport(Vector3(-33, 0, 0), 4.71)},
		{"ticks": 50, "input": {}},
		{"ticks": 2, "setup": func(): skip.call(12)},
		{"ticks": 50, "input": {}},
		{"ticks": 1, "shot": "ch1_10_yana_gun", "input": {}},
		{"ticks": 2, "setup": func(): skip.call(30)},
		{"ticks": 90, "input": {}},
		{"ticks": 1, "shot": "ch1_11_gate_open", "check": func(): return _check(main.game.flag("ch1.got_spark") and main.game.has_item("weapon.spark"), "ヤーナから父の銃を受け取る")},
	]


## 町の見た目の確認（--town_shots。中段の広場と市場を昼と停止の夜に、いくつかの向きから撮る。イベントは走らせない）
## --town_view=<名前> で 1 つの向きだけ（スマホの寸法の撮影用）
func _town_steps() -> Array:
	# [名前, 立つ所, 見る所, 見下ろす角度（度）]
	var views := [
		["plaza", Vector3(0, 0, -9), Vector3(0, 0, 8), 14.0],
		["market", Vector3(17, 0, -2), Vector3(32, 0, 6), 12.0],
		["west", Vector3(-6, 0, -5), Vector3(-30, 0, 6), 12.0],
		["edge", Vector3(-20, 0, -12.5), Vector3(-34, 0, -30), 22.0],
		["side", Vector3(-44, 0, -4), Vector3(-70, 0, -14), 16.0],
		["high", Vector3(0, 5, 29), Vector3(0, 0, 0), 30.0],
	]
	if main.args.has("town_view"):
		views = views.filter(func(v): return v[0] == main.args["town_view"])
	var night := ["ch1.night", "ch1.ordo_stopped", "ch1.scolded", "ch1.debt_scene", "ch1.nico_rescued", "ch1.plaza_done"]
	var steps := []
	for state in ["day", "night"]:
		for v in views:
			steps.append({"ticks": 2, "setup": func():
				var g: GameSim = main.game
				g.god_mode = true
				for f in night:
					g.set_flag(f, state == "night")
				g.load_room("ch1.mid", "start")
				for t in g.triggers:
					t.fired = true
				_stand(v[1], v[2])
				g.cam.pitch = float(v[3]) * U.DEG
				main.snap_views()})
			steps.append({"ticks": 40, "input": {}})
			steps.append({"ticks": 1, "shot": "town_%s_%s" % [state, v[0]], "input": {}})
	return steps


## 遺構の全部屋を 1 枚ずつ撮る（--ruins_shots。部屋の形と色の確認用。イベントは走らせない）
func _ruins_survey_steps() -> Array:
	var list := [
		["r02", "from_r01", Vector3(0, 0, -10), Vector3(0, 0, 5)], ["r03", "from_r02", Vector3(0, 0, -16), Vector3(0, 0, 10)],
		["r04", "from_r03", Vector3(0, 0, -9.5), Vector3(0, 0, 6)], ["r05", "from_r04", Vector3(0, 0, -9.5), Vector3(0, 0, 8)],
		["r06", "fall", Vector3(0, 0, -12), Vector3(0, 0, 8)], ["r07", "from_r06", Vector3(0, 0, -16), Vector3(0, 0, 18)],
		["r08", "from_r07", Vector3(0, 0, -8.5), Vector3(0, 0, 0)], ["r09", "from_r08", Vector3(0, 0, -9.5), Vector3(0, 0, 8)],
		["r10", "from_r09", Vector3(0, 0, -9.5), Vector3(0, 0, 8)], ["r11", "from_r10", Vector3(-3, 21, -3.5), Vector3(3, 14, 3)],
		["r12", "from_r11", Vector3(0, 0, -16), Vector3(0, 0, 12)], ["r13", "from_r12", Vector3(0, 0, -12.5), Vector3(0, 0, 8)],
		["r14", "from_r12", Vector3(3, 0, 0), Vector3(-5, 0, 0)], ["r15", "from_r13", Vector3(0, 0, -9.5), Vector3(0, 0, 8)],
		["r16", "from_r15", Vector3(0, 20, -3), Vector3(0, 10, 3)], ["r17", "from_r12", Vector3(3, 0, 0), Vector3(-5, 0, 0)],
		["r18", "from_r16", Vector3(0, 0, -10), Vector3(0, 0, 6)], ["r19", "from_r18", Vector3(0, 0, 14.9), Vector3(0, 0, 0)],
		["r20", "from_r19", Vector3(0, 0, -8), Vector3(0, 0, 2)],
	]
	var steps := []
	for it in list:
		steps.append({"ticks": 2, "setup": func():
			var g: GameSim = main.game
			g.god_mode = true
			g.load_room("ch1." + it[0], it[1])
			for t in g.triggers:
				t.fired = true
			_stand(it[2], it[3])})
		steps.append({"ticks": 50, "input": {}})
		steps.append({"ticks": 1, "shot": "ruin_" + it[0], "input": {}})
	return steps


## 第 1 章 後半の画面の確認（--ch1b_shots）：B1 崩落・B2 配管広間・B3 ピストン・浮遊型・ボス・ノードの記憶・朝の町・章末
func _ch1b_steps() -> Array:
	var go := func(room: String, spawn: String, at: Vector3, look: Vector3, flags: Array = []):
		var g: GameSim = main.game
		g.god_mode = true
		# 前の場面のイベント・会話を片付ける
		g.story._event_queue.clear()
		g.story.dialogue = {}
		g.story._wait_time = 0.0
		g.story._has_wait_cond = false
		g.story._waiting_dialogue = false
		g.player_locked = false
		g.cam_focus = null
		for f in flags:
			if String(f).begins_with("-"):
				g.set_flag(String(f).substr(1), false)
			else:
				g.set_flag(f)
		g.load_room(room, spawn)
		for t in g.triggers:
			t.fired = true
		_stand(at, look)
	var skip := func(n: int):
		for i in n:
			if main.game.story.blocking():
				main.game.story.confirm()
	var late := ["ch1.got_spark", "ch1.ordo_stopped", "ch1.night"]
	var all := [
		{"ticks": 230, "input": {}},
		{"ticks": 2, "setup": func(): skip.call(30)},
		{"ticks": 60, "input": {}},
		{"ticks": 2, "setup": func(): skip.call(30)},
		{"ticks": 2, "setup": func():
			go.call("ch1.r05", "from_r04", Vector3(0, 0, 0), Vector3(0, 0, 8), late)
			main.game.story.start_event("ch1.collapse")},
		{"ticks": 24, "input": {}},
		{"ticks": 2, "setup": func(): skip.call(2)},
		{"ticks": 75, "input": {}},
		{"ticks": 1, "shot": "ch1b_01_collapse", "input": {}},
		{"ticks": 2, "setup": func(): skip.call(4)},
		{"ticks": 2, "setup": func(): go.call("ch1.r09", "from_r08", Vector3(0, 0, -9.5), Vector3(0, 0, 8), late + ["ch1.frame_fitted"])},
		{"ticks": 150, "input": {"move_y": 0.0}},
		{"ticks": 1, "shot": "ch1b_02_b2_pipes", "input": {}},
		{"ticks": 2, "setup": func(): go.call("ch1.r12", "from_r11", Vector3(0, 0, -10.5), Vector3(0, 0, 12), late + ["ch1.frame_fitted", "ch1.drive_powered", "switch.ch1.r12.s1", "switch.ch1.r12.s2"])},
		{"ticks": 130, "input": {}},
		{"ticks": 1, "shot": "ch1b_03_b3_pistons", "input": {}},
		{"ticks": 2, "setup": func(): go.call("ch1.r13", "from_r12", Vector3(0, 0, -9), Vector3(0, 3, 8), late + ["ch1.frame_fitted", "ch1.drive_powered"])},
		{"ticks": 150, "input": {}},
		{"ticks": 1, "shot": "ch1b_04_floaters", "input": {}},
		{"ticks": 2, "setup": func(): go.call("ch1.r19", "from_r18", Vector3(0, 0, 6), Vector3(0, 0, -8), late + ["ch1.frame_fitted", "ch1.boss_intro", "ch1.diagnosis"])},
		{"ticks": 420, "input": {}},
		{"ticks": 1, "shot": "ch1b_05_boss", "input": {}},
		{"ticks": 2, "setup": func():
			go.call("ch1.r20", "from_r19", Vector3(0, 0, -6), Vector3(0, 0, 2), late + ["ch1.frame_fitted", "ch1.boss_defeated", "ch1.ordo_restarted"])
			main.game.story.start_dialogue("ch1.node")},
		{"ticks": 2, "setup": func(): skip.call(4)},
		{"ticks": 70, "input": {}},
		{"ticks": 1, "shot": "ch1b_06_node_memory", "input": {}},
		{"ticks": 2, "setup": func(): skip.call(40)},
		{"ticks": 2, "setup": func(): go.call("ch1.mid", "start", Vector3(-4, 0, -4), Vector3(8, 0, 10), ["-ch1.night", "ch1.got_spark", "ch1.ordo_stopped", "ch1.ordo_restarted", "ch1.morning", "ch1.descent_permit", "ch1.plaza_done"])},
		{"ticks": 60, "input": {}},
		{"ticks": 1, "shot": "ch1b_07_morning_town", "input": {}},
		{"ticks": 2, "setup": func():
			go.call("ch1.upper", "start", Vector3(0, 0, 16), Vector3(0, 0, 40), ["-ch1.night", "ch1.got_spark", "ch1.ordo_restarted", "ch1.morning", "ch1.descent_permit", "ch1.drill_developed"])
			main.game.story.start_event("ch1.ending")},
		{"ticks": 240, "input": {}},
		{"ticks": 1, "shot": "ch1b_08_ending", "check": func(): return _check(main.game.story.running_event() or main.game.flag("ch1.complete"), "章末の演出が走る")},
		{"ticks": 2, "setup": func(): skip.call(40)},
		{"ticks": 90, "input": {}},
		{"ticks": 2, "setup": func(): skip.call(40)},
		{"ticks": 60, "input": {}},
		{"ticks": 1, "check": func(): return _check(main.game.flag("ch1.complete"), "章末のフラグが立つ")},
	]
	# --only8：章末の場面だけ（撮り直し用）
	if main.args.has("only8"):
		return [{"ticks": 20, "input": {}}] + all.slice(all.size() - 8)
	return all


func _alive_count(kind: String) -> int:
	var n := 0
	for e in main.game.enemies:
		if e.kind == kind and e.alive:
			n += 1
	return n


func _arena_steps() -> Array:
	var steps := []
	# 子番機：跳びついてくる。銃で倒す
	steps.append_array([
		{"ticks": 2, "setup": func():
			_arena_start("mini")
			_stand(Vector3(0, 0, 2), Vector3(0, 0, -9))},
		{"ticks": 150, "input": {}},
		{"ticks": 1, "shot": "10_mini", "input": {}},
		{"ticks": 420, "input_fn": func(i): return {"lock_on": true, "fire": i % 8 < 4}},
		{"ticks": 1, "check": func():
			return _check(_alive_count("mini") < 3, "子番機を銃で倒せる")},
	])
	# 盾型：正面は装甲。光刃で盾を崩す
	steps.append_array([
		{"ticks": 2, "setup": func():
			_arena_start("shield")
			_stand(Vector3(0, 0, 3), Vector3(0, 0, -9))},
		{"ticks": 150, "input": {}},
		{"ticks": 1, "shot": "11_shield", "input": {}},
		{"ticks": 2, "setup": func():
			var s = main.game.enemies[1]
			for e in main.game.enemies:
				if e != s:
					e.alive = false
					main.game.phys.remove(e.body)
			s.become_alert()
			_stand(s.pos + Vector3(0, 0, 1.6), s.pos)},
		{"ticks": 360, "input_fn": func(i):
			for e in main.game.enemies:
				if e.state == "stunned":
					_seen["shield_broken"] = true
			return {"sword": i % 10 < 2}},
		{"ticks": 1, "shot": "11b_shield_blade", "check": func(): return _check(_seen.has("shield_broken"), "光刃で盾型の盾を崩せる")},
	])
	# 浮遊型：旋回して撃つ。銃で撃ち落とす
	steps.append_array([
		{"ticks": 2, "setup": func():
			_arena_start("floater")
			_stand(Vector3(0, 0, 2), Vector3(0, 0, -9))},
		{"ticks": 200, "input": {}},
		{"ticks": 1, "shot": "12_floater", "input": {}},
		{"ticks": 480, "input_fn": func(i): return {"lock_on": true, "fire": i % 8 < 4}},
		{"ticks": 1, "check": func(): return _check(_alive_count("floater") < 3, "浮遊型を銃で撃ち落とせる")},
	])
	# ボス「閂」：始まり → 回転薙ぎの予兆 → 核の露出 → 叩きつけ → 過熱 → 段階の移り変わり → 撃破
	steps.append_array([
		{"ticks": 2, "setup": func(): _arena_start("kannuki")},
		{"ticks": 150, "input": {}},
		{"ticks": 1, "shot": "13_kannuki_start", "input": {}, "check": func():
			return _check(main.game.boss != null and main.game.boss.state != "idle" and not main.game.boss_status().is_empty(), "閂の戦いが始まり、体力バーが出る")},
		{"ticks": 2, "setup": func():
			main.game.boss.debug_set_phase(1)
			main.game.boss.set_state("spin_windup")},
		{"ticks": 60, "input": {}},
		{"ticks": 1, "shot": "14_kannuki_spin", "input": {}},
		{"ticks": 2, "setup": func():
			var b = main.game.boss
			b.set_state("stuck")
			b.core_open = true},
		{"ticks": 40, "input": {}},
		{"ticks": 1, "shot": "15_kannuki_core", "input": {}},
		{"ticks": 2, "setup": func():
			var b = main.game.boss
			b.debug_set_phase(2)
			b.pos = Vector3(0, 0, 0)
			main.game.phys.set_feet(b.body, Vector3.ZERO)
			b.set_state("slam_windup")},
		{"ticks": 66, "input": {}},
		{"ticks": 1, "shot": "16_kannuki_slam", "input": {}},
		{"ticks": 2, "setup": func():
			var b = main.game.boss
			b.debug_set_phase(3)
			b.set_state("engage")
			b.heat_state = 2
			b.heat_time = 0.0},
		{"ticks": 90, "input": {}},
		{"ticks": 1, "shot": "17_kannuki_overheat", "input": {}},
		# 段階の移り変わり：大きく当てても境で止まり、次の区切りで段階が移る
		{"ticks": 2, "setup": func():
			var b = main.game.boss
			b.debug_set_phase(1)
			b.core_open = true
			main.game.damage_enemy(b, 700.0, main.game.player.pos, {"melee": true, "at": b.axis_center()})
			_check(b.hp >= 1200.0 * 0.66 - 0.5, "ボスの HP は 66% の境で止まる（段階を飛ばさない）")},
		{"ticks": 720, "input": {}},
		{"ticks": 1, "check": func(): return _check(main.game.boss.phase >= 2, "66% を割ると第 2 段階に移る")},
		{"ticks": 2, "setup": func():
			var b = main.game.boss
			b.debug_set_phase(3)
			b.core_open = true
			for i in 60:
				main.game.damage_enemy(b, 50.0, main.game.player.pos, {"melee": true, "at": b.axis_center()})},
		{"ticks": 30, "input": {}},
		{"ticks": 1, "check": func(): return _check(not main.game.boss.alive and main.game.story.flags.get("ch1.boss_defeated", false), "核を狙えば閂を倒せる（ch1.boss_defeated）")},
		{"ticks": 60, "input": {}},
		{"ticks": 1, "shot": "18_kannuki_defeated", "input": {}},
	])
	return steps


## 段階 D（音と UI）の画面の確認：ポーズ（地図）・持ち物・店・工房・顔のアイコンつきの会話・ボス戦の字幕
func _cp2d_steps() -> Array:
	var prep := func(room: String):
		main.arena_kind = ""
		main.args["room"] = room
		main.start_game(null)
		var g: GameSim = main.game
		g.god_mode = true
		for f in ["ch1.chores_started", "ch1.nico_rescued", "ch1.scolded", "ch1.debt_scene", "ch1.got_spark",
				"visited.ch1.training", "visited.ch1.lower", "visited.ch1.mid", "visited.ch1.upper", "visited.ch1.r01", "visited.ch1.r02", "visited.ch1.r03"]:
			g.set_flag(f)
		g.give_cells(340)
		g.give_item("weapon.spark")
		g.give_item("chip.charge")
		g.give_item("frame.vestige")
		g.add_material("scrap", 1)
		g.relics["relic.old_gear"] = true
		g.relics["relic.broken_lens"] = true
		g.guild_points = 20
		g.objective = "遺構の奥へ進み、動力の中継器を探す"
		g.drain_events()
	return [
		{"ticks": 2, "setup": func(): prep.call("ch1.mid")},
		{"ticks": 30, "input": {}},
		{"ticks": 1, "check": func(): return _check(main.audio.current_music == "bgm_town_day", "昼の町では昼の町の曲が鳴る（%s）" % main.audio.current_music)},
		{"ticks": 1, "shot": "01_pause_map", "setup": func():
			main.pause()
			main.menu.show_pause(main, 3),
			"check": func(): return _check(main.menu.is_open() and main.state == "paused", "ポーズ画面が開く"),
			"after": func(): main.resume()},
		{"ticks": 1, "shot": "02_inventory", "setup": func():
			main.pause()
			main.menu.show_pause(main, 2),
			"after": func(): main.resume()},
		{"ticks": 1, "shot": "03_shop", "setup": func(): main.open_economy_ui("shop", "zakka"),
			"after": func(): main.resume()},
		{"ticks": 1, "shot": "04_workshop", "setup": func(): main.open_economy_ui("workshop", "yana", 1),
			"after": func(): main.resume()},
		{"ticks": 1, "check": func(): return _check(not main.menu.is_open() and main.state == "playing", "画面を閉じるとゲームに戻る")},
		{"ticks": 2, "setup": func(): main.game.story.start_dialogue("ch1.debt")},
		{"ticks": 100, "input": {}},
		{"ticks": 1, "shot": "05_dialogue", "input": {}, "check": func():
			return _check(main.hud._dlg_icon.visible and main.hud._dlg_icon.texture != null, "ヤーナの会話に顔のアイコンが出る")},
		{"ticks": 2, "setup": func():
			prep.call("ch1.r19")
			pass},
		{"ticks": 400, "input_fn": func(i): return {"jump": i % 20 < 2 and not main.game.story.dialogue.is_empty()}},
		{"ticks": 2, "setup": func():
			main.game.player.teleport(Vector3(0, 0, 6), PI)
			main.game.cam.yaw = PI
			main.snap_views()},
		{"ticks": 240, "input": {}},
		{"ticks": 2, "setup": func():
			main._lines.clear()
			main._line_time = 0.0
			main.game.emit_event({"type": "bossLine", "who": "閂", "text": "……侵入者……回収屋の印を確認……排除する……"})},
		{"ticks": 40, "input": {}},
		{"ticks": 1, "shot": "06_boss_subtitle", "input": {}, "check": func():
			return _check(main.hud.subtitle_text().contains("排除") and main.audio.current_music == "bgm_boss", "ボス戦の字幕と、ボスの曲（%s）" % main.audio.current_music)},
	]


## UI の部品（Codex の W2-08）の画面の確認（--ui_shots。見本の通しでも走る）：町の HUD・ボス戦の HUD（ロックオン・解析・弱点・
## チャージ・危険の HP・字幕）・会話（顔と選択肢）・ノードの記憶・ポーズ・状態・持ち物・店・工房・ギルド・セーブ・操作の設定・やられた画面
func _ui_steps() -> Array:
	var prep := func(room: String):
		main.arena_kind = ""
		main.args["room"] = room
		main.start_game(null)
		var g: GameSim = main.game
		g.god_mode = true
		for f in ["ch1.chores_started", "ch1.nico_rescued", "ch1.scolded", "ch1.debt_scene", "ch1.got_spark",
				"visited.ch1.training", "visited.ch1.lower", "visited.ch1.mid", "visited.ch1.upper"]:
			g.set_flag(f)
		g.give_cells(1240)
		g.give_item("weapon.spark")
		g.give_item("special.drill")
		g.add_material("scrap", 2)
		g.relics["relic.old_gear"] = true
		g.guild_points = 20
		g.objective = "遺構の奥へ進み、動力の中継器を探す"
		g.drain_events()
	return [
		# 町の HUD：HP・特殊武器・補修パック・主武器・セル・目的・調べるの案内・拾った知らせ
		{"ticks": 2, "setup": func():
			prep.call("sample.hub")
			_stand(Vector3(-6.4, 0, 8), Vector3(-8, 0, 8))},
		{"ticks": 30, "input": {}},
		{"ticks": 1, "setup": func(): main.hud.show_toast("錆鉄 ×1 を手に入れた")},
		{"ticks": 10, "input": {}},
		{"ticks": 1, "shot": "ui_01_hud", "input": {}, "check": func():
			return _check(main.hud._we_row.visible and main.hud._objective_box.visible and main.hud._prompt_box.visible, "HUD：特殊武器のゲージ・目的・調べるの案内が出る")},
		# 番機の警戒の合図（頭上の「！」の部品）
		{"ticks": 2, "setup": func():
			_arena_start("shield")
			_stand(Vector3(0, 0, 3), Vector3(0, 0, -9))},
		{"ticks": 20, "input": {}},
		{"ticks": 2, "setup": func():
			for e in main.game.enemies:
				e.set_state("idle")
				e.become_alert()},
		{"ticks": 1, "shot": "ui_01b_alert", "input": {}, "check": func():
			return _check(main.game.enemies.any(func(e): return e.alerting()), "番機が警戒すると頭上に「！」が出る")},
		# ボス戦：ロックオン（解析中）→ 解析済み・弱点があいている、チャージ 1 段目、危険の HP、字幕
		{"ticks": 2, "setup": func():
			_arena_start("kannuki")
			main.game.give_item("special.drill")
			main.game.give_item("weapon.spark")},
		{"ticks": 150, "input": {}},
		{"ticks": 40, "input": {"lock_on": true}},
		{"ticks": 1, "shot": "ui_02_boss_scan", "input": {"lock_on": true}, "check": func():
			return _check(main.hud._boss_box.visible and main.hud._reticle.visible and not main.hud._reticle.scanned, "ボスの体力の枠と、解析中の照準が出る")},
		{"ticks": 200, "input": {"lock_on": true}},
		{"ticks": 2, "setup": func():
			var g: GameSim = main.game
			g.give_item("chip.charge")
			if not g.charge_type():
				g.toggle_chip("chip.charge")
			var b = g.boss
			b.set_state("stuck")
			b.core_open = true
			g.player.hp = g.player.max_hp * 0.22
			main._lines.clear()
			main._line_time = 0.0
			g.emit_event({"type": "bossLine", "who": "閂", "text": "……侵入者……排除する……"}),
			"input": {"lock_on": true}},
		{"ticks": 44, "input": {"lock_on": true, "fire": true}},
		{"ticks": 1, "shot": "ui_03_boss_weak", "input": {"lock_on": true, "fire": true}, "check": func():
			var h: Hud = main.hud
			h.sync(main.game, main.camera, 0.0)
			return _check(h._reticle.scanned and h._reticle.weak and h._charge.visible and h._charge.stage == 1 and h._hp.lag > h._hp.value, "解析済みで弱点の照準・チャージ 1 段目・HP の減った分が出る")},
		{"ticks": 2, "setup": func():
			main.game.player.hurt_time = 0.0
			main.game.player.gun_charge = 1.3,
			"input": {"lock_on": true, "fire": true}},
		{"ticks": 1, "shot": "ui_03b_charge2", "input": {"lock_on": true, "fire": true}, "check": func():
			main.hud.sync(main.game, main.camera, 0.0)
			return _check(main.hud._charge.stage == 2, "チャージ 2 段目")},
		# 会話：顔の枠・名前の札・選択肢
		{"ticks": 2, "setup": func():
			prep.call("ch1.mid")
			main.game.story.start_dialogue("ch1.debt")},
		{"ticks": 400, "input_fn": func(i):
			var d: Dictionary = main.game.story.dialogue
			return {"jump": i % 20 < 2 and not d.is_empty() and not d.has("choices")}},
		{"ticks": 60, "input": {}},
		{"ticks": 1, "shot": "ui_04_dialogue_choice", "input": {}, "check": func():
			var h: Hud = main.hud
			return _check(h._dlg.visible and h._dlg_choices.visible and h._dlg_icon.visible, "会話の枠に顔と選択肢が出る")},
		{"ticks": 2, "setup": func():
			main.game.story.dialogue = {}
			main.game.story.start_dialogue("ch1.node")},
		{"ticks": 160, "input_fn": func(i): return {"jump": i % 40 < 2 and i < 120}},
		{"ticks": 1, "shot": "ui_05_node_memory", "input": {}, "check": func():
			return _check(main.hud._mem_box.visible, "ノードの記憶の取り込みの枠が出る")},
		{"ticks": 2, "setup": func(): main.game.story.dialogue = {}},
		{"ticks": 2, "setup": func():
			prep.call("ch1.mid")
			main.game.give_item("chip.charge")},
		{"ticks": 20, "input": {}},
		_menu_shot("ui_06_pause", func(): main.menu.show_pause(main, 0), func():
			return _check(main.menu.buttons.size() == 11 and main.menu.buttons[1].icon != null, "ポーズの行に絵（回収屋の印など）が付く")),
		_menu_shot("ui_07_status", func(): main.menu.show_pause(main, 1)),
		_menu_shot("ui_08_items", func(): main.menu.show_pause(main, 2)),
		{"ticks": 1, "shot": "ui_09_shop", "setup": func(): main.open_economy_ui("shop", "zakka"), "after": func(): main.resume()},
		{"ticks": 1, "shot": "ui_10_workshop", "setup": func(): main.open_economy_ui("workshop", "yana", 0), "after": func(): main.resume()},
		{"ticks": 1, "shot": "ui_11_guild", "setup": func(): main.open_economy_ui("guild", "main"), "after": func(): main.resume()},
		_menu_shot("ui_12_save", func(): main.menu.show_save(main, true)),
		_menu_shot("ui_13_controls", func(): main.menu.show_controls(func(): main.resume())),
		{"ticks": 1, "shot": "ui_14_retry", "setup": func(): main._open_retry(), "after": func(): main.resume(), "check": func():
			return _check(main.menu.is_open() and main.menu.buttons.size() == 3, "やられた画面：3 つの選択肢")},
		{"ticks": 2, "input": {}},
	]


## ポーズから開くメニューの画面を撮る手順（撮ったあとゲームに戻る）
func _menu_shot(name: String, open: Callable, check := Callable()) -> Dictionary:
	var d := {"ticks": 1, "shot": name, "setup": func():
		main.pause()
		open.call(),
		"after": func(): main.resume()}
	if check.is_valid():
		d["check"] = check
	return d


## ゲームパッドの操作の設定画面（--pad_shots）：ポーズから開く・割り当て待ち・割り当て・入れ替え・初期に戻す
func _pad_steps() -> Array:
	var press := func(i: int):
		var e := InputEventJoypadButton.new()
		e.button_index = i
		e.pressed = true
		main.menu.feed_event(e)
	var open_controls := func():
		main.pause()
		main.menu.show_pause(main, 9)
		main.menu.buttons[9].pressed.emit()
	return [
		{"ticks": 2, "setup": func():
			PadConfig.path = "user://demo_input.cfg"
			PadConfig.reset_all()},
		{"ticks": 1, "shot": "01_controls", "setup": func():
			open_controls.call()
			press.call(7),
			"check": func(): return _check(main.menu.buttons.size() == PadConfig.ACTIONS.size() + 6 and main.menu.pad_info_text().contains("ボタン 7"), "操作の設定の画面が開き、押したボタンの番号が出る"),
			"after": func(): main.resume()},
		{"ticks": 1, "shot": "02_listening", "setup": func():
			open_controls.call()
			main.menu.buttons[0].pressed.emit(),
			"check": func(): return _check(main.menu._listen == "jump", "ジャンプの割り当て待ちになる"),
			"after": func(): main.resume()},
		{"ticks": 1, "shot": "03_assigned", "setup": func():
			open_controls.call()
			main.menu.buttons[0].pressed.emit()
			press.call(3),
			"check": func(): return _check(PadConfig.pad.jump == "b3" and PadConfig.pad.special == "b0", "Y を割り当てると、特殊武器と入れ替わる"),
			"after": func(): main.resume()},
		{"ticks": 1, "shot": "04_ps_preset", "setup": func():
			open_controls.call()
			main.menu.buttons[PadConfig.ACTIONS.size() + 3].pressed.emit(),
			"check": func(): return _check(PadConfig.pad.jump == "b1" and PadConfig.code_short("b1") == "×", "PS 配置にすると × がジャンプ・決定になる"),
			"after": func(): main.resume()},
		{"ticks": 2, "setup": func():
			PadConfig.reset_all()
			DirAccess.remove_absolute("user://demo_input.cfg")
			PadConfig.path = PadConfig.PATH
			PadConfig.load_file()
			PadConfig.apply()},
		{"ticks": 1, "check": func(): return _check(PadConfig.pad.jump == "b0" and main.state == "playing", "初期に戻して、ゲームに戻る")},
	]


func _check(cond: bool, what: String) -> bool:
	print(("✓ " if cond else "✗ ") + what)
	if not cond:
		failures.append(what)
	return cond


## 立ち位置と向きを決める（見る先の方を向く）
func _stand(at: Vector3, look: Vector3) -> void:
	var g: GameSim = main.game
	var yaw := U.dir_to_yaw(look.x - at.x, look.z - at.z)
	g.player.teleport(at, yaw)
	g.cam.yaw = yaw
	main.snap_views()


## 撮影を待っている間は true（ゲームを進めない）
func holding() -> bool:
	return _pending_shot != ""


## 1 刻み分の入力（main の _physics_process から呼ばれる）
func next_input() -> InputFrame:
	if _bot_active:
		return _bot_input()
	if _step >= _steps.size():
		return InputFrame.new()
	var s: Dictionary = _steps[_step]
	if _tick == 0:
		_cur = s
		if s.has("setup"):
			s.setup.call()
		if s.has("check"):
			s.check.call()
		if s.has("shot"):
			_pending_shot = s.shot
		if s.has("done"):
			_finish()
	var d: Dictionary = {}
	if s.has("input"):
		d = s.input
	elif s.has("input_fn"):
		d = s.input_fn.call(_tick)
	_tick += 1
	if _tick >= s.ticks:
		_tick = 0
		_step += 1
	return InputFrame.of(d)


## 通しの自動操作：前の刻みの入力が使われたら、操作役（Ch1Run）を 1 刻み進めて次の入力をもらう
func _bot_input() -> InputFrame:
	if _bot_consumed:
		_bot_consumed = false
		bot_ticks += 1
		if bot_shot_every > 0 and bot_ticks % bot_shot_every == 0 and _pending_shot == "":
			_pending_shot = "auto_%04d" % (bot_ticks / bot_shot_every)
		bot_ticked.emit()
	_bot_consumed = true
	var f := InputFrame.of(_bot_frame)
	_bot_frame = {}
	return f


## --- Ch1Run の運転役の窓口 ---
func tick(f: Dictionary) -> void:
	_bot_frame = f
	await bot_ticked


func shot(shot_name: String) -> void:
	_pending_shot = shot_name
	await bot_shot_done


func milestone(shot_name: String) -> void:
	await shot(shot_name)


func after_warp() -> void:
	main.snap_views()


## 「はじめから」から「第 1 章 クリア」までを、実際のゲームの進行（画面・音・UI つき）の中で自動で遊ぶ
func _run_bot() -> void:
	var t0 := Time.get_ticks_msec()
	var g: GameSim = main.game
	g.god_mode = true
	_bot_active = true
	var run := Ch1Run.new(self, self)
	await run.play_all(g)
	_bot_active = false
	var secs := Time.get_ticks_msec() - t0
	var game_secs: float = g.play_time
	print("通し：ゲーム内 %d 分 %d 秒（%d 刻み）、実時間 %.1f 秒、撮影 %d 枚、フラグ ch1.complete=%s" % [
		int(game_secs / 60.0), int(game_secs) % 60, bot_ticks, secs / 1000.0, shots_taken, str(g.flag("ch1.complete"))])
	_check(g.flag("ch1.complete"), "自動操作が第 1 章をクリアまで遊びきる")
	_finish()


## Ch1Run の確認用（TestHelpers と同じ形）
func expect(cond: bool, msg: String) -> void:
	_check(cond, msg)


func near(a: float, b: float, tol: float, msg: String) -> void:
	_check(absf(a - b) <= tol, "%s（%.3f、期待 %.3f±%.3f）" % [msg, a, b, tol])


func between(v: float, lo: float, hi: float, msg: String) -> void:
	_check(v > lo and v < hi, "%s（%.3f、期待 %.3f〜%.3f）" % [msg, v, lo, hi])


func _process(_dt: float) -> void:
	if not _started:
		_started = true
		main.show_title()
		for i in 10:
			await get_tree().process_frame
		await _shoot("00_title")
		if main.args.has("ch1_full"):
			main.start_game(null)
			for i in 30:
				await get_tree().physics_frame
			_run_bot()
			return
		if not (main.args.has("ch1_shots") or main.args.has("town_shots") or main.args.has("ruins_shots") or main.args.has("ch1b_shots") or main.args.has("pad_shots")):
			main.args["mvp"] = "1"   # 見本の前半は古い試験場（mvp.main）で進める
		main.start_game(null)
		main.game.god_mode = true
		for i in 30:
			await get_tree().physics_frame
		_pending_shot = "01_start"
	# 通しの自動操作：店・工房・ギルドの画面が開いたら、撮ってから閉じる（プレイヤーなら選んで閉じる）
	if _bot_active and main.state == "paused" and main.menu.is_open() and _pending_shot == "" and not _shooting:
		_ui_shots += 1
		_cur = {"after": func(): main.resume()}
		_pending_shot = "ui_%02d" % _ui_shots
	if _pending_shot != "" and not _shooting:
		_shooting = true
		var name := _pending_shot
		await _shoot(name)
		if _cur.has("after"):
			_cur.after.call()
		_pending_shot = ""
		_shooting = false
		bot_shot_done.emit()


func _shoot(name: String) -> void:
	# 画面なし（CI の通しのテスト）では撮影しない
	if DisplayServer.get_name() == "headless":
		await get_tree().process_frame
		return
	RenderingServer.render_loop_enabled = true
	await RenderingServer.frame_post_draw
	await RenderingServer.frame_post_draw
	var img := get_viewport().get_texture().get_image()
	RenderingServer.render_loop_enabled = false
	var path := "%s/%s.png" % [out_dir, name]
	if main.args.has("jpg"):
		# 小さな JPEG（docs/progress_shots 用）
		img.resize(960, 540, Image.INTERPOLATE_BILINEAR)
		path = "%s/%s.jpg" % [out_dir, name]
		img.save_jpg(path, 0.82)
	else:
		img.save_png(path)
	shots_taken += 1
	print("撮影：", path)


func _finish() -> void:
	RenderingServer.render_loop_enabled = true
	print("見本の完了（失敗 %d 件）" % failures.size())
	get_tree().quit(1 if failures.size() > 0 else 0)
