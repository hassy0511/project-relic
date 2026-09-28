extends Node
## ゲーム全体：タイトル → プレイ ⇔ ポーズ。1/60 秒ごとにゲームの中身を進め、見た目・音・UI に反映する。
## 引数：-- --demo=<出力フォルダ>  自動の見本（起動 → 会話 → 戦闘 → 斬撃 → ドリル）を進めて各場面を撮り、終了する
##       -- --haru=proxy            ハルを MVP の仮のモデルにする（b で AI 変換のハル）
##       -- --shade=toon            3 段の塗り分け

const SAVE_PATH := "user://save_slot1.json"
const AREA_ID := "area.mvp"

var state := "title"
var input: InputSource
var audio: GameAudio
var camera: CameraRig
var hud: Hud
var menu: Menu
var perf: Label
var level: Dictionary
var game: GameSim = null
var views: Node3D = null
var player_view: PlayerView
var enemy_view: EnemyView
var props_view: PropsView
var fx: Fx
var sun: DirectionalLight3D
var args := {}
var demo: Demo = null


func _ready() -> void:
	for a in OS.get_cmdline_user_args():
		var kv := a.trim_prefix("--").split("=", true, 1)
		args[kv[0]] = kv[1] if kv.size() > 1 else "1"
	InputSource.setup_actions()
	input = InputSource.new()
	add_child(input)
	audio = GameAudio.new()
	add_child(audio)
	sun = EnvironmentSetup.build(self)
	level = LevelLoader.load_level("res://assets/levels/mvp_greybox.glb")
	add_child(level.node)
	camera = CameraRig.new()
	add_child(camera)
	camera.current = true
	camera.position = Vector3(0, 6, -10)
	camera.look_at(Vector3.ZERO)
	hud = Hud.new()
	add_child(hud)
	hud.visible = false
	menu = Menu.new()
	add_child(menu)
	menu.moved.connect(func(): audio.play("ui_move"))
	menu.chosen.connect(func(): audio.play("ui_ok"))
	perf = Hud.make_label("", 16)
	perf.position = Vector2(32, 150)
	perf.visible = false
	hud.add_child(perf)
	if args.has("demo"):
		demo = Demo.new(self, args.demo)
		add_child(demo)
	else:
		show_title()


## 瞬間移動のあと、見た目の補間を切る（前の位置から滑って見えないように）
func snap_views() -> void:
	if views:
		player_view.position = game.player.pos
		player_view.reset_physics_interpolation()
		camera.sync(game, game.player.pos, 1.0, 0.0)
		camera.reset_physics_interpolation()


func _placement() -> Dictionary:
	return U.load_json("res://content/areas/mvp.json")


func has_save() -> bool:
	return FileAccess.file_exists(SAVE_PATH)


func read_save():
	if not has_save():
		return null
	return GameSim.parse_save(FileAccess.get_file_as_string(SAVE_PATH))


func show_title() -> void:
	state = "title"
	hud.visible = false
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	menu.show_title(has_save(), func(): start_game(null), func(): start_game(read_save()), func(): get_tree().quit())


func start_game(save) -> void:
	if views:
		views.queue_free()
	if game:
		game.queue_free()
	game = GameSim.new()
	add_child(game)
	game.setup({
		"geometry": level.geometry,
		"placement": _placement(),
		"tuning": U.load_json("res://content/tuning.json"),
		"dialogues": U.load_json("res://content/dialogue/mvp.json"),
		"events": U.load_json("res://content/events/mvp.json"),
		"seed": 12345,
		"save": save,
	})
	views = Node3D.new()
	add_child(views)
	player_view = PlayerView.new()
	views.add_child(player_view)
	var model := "haru_a"
	match args.get("haru", ""):
		"proxy":
			model = "haru_proxy"
		"b":
			model = "haru_b"
	var path := "res://assets/models/%s.glb" % model
	if not ResourceLoader.exists(path):
		path = "res://assets/models/haru_a.glb"
	player_view.load_model(path, args.get("shade", "soft"))
	enemy_view = EnemyView.new()
	views.add_child(enemy_view)
	props_view = PropsView.new()
	views.add_child(props_view)
	props_view.build(game)
	fx = Fx.new()
	views.add_child(fx)
	menu.hide_menu()
	hud.visible = true
	state = "playing"
	audio.play_music("bgm_trial")
	if save != null:
		hud.show_toast("セーブした場所から再開しました")


func pause() -> void:
	if game == null:
		return
	state = "paused"
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	audio.play("ui_ok")
	menu.show_pause(game,
		func():
			menu.hide_menu()
			state = "playing",
		func(): game.toggle_chip("chip.charge"),
		func():
			var s = read_save()
			if s != null:
				start_game(s),
		func(): show_title())


func _unhandled_input(event: InputEvent) -> void:
	if state == "playing" and event is InputEventMouseButton and event.pressed and Input.mouse_mode != Input.MOUSE_MODE_CAPTURED:
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
	if event is InputEventKey and event.pressed and event.physical_keycode == KEY_F1:
		perf.visible = not perf.visible
	if state == "paused" and event.is_action_pressed("pause"):
		menu.hide_menu()
		state = "playing"
		get_viewport().set_input_as_handled()


func _physics_process(dt: float) -> void:
	if state != "playing" or game == null:
		return
	if demo != null and (demo.holding() or not demo._started):
		return
	if input.take_one_shot("pause") and demo == null:
		pause()
		return
	hud.device = input.last_device
	var f: InputFrame = demo.next_input() if demo else input.sample(dt)
	game.step(f)
	_handle_events()
	player_view.sync(game.player, game, dt, _aim_dir())
	enemy_view.sync(game.enemies, dt)
	props_view.sync(game, dt)
	fx.sync(game, dt)
	camera.sync(game, game.player.pos, dt, fx.shake)


func _process(dt: float) -> void:
	if game and state == "playing":
		hud.sync(game, camera, dt)
	if perf.visible:
		perf.text = "%d fps　描画 %d 回　三角形 %d" % [
			Engine.get_frames_per_second(),
			RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_DRAW_CALLS_IN_FRAME),
			RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_PRIMITIVES_IN_FRAME)]


func _aim_dir() -> Vector3:
	var t = game.lock_on.target
	if t != null:
		return (t.center() - game.player.chest()).normalized()
	return camera.forward_dir()


func _handle_events() -> void:
	for e in game.drain_events():
		fx.handle(e)
		match e.type:
			"sfx":
				audio.play(e.id, e.get("at"))
			"message":
				hud.show_toast(e.text)
			"saved":
				var f := FileAccess.open(SAVE_PATH, FileAccess.WRITE)
				if f:
					var data := game.to_save(AREA_ID)
					data["savedAt"] = Time.get_datetime_string_from_system()
					f.store_string(JSON.stringify(data))
					hud.show_toast("セーブしました（HP と武器エネルギーが回復）")
				else:
					hud.show_toast("セーブできませんでした")
			"playerHurt":
				hud.flash_damage()
			"playerDied":
				hud.show_toast("やられた……中継地点から再開します")
