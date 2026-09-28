class_name Demo
extends Node
## 自動の見本：決まった入力でゲームを進め、場面ごとに画面を撮って終了する。
## 画面の確認と、起動から一通り遊べることの確認（通しのテスト）に使う。
## 起動 → ヤーナと会話 → 奥の部屋で戦闘 → 光刃 → ひび割れた壁をドリルで壊す
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


func _init(m, dir: String) -> void:
	main = m
	out_dir = dir


func _ready() -> void:
	DirAccess.make_dir_recursive_absolute(out_dir)
	_steps = [
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
		{"ticks": 1, "done": true},
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
