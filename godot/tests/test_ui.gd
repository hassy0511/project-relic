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
	for who in ["ハル", "ヤーナ", "バートン"]:
		var t := Hud.face_texture(who, "normal")
		h.expect(t != null and t.get_width() > 100, "%s の顔のアイコンがある" % who)
		h.expect(Hud.face_texture(who, "angry") != Hud.face_texture(who, "normal"), "%s は表情で切り出す位置が変わる" % who)
	h.expect(Hud.face_texture("ニコ", "normal") == null, "絵の無い人は頭文字の丸（null）")


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
	menu.queue_free()
	fm.queue_free()
	h.free_game(g)


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


func test_practice_dummy_for_lock_on() -> void:
	var g := _new_game()
	await h.settle()
	g.load_room("ch1.training", "start")
	await _pump(g, 6)
	g.set_flag("ch1.chores_started")
	for id in ["ch1.tg1", "ch1.tg2", "ch1.tg3"]:
		g.activate_switch(g.switch_by_id(id))
	await _pump(g, 120)
	var dummy = g.enemies.filter(func(e): return e.id == "ch1.practice")
	h.expect(dummy.size() == 1 and dummy[0].passive and dummy[0].invulnerable, "的を撃ち終えると、練習用の番機が出る（動かない・倒せない）")
	var d = dummy[0]
	g.player.teleport(Vector3(8, 0, 6), 0.0)
	g.cam.yaw = 0.0
	await _pump(g, 30)
	for i in 60:
		await h.tree.physics_frame
		g.step(InputFrame.of({"lock_on": true}))
		g.drain_events()
	h.expect(g.lock_on.target == d, "練習用の番機をロックオンできる")
	h.near(d.pos.x, 8.0, 0.2, "練習用の番機は動かない")
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
			"icon_map_current", "icon_map_quest", "icon_map_save_beacon", "icon_map_destination", "icon_item_relic"]:
		names.append(n)
	for n in names:
		if UiArt.tex(n) == null:
			missing.append(n)
	h.expect(missing.is_empty(), "UI の部品の絵がそろっている（足りない：%s）" % str(missing))
	for m in Cond.MARKS:
		h.expect(UiArt.RANK_ICONS.has(m), "回収屋の印「%s」にバッジの絵がある" % m)
	var th := UiArt.theme()
	h.expect(th.get_stylebox("normal", "Button") is StyleBoxTexture and th.get_stylebox("focus", "Button") is StyleBoxTexture, "ボタンの見た目が部品の絵（9 分割）")
	var sb: StyleBoxTexture = UiArt.box("choice")
	h.expect(sb.texture_margin_top * 2 < sb.texture.get_height(), "選択肢の札の角が、縦に伸ばせる余地を残している")
	h.expect(UiArt.item_icon("relic.big_gear") != null and UiArt.item_icon("scrap") == null, "遺物は汎用の遺物の絵、素材は絵なし")


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
	h.expect(hud._hp.fill == UiArt.tex("ui_parts_gauge_hp_fill_full"), "満タンの中身")
	g.player.hp = g.player.max_hp * 0.2
	hud.sync(g, cam, 0.016)
	h.expect(hud._hp.fill == UiArt.tex("ui_parts_gauge_hp_fill_danger") and hud._hp.lag > hud._hp.value, "3 割を切ると危険の中身、減った分は遅れて縮む")
	for i in 120:
		hud.sync(g, cam, 0.05)
	h.near(hud._hp.lag, hud._hp.value, 0.01, "減った分はしばらくすると追いつく")
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
	hud.queue_free()
	cam.queue_free()
	h.free_game(g)
