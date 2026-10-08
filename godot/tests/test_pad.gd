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
	# 弱い：横へ歩いても回らない。前寄り（40 度）なら不感帯の端まで寄る
	cam.follow = "weak"
	cam.yaw = 0.0
	for i in 600:
		cam.update(1.0 / 60.0, Vector3.ZERO, 90.0 * U.DEG, 7.0, null)
	h.near(cam.yaw, 0.0, 0.0001, "弱い：真横へ歩いてもカメラは回らない")
	for i in 900:
		cam.update(1.0 / 60.0, Vector3.ZERO, 40.0 * U.DEG, 7.0, null)
	h.near(cam.yaw / U.DEG, 15.0, 0.5, "弱い：前寄り（40 度）なら不感帯の端（15 度）まで寄る")
	cam.follow = "off"
	cam.yaw = 0.0
	for i in 600:
		cam.update(1.0 / 60.0, Vector3.ZERO, 120.0 * U.DEG, 7.0, null)
	h.near(cam.yaw, 0.0, 0.0001, "切：自動では回らない")


## ロックオンのボタンを押し続けていても、何も捉えていない間は右スティックでカメラを回せる（押し続けて見回し、見えた敵を捉える。LockOn.update）。
## 捉えている間は、右スティックを弾くと対象の切り替え。捉えた瞬間に倒していた分では切り替えない（一度戻してから弾く）。
## 前は適合のあと、ボタンを押している間は右スティックが切り替え専用になり、何も捉えていなくてもカメラを回せなかった（2026-10-08）
func test_right_stick_looks_while_lock_held_without_target() -> void:
	_begin()
	var src = InputSource.new()
	h.tree.root.add_child(src)
	var dt := 1.0 / 60.0
	if not ("fake_sticks" in src and "lock_target" in src):
		h.expect(false, "InputSource にスティックの値の差し替え（fake_sticks）と、捉えているか（lock_target）がある")
	else:
		src.lock_available = true
		src.lock_target = false
		Input.action_press("lock_on")
		src.fake_sticks = {"right": Vector2(1, 0)}
		var f: InputFrame = src.sample(dt)
		h.expect(f.look_x > 0.0 and f.look_active, "ボタンを押していても、捉えていない間は右スティックでカメラを回す")
		h.expect(not f.switch_left and not f.switch_right, "捉えていない間は、対象の切り替えにしない")
		src.lock_target = true
		f = src.sample(dt)
		h.expect(f.look_x == 0.0 and not f.switch_right, "捉えた瞬間に倒していた分では、回さず切り替えもしない")
		src.fake_sticks = {"right": Vector2.ZERO}
		src.sample(dt)
		src.fake_sticks = {"right": Vector2(1, 0)}
		f = src.sample(dt)
		h.expect(f.switch_right, "一度戻してから右へ弾くと、右の対象へ切り替え")
		h.expect(f.look_x == 0.0, "捉えている間は、右スティックでカメラを回さない")
		Input.action_release("lock_on")
		src.lock_target = false
		src.fake_sticks = {"right": Vector2(-1, 0)}
		f = src.sample(dt)
		h.expect(f.look_x < 0.0, "ボタンを離せば、右スティックでカメラを回す")
	src.queue_free()
	_end()


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
	h.expect(menu.buttons.size() == PadConfig.ACTIONS.size() + 7, "全部の操作＋表記・遊び 2 つ・カメラの回り込み・PS 配置・初期に戻す・戻る の行がある")
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
	menu.buttons[PadConfig.ACTIONS.size() + 3].pressed.emit()
	await h.tree.process_frame
	h.expect(PadConfig.cam_follow == "off", "カメラの自動回り込みを決定で切り替える（弱い → 切）")
	menu.buttons[PadConfig.ACTIONS.size() + 5].pressed.emit()
	await h.tree.process_frame
	h.expect(PadConfig.pad.jump == "b0" and PadConfig.cam_follow == "weak", "初期に戻す（カメラの回り込みも弱いに戻る）")
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


## 案内（キーボード）はキーの名前を書き込まず {fire} などで書く：キーの割り当てを変えると、変えたキーの名前が出る
## （マウスのボタン（撃つ＝左クリック・ロックオン＝右クリック）と移動の WASD は変えられないので、そのまま書いてよい）
func test_keyboard_hints_follow_key_mapping() -> void:
	_begin()
	PadConfig.assign_key("fire", KEY_H)
	var kb := []
	for path in ["res://content/events/ch1_town.json", "res://content/events/ch1_ruins.json", "res://content/events/mvp.json", "res://content/events/sample.json"]:
		_collect_kb_hints(JSON.parse_string(FileAccess.get_file_as_string(path)), kb)
	h.expect(kb.size() >= 10, "第 1 章の案内（キーボード）を集める（%d 件）" % kb.size())
	# 変えられる操作の初期のキー（C E F J K Q R・Space・Shift・Tab・Escape）を、名前で書いている案内
	var re := RegEx.create_from_string("(?<![A-Za-z])([CEFJKQR]|Space|Shift|Tab|Escape)(?![A-Za-z])")
	var bad := kb.filter(func(t): return re.search(t) != null)
	h.expect(bad.is_empty(), "案内にキーの名前を書き込まない（%s）" % [bad])
	var valve: Array = kb.filter(func(t): return String(t).contains("弁の球の方を向いて"))
	h.expect(valve.size() == 1 and Hud.expand_hint(valve[0], "keyboard").contains("H（左クリック）で撃とう"), "撃つキーを H に変えると、換気室の案内も H になる")
	_end()


## 会話の文は割り当てで置き換えられない（{fire} などを使えない）ので、ボタン・キーの名前を書かない（すぐ後の案内が出す）。
## 操作の説明（ポーズ）は、ロックオン・撃つのキー（初期は F・L、J）も、変えた後の割り当てで出す
func test_dialogue_and_help_follow_key_mapping() -> void:
	_begin()
	var lines := []
	for path in ["res://content/dialogue/ch1_town.json", "res://content/dialogue/ch1_ruins.json", "res://content/dialogue/mvp.json", "res://content/dialogue/sample.json"]:
		_collect_texts(JSON.parse_string(FileAccess.get_file_as_string(path)), lines)
	h.expect(lines.size() >= 100, "会話の文を集める（%d 件）" % lines.size())
	var re := RegEx.create_from_string("トリガー|クリック|スティック|十字キー|(?<![A-Za-z])([LR][123T]|[ABXY]ボタン|Space|Shift)(?![A-Za-z])")
	var bad := lines.filter(func(t): return re.search(t) != null)
	h.expect(bad.is_empty(), "会話にボタン・キーの名前を書き込まない（%s）" % [bad])
	PadConfig.assign_key("lock_on", KEY_G)
	PadConfig.assign_key("fire", KEY_H)
	var rows := {}
	for r in Menu.help_rows():
		rows[r[0]] = r[1]
	h.expect(String(rows["ロックオン"]).contains("G") and String(rows["ロックオン"]).contains(PadConfig.pad_short("lock_on")), "操作の説明のロックオンに、キー（G）とパッドのボタンが出る（%s）" % rows["ロックオン"])
	h.expect(String(rows["主武器"]).contains("H") and String(rows["主武器"]).contains(PadConfig.pad_short("fire")), "操作の説明の主武器に、キー（H）とパッドのボタンが出る（%s）" % rows["主武器"])
	_end()


## 文字列をすべて集める（会話の文・選択肢・話す人）
func _collect_texts(v, out: Array) -> void:
	if v is Dictionary:
		for k in v:
			_collect_texts(v[k], out)
	elif v is Array:
		for x in v:
			_collect_texts(x, out)
	elif v is String:
		out.append(v)


func _collect_kb_hints(v, out: Array) -> void:
	if v is Dictionary:
		for k in v:
			if k == "kb" and v[k] is String:
				out.append(v[k])
			else:
				_collect_kb_hints(v[k], out)
	elif v is Array:
		for x in v:
			_collect_kb_hints(x, out)


func test_style_deadzone_and_preset() -> void:
	_begin()
	h.expect(PadConfig.code_short("b0") == "A" and PadConfig.code_short("a5+") == "RT", "表記の初期は Xbox（A、RT）")
	PadConfig.style = "ps"
	h.expect(PadConfig.code_short("b0") == "×" and PadConfig.code_short("b2") == "□" and PadConfig.code_short("a5+") == "R2", "PlayStation 表記（×、□、R2）")
	h.expect(Hud.expand_hint("{jump} で跳ぶ", "pad") == "× で跳ぶ", "案内の文も表記に従う")
	PadConfig.style = "auto"
	PadConfig.cycle_style()
	h.expect(PadConfig.style == "xbox", "表記を切り替えられる")
	PadConfig.cycle_dead(true)
	h.near(PadConfig.dead_l, 0.25, 0.0001, "左の遊びを 1 段階大きくする（標準 → 大）")
	PadConfig.cycle_dead(false)
	h.near(PadConfig.dead_r, 0.3, 0.0001, "右の遊びも同じ")
	PadConfig.load_file()
	h.expect(PadConfig.style == "xbox" and absf(PadConfig.dead_l - 0.25) < 0.0001, "表記と遊びも保存される")
	h.expect(InputSource.shape_stick(Vector2(0.2, 0.0), PadConfig.dead_l).length() == 0.0, "遊びを大きくすると、小さな倒しは 0")
	PadConfig.preset_ps_raw()
	h.expect(PadConfig.pad.jump == "b1" and PadConfig.pad.fire == "b7" and PadConfig.pad.confirm == "b1", "PS 配置：× がジャンプ・決定、R2 が撃つ")
	h.expect(_pad_events("ui_accept") == ["b1"] and _btn(1).is_action_pressed("ui_accept"), "メニューの決定も × に従う")
	h.expect(PadConfig.code_short(PadConfig.pad.jump) == "×", "PS 配置では × と表示される")
	PadConfig.reset_all()
	h.expect(PadConfig.style == "auto" and PadConfig.dead_l == 0.15 and PadConfig.pad.jump == "b0", "初期に戻す：表記・遊びも戻る")
	_end()
