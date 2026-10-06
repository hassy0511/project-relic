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
var _blip_shown := 0
var _blip_id := ""
var _retry_open := false


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
	touch.activated.connect(func():
		menu.touch_mode = true
		_update_ui_scale())
	get_window().size_changed.connect(_update_ui_scale)
	audio = GameAudio.new()
	add_child(audio)
	# ファンファーレなど、ループしない曲が鳴り終わったら部屋の曲へ戻す
	audio.music_finished.connect(func(id: String):
		if game != null and game.music_override == id:
			game.music_override = "")
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
	_update_ui_scale()
	perf = Hud.make_label("", 16)
	perf.position = Vector2(32, 230)
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
	_title_backdrop()
	menu.show_title(has_save(), func(): start_game(null), func(): start_game(read_save()), func(): get_tree().quit())


## タイトルの後ろ：夜明けの空（ui_title.png の空の色）。遊んでいた部屋は隠す（はじめから・つづきからで作り直す）
func _title_backdrop() -> void:
	if views != null and is_instance_valid(views):
		views.visible = false
	if level != null and is_instance_valid(level):
		level.visible = false
	EnvironmentSetup.apply_mood(sun, "title")
	camera.position = Vector3(0, 3, 0)
	camera.rotation_degrees = Vector3(7, 50, 0)


## スマホ（画面に触れて操作する、低い画面）では、画面の部品を大きく描く。
## 文字が 1080 の高さの画面で 26px のとき、画面の高さ 390px で約 16px になるように（spec：360px 高で本文 16px 以上）
func _update_ui_scale() -> void:
	var f := 1.0
	if touch.active:
		var win := get_window()
		var sc := DisplayServer.screen_get_scale() if OS.has_feature("web") else 1.0
		var logical_h := float(win.size.y) / maxf(1.0, sc)
		f = 1080.0 / clampf(logical_h * 1.75, 640.0, 1080.0)
	if not is_equal_approx(get_window().content_scale_factor, f):
		get_window().content_scale_factor = f


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
	_retry_open = false
	# やられたら「やられた」画面で選ぶ（見本・自動確認では自動で再開する）
	game.manual_respawn = demo == null
	audio.play_music(arena_music() if arena_kind != "" else game.music_id(), 0.3)
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
	menu.show_pause(self)


## ポーズ・店などの画面を閉じて、ゲームに戻る
func resume() -> void:
	menu.hide_menu()
	state = "playing"


func toggle_chip() -> void:
	game.toggle_chip("chip.charge")


func to_title() -> void:
	show_title()


## 手動セーブできる状況か（会話・イベント・ボス戦・やられている間は不可）
func can_save() -> bool:
	return game != null and not game.story.blocking() and not game.story.running_event() \
		and game.boss_status().is_empty() and not game.player.dead


func read_slot(path: String):
	if not FileAccess.file_exists(path):
		return null
	return GameSim.parse_save(FileAccess.get_file_as_string(path))


func save_slot(path: String) -> bool:
	var ok := _write_save(path)
	menu.set_note("セーブした" if ok else "セーブできなかった")
	audio.play("save")
	return ok


func load_slot(path: String) -> void:
	var d = read_slot(path)
	if d != null:
		start_game(d)


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
	if game.manual_respawn and game.player.dead and game.player.dead_time >= 1.3 and not _retry_open:
		_open_retry()
		return
	var f: InputFrame = demo.next_input() if demo else input.sample(dt)
	game.step(f)
	_handle_events()
	_update_audio()
	player_view.sync(game.player, game, dt, _aim_dir())
	nagomi_view.sync(game, camera.global_position, dt)
	enemy_view.sync(game.enemies, dt)
	_update_lines(dt)
	props_view.sync(game, dt)
	fx.sync(game, dt)
	camera.sync(game, game.player.pos, dt, fx.shake)


func _process(dt: float) -> void:
	if game != null:
		var dlg: Dictionary = game.story.dialogue
		touch.stick_hint = dlg.is_empty()
	touch.set_shown(state == "playing" and demo == null or (demo != null and args.has("touch") and state == "playing"))
	hud.compact = touch.active
	if game and state == "playing":
		hud.sync(game, camera, dt)
	if perf.visible:
		perf.text = "%d fps　描画 %d 回　三角形 %d" % [
			Engine.get_frames_per_second(),
			RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_DRAW_CALLS_IN_FRAME),
			RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_PRIMITIVES_IN_FRAME)]


## 音楽（部屋・状況から決まる曲へ、なめらかに切り替える）としゃべり音
func _update_audio() -> void:
	audio.play_music(arena_music() if arena_kind != "" else game.music_id())
	var d: Dictionary = game.story.dialogue
	if d.is_empty():
		_blip_shown = 0
		_blip_id = ""
	else:
		var key := "%s:%d" % [d.id, d.index]
		if key != _blip_id:
			_blip_id = key
			_blip_shown = 0
		if int(d.shown) >= _blip_shown + 2:
			_blip_shown = int(d.shown)
			var ch := String(d.text).substr(maxi(0, _blip_shown - 1), 1)
			if ch != "　" and ch != " " and ch != "…" and ch != "。" and ch != "、":
				audio.play("blip")


## 試しの部屋の曲：ボスの部屋だけボスの曲
func arena_music() -> String:
	return "bgm_boss" if arena_kind == "kannuki" else "bgm_trial"


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
				if menu.is_open():
					menu.set_note(e.text)
				else:
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
				pass   # 曲は game.music_id()（music_override）から毎刻み決まる
			"respawned":
				hud.fade_in(0.8)
			"playerHurt":
				hud.flash_damage()
			"bossLine":
				_lines.append([e.who, e.text])
			"bossPhase":
				audio.play("boss_phase")
				hud.show_subtitle("閂", "――第 %d 段階――" % e.phase, 2.2)
			"bossStart":
				audio.play("alert")
			"bossReset":
				_lines.clear()
			"playerDied":
				_retry_open = false


## やられた画面：中継地点から再開・最後のセーブから・タイトルへ
func _open_retry() -> void:
	_retry_open = true
	state = "paused"
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	menu.show_retry(has_save(),
		func():
			game.request_respawn()
			_retry_open = false
			resume(),
		func():
			var sv = read_save()
			if sv != null:
				start_game(sv),
		func(): show_title())


func _write_save(path: String) -> bool:
	var f := FileAccess.open(path, FileAccess.WRITE)
	if f == null:
		return false
	var data := game.to_save()
	data["savedAt"] = Time.get_datetime_string_from_system()
	f.store_string(JSON.stringify(data))
	return true


## 店・工房・ギルドの画面。左に品の一覧（値段・状態）、右に選んでいる品の説明。買う・作る・受けるたびに作り直し、選択位置は保つ
func open_economy_ui(kind: String, id: String, focus := 0) -> void:
	state = "paused"
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	var g := game
	var eco: Dictionary = g.world.economy
	var rows := []
	var title := ""
	var sub := "セル %d" % g.cells
	var again := func(idx: int):
		_flush_events()
		open_economy_ui(kind, id, idx)
	match kind:
		"shop":
			var shop: Dictionary = eco.get("shops", {}).get(id, {})
			title = shop.get("name", "店")
			for s in shop.get("stock", []):
				var idx := rows.size()
				rows.append({"label": g.world.item_name(s.item), "right": "%d セル" % int(s.price), "dim": g.cells < int(s.price), "icon": UiArt.item_icon(String(s.item)),
					"detail": PauseInfo.shop_detail(g, id, s),
					"cb": func():
						Economy.buy(g, id, s.item)
						again.call(idx)})
			if shop.get("buys_relics", false):
				for r in g.relics.keys():
					var idx := rows.size()
					var price := int(g.world.items.get(r, {}).get("sell", 20))
					rows.append({"label": "売る：%s" % g.world.item_name(r), "right": "+%d セル" % price, "icon": UiArt.item_icon(String(r)),
						"detail": "%s\n\n遺物を売る。\n買い取り価格　%d セル" % [g.world.item_name(r), price],
						"cb": func():
							Economy.sell_relic(g, id, r)
							again.call(maxi(0, idx - 1))})
			if rows.is_empty():
				rows.append({"label": "（いま売っている物はない）", "dim": true, "detail": "遺物を持ってくると買い取る。", "cb": func(): pass})
		"workshop":
			var ws: Dictionary = eco.get("workshops", {}).get(id, {})
			title = ws.get("name", "工房")
			for r in ws.get("recipes", []):
				var idx := rows.size()
				var crafted: bool = g.flag("crafted." + r.id) and r.id == "drill"
				var can: bool = Cond.eval(r.get("cond"), g) and not crafted
				var ok := can
				if ok:
					for m in r.get("needs", {}):
						if g.material_count(m) < int(r.needs[m]):
							ok = false
					ok = ok and g.cells >= int(r.get("cost", 0))
				rows.append({"label": ("（開発済み）" if crafted else "") + String(r.name), "right": "%d セル" % int(r.get("cost", 0)), "icon": UiArt.item_icon(String(r.get("gives", {}).get("item", "consumable.repair"))),
					"dim": not ok, "detail": PauseInfo.recipe_detail(g, r),
					"cb": func():
						Economy.craft(g, id, r.id)
						again.call(idx)})
		"guild":
			title = "回収屋ギルド"
			sub = "ギルドポイント %d　／　印：%s　／　セル %d" % [g.guild_points, g.mark, g.cells]
			for r in eco.get("guild", {}).get("requests", []):
				var st: String = g.requests.get(r.id, "")
				var idx := rows.size()
				if st == "done":
					rows.append({"label": "（達成済み）%s" % r.name, "dim": true, "icon": UiArt.tex("icon_map_quest"), "detail": PauseInfo.request_detail(g, r), "cb": func(): pass})
				elif st == "":
					if not Cond.eval(r.get("cond"), g):
						continue
					rows.append({"label": "受ける：%s" % r.name, "right": PauseInfo.reward_text(r), "icon": UiArt.tex("icon_map_quest"), "detail": PauseInfo.request_detail(g, r),
						"cb": func():
							Economy.accept_request(g, r.id)
							again.call(idx)})
				else:
					var done: bool = Cond.eval(r.get("done"), g)
					rows.append({"label": "報告する：%s" % r.name, "right": "報告できる" if done else "進行中", "dim": not done, "icon": UiArt.tex("icon_map_quest"),
						"detail": PauseInfo.request_detail(g, r),
						"cb": func():
							Economy.complete_request(g, r.id)
							again.call(idx)})
			if rows.is_empty():
				rows.append({"label": "（いま受けられる依頼はない）", "dim": true, "detail": "物語を進めると、依頼が増える。", "cb": func(): pass})
	menu.show_trade(title, sub, rows, resume, focus)


## ポーズ中の操作（買う・作る）で出た音とメッセージを、すぐ出す
func _flush_events() -> void:
	_handle_events()


## 戦闘中の掛け合いは操作を止めずに、1 行ずつ上の通知に出す
func _update_lines(dt: float) -> void:
	_line_time -= dt
	if _line_time <= 0.0 and not _lines.is_empty():
		var ln: Array = _lines.pop_front()
		hud.show_subtitle(ln[0], ln[1], 3.2)
		_line_time = 3.2
