class_name Menu
extends CanvasLayer
## タイトルとポーズのメニュー。キーボード・ゲームパッド・マウスで選べる（Godot のフォーカス移動を使う）

## 操作の説明（いまの割り当てを反映する。パッドの名前は設定画面で変えた後のもの）
static func help_rows() -> Array:
	var pk := func(a: String) -> String: return "%s ／ %s" % [PadConfig.keys_text(a), PadConfig.pad_short(a)]
	return [
		["移動", "WASD ／ 左スティック"],
		["カメラ", "マウス（画面をクリックで固定）／ 矢印キー ／ 右スティック"],
		["ジャンプ・調べる", pk.call("jump")],
		["ダッシュ", pk.call("dash")],
		["主武器", "左クリック ／ %s（チャージ型は長押しで溜め）" % PadConfig.pad_short("fire")],
		["光刃", "%s（連打でコンボ、長押しで溜め斬り）" % pk.call("sword")],
		["特殊武器", "%s（押しっぱなし）" % pk.call("special")],
		["ロックオン", "右クリック ／ %s（押している間）" % PadConfig.pad_short("lock_on")],
		["対象の切り替え", "ロックオン中にマウスを横に振る ／ 右スティックを弾く"],
		["回復", pk.call("heal")],
		["カメラを背後へ", pk.call("camera_reset")],
		["地図", pk.call("map")],
		["ポーズ", pk.call("pause")],
		["メニューの決定・会話を送る", "%s ／ %s" % [PadConfig.keys_text("confirm"), PadConfig.pad_short("confirm")]],
		["メニューの戻る", "%s ／ %s" % [PadConfig.keys_text("back"), PadConfig.pad_short("back")]],
		["性能の表示", "F1"],
		["ハルの見た目の切り替え", "F2"],
		["ボタンの割り当て", "タイトル／ポーズの「操作の設定」で変えられる"],
	]

## スマホの画面の操作のときの説明
const HELP_TOUCH := [
	["移動", "画面の左半分に触れて、そのまま動かす"],
	["カメラ", "画面の右半分をなぞる"],
	["ボタン", "右下：ジャンプ・撃つ・斬る・ダッシュ・特殊・ロック・回復"],
	["ロックオン", "「ロック」で入り切り。ロック中に右半分を左右に払うと対象の切り替え"],
	["ポーズ・カメラを背後へ", "右上の「ポーズ」「背後」"],
]

## スマホの画面の操作が有効か（main が設定する）
var touch_mode := false

signal moved
signal chosen

var _root: Control
var _back := Callable()
var _detail: Label
var _note: Label
## 操作の設定画面：割り当て待ちの操作の名前（"" なら待っていない）、画面が開いているか、押したボタンの表示
var _listen := ""
var _controls_open := false
var _pad_info: Label
var _last_press := "（まだ押していない）"
var _controls_back := Callable()
var _controls_row := 0
var _title_args: Array = []
## 今の画面の押せる行（テスト用）
var buttons: Array[Button] = []


func _ready() -> void:
	layer = 10
	_root = Control.new()
	_root.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(_root)
	hide_menu()


func is_open() -> bool:
	return _root.visible


func _unhandled_input(event: InputEvent) -> void:
	# パッドの B／決定の外の「戻る」：サブ画面なら 1 つ前へ（ポーズの一番上では main が閉じる）
	if _root.visible and _back.is_valid() and event.is_action_pressed("ui_cancel"):
		get_viewport().set_input_as_handled()
		moved.emit()
		_back.call()


func hide_menu() -> void:
	_back = Callable()
	_controls_open = false
	_listen = ""
	buttons.clear()
	_root.visible = false
	for c in _root.get_children():
		c.queue_free()


func _build(title: String, sub: String, badge: String, items: Array, dark: bool, show_help := true) -> void:
	for c in _root.get_children():
		c.queue_free()
	_root.visible = true
	var bg := ColorRect.new()
	bg.color = Color(0.06, 0.05, 0.04, 0.55 if dark else 0.35)
	bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	_root.add_child(bg)
	var center := CenterContainer.new()
	center.set_anchors_preset(Control.PRESET_FULL_RECT)
	_root.add_child(center)
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 14)
	center.add_child(box)
	var t := Hud.make_label(title, 96 if show_help else 56, Color("#f3e9d2"), true)
	t.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	box.add_child(t)
	if sub != "":
		var s := Hud.make_label(sub, 30, Color("#ffb23e"))
		s.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		box.add_child(s)
	if badge != "":
		var b := Hud.make_label(badge, 20, Color("#c8bca8"))
		b.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		box.add_child(b)
	var spacer := Control.new()
	spacer.custom_minimum_size = Vector2(0, 20)
	box.add_child(spacer)
	var first: Button = null
	for it in items:
		var btn := Button.new()
		btn.text = it[0]
		btn.disabled = it.size() > 2 and it[2]
		btn.custom_minimum_size = Vector2(480, 56)
		btn.add_theme_font_size_override("font_size", 26)
		btn.pressed.connect(func():
			chosen.emit()
			it[1].call())
		btn.focus_entered.connect(func(): moved.emit())
		btn.mouse_entered.connect(func():
			if not btn.disabled:
				btn.grab_focus())
		box.add_child(btn)
		if first == null and not btn.disabled:
			first = btn
	if not show_help:
		if first:
			first.call_deferred("grab_focus")
		return
	var help := GridContainer.new()
	help.columns = 2
	help.add_theme_constant_override("h_separation", 24)
	var spacer2 := Control.new()
	spacer2.custom_minimum_size = Vector2(0, 16)
	box.add_child(spacer2)
	box.add_child(help)
	for h in (HELP_TOUCH if touch_mode else help_rows()):
		help.add_child(Hud.make_label(h[0], 18, Color("#ffb23e"), true))
		help.add_child(Hud.make_label(h[1], 18, Color("#e8dcc4")))
	if first:
		first.call_deferred("grab_focus")


func show_title(has_save: bool, new_game: Callable, cont: Callable, quit_game: Callable) -> void:
	_title_args = [has_save, new_game, cont, quit_game]
	var items := [["はじめから", new_game], ["つづきから", cont, not has_save],
		["操作の設定", func(): show_controls(func(): show_title(has_save, new_game, cont, quit_game))]]
	if not OS.has_feature("web"):
		items.append(["終了", quit_game])
	_build("ARKWALKER", "アークウォーカー", "試遊版（Godot 版・仮の見た目）", items, true)



## 画面の下の一行（買った・足りないなど）。メニューを開いている間は、通知がこちらに出る
func set_note(text: String) -> void:
	if _note != null and is_instance_valid(_note):
		_note.text = text


## 2 つに分けた画面：左に押せる行（上下で選ぶ）、右に選んでいる行の説明。パッド・キーボード・タッチで同じに使える。
## rows：[{ label, right?, detail?, dim?（薄く表示。押すと callback は呼ばれる）, cb }]
func _screen(title: String, sub: String, rows: Array, focus := 0, back := Callable(), footer := "") -> void:
	for c in _root.get_children():
		c.queue_free()
	buttons.clear()
	_root.visible = true
	_back = back
	_controls_open = false
	_listen = ""
	var bg := ColorRect.new()
	bg.color = Color(0.04, 0.03, 0.03, 0.72)
	bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	_root.add_child(bg)
	var center := CenterContainer.new()
	center.set_anchors_preset(Control.PRESET_FULL_RECT)
	_root.add_child(center)
	var panel := PanelContainer.new()
	panel.add_theme_stylebox_override("panel", Hud.panel_style(Color(0.11, 0.09, 0.07, 0.96), 14))
	panel.custom_minimum_size = Vector2(1560, 940)
	center.add_child(panel)
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 12)
	panel.add_child(box)
	var head := HBoxContainer.new()
	box.add_child(head)
	head.add_child(Hud.make_label(title, 44, Color("#f3e9d2"), true))
	var gap := Control.new()
	gap.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	head.add_child(gap)
	head.add_child(Hud.make_label(sub, 26, Color("#ffb23e")))
	box.add_child(HSeparator.new())
	var body := HBoxContainer.new()
	body.add_theme_constant_override("separation", 24)
	body.size_flags_vertical = Control.SIZE_EXPAND_FILL
	box.add_child(body)
	var left := ScrollContainer.new()
	left.custom_minimum_size = Vector2(640, 730)
	left.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	left.follow_focus = true
	body.add_child(left)
	var list := VBoxContainer.new()
	list.add_theme_constant_override("separation", 8)
	list.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	left.add_child(list)
	var right := PanelContainer.new()
	right.add_theme_stylebox_override("panel", Hud.panel_style(Color(0.05, 0.04, 0.03, 0.7), 10))
	right.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	body.add_child(right)
	var rscroll := ScrollContainer.new()
	rscroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	right.add_child(rscroll)
	_detail = Hud.make_label("", 26, Color("#e8dcc4"))
	_detail.autowrap_mode = TextServer.AUTOWRAP_ARBITRARY
	_detail.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_detail.custom_minimum_size = Vector2(780, 0)
	rscroll.add_child(_detail)
	_note = Hud.make_label("", 26, Color("#fff3b0"), true)
	box.add_child(_note)
	var foot_text := footer if footer != "" else ("上下：選ぶ　決定：%s ／ %s ／ タップ　戻る：%s ／ %s" % [PadConfig.keys_text("confirm").get_slice(" / ", 0), PadConfig.pad_short("confirm"), PadConfig.keys_text("back").get_slice(" / ", 0), PadConfig.pad_short("back")] if not touch_mode else "タップで選ぶ")
	box.add_child(Hud.make_label(foot_text, 18, Color("#a89c88")))
	var first: Button = null
	for i in rows.size():
		var row: Dictionary = rows[i]
		var btn := Button.new()
		btn.custom_minimum_size = Vector2(0, 64)
		btn.alignment = HORIZONTAL_ALIGNMENT_LEFT
		btn.text = " " + String(row.label)
		btn.clip_text = true
		btn.add_theme_font_size_override("font_size", 26)
		btn.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		if row.get("dim", false):
			btn.modulate = Color(1, 1, 1, 0.55)
		if String(row.get("right", "")) != "":
			var rl := Hud.make_label(String(row.right), 24, Color("#ffb23e"))
			rl.set_anchors_preset(Control.PRESET_FULL_RECT)
			rl.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
			rl.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
			rl.offset_right = -16
			rl.mouse_filter = Control.MOUSE_FILTER_IGNORE
			btn.add_child(rl)
		var detail := String(row.get("detail", ""))
		btn.focus_entered.connect(func():
			_detail.text = detail
			moved.emit())
		btn.mouse_entered.connect(func(): btn.grab_focus())
		btn.pressed.connect(func():
			chosen.emit()
			row.cb.call())
		list.add_child(btn)
		buttons.append(btn)
		if i == clampi(focus, 0, rows.size() - 1):
			first = btn
			_detail.text = detail
	if first:
		first.call_deferred("grab_focus")


## ポーズ画面。main：game・resume()・toggle_chip()・save_slot(path)・load_slot(path)・read_slot(path)・to_title()・can_save()・
## SAVE_PATH・AUTOSAVE_PATH を持つ（main.gd）。右側に、選んでいる項目の内容がそのまま出る
func show_pause(main, focus := 0) -> void:
	var game: GameSim = main.game
	var again := func(i: int): show_pause(main, i)
	var has_chip := game.has_item("chip.charge")
	var chip_label := "チップ：まだ持っていない"
	if has_chip:
		chip_label = "チップ「チャージ化」：%s" % ("装着中（外す）" if game.charge_type() else "外している（付ける）")
	var rows := [
		{"label": "ゲームに戻る", "detail": "今の目的\n　%s" % (game.objective if game.objective != "" else "（なし）"), "cb": main.resume},
		{"label": "ステータス", "detail": PauseInfo.status_text(game), "cb": func(): pass},
		{"label": "持ち物", "detail": PauseInfo.items_text(game), "cb": func(): pass},
		{"label": "地図（入った部屋）", "detail": PauseInfo.map_text(game), "cb": func(): pass},
		{"label": "ギルドの依頼", "detail": PauseInfo.requests_text(game), "cb": func(): pass},
		{"label": chip_label, "detail": "チャージ化：主武器が「長押しで溜める」型になる。押すと付け外しできる。", "dim": not has_chip, "cb": func():
			if has_chip:
				main.toggle_chip()
				again.call(5)},
		{"label": "セーブ", "detail": "手動のセーブ（スロット 1）。ビーコンでは自動でも保存される。", "cb": func(): show_save(main, true)},
		{"label": "ロード", "detail": "保存したところから再開する。", "cb": func(): show_save(main, false)},
		{"label": "操作の説明", "detail": PauseInfo.help_text(touch_mode), "cb": func(): pass},
		{"label": "操作の設定", "detail": "ボタン・キーの割り当てを変える。コントローラーの名前と、押したボタンの番号も見られる。", "cb": func(): show_controls(func(): show_pause(main, 9))},
		{"label": "タイトルへ", "detail": "タイトル画面に戻る（保存していない進みは失われる）。", "cb": main.to_title},
	]
	_screen("PAUSE", "セル %d　／　%s" % [game.cells, PauseInfo.play_time_text(game.play_time)], rows, focus)


## 操作の設定の画面。行を決定すると割り当て待ちになり、その状態で押したボタン・キーが割り当たる
## （どんなコントローラーでも、押したボタンの番号・軸で割り当てる。同じ組で使い済みなら入れ替える）
func show_controls(back: Callable, focus := 0, note := "") -> void:
	PadConfig.ensure_loaded()
	_controls_back = back
	var rows := []
	for a in PadConfig.ACTIONS:
		var id: String = a[0]
		var idx: int = rows.size()
		rows.append({
			"label": a[1],
			"right": "%s ／ %s" % [PadConfig.code_text(String(PadConfig.pad.get(id, ""))), PadConfig.keys_text(id, 2)],
			"detail": "%s\n\nパッド：%s\nキー：%s\n\n決定してから、割り当てたいボタン（またはキー）を押す。\nトリガーが「ボタン」でも「軸」でも、押したものがそのまま割り当たる。\n同じボタンを使っている操作があれば入れ替える。\nやめるときは Esc。" % [a[1] + {"confirm": "（メニューの決定と、会話を送るのに使う）", "back": "（メニューで 1 つ前の画面に戻るのに使う）"}.get(id, ""), PadConfig.code_text(String(PadConfig.pad.get(id, ""))), PadConfig.keys_text(id)],
			"cb": func(): _begin_listen(id, idx),
		})
	rows.append({"label": "ボタンの表記", "right": "%s%s" % [PadConfig.STYLE_TEXT[PadConfig.style], "：" + PadConfig.style_resolved() if PadConfig.style == "auto" else ""],
		"detail": "画面や案内に出すボタンの名前。Xbox は A B X Y、PlayStation は × ○ □ △（「番号順の機種」は、ボタンが番号順で届く PS 系用）。自動はコントローラーの名前で決める。決定で切り替える。",
		"cb": func():
			PadConfig.cycle_style()
			show_controls(back, PadConfig.ACTIONS.size(), "表記：%s" % PadConfig.STYLE_TEXT[PadConfig.style])})
	rows.append({"label": "左スティックの遊び", "right": PadConfig.dead_text(true),
		"detail": "左スティックを離しても勝手に動くときは大きくする（遊びが大きいほど、倒し始めの反応は遅くなる）。決定で小→標準→大→特大と切り替える。下の「左スティック」の値が 0 に近いときが、離した状態。",
		"cb": func():
			PadConfig.cycle_dead(true)
			show_controls(back, PadConfig.ACTIONS.size() + 1, "左スティックの遊び：%s" % PadConfig.dead_text(true))})
	rows.append({"label": "右スティックの遊び", "right": PadConfig.dead_text(false),
		"detail": "右スティックを離してもカメラが勝手に回るときは大きくする。決定で切り替える。",
		"cb": func():
			PadConfig.cycle_dead(false)
			show_controls(back, PadConfig.ACTIONS.size() + 2, "右スティックの遊び：%s" % PadConfig.dead_text(false))})
	rows.append({"label": "PS 配置（× で決定）", "detail": "PlayStation 系のコントローラーで、ブラウザが標準の割り当てにしてくれず、ボタンが番号順（□=0 ×=1 ○=2 △=3 L1=4 R1=5 L2=6 R2=7 SHARE=8 OPTIONS=9 L3=10 R3=11）で届くとき用。× がジャンプ・決定、○ がダッシュ・戻る、□ が斬る、△ が特殊武器、L2 がロックオン、R2 が撃つになる。\n標準の割り当てで届くコントローラーなら「初期に戻す」のままで × が決定になる。うまく合わないときは、各行を選んで 1 つずつ割り当てる。", "cb": func():
		PadConfig.preset_ps_raw()
		show_controls(back, PadConfig.ACTIONS.size() + 3, "PS 配置にした（×＝決定）")})
	rows.append({"label": "初期に戻す", "detail": "ボタン・キーの割り当てと、表記・スティックの遊びをすべて初めの状態に戻す。", "cb": func():
		PadConfig.reset_all()
		show_controls(back, 0, "初期の割り当てに戻した")})
	rows.append({"label": "戻る", "detail": "前の画面へ戻る。", "cb": back})
	_screen("操作の設定", "ボタンの割り当て", rows, focus, back,
		"上下：選ぶ　決定：選んで、割り当てたいボタン／キーを押す　戻る：Esc ／ %s" % PadConfig.pad_short("back"))
	_controls_open = true
	_controls_row = focus
	_pad_info = Hud.make_label("", 20, Color("#9fd4c0"))
	_pad_info.autowrap_mode = TextServer.AUTOWRAP_ARBITRARY
	_pad_info.custom_minimum_size = Vector2(1400, 0)
	_note.get_parent().add_child(_pad_info)
	_note.get_parent().move_child(_pad_info, _note.get_index())
	_refresh_pad_info()
	if note != "":
		set_note(note)


func pad_info_text() -> String:
	var names := []
	for d in Input.get_connected_joypads():
		names.append("%s（番号 %d）" % [Input.get_joy_name(d), d])
	var who := "、".join(names) if not names.is_empty() else "見つかりません（ボタンを 1 つ押すと認識されることがあります）"
	var l := InputSource.read_stick(JOY_AXIS_LEFT_X, JOY_AXIS_LEFT_Y)
	var r := InputSource.read_stick(JOY_AXIS_RIGHT_X, JOY_AXIS_RIGHT_Y)
	return "コントローラー：%s\n押したボタンの番号：%s　　左スティック（%.2f, %.2f）　右スティック（%.2f, %.2f）　← 離したときに 0 から離れていたら「遊び」を大きくする" % [who, _last_press, l.x, l.y, r.x, r.y]


func _refresh_pad_info() -> void:
	if _pad_info != null and is_instance_valid(_pad_info):
		_pad_info.text = pad_info_text() if _listen == "" else "「%s」に割り当てる：ボタン・キーを押してください（Esc でやめる）\n%s" % [PadConfig.label_of(_listen), pad_info_text()]


func _begin_listen(id: String, row: int) -> void:
	_listen = id
	_controls_row = row
	set_note("")
	_refresh_pad_info()


## 割り当て待ちのとき、押されたボタン・キーを割り当てる（テストからも呼ぶ）。返り値：受け付けたか
func feed_event(event: InputEvent) -> bool:
	if not _controls_open:
		return false
	var code := ""
	if event is InputEventJoypadButton and event.pressed:
		code = "b%d" % event.button_index
		var bn := PadConfig.button_name(event.button_index)
		_last_press = "ボタン %d%s" % [event.button_index, "（%s）" % bn if bn != "" else ""]
	elif event is InputEventJoypadMotion and absf(event.axis_value) >= 0.6 and event.axis >= 4:
		code = PadConfig.code_of_axis(event.axis, event.axis_value)
		_last_press = "軸 %d（%s）" % [event.axis, "＋" if event.axis_value > 0.0 else "−"]
	var key := -1
	if event is InputEventKey and event.pressed and not event.echo:
		key = event.physical_keycode
	if code == "" and key < 0:
		if _listen == "":
			_refresh_pad_info()
		return false
	if _listen == "":
		_refresh_pad_info()
		return false
	var id := _listen
	_listen = ""
	if key == KEY_ESCAPE:
		show_controls(_controls_back, _controls_row, "割り当てをやめた")
		return true
	var swapped := PadConfig.assign_pad(id, code) if code != "" else PadConfig.assign_key(id, key)
	var msg := "「%s」に %s を割り当てた" % [PadConfig.label_of(id), PadConfig.code_text(code) if code != "" else OS.get_keycode_string(key)]
	if swapped != "":
		msg += "（「%s」と入れ替えた）" % PadConfig.label_of(swapped)
	show_controls(_controls_back, _controls_row, msg)
	return true


var _info_time := 0.0


func _process(dt: float) -> void:
	if _controls_open:
		_info_time += dt
		if _info_time > 0.15:
			_info_time = 0.0
			_refresh_pad_info()


func _input(event: InputEvent) -> void:
	if feed_event(event) or (_controls_open and _listen != "" and (event is InputEventKey or event is InputEventJoypadButton)):
		get_viewport().set_input_as_handled()


## セーブ・ロードの画面（スロット 1 とオートセーブ）
func show_save(main, saving: bool) -> void:
	var rows := []
	for slot in [["スロット 1", main.SAVE_PATH], ["オートセーブ", main.AUTOSAVE_PATH]]:
		var d = main.read_slot(slot[1])
		var path: String = slot[1]
		var is_auto: bool = path == main.AUTOSAVE_PATH
		var detail := PauseInfo.save_info(d)
		if saving and is_auto:
			detail = "オートセーブは、部屋を移るときに自動で書き換わる（手では書けない）。\n\n" + detail
		elif saving and not main.can_save():
			detail = "いまはセーブできない（会話・イベント中、ボス戦中）。\n\n" + detail
		rows.append({
			"label": "%s　%s" % [slot[0], "" if d == null else "（保存あり）"],
			"detail": detail,
			"dim": (saving and (is_auto or not main.can_save())) or (not saving and d == null),
			"cb": func():
				if saving:
					if not is_auto and main.can_save():
						main.save_slot(path)
						show_save(main, true)
					else:
						set_note("ここには保存できない")
				elif d != null:
					main.load_slot(path)
				else:
					set_note("保存がない"),
		})
	rows.append({"label": "戻る", "detail": "ポーズ画面へ戻る。", "cb": func(): show_pause(main, 6 if saving else 7)})
	_screen("SAVE" if saving else "LOAD", "", rows, 0, func(): show_pause(main, 6 if saving else 7))


## 店・工房・ギルドの共通の画面。rows は _screen と同じ。最後に「閉じる」を足す
func show_trade(title: String, sub: String, rows: Array, close: Callable, focus := 0) -> void:
	var all := rows.duplicate()
	all.append({"label": "閉じる", "detail": "画面を閉じる。", "cb": close})
	_screen(title, sub, all, focus, close)


## やられたときの画面
func show_retry(has_save: bool, retry: Callable, load_save: Callable, to_title: Callable) -> void:
	var items := [["中継地点から再開する", retry], ["最後のセーブから再開", load_save, not has_save], ["タイトルへ", to_title]]
	_build("やられた……", "倒したボス・開けた宝箱・立てたフラグはそのまま残っている", "", items, true, false)
