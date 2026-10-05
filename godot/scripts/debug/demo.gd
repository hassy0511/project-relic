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


func _init(m, dir: String) -> void:
	main = m
	out_dir = dir


func _ready() -> void:
	DirAccess.make_dir_recursive_absolute(out_dir)
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
	if main.args.has("arena_only") or main.args.has("world_only") or main.args.has("ch1_shots") or main.args.has("ruins_shots") or main.args.has("ch1b_shots"):
		_steps.clear()
	if main.args.has("ch1_shots"):
		_steps.append_array(_ch1_steps())
	elif main.args.has("ruins_shots"):
		_steps.append_array(_ruins_survey_steps())
	elif main.args.has("ch1b_shots"):
		_steps.append_array(_ch1b_steps())
	else:
		if not main.args.has("world_only"):
			_steps.append_array(_arena_steps())
		_steps.append_array(_world_steps())
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
	return [
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


func _process(_dt: float) -> void:
	if not _started:
		_started = true
		main.show_title()
		for i in 10:
			await get_tree().process_frame
		await _shoot("00_title")
		if not (main.args.has("ch1_shots") or main.args.has("ruins_shots") or main.args.has("ch1b_shots")):
			main.args["mvp"] = "1"   # 見本の前半は古い試験場（mvp.main）で進める
		main.start_game(null)
		main.game.god_mode = true
		for i in 30:
			await get_tree().physics_frame
		_pending_shot = "01_start"
	if _pending_shot != "" and not _shooting:
		_shooting = true
		var name := _pending_shot
		await _shoot(name)
		_pending_shot = ""
		_shooting = false


func _shoot(name: String) -> void:
	# 画面なし（CI の通しのテスト）では撮影しない
	if DisplayServer.get_name() == "headless":
		await get_tree().process_frame
		return
	await RenderingServer.frame_post_draw
	await RenderingServer.frame_post_draw
	var img := get_viewport().get_texture().get_image()
	var path := "%s/%s.png" % [out_dir, name]
	if main.args.has("jpg"):
		# 小さな JPEG（docs/progress_shots 用）
		img.resize(960, 540, Image.INTERPOLATE_BILINEAR)
		path = "%s/%s.jpg" % [out_dir, name]
		img.save_jpg(path, 0.82)
	else:
		img.save_png(path)
	print("撮影：", path)


func _finish() -> void:
	print("見本の完了（失敗 %d 件）" % failures.size())
	get_tree().quit(1 if failures.size() > 0 else 0)
