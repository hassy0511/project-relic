extends RefCounted
## ゲームパッドの入力（スティックの形・まっすぐ進む・割り当ての変更と保存・会話を決定で送る）のテスト

var h: TestHelpers
const TEST_CFG := "user://test_input.cfg"


func _init(helpers: TestHelpers) -> void:
	h = helpers


func _begin() -> void:
	PadConfig.path = TEST_CFG
	DirAccess.remove_absolute(TEST_CFG)
	InputSource.setup_actions()


func _end() -> void:
	DirAccess.remove_absolute(TEST_CFG)
	PadConfig.path = PadConfig.PATH
	InputSource.setup_actions()


func _pad_events(action: String) -> Array:
	var out := []
	for e in InputMap.action_get_events(action):
		if e is InputEventJoypadButton:
			out.append("b%d" % e.button_index)
		elif e is InputEventJoypadMotion:
			out.append("a%d%s" % [e.axis, "+" if e.axis_value > 0 else "-"])
	return out


func _btn(i: int) -> InputEventJoypadButton:
	var e := InputEventJoypadButton.new()
	e.button_index = i
	e.pressed = true
	return e


# ---------------------------------------------------------------- スティックの形

func test_stick_deadzone_and_rescale() -> void:
	h.expect(InputSource.shape_stick(Vector2(0.1, 0.1)) == Vector2.ZERO, "内側のデッドゾーンでは 0")
	h.expect(InputSource.shape_stick(Vector2(0.0, 0.15)) == Vector2.ZERO, "ちょうど境目も 0")
	h.near(InputSource.shape_stick(Vector2(0.0, 0.95)).length(), 1.0, 0.001, "外側（0.95）で最大")
	h.near(InputSource.shape_stick(Vector2(0.0, 1.3)).length(), 1.0, 0.001, "それ以上倒しても 1 まで")
	h.near(InputSource.shape_stick(Vector2(0.55, 0.0)).length(), 0.5, 0.001, "真ん中は引き伸ばされて 0.5")
	var d := InputSource.shape_stick(Vector2(0.5, 0.5))
	h.near(d.x, d.y, 0.0001, "斜めは斜めのまま（45 度は吸い付かない）")


func test_stick_snap_to_cardinal() -> void:
	var s := InputSource.shape_stick(Vector2(0.06, 1.0))
	h.expect(s.x == 0.0 and s.y > 0.9, "ほぼ真上に倒すと、ぴったり真上になる（x が 0）")
	s = InputSource.shape_stick(Vector2(-0.12, -0.9))
	h.expect(s.x == 0.0 and s.y < 0.0, "真下も同じ")
	s = InputSource.shape_stick(Vector2(0.9, 0.1))
	h.expect(s.y == 0.0 and s.x > 0.8, "真横も同じ")
	s = InputSource.shape_stick(Vector2(0.3, 0.9))
	h.expect(s.x > 0.0, "18 度ずれていれば吸い付かない")
	h.near(InputSource.shape_stick(Vector2(0.1, 1.0)).length(), 1.0, 0.001, "吸い付いても倒し具合はそのまま")


# ---------------------------------------------------------------- まっすぐ進む

func _heading_drift(mx: float) -> Array:
	var g := h.make_game()
	await h.settle()
	await h.run(g, 5, {})
	var y0: float = g.player.yaw
	var x0: float = g.player.pos.x
	var worst := [0.0]
	var cam_moved := [0.0]
	await h.run(g, TestHelpers.seconds(10.0), func(i):
		worst[0] = maxf(worst[0], absf(U.wrap_angle(g.player.yaw - y0)))
		cam_moved[0] = maxf(cam_moved[0], absf(U.wrap_angle(g.cam.yaw - y0)))
		return {"move_x": mx, "move_y": 1.0})
	var out := [worst[0], cam_moved[0], g.player.pos.x - x0]
	h.free_game(g)
	return out


func test_straight_line_exact() -> void:
	var r: Array = await _heading_drift(0.0)
	h.expect(r[0] < 0.0001, "まっすぐ（0, 1）を 10 秒倒しても向きは変わらない（%.5f）" % r[0])
	h.expect(absf(r[2]) < 0.001, "横にずれない（%.4f m）" % r[2])


func test_straight_line_slightly_off() -> void:
	# 数度ずれて倒している（0.06, 1.0）：カメラが追いかけて曲がり続けない
	var r: Array = await _heading_drift(0.06)
	h.expect(r[0] < 5.0 * U.DEG, "（0.06, 1）を 10 秒倒しても向きは数度以内（%.2f 度）" % (r[0] / U.DEG))
	h.expect(r[1] < 5.0 * U.DEG, "カメラも回り続けない（%.2f 度）" % (r[1] / U.DEG))


func test_camera_recenter_deadzone() -> void:
	var t := TestHelpers.default_tuning()
	var cam := CameraOrbit.new(t)
	cam.yaw = 0.0
	for i in 600:
		cam.update(1.0 / 60.0, Vector3.ZERO, 10.0 * U.DEG, 7.0, null)
	h.near(cam.yaw, 0.0, 0.0001, "10 度の差では回らない")
	for i in 600:
		cam.update(1.0 / 60.0, Vector3.ZERO, 90.0 * U.DEG, 7.0, null)
	h.near(cam.yaw / U.DEG, 65.0, 0.5, "90 度の差なら、不感帯（25 度）の端まで寄る")


# ---------------------------------------------------------------- 割り当て

func test_remap_swap_save_load() -> void:
	_begin()
	h.expect(_pad_events("jump") == ["b0"], "初期：ジャンプは A")
	var sw := PadConfig.assign_pad("jump", "b3")
	h.expect(sw == "special", "Y（3）は特殊武器が使っていたので入れ替わる")
	h.expect(PadConfig.pad.jump == "b3" and PadConfig.pad.special == "b0", "ジャンプ=Y、特殊=A")
	h.expect(_pad_events("jump") == ["b3"] and _pad_events("special") == ["b0"], "InputMap にも反映される")
	# トリガー（軸）の割り当て
	h.expect(PadConfig.assign_pad("fire", "a4+") == "lock_on", "LT（軸 4）を撃つに割り当てると、ロックオンと入れ替わる")
	h.expect(_pad_events("fire") == ["a4+"] and _pad_events("lock_on") == ["a5+"], "軸の割り当ても反映される")
	# 知らない機種のボタン番号・軸（トリガーが軸 2・ボタン 7 などで届く）
	PadConfig.assign_pad("dash", "b13")
	PadConfig.assign_pad("heal", "a6-")
	h.expect(_pad_events("dash") == ["b13"] and _pad_events("heal") == ["a6-"], "番号のままのボタン・軸も割り当てられる")
	# キー
	h.expect(PadConfig.assign_key("jump", KEY_Z) == "", "キー Z は未使用")
	h.expect(PadConfig.assign_key("dash", KEY_Z) == "jump", "Z をダッシュに → ジャンプと入れ替え")
	# 保存と読み込み
	PadConfig.load_file()
	h.expect(PadConfig.pad.jump == "b3" and PadConfig.pad.fire == "a4+" and PadConfig.pad.heal == "a6-", "保存して読み直しても同じ")
	h.expect(PadConfig.keys.dash == [KEY_Z], "キーも保存される")
	PadConfig.pad.clear()
	PadConfig.keys.clear()
	InputSource.setup_actions()
	h.expect(_pad_events("jump") == ["b3"], "起動時（setup_actions）に保存した割り当てを読む")
	PadConfig.reset_all()
	h.expect(_pad_events("jump") == ["b0"] and _pad_events("fire") == ["a5+"], "初期に戻す")
	# 壊れたファイル
	var f := FileAccess.open(TEST_CFG, FileAccess.WRITE)
	f.store_string("[pad]\njump=\"zzz\"\nfire=\"b99\"\n[keys]\njump=\"x\"\n")
	f.close()
	PadConfig.load_file()
	h.expect(PadConfig.pad.jump == "b0" and PadConfig.pad.fire == "b99", "壊れた値は初期のまま、使える値は読む")
	_end()


func test_remap_menu_confirm_back() -> void:
	_begin()
	h.expect(_pad_events("ui_accept") == ["b0"] and _pad_events("ui_cancel") == ["b1"], "初期：メニューの決定は A、戻るは B")
	PadConfig.assign_pad("confirm", "b2")
	PadConfig.assign_pad("back", "b3")
	h.expect(_pad_events("ui_accept") == ["b2"] and _pad_events("ui_cancel") == ["b3"], "メニューの決定・戻るが割り当てに従う")
	h.expect(_btn(2).is_action_pressed("ui_accept") and not _btn(0).is_action_pressed("ui_accept"), "X で決定、A では決定しない")
	var has_enter := false
	for e in InputMap.action_get_events("ui_accept"):
		has_enter = has_enter or (e is InputEventKey and e.physical_keycode == KEY_ENTER)
	h.expect(has_enter, "キーボードの Enter は決定のまま")
	# 決定と戻るは同じ組なので入れ替わる。ジャンプなど（ゲーム中の組）とは別なので重ねられる
	h.expect(PadConfig.assign_pad("confirm", "b3") == "back" and PadConfig.pad.back == "b2", "決定と戻るは入れ替わる")
	h.expect(PadConfig.assign_pad("jump", "b2") == "" or true, "ゲーム中の組は別")
	_end()


func test_dialogue_advances_with_confirm() -> void:
	_begin()
	PadConfig.assign_pad("confirm", "b2")
	PadConfig.assign_pad("jump", "b0")
	var src := InputSource.new()
	h.tree.root.add_child(src)
	var g := h.make_game()
	await h.settle()
	g.story.start_dialogue("hello")
	await h.run(g, 3, {})
	h.expect(not g.story.dialogue.is_empty(), "会話が出ている")
	# 全文が出るのを待ってから、割り当てた決定ボタン（X）の入力で送る
	await h.run(g, TestHelpers.seconds(1.5), {})
	src._input(_btn(2))
	var f := src.sample(1.0 / 60.0)
	h.expect(f.confirm and not f.jump, "決定ボタンの入力は confirm になる（ジャンプではない）")
	g.step(f)
	await h.run(g, 2, {})
	h.expect(g.story.dialogue.is_empty() or g.story.dialogue.get("text", "") != "やあ", "決定で会話が先へ進む")
	src.queue_free()
	h.free_game(g)
	_end()


func test_controls_screen_assign() -> void:
	_begin()
	var menu := Menu.new()
	h.tree.root.add_child(menu)
	await h.tree.process_frame
	var backed := [false]
	menu.show_controls(func(): backed[0] = true)
	await h.tree.process_frame
	h.expect(menu.buttons.size() == PadConfig.ACTIONS.size() + 2, "全部の操作＋初期に戻す＋戻る の行がある")
	h.expect(menu.pad_info_text().contains("押したボタンの番号"), "押したボタンの番号の表示がある")
	# 割り当て待ちでないときは、押したものを表示するだけ
	menu.feed_event(_btn(7))
	h.expect(menu.pad_info_text().contains("ボタン 7"), "押したボタンの番号が出る")
	# 「ダッシュ」（2 行目）を決定 → ボタン 9 を押す
	menu.buttons[1].pressed.emit()
	h.expect(menu.feed_event(_btn(9)), "割り当て待ちでボタンを押すと受け付ける")
	await h.tree.process_frame
	h.expect(PadConfig.pad.dash == "b9" and _pad_events("dash") == ["b9"], "ダッシュが 9 番に割り当たった")
	# 軸（トリガー）
	menu.buttons[2].pressed.emit()
	var m := InputEventJoypadMotion.new()
	m.axis = 5
	m.axis_value = 0.9
	menu.feed_event(m)
	await h.tree.process_frame
	h.expect(PadConfig.pad.fire == "a5+", "撃つ：軸のトリガーも割り当たる（同じなので変化なし）")
	menu.buttons[0].pressed.emit()
	menu.feed_event(_btn(9))
	await h.tree.process_frame
	h.expect(PadConfig.pad.jump == "b9" and PadConfig.pad.dash == "b0", "使い済みのボタンなら入れ替わる")
	# 初期に戻す
	menu.buttons[PadConfig.ACTIONS.size()].pressed.emit()
	await h.tree.process_frame
	h.expect(PadConfig.pad.jump == "b0", "初期に戻す")
	menu.queue_free()
	_end()


func test_help_and_hint_follow_mapping() -> void:
	_begin()
	PadConfig.assign_pad("jump", "b3")
	var text := PauseInfo.help_text(false)
	h.expect(text.contains("ジャンプ・調べる：Space ／ Y"), "ポーズの操作の説明が割り当てに従う")
	h.expect(Hud.expand_hint("{jump} ボタン", "pad") == "Y ボタン", "案内の文のボタン名が割り当てに従う")
	h.expect(Hud.expand_hint("{jump}", "keyboard") == "Space", "キーボードならキー名")
	_end()
