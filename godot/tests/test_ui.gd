extends RefCounted
## 段階 D（音と UI）のテスト：曲の選び方・音の ID がそろっていること・曲の切り替え・ポーズ／店／工房／ギルドの画面・顔のアイコン・字幕・やられた画面の再開待ち・練習用の的

var h: TestHelpers


func _init(helpers: TestHelpers) -> void:
	h = helpers


func _new_game() -> GameSim:
	var g := GameSim.new()
	var vp := SubViewport.new()
	vp.own_world_3d = true
	vp.render_target_update_mode = SubViewport.UPDATE_DISABLED
	vp.size = Vector2i(2, 2)
	h.tree.root.add_child(vp)
	vp.add_child(g)
	g.setup({"world": World.load_manifest("res://content/world.json"), "tuning": TestHelpers.default_tuning(), "seed": 1})
	g.god_mode = true
	return g


func _pump(g: GameSim, ticks: int, input := {}) -> void:
	for i in ticks:
		await h.tree.physics_frame
		var f := input
		if g.story.blocking():
			f = {"jump": (i % 6) < 3}
		g.step(InputFrame.of(f))
		g.drain_events()


## content と scripts で使う音の ID（効果音・曲）が、すべて assets/audio にある
func test_all_sound_ids_exist() -> void:
	var ids := {}
	var re := RegEx.new()
	re.compile("\"(?:sfx|music|id)\"\\s*:\\s*\"([a-z_0-9]+)\"")
	var re_play := RegEx.new()
	re_play.compile("play(?:_music)?\\(\"([a-z_0-9]+)\"")
	var re_event := RegEx.new()
	re_event.compile("\"type\": \"sfx\", \"id\": \"([a-z_0-9]+)\"")
	var files := []
	for dir in ["res://scripts/sim", "res://scripts/sim/enemies", "res://scripts", "res://content/events", "res://scripts/ui"]:
		for f in DirAccess.get_files_at(dir):
			if f.ends_with(".gd") or f.ends_with(".json"):
				files.append(dir + "/" + f)
	for path in files:
		var text := FileAccess.get_file_as_string(path)
		for m in re_event.search_all(text):
			ids[m.get_string(1)] = path
		for m in re_play.search_all(text):
			ids[m.get_string(1)] = path
		if path.ends_with(".json"):
			var d = JSON.parse_string(text)
			_collect_steps(d, ids, path)
	for id in ["bgm_town_day", "bgm_town_night", "bgm_ruins", "bgm_boss", "bgm_end", "door", "locked", "switch", "lift", "beacon", "blip", "boss_phase", "rumble", "wall_break", "chest", "pickup", "ui_move", "ui_ok", "buy", "complete"]:
		ids[id] = "必須"
	print("音の ID ", ids.size(), " 件を確認")
	var missing := []
	for id in ids:
		if not ResourceLoader.exists("res://assets/audio/%s.ogg" % id):
			missing.append("%s（%s）" % [id, ids[id]])
	h.expect(missing.is_empty(), "使っている音の ID がすべて assets/audio にある（足りない：%s）" % str(missing))


func _collect_steps(node, ids: Dictionary, path: String) -> void:
	if node is Dictionary:
		for k in ["sfx", "music"]:
			if node.has(k) and node[k] is String and not (node[k] in ["none", "auto"]):
				ids[node[k]] = path
		for v in node.values():
			_collect_steps(v, ids, path)
	elif node is Array:
		for v in node:
			_collect_steps(v, ids, path)


func test_music_selection() -> void:
	var g := _new_game()
	await h.settle()
	h.expect(g.music_id() == "bgm_town_day", "最初の町（オープニング）は昼の町の曲（%s）" % g.music_id())
	g.set_flag("ch1.night")
	h.expect(g.music_id() == "bgm_town_night", "停電の夜は夜の曲")
	g.set_flag("ch1.night", false)
	g.load_room("ch1.r02", "from_r01")
	await _pump(g, 6)
	h.expect(g.music_id() == "bgm_ruins", "遺構は遺構の曲（%s）" % g.music_id())
	g.load_room("ch1.r19", "from_r18")
	await _pump(g, 6)
	h.expect(g.music_id() == "bgm_ruins", "ボスが動き出す前は遺構の曲（%s）" % g.music_id())
	g.player.teleport(Vector3(0, 0, 6), PI)
	await _pump(g, 400)
	h.expect(not g.boss_status().is_empty() and g.music_id() == "bgm_boss", "ボス戦が始まるとボスの曲（%s）" % g.music_id())
	g.music_override = "none"
	h.expect(g.music_id() == "", "music の none で無音")
	g.music_override = "bgm_end"
	h.expect(g.music_id() == "bgm_end", "music の指定は部屋・ボスより優先")
	g.load_room("ch1.r20", "from_r19")
	await _pump(g, 6)
	h.expect(g.music_override == "", "部屋を移ると music の指定は解ける")
	h.free_game(g)


func test_music_crossfade() -> void:
	var a := GameAudio.new()
	h.tree.root.add_child(a)
	a.fade_time = 0.2
	a.play_music("bgm_town_day")
	h.expect(a.current_music == "bgm_town_day" and a._active != null and a._active.playing, "曲を鳴らせる")
	var first := a._active
	await h.tree.create_timer(0.3).timeout
	h.expect(first.volume_db > -10.0, "上がりきると聞こえる大きさ（%.1f dB）" % first.volume_db)
	a.play_music("bgm_town_day")
	h.expect(a._active == first, "同じ曲を続けて頼んでも切り替えない")
	a.play_music("bgm_ruins")
	h.expect(a._active != first and a._active.playing and first.playing, "切り替え中は 2 つ同時に鳴る（クロスフェード）")
	await h.tree.create_timer(0.4).timeout
	h.expect(not first.playing and a.current_music == "bgm_ruins", "切り替えが終わると前の曲は止まる")
	a.play_music("")
	await h.tree.create_timer(0.4).timeout
	h.expect(a.current_music == "" and not a._music.playing and not a._music_b.playing, "空の ID で止まる")
	a.queue_free()


func test_face_icons() -> void:
	var was := Hud.haru_framed
	Hud.haru_framed = true
	for who in Hud.FACE_ID:
		var t := Hud.face_texture(who, "normal")
		h.expect(t != null and t.get_width() >= 256, "%s の顔のアイコンがある" % who)
	for who in ["ハル", "ヤーナ", "バートン", "ニコ", "トルーデ"]:
		h.expect(Hud.face_texture(who, "angry") != Hud.face_texture(who, "normal"), "%s は表情で絵が変わる" % who)
	# 読み替えの先の絵がある（無いと黙って normal になるため）
	for id in Hud.FACE_ALIAS:
		for face in Hud.FACE_ALIAS[id]:
			var to: String = Hud.FACE_ALIAS[id][face]
			h.expect(ResourceLoader.exists("res://assets/ui/faces/%s_%s.png" % [id, to]), "%s の %s の読み替え先（%s）の絵がある" % [id, face, to])
	# 第 1 章の台詞の表情は、絵のある人ならどれも絵になる
	var missing := []
	for path in ["res://content/dialogue/ch1_town.json", "res://content/dialogue/ch1_ruins.json"]:
		for line in _dialogue_lines(JSON.parse_string(FileAccess.get_file_as_string(path))):
			if Hud.FACE_ID.has(line.who) and Hud.face_texture(line.who, line.get("face", "normal")) == null:
				missing.append("%s:%s" % [line.who, line.get("face", "normal")])
	h.expect(missing.is_empty(), "第 1 章の台詞の顔がどれも出る（%s）" % ", ".join(missing))
	# ハルは、フレームと適合する前は板と肩ひもの無い顔
	var framed := Hud.face_texture("ハル", "smirk")
	Hud.haru_framed = false
	var bare := Hud.face_texture("ハル", "smirk")
	h.expect(bare != null and bare != framed and bare.resource_path.contains("haru_nf_smirk"), "フレームの前のハルは別の顔の組（%s）" % (bare.resource_path if bare else "null"))
	Hud.haru_framed = was
	h.expect(Hud.face_texture("老人ゲン", "normal") == null, "絵の無い人は頭文字の丸（null）")


## 会話の JSON から台詞の行（who と text のある辞書）を全部集める
static func _dialogue_lines(x) -> Array:
	var out := []
	if x is Dictionary:
		if x.has("who") and x.has("text"):
			out.append(x)
		for v in x.values():
			out.append_array(_dialogue_lines(v))
	elif x is Array:
		for v in x:
			out.append_array(_dialogue_lines(v))
	return out


func test_pause_info_texts() -> void:
	var g := _new_game()
	await h.settle()
	g.load_room("ch1.mid", "start")
	await _pump(g, 6)
	g.give_cells(300)
	g.add_material("scrap", 2)
	g.give_relic("relic.old_gear")
	g.give_item("weapon.spark")
	g.guild_points = 20
	var st := PauseInfo.status_text(g)
	h.expect(st.contains("HP") and st.contains("セル　300") and st.contains("ギルドポイント　20") and st.contains("見習い"), "ステータスに HP・セル・ギルドポイント・印が出る")
	var it := PauseInfo.items_text(g)
	h.expect(it.contains("錆鉄 ×2") and it.contains("古い歯車") and it.contains("スパーク"), "持ち物に素材・遺物・武器が出る（%s）" % it.replace("\n", "/"))
	var mp := PauseInfo.map_text(g)
	h.expect(mp.contains("◆") and mp.contains("入った部屋"), "地図に今いる部屋の印が出る")
	h.expect(PauseInfo.help_text(false).contains("ジャンプ") and PauseInfo.help_text(true).contains("タッチ") == false and PauseInfo.help_text(true).contains("画面"), "操作の説明（キーボード／タッチ）")
	h.expect(PauseInfo.requests_text(g).contains("依頼"), "依頼の欄（無いときの案内）")
	h.free_game(g)


class FakeMain:
	extends Node
	const SAVE_PATH := "user://test_slot.json"
	const AUTOSAVE_PATH := "user://test_auto.json"
	var game: GameSim
	var log: Array = []

	func resume() -> void:
		log.append("resume")

	func toggle_chip() -> void:
		log.append("chip")

	func to_title() -> void:
		log.append("title")

	func can_save() -> bool:
		return true

	func read_slot(_p: String):
		return null

	func save_slot(_p: String) -> bool:
		log.append("save")
		return true

	func load_slot(_p: String) -> void:
		log.append("load")


func test_menu_screens() -> void:
	var g := _new_game()
	await h.settle()
	g.load_room("ch1.mid", "start")
	await _pump(g, 6)
	var menu := Menu.new()
	h.tree.root.add_child(menu)
	var fm := FakeMain.new()
	fm.game = g
	h.tree.root.add_child(fm)
	menu.show_pause(fm)
	await h.tree.process_frame
	h.expect(menu.is_open() and menu.buttons.size() == 11, "ポーズ画面に 11 個の項目（%d）" % menu.buttons.size())
	menu.buttons[2].grab_focus()
	await h.tree.process_frame
	h.expect(menu._detail.text.contains("持ち物") == false and menu._detail.text != "", "持ち物を選ぶと右に中身が出る")
	menu.buttons[0].pressed.emit()
	h.expect(fm.log == ["resume"], "「ゲームに戻る」で再開")
	menu.buttons[6].pressed.emit()
	await h.tree.process_frame
	h.expect(menu.buttons.size() == 3, "セーブ画面：スロット 1・オートセーブ・戻る（%d）" % menu.buttons.size())
	menu.buttons[0].pressed.emit()
	h.expect(fm.log.has("save"), "スロット 1 に保存できる")
	await h.tree.process_frame
	# 店
	menu.show_trade("雑貨屋", "セル 300", [
		{"label": "補修パック", "right": "150 セル", "detail": "説明", "cb": func(): fm.log.append("buy")},
		{"label": "錆鉄", "right": "30 セル", "dim": true, "detail": "説明 2", "cb": func(): fm.log.append("buy2")},
	], func(): fm.log.append("closed"))
	await h.tree.process_frame
	h.expect(menu.buttons.size() == 3 and menu.buttons[1].modulate.a < 1.0, "店の画面：品 2 つ＋閉じる。買えない品は薄い")
	menu.buttons[1].pressed.emit()
	h.expect(fm.log.has("buy2"), "薄い品も押せる（理由は通知に出る）")
	menu.buttons[2].pressed.emit()
	h.expect(fm.log.has("closed"), "閉じるで閉じる")
	menu.set_note("テスト")
	menu.show_retry(false, func(): fm.log.append("retry"), func(): pass, func(): pass)
	await h.tree.process_frame
	h.expect(menu.is_open(), "やられた画面が開く")
	# タイトル（r2）：背景とロゴが絵。選択肢は右下（左下は絵のハル）。「つづきから」はセーブが無いと押せない
	menu.show_title(false, func(): fm.log.append("new"), func(): pass, func(): pass)
	await h.tree.process_frame
	await h.tree.process_frame
	var texs := []
	for c in menu._root.get_children():
		if c is TextureRect:
			texs.append(c.texture)
	h.expect(texs.has(UiArt.tex("ui_title_r2")) and (texs.has(UiArt.tex("ui_title_logo")) or texs.has(UiArt.tex("ui_title_logo_nosub"))), "タイトルの背景とロゴが絵")
	h.expect(menu.buttons.size() >= 3 and menu.buttons[1].disabled and menu.buttons[0].has_focus(), "タイトルの選択肢：最初の行を選んでいて、セーブが無いと「つづきから」は押せない")
	h.expect(menu.buttons[0].get_global_rect().position.x > menu._view().x * 0.45, "タイトルの選択肢は右側（左下の絵のハルを隠さない）")
	menu.buttons[0].pressed.emit()
	h.expect(fm.log.has("new"), "「はじめから」を押せる")
	menu.queue_free()
	fm.queue_free()
	h.free_game(g)


## タップ（画面に触れると届く左クリック：device が DEVICE_ID_EMULATION）を、画面（SubViewport）に押して離す
func _tap(vp: SubViewport, pos: Vector2, dev := InputEvent.DEVICE_ID_EMULATION) -> void:
	for pressed in [true, false]:
		var e := InputEventMouseButton.new()
		e.button_index = MOUSE_BUTTON_LEFT
		e.pressed = pressed
		e.position = pos
		e.global_position = pos
		e.device = dev
		e.button_mask = MOUSE_BUTTON_MASK_LEFT if pressed else 0
		vp.push_input(e)
	await h.tree.process_frame


## スマホのメニュー（844×390 の画面と同じ UI の大きさ）：行の高さは実寸 48px 以上。選んでいない行のタップは選ぶだけ（右に説明）、
## 選んでいる行をもう一度タップで決定。見出しの「戻る」「閉じる」で 1 つ前へ。一覧は指でずらせる（押しは取り消し）。
## マウス（パソコン）のクリックは今までどおり 1 回で決定
func test_menu_touch() -> void:
	var g := _new_game()
	await h.settle()
	g.load_room("ch1.mid", "start")
	await _pump(g, 6)
	var vp := SubViewport.new()
	vp.size = Vector2i(1477, 682)
	h.tree.root.add_child(vp)
	var menu := Menu.new()
	menu.touch_mode = true
	vp.add_child(menu)
	var fm := FakeMain.new()
	fm.game = g
	h.tree.root.add_child(fm)
	menu.show_pause(fm)
	await h.tree.process_frame
	await h.tree.process_frame
	var px := 390.0 / 682.0
	h.expect(menu.buttons[0].has_focus() and menu.buttons[0].size.y * px >= 48.0, "ポーズ：最初の行を選んでいて、行の高さが実寸 %.1fpx（48px 以上）" % (menu.buttons[0].size.y * px))
	h.expect(menu.back_button != null and menu.back_button.size.y * px >= 48.0 and menu.back_button.get_global_rect().position.x > vp.size.x * 0.6, "見出しの右に「閉じる」（実寸 48px 以上）")
	# 「持ち物」：1 回目のタップで選ぶ（右に中身）。決定の働きは無い行
	await _tap(vp, menu.buttons[2].get_global_rect().get_center())
	h.expect(menu.buttons[2].has_focus() and menu._detail.text == PauseInfo.items_text(g), "選んでいない行をタップすると選び、右に中身が出る")
	# 「セーブ」：1 回目は選ぶだけ、2 回目で開く（一覧の下の行は指でずらして出す。ここではフォーカスで見える所へ）
	menu.buttons[6].grab_focus()
	await h.tree.process_frame
	menu.buttons[5].grab_focus()
	await h.tree.process_frame
	await _tap(vp, menu.buttons[6].get_global_rect().get_center())
	h.expect(menu.buttons.size() == 11 and menu.buttons[6].has_focus(), "選んでいない「セーブ」の 1 回目のタップは選ぶだけ")
	await _tap(vp, menu.buttons[6].get_global_rect().get_center())
	await h.tree.process_frame
	h.expect(menu.buttons.size() == 3, "選んでいる「セーブ」をもう一度タップすると開く（%d）" % menu.buttons.size())
	# セーブ画面の「戻る」→ ポーズ、ポーズの「閉じる」→ ゲームに戻る
	await h.tree.process_frame
	h.expect(menu.back_button != null, "セーブ画面にも「戻る」")
	await _tap(vp, menu.back_button.get_global_rect().get_center())
	await h.tree.process_frame
	h.expect(menu.buttons.size() == 11, "「戻る」のタップでポーズ画面へ戻る")
	await h.tree.process_frame
	await _tap(vp, menu.back_button.get_global_rect().get_center())
	h.expect(fm.log.has("resume"), "ポーズの「閉じる」のタップでゲームに戻る")
	# 店：選んでいない品の 1 回目のタップでは買わない、2 回目で買う。「閉じる」で閉じる
	fm.log.clear()
	menu.show_trade("雑貨屋", "セル 300", [
		{"label": "補修パック", "right": "150 セル", "detail": "説明 1", "cb": func(): fm.log.append("buy")},
		{"label": "錆鉄", "right": "30 セル", "detail": "説明 2", "cb": func(): fm.log.append("buy2")},
	], func(): fm.log.append("closed"))
	await h.tree.process_frame
	await h.tree.process_frame
	await _tap(vp, menu.buttons[1].get_global_rect().get_center())
	h.expect(fm.log.is_empty() and menu._detail.text == "説明 2", "店：選んでいない品のタップは選ぶだけ（説明が出る）")
	await _tap(vp, menu.buttons[1].get_global_rect().get_center())
	h.expect(fm.log == ["buy2"], "店：選んでいる品をもう一度タップで買う（%s）" % str(fm.log))
	await _tap(vp, menu.back_button.get_global_rect().get_center())
	h.expect(fm.log.has("closed"), "店：見出しの「閉じる」で閉じる")
	# 指でずらすと一覧が動き、押した行は決定されない（ブラウザのスマホと同じく、画面に触れられる端末として）
	fm.log.clear()
	var rows := []
	for i in 14:
		rows.append({"label": "品 %d" % i, "detail": "説明", "cb": func(): fm.log.append("row%d" % i)})
	menu.show_trade("店", "", rows, func(): fm.log.append("closed"))
	await h.tree.process_frame
	await h.tree.process_frame
	var scroll := menu.buttons[0].get_parent().get_parent() as ScrollContainer
	var was := Input.is_emulating_touch_from_mouse()
	Input.set_emulate_touch_from_mouse(true)
	var from := menu.buttons[1].get_global_rect().get_center()
	var press := InputEventMouseButton.new()
	press.button_index = MOUSE_BUTTON_LEFT
	press.pressed = true
	press.position = from
	press.device = InputEvent.DEVICE_ID_EMULATION
	press.button_mask = MOUSE_BUTTON_MASK_LEFT
	vp.push_input(press)
	for k in 12:
		var m := InputEventMouseMotion.new()
		m.position = from - Vector2(0, 20 * (k + 1))
		m.relative = Vector2(0, -20)
		m.button_mask = MOUSE_BUTTON_MASK_LEFT
		m.device = InputEvent.DEVICE_ID_EMULATION
		vp.push_input(m)
		await h.tree.physics_frame
	var rel := press.duplicate() as InputEventMouseButton
	rel.pressed = false
	rel.button_mask = 0
	rel.position = from - Vector2(0, 240)
	vp.push_input(rel)
	for k in 10:
		await h.tree.physics_frame
	Input.set_emulate_touch_from_mouse(was)
	h.expect(scroll.scroll_vertical > 100 and fm.log.is_empty(), "指でずらすと一覧が動き（%d）、行は決定されない（%s）" % [scroll.scroll_vertical, str(fm.log)])
	# マウス（パソコン）：選んでいない行のクリックも 1 回で決定（今までどおり）
	menu.touch_mode = false
	fm.log.clear()
	menu.show_trade("店", "", [
		{"label": "補修パック", "detail": "説明 1", "cb": func(): fm.log.append("buy")},
		{"label": "錆鉄", "detail": "説明 2", "cb": func(): fm.log.append("buy2")},
	], func(): fm.log.append("closed"))
	await h.tree.process_frame
	await h.tree.process_frame
	h.expect(menu.back_button == null and menu.buttons[0].size.y < Hud.TOUCH_ROW, "パソコン：見出しの「戻る」は無く、行の高さも前のまま")
	await _tap(vp, menu.buttons[1].get_global_rect().get_center(), 0)
	h.expect(fm.log == ["buy2"], "パソコン：マウスのクリックは 1 回で決定（%s）" % str(fm.log))
	menu.queue_free()
	fm.queue_free()
	vp.queue_free()
	h.free_game(g)


## スマホのタイトル：選択肢の行は指で押せる高さ（844×390 では実寸 48px 以上）で、右上の操作の説明に重ならない（667×375 でも）。
## 1 回のタップで決定
func test_title_touch() -> void:
	for sz in [Vector2i(1477, 682), Vector2i(1167, 656)]:
		var vp := SubViewport.new()
		vp.size = sz
		h.tree.root.add_child(vp)
		var menu := Menu.new()
		menu.touch_mode = true
		vp.add_child(menu)
		var log := []
		menu.show_title(true, func(): log.append("new"), func(): log.append("cont"), func(): pass)
		for i in 3:
			await h.tree.process_frame
		var help: Control = null
		for c in menu._root.get_children():
			if c is PanelContainer:
				help = c
		var top := INF
		for b in menu.buttons:
			top = minf(top, b.get_global_rect().position.y)
		h.expect(help != null and top > help.get_global_rect().end.y, "%s：タイトルの選択肢が右上の説明に重ならない（行の上 %.0f、説明の下 %.0f）" % [sz, top, help.get_global_rect().end.y])
		h.expect(menu.buttons[0].size.y >= 64.0, "%s：タイトルの行の高さ %.0f" % [sz, menu.buttons[0].size.y])
		if sz.x == 1477:
			h.expect(menu.buttons[0].size.y * 390.0 / 682.0 >= 48.0, "844×390：タイトルの行が実寸 48px 以上")
		await _tap(vp, menu.buttons[1].get_global_rect().get_center())
		h.expect(log == ["cont"], "%s：タイトルの選択肢は 1 回のタップで決定（%s）" % [sz, str(log)])
		menu.queue_free()
		vp.queue_free()


func test_shop_and_workshop_texts() -> void:
	var g := _new_game()
	await h.settle()
	var shop: Dictionary = g.world.economy.shops.zakka
	var d := PauseInfo.shop_detail(g, "zakka", shop.stock[0])
	h.expect(d.contains("150 セル") and d.contains("足りない"), "店：値段と、足りないことが出る（%s）" % d.replace("\n", "/"))
	g.give_cells(200)
	h.expect(PauseInfo.shop_detail(g, "zakka", shop.stock[0]).contains("買える"), "セルが足りると「買える」")
	var rec: Dictionary = g.world.economy.workshops.yana.recipes[1]
	var rd := PauseInfo.recipe_detail(g, rec)
	h.expect(rd.contains("錆鉄 ×2") and rd.contains("持っている 0") and rd.contains("×"), "工房：必要な素材と持っている数、足りない印")
	g.add_material("scrap", 2)
	g.add_material("wire", 1)
	h.expect(not PauseInfo.recipe_detail(g, rec).contains("　×"), "素材がそろうと × が消える")
	var req: Dictionary = g.world.economy.guild.requests[0]
	h.expect(PauseInfo.request_detail(g, req).contains("200 セル") and PauseInfo.request_detail(g, req).contains("まだ受けていない"), "ギルド：報酬と状態")
	h.free_game(g)


func test_manual_respawn_waits_for_retry() -> void:
	var g := _new_game()
	await h.settle()
	g.god_mode = false
	g.manual_respawn = true
	g.load_room("ch1.lower", "start")
	await _pump(g, 6)
	g.player.hp = 0.0
	g.player.dead = true
	await _pump(g, 200)
	h.expect(g.player.dead, "再開を選ぶまで、やられたまま待つ")
	g.request_respawn()
	await _pump(g, 10)
	h.expect(not g.player.dead and g.player.hp > 0.0, "再開を選ぶと復帰する")
	h.free_game(g)


## 訓練場（適合の前）：的を撃ち終えても練習用の番機は出ず、ロックオンはまだ使えない（ロックオンはナゴミの力。封印室で覚える）
func test_training_has_no_lock_on_before_fitting() -> void:
	var g := _new_game()
	await h.settle()
	g.load_room("ch1.training", "start")
	await _pump(g, 6)
	g.set_flag("ch1.chores_started")
	for id in ["ch1.tg1", "ch1.tg2", "ch1.tg3"]:
		g.activate_switch(g.switch_by_id(id))
	await _pump(g, 120)
	h.expect(g.flag("ch1.t_shoot"), "的を 3 つ撃つと案内が進む")
	h.expect(g.enemies.filter(func(e): return e.id == "ch1.practice").is_empty(), "練習用の番機は出ない")
	g.spawn_enemy_spec({"type": "sentry", "pos": [8, 0, 15], "passive": true, "invulnerable": true})
	g.player.teleport(Vector3(8, 0, 6), 0.0)
	g.cam.yaw = 0.0
	for i in 30:
		await h.tree.physics_frame
		g.step(InputFrame.of({"lock_on": true}))
		g.drain_events()
	h.expect(g.lock_on.target == null, "適合の前はロックオンできない")
	h.free_game(g)


## UI の部品（Codex の W2-08）：使っている絵がすべて assets/ui にあり、ボタン・パネルが 9 分割の絵になっている
func test_ui_art_parts() -> void:
	var missing := []
	var names := []
	for part in UiArt.SLICE:
		names.append("ui_parts_panel_" + part)
	for k in UiArt.GAUGE:
		names.append(UiArt.GAUGE[k].frame)
	for n in UiArt.ITEM_ICONS.values() + UiArt.RANK_ICONS.values():
		names.append(n)
	for sym in TouchControls.SYMBOLS.values():
		names.append("ui_parts_touch_symbol_" + sym)
	for n in ["ui_parts_gauge_hp_fill_full", "ui_parts_gauge_hp_fill_damaged", "ui_parts_gauge_hp_fill_danger",
			"ui_parts_gauge_energy_fill", "ui_parts_gauge_boss_fill", "ui_parts_gauge_boss_divider",
			"ui_parts_gauge_charge_stage1", "ui_parts_gauge_charge_stage2", "ui_parts_lockon_normal",
			"ui_parts_lockon_analyzing", "ui_parts_lockon_weakpoint", "ui_parts_lockon_alert", "ui_parts_face_frame",
			"ui_parts_face_frame_wait", "ui_parts_cursor", "ui_parts_advance", "ui_parts_touch_joystick_base",
			"ui_parts_touch_joystick_knob", "ui_parts_touch_button_normal", "ui_parts_touch_button_pressed",
			"ui_parts_touch_button_lock_on", "icon_spark_rapid", "icon_spark_charge", "icon_blade",
			"icon_map_current", "icon_map_quest", "icon_map_save_beacon", "icon_map_destination", "icon_item_relic",
			# r2（2026-10-17）
			"ui_parts_gauge_hp_fill_full_r2", "ui_parts_gauge_hp_fill_damaged_r2", "ui_parts_gauge_hp_fill_danger_r2",
			"ui_parts_gauge_charge_track", "ui_parts_gauge_charge_fill_stage1", "ui_parts_gauge_charge_fill_stage2",
			"ui_parts_lockon_analyzing_track", "ui_parts_lockon_analyzing_fill", "ui_title_r2", "ui_title_logo", "ui_title_logo_nosub"]:
		names.append(n)
	for n in names:
		if UiArt.tex(n) == null:
			missing.append(n)
	h.expect(missing.is_empty(), "UI の部品の絵がそろっている（足りない：%s）" % str(missing))
	for m in Cond.MARKS:
		h.expect(UiArt.RANK_ICONS.has(m), "回収屋の印「%s」にバッジの絵がある" % m)
	var th := UiArt.theme()
	h.expect(th.get_stylebox("normal", "Button") is StyleBoxTexture and th.get_stylebox("focus", "Button") is StyleBoxTexture, "ボタンの見た目が部品の絵（9 分割）")
	var sb: StyleBoxTexture = UiArt.box("choice_r2")
	h.expect(sb.texture_margin_top * 2 + 30 <= sb.texture.get_height(), "選択肢の札（r2）の角が、縦に伸ばせる余地を半分以上残している")
	h.expect((th.get_stylebox("focus", "Button") as StyleBoxTexture).texture == UiArt.tex("ui_parts_panel_button_focus_r2")
		and (th.get_stylebox("pressed", "Button") as StyleBoxTexture).texture == UiArt.tex("ui_parts_panel_button_pressed"),
		"選んでいる行は琥珀の縁の札（r2）、押した行は煉瓦色の札")
	h.expect(UiArt.item_icon("relic.big_gear") != null and UiArt.item_icon("scrap") == null, "遺物は汎用の遺物の絵、素材は絵なし")
	# メニューの行：長い名前は「…」で終わる。押している間はフォーカスの札を外して、押した札（煉瓦色）を見せる
	# （Godot はフォーカスの札を状態の札の上に重ねて描くため）。右に値段のある行の自前の札も、離すと元に戻る
	var m := Menu.new()
	var row: Button = m._row_button("補修パックを作る（錆鉄 ×2・導線 ×1）", 64, 28)
	h.expect(row.text_overrun_behavior == TextServer.OVERRUN_TRIM_ELLIPSIS, "入りきらない行の名前は「…」で終わる")
	row.button_down.emit()
	var shows_pressed := row.get_theme_stylebox("focus") is StyleBoxEmpty
	row.button_up.emit()
	h.expect(shows_pressed and not row.has_theme_stylebox_override("focus"), "押している間だけ押した札が見え、離すと選んでいる札に戻る")
	m._reserve_right(row, 120.0)
	var own := row.get_theme_stylebox("focus")
	row.button_down.emit()
	row.button_up.emit()
	h.expect(row.get_theme_stylebox("focus") == own, "右に値段のある行も、離すと自前の札に戻る")
	row.free()
	m.free()


## HUD：HP の危険の色・減った分、ボスの区切り、会話の選択肢の札
func test_hud_states() -> void:
	var g := _new_game()
	await h.settle()
	g.load_room("ch1.mid", "start")
	await _pump(g, 6)
	var hud := Hud.new()
	h.tree.root.add_child(hud)
	var cam := Camera3D.new()
	h.tree.root.add_child(cam)
	await h.tree.process_frame
	hud.sync(g, cam, 0.016)
	h.expect(hud._hp.fill == UiArt.tex("ui_parts_gauge_hp_fill_full_r2") and hud._hp.lag_fill == UiArt.tex("ui_parts_gauge_hp_fill_damaged_r2"), "満タンの中身（r2）、減った分は白磁色の中身")
	g.player.hp = g.player.max_hp * 0.6
	hud.sync(g, cam, 0.016)
	h.expect(hud._hp.fill == UiArt.tex("ui_parts_gauge_hp_fill_full_r2") and hud._hp.lag > hud._hp.value, "3 割より上で減ると、通常の中身のまま、減った分が遅れて縮む")
	g.player.hp = g.player.max_hp * 0.2
	hud.sync(g, cam, 0.016)
	h.expect(hud._hp.fill == UiArt.tex("ui_parts_gauge_hp_fill_danger_r2") and hud._hp.lag > hud._hp.value, "3 割を切ると危険の中身（r2）、減った分は遅れて縮む")
	var lit := []
	for i in 12:
		hud.sync(g, cam, 0.06)
		lit.append(hud._hp.fill_modulate.v)
	h.expect(lit.max() > 0.95 and lit.min() < 0.6, "危険の中身は点滅する（明るさ %.2f〜%.2f）" % [lit.min(), lit.max()])
	for i in 120:
		hud.sync(g, cam, 0.05)
	h.near(hud._hp.lag, hud._hp.value, 0.01, "減った分はしばらくすると追いつく")
	# チャージ（r2）：1 段目までは 1 段目の輪が一周、1 段目から 2 段目までは 2 段目の輪が一周、溜まりきると琥珀の輪
	var cfg: Dictionary = g.tuning.gun
	for c in [[0.5, 0, 0.5], [1.5, 1, 0.5], [2.2, 2, -1.0]]:
		g.player.gun_charge = float(cfg.chargeLv1Time) * c[0] if c[0] < 1.0 else float(cfg.chargeLv1Time) + (float(cfg.chargeLv2Time) - float(cfg.chargeLv1Time)) * (c[0] - 1.0)
		hud.sync(g, cam, 0.016)
		h.expect(hud._charge.visible and hud._charge.stage == c[1] and (c[2] < 0.0 or absf(hud._charge.progress - c[2]) < 0.01),
			"主武器のチャージ %.2f 秒：%d 段目、段の中の進み %.2f" % [g.player.gun_charge, hud._charge.stage, hud._charge.progress])
	g.player.gun_charge = 0.0
	# 「HP」の文字は中身に重ならない（危険の色の文字が赤い中身に溶けない）
	h.expect(hud._hp_label.position.x + hud._hp_label.get_minimum_size().x < hud._hp.fill_rect().position.x * Hud.GAUGE_SCALE,
		"「HP」の文字の右から中身が始まる")
	# スマホの配置：補助の文字は 360px の高さで 14px 以上（spec）。360px の高さでの UI の縮尺は main._update_ui_scale で 360/640
	hud.compact = true
	hud.sync(g, cam, 0.016)
	var k := 360.0 / 640.0
	for l in [hud._hp_label, hud._hp_text, hud._objective, hud._boss_phase, hud._sub_who, hud._prompt_key]:
		h.expect(l.get_theme_font_size("font_size") * k >= 14.0, "スマホの補助の文字が 14px 以上（%s：%d）" % [l.text, l.get_theme_font_size("font_size")])
	h.expect(hud._reticle.text_size * k >= 14.0 and hud._reticle.scan_size * k >= 14.0, "スマホの照準の説明の文字が 14px 以上")
	h.expect(hud._hp_label.position.x + hud._hp_label.get_minimum_size().x < hud._hp.fill_rect().position.x * Hud.GAUGE_SCALE,
		"スマホでも「HP」の文字の右から中身が始まる")
	hud.compact = false
	hud.sync(g, cam, 0.016)
	g.story.start_dialogue("ch1.debt")
	for i in 1200:
		var d: Dictionary = g.story.dialogue
		if d.is_empty() or (d.has("choices") and d.shown >= String(d.text).length()):
			break
		await h.tree.physics_frame
		g.step(InputFrame.of({"jump": i % 6 < 3}))
		g.drain_events()
	hud.sync(g, cam, 0.016)
	h.expect(hud._dlg.visible and hud._dlg_choices.visible and hud._dlg_choice_rows.size() >= 2, "選択肢の札が出る")
	var p0: PanelContainer = hud._dlg_choice_rows[0][0]
	var p1: PanelContainer = hud._dlg_choice_rows[1][0]
	var sel := int(g.story.dialogue.sel)
	var on_style := (p0 if sel == 0 else p1).get_theme_stylebox("panel")
	var off_style := (p1 if sel == 0 else p0).get_theme_stylebox("panel")
	hud.sync(g, cam, 0.016)
	h.expect(on_style != off_style and (p0 if sel == 0 else p1).get_theme_stylebox("panel") == on_style, "選んでいる札は別の見た目で、毎フレーム作り直さない")
	hud.queue_free()
	cam.queue_free()
	h.free_game(g)


## ロックオンの照準：捉えた敵に弾が届かない（ロックオンは弾の射程より遠くまで捉える）ときは、照準を薄くして「射程外」と出す（LockOn.in_reach）
func test_reticle_out_of_reach() -> void:
	for z in [8.0, 24.0]:
		var g := h.make_game({
			"markers": {"e1": Vector3(0, 0, z)},
			"placement": {"enemies": [{"type": "sentry", "at": "e1", "passive": true}]},
		})
		await h.settle()
		g.god_mode = true
		await h.run(g, 3, {})
		await h.run(g, 2, {"lock_on": true})
		var hud := Hud.new()
		h.tree.root.add_child(hud)
		var cam := Camera3D.new()
		h.tree.root.add_child(cam)
		cam.global_position = Vector3(0, 2, -4)
		cam.look_at(Vector3(0, 1, z))
		await h.tree.process_frame
		hud.sync(g, cam, 0.016)
		h.expect(hud._reticle.visible, "%.0fm 先の敵：照準が出る" % z)
		h.expect(hud._reticle.get("far") == (z > 20.0), "%.0fm 先の敵：%s" % [z, "射程外と出る" if z > 20.0 else "射程外とは出ない"])
		hud.queue_free()
		cam.queue_free()
		h.free_game(g)


func test_frame_parts_toggle() -> void:
	# 外装フレームの段：haru_r は胴・腕・脚の群が別の物体。set_frame_parts で付いている群だけ見せる
	var v := PlayerView.new()
	h.tree.root.add_child(v)
	v.load_model("res://assets/models/haru_r.glb")
	h.expect(v.frame_nodes.size() == 3, "haru_r に Frame_core・Frame_arm・Frame_legs がある")
	h.expect(v.model.find_child("Haru", true, false) != null, "作業着の体 Haru は残る")
	var all_on := true
	for k in v.frame_nodes:
		all_on = all_on and (v.frame_nodes[k] as Node3D).visible
	h.expect(all_on, "既定はフレームを全部見せる")
	v.set_frame_parts(true, false, false)
	h.expect(v.frame_nodes["core"].visible and not v.frame_nodes["arm"].visible and not v.frame_nodes["legs"].visible,
		"胴だけ見せる")
	v.set_frame_parts(false, false, false)
	h.expect(not v.frame_nodes["core"].visible, "全部隠せる")
	v.set_frame_parts(true, true, true)
	h.expect(v.frame_nodes["legs"].visible and v.frame_nodes["arm"].visible, "全部戻せる")
	# 毎フレームの更新（被弾の点滅の処理）が、隠した部品を見せてしまわない
	var g := h.make_game({})
	await h.settle()
	v.set_frame_parts(true, false, false)
	for i in 3:
		v.sync(g.player, g, 1.0 / 60.0, Vector3.FORWARD)
	h.expect(v.frame_nodes["core"].visible and not v.frame_nodes["arm"].visible and not v.frame_nodes["legs"].visible,
		"毎フレームの更新のあとも、隠した部品は隠れたまま")
	h.free_game(g)
	v.free()
	# 群の無いモデル（仮のモデル）では何もしない
	var p := PlayerView.new()
	h.tree.root.add_child(p)
	p.load_model("res://assets/models/haru_proxy.glb")
	p.set_frame_parts(false, true, false)
	h.expect(p.frame_nodes.is_empty(), "群の無いモデルでは何もしない")
	p.free()
