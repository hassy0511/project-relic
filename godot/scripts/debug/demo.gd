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
	if main.args.has("arena_only"):
		_steps.clear()
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
	img.save_png(path)
	print("撮影：", path)


func _finish() -> void:
	print("見本の完了（失敗 %d 件）" % failures.size())
	get_tree().quit(1 if failures.size() > 0 else 0)
