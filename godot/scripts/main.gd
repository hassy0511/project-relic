extends Node
## ゲーム全体：タイトル → プレイ ⇔ ポーズ。1/60 秒ごとにゲームの中身を進め、見た目・音・UI に反映する。
## 引数：-- --demo=<出力フォルダ>  自動の見本（起動 → 会話 → 戦闘 → 斬撃 → ドリル）を進めて各場面を撮り、終了する
##       -- --haru=a                ハルを以前の試作にする（既定は絵から起こした haru_r。proxy で MVP の仮、b で AI 変換）。F2 で切り替え
##       -- --shade=toon            3 段の塗り分け
##       -- --touch                 スマホの画面の操作を出す（スマホのブラウザでは自動で出る）
##       -- --arena=<型>            試しの部屋（直径 32 m の円形）から始める。型：mini（子番機）| shield（盾型）| floater（浮遊型）|
##                                 kannuki（ボス「閂」と壊れる柱 4 本）| all（3 種）。タイトルを飛ばし、HP 無限にはしない
##                                 （--god を足すと、やられない）。例：tools/godot.sh shot -- --arena=kannuki --god
##       -- --room=<部屋 id>[:<目印>]  その部屋から始める（例：--room=sample.gym  --room=sample.hub:from_gym）。タイトルを飛ばす
##       -- --mvp                  第 1 章ではなく、古い試験場（mvp.main）から始める（開発用）
##       -- --flags=a,b             始めにフラグを立てておく（扉の条件などの確認用）
##       -- --items=a,b             始めにアイテムを持っておく（例：--items=special.drill,key.sample）
## ブラウザ版では URL の引数で同じことができる：…/project-relic/?arena=kannuki&god や ?room=sample.gym（demo 以外）

const SAVE_PATH := "user://save_slot1.json"
const AUTOSAVE_PATH := "user://save_auto.json"
const WORLD_PATH := "res://content/world.json"

var state := "title"
var input: InputSource
var audio: GameAudio
var camera: CameraRig
var hud: Hud
var menu: Menu
var perf: Label
var level: Node3D
var world: World
var game: GameSim = null
var views: Node3D = null
var player_view: PlayerView
var nagomi_view: NagomiView = null
var enemy_view: EnemyView
var props_view: PropsView
var fx: Fx
var sun: DirectionalLight3D
var args := {}
var demo: Demo = null
var haru_path := ""
var touch: TouchControls
var arena_kind := ""
var _lines: Array = []
var _line_time := 0.0


func _ready() -> void:
	for a in OS.get_cmdline_user_args():
		var kv := a.trim_prefix("--").split("=", true, 1)
		args[kv[0]] = kv[1] if kv.size() > 1 else "1"
	# ブラウザ版：URL の ?arena=kannuki&god のような引数も同じに扱う（コマンドラインの引数が渡せないため）
	if OS.has_feature("web"):
		var q = JavaScriptBridge.eval("window.location.search", true)
		if q is String:
			var query: String = q
			for a in query.trim_prefix("?").split("&", false):
				var kv: PackedStringArray = a.uri_decode().split("=", true, 1)
				args[kv[0]] = kv[1] if kv.size() > 1 else "1"
	InputSource.setup_actions()
	input = InputSource.new()
	add_child(input)
	touch = TouchControls.new()
	add_child(touch)
	input.touch = touch
	if args.has("touch") or (DisplayServer.is_touchscreen_available() and OS.has_feature("web")):
		touch.activate()
	touch.activated.connect(func(): menu.touch_mode = true)
	audio = GameAudio.new()
	add_child(audio)
	sun = EnvironmentSetup.build(self)
	arena_kind = args.get("arena", "")
	world = World.load_manifest(WORLD_PATH)
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
	menu.touch_mode = touch.active
	perf = Hud.make_label("", 16)
	perf.position = Vector2(32, 150)
	perf.visible = false
	hud.add_child(perf)
	if args.has("demo"):
		demo = Demo.new(self, args.demo)
		add_child(demo)
	elif arena_kind != "" or args.has("room"):
		start_game(null)
		if args.has("god"):
			game.god_mode = true
	else:
		show_title()


## 今の部屋の地形・仕掛け・敵の見た目を作り直す（始めと、部屋を移ったとき）
func _rebuild_room_views() -> void:
	if level != null and is_instance_valid(level):
		level.queue_free()
	if arena_kind != "":
		level = ArenaView.build(game.geometry)
	else:
		level = RoomView.build(game.world, game.room_id)
	add_child(level)
	_apply_mood()
	if enemy_view != null and is_instance_valid(enemy_view):
		enemy_view.queue_free()
	enemy_view = EnemyView.new()
	views.add_child(enemy_view)
	if props_view != null and is_instance_valid(props_view):
		props_view.queue_free()
	props_view = PropsView.new()
	views.add_child(props_view)
	props_view.build(game)


## 空と光の雰囲気：屋内の部屋は interior、屋外の部屋の mood（dawn など）、停電の夜（フラグ ch1.night）は night
func _apply_mood() -> void:
	var mood := "day"
	if arena_kind == "":
		var r: Dictionary = game.room
		mood = String(r.get("mood", "day"))
		if mood == "outdoor" or mood == "day":
			mood = "night" if game.flag("ch1.night") else "day"
	EnvironmentSetup.apply_mood(sun, mood)


## 試しの部屋に切り替えて始め直す（見本・確認用）
func load_arena(kind: String) -> void:
	arena_kind = kind
	start_game(null)


## 瞬間移動のあと、見た目の補間を切る（前の位置から滑って見えないように）
func snap_views() -> void:
	if views:
		player_view.position = game.player.pos
		player_view.reset_physics_interpolation()
		if nagomi_view:
			nagomi_view.snap(game.player)
		camera.sync(game, game.player.pos, 1.0, 0.0)
		camera.reset_physics_interpolation()


func has_save() -> bool:
	return FileAccess.file_exists(SAVE_PATH) or FileAccess.file_exists(AUTOSAVE_PATH)


## 手動セーブとオートセーブのうち、新しいほう
func read_save():
	var best = null
	for path in [SAVE_PATH, AUTOSAVE_PATH]:
		if not FileAccess.file_exists(path):
			continue
		var d = GameSim.parse_save(FileAccess.get_file_as_string(path))
		if d != null and (best == null or String(d.get("savedAt", "")) > String(best.get("savedAt", ""))):
			best = d
	return best


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
	var init := {"tuning": U.load_json("res://content/tuning.json"), "seed": 12345, "save": save}
	if arena_kind != "":
		# 試しの部屋：1 部屋だけの世界
		init.merge({"geometry": Arena.geometry(16.0), "placement": Arena.placement(arena_kind), "dialogues": world.dialogues, "events": world.events})
	else:
		init["world"] = world
		if args.has("room") and save == null:
			var kv := String(args.room).split(":", true, 1)
			init["start"] = {"room": kv[0], "spawn": kv[1] if kv.size() > 1 else "start"}
		elif args.has("mvp") and save == null:
			init["start"] = {"room": "mvp.main", "spawn": "start"}
	game.setup(init)
	if save == null:
		for f in String(args.get("flags", "")).split(",", false):
			game.set_flag(f)
		for it in String(args.get("items", "")).split(",", false):
			game.items[it] = true
	views = Node3D.new()
	add_child(views)
	player_view = null
	nagomi_view = NagomiView.new()
	views.add_child(nagomi_view)
	_load_haru(_haru_path(args.get("haru", "r")))
	enemy_view = null
	props_view = null
	_rebuild_room_views()
	game.drain_events()
	fx = Fx.new()
	views.add_child(fx)
	menu.hide_menu()
	hud.set_hint("")
	hud.visible = true
	state = "playing"
	audio.play_music("bgm_trial")
	if save != null:
		hud.show_toast("セーブした場所から再開しました")


## ハルのモデル：r = 絵から起こしたもの（既定）、a = 箱の組み合わせの試作、proxy = MVP の仮、b = AI 変換
func _haru_path(key: String) -> String:
	var model: String = {"a": "haru_a", "proxy": "haru_proxy", "b": "haru_b"}.get(key, "haru_r")
	var path := "res://assets/models/%s.glb" % model
	if not ResourceLoader.exists(path):
		path = "res://assets/models/haru_a.glb"
	return path


func _load_haru(path: String) -> void:
	if player_view and is_instance_valid(player_view):
		player_view.queue_free()
	player_view = PlayerView.new()
	views.add_child(player_view)
	views.move_child(player_view, 0)
	player_view.load_model(path, args.get("shade", "soft"))
	haru_path = path
	snap_views()


## F2：ハルの見た目を切り替える（比べて確かめるため）
func toggle_haru() -> void:
	var order := ["res://assets/models/haru_r.glb", "res://assets/models/haru_a.glb"]
	var i := order.find(haru_path)
	var next: String = order[(i + 1) % order.size()]
	if not ResourceLoader.exists(next):
		return
	_load_haru(next)
	hud.show_toast("ハルの見た目：%s" % ("絵から起こしたもの" if next.contains("haru_r") else "以前の試作"))


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
	if state == "playing" and event is InputEventMouseButton and event.pressed and Input.mouse_mode != Input.MOUSE_MODE_CAPTURED and not touch.active:
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
	if event is InputEventKey and event.pressed and event.physical_keycode == KEY_F1:
		perf.visible = not perf.visible
	if event is InputEventKey and event.pressed and event.physical_keycode == KEY_F2 and state == "playing" and demo == null:
		toggle_haru()
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
	nagomi_view.sync(game, camera.global_position, dt)
	enemy_view.sync(game.enemies, dt)
	_update_lines(dt)
	props_view.sync(game, dt)
	fx.sync(game, dt)
	camera.sync(game, game.player.pos, dt, fx.shake)


func _process(dt: float) -> void:
	touch.set_shown(state == "playing" and demo == null or (demo != null and args.has("touch") and state == "playing"))
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
				if _write_save(SAVE_PATH):
					hud.show_toast("セーブしました（HP と武器エネルギーが回復）")
				else:
					hud.show_toast("セーブできませんでした")
			"autosave":
				_write_save(AUTOSAVE_PATH)
			"roomChanged":
				if not e.first:
					_rebuild_room_views()
					snap_views()
					hud.fade_in(0.6)
			"snap":
				snap_views()
			"hint":
				hud.set_hint(e.text)
			"npcRemoved":
				if props_view != null:
					props_view.hide_npc(e.id)
			"flagSet":
				if e.name == "ch1.night":
					_apply_mood()
			"ui":
				open_economy_ui(e.kind, e.id)
			"music":
				if audio.has_method("play_music"):
					audio.play_music(e.id)
			"respawned":
				hud.fade_in(0.8)
			"playerHurt":
				hud.flash_damage()
			"bossLine":
				_lines.append("%s：%s" % [e.who, e.text])
			"bossPhase":
				hud.show_toast("閂が第 %d 段階に入った" % e.phase)
			"bossStart":
				audio.play("alert")
			"bossReset":
				_lines.clear()
			"playerDied":
				hud.show_toast("やられた……中継地点から再開します")


func _write_save(path: String) -> bool:
	var f := FileAccess.open(path, FileAccess.WRITE)
	if f == null:
		return false
	var data := game.to_save()
	data["savedAt"] = Time.get_datetime_string_from_system()
	f.store_string(JSON.stringify(data))
	return true


## 店・工房・ギルドの薄い画面（段階 D で作り込む）
func open_economy_ui(kind: String, id: String) -> void:
	state = "paused"
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	var g := game
	var eco: Dictionary = g.world.economy
	var close := func():
		menu.hide_menu()
		state = "playing"
	var items := []
	var title := ""
	match kind:
		"shop":
			var shop: Dictionary = eco.get("shops", {}).get(id, {})
			title = shop.get("name", "店")
			for s in shop.get("stock", []):
				items.append(["%s　%d セル" % [g.world.item_name(s.item), int(s.price)], func():
					Economy.buy(g, id, s.item)
					open_economy_ui(kind, id)])
			if shop.get("buys_relics", false):
				for r in g.relics.keys():
					items.append(["売る：%s　%d セル" % [g.world.item_name(r), int(g.world.items.get(r, {}).get("sell", 20))], func():
						Economy.sell_relic(g, id, r)
						open_economy_ui(kind, id)])
		"workshop":
			var ws: Dictionary = eco.get("workshops", {}).get(id, {})
			title = ws.get("name", "工房")
			for r in ws.get("recipes", []):
				items.append(["%s　%d セル" % [r.name, int(r.get("cost", 0))], func():
					Economy.craft(g, id, r.id)
					open_economy_ui(kind, id), g.flag("crafted." + r.id)])
		"guild":
			title = "回収屋ギルド"
			for r in eco.get("guild", {}).get("requests", []):
				var st: String = g.requests.get(r.id, "")
				if st == "done":
					continue
				if st == "":
					if not Cond.eval(r.get("cond"), g):
						continue
					items.append(["受ける：%s" % r.name, func():
						Economy.accept_request(g, r.id)
						open_economy_ui(kind, id)])
				else:
					items.append(["報告する：%s" % r.name, func():
						Economy.complete_request(g, r.id)
						open_economy_ui(kind, id)])
	items.append(["閉じる", close])
	menu.show_list(title, "セル %d" % g.cells, items)


## 戦闘中の掛け合いは操作を止めずに、1 行ずつ上の通知に出す
func _update_lines(dt: float) -> void:
	_line_time -= dt
	if _line_time <= 0.0 and not _lines.is_empty():
		hud.show_toast(_lines.pop_front())
		_line_time = 2.8
