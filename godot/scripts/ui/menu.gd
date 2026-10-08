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
		["主武器", "左クリック ／ %s（ハルの向いている方へ撃つ。チャージ型は長押しで溜め）" % PadConfig.pad_short("fire")],
		["光刃", "%s（連打でコンボ、長押しで溜め斬り）" % pk.call("sword")],
		["特殊武器", "%s（押しっぱなし）" % pk.call("special")],
		["ロックオン", "右クリック ／ %s（押している間。弾は対象へ。対象がいないときはカメラを背後へ）" % PadConfig.pad_short("lock_on")],
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
	["撃つ", "ハルの向いている方へ撃つ（ロック中は対象へ）"],
	["ロックオン", "「ロック」で入り切り。ロック中に右半分を左右に払うと対象の切り替え"],
	["ポーズ・カメラを背後へ", "右上の「ポーズ」「背後」"],
]
## タイトル画面のスマホ用の短い説明（低い画面でも 360px の高さで 14px 以上の文字で、ロゴと選択肢の横に収まるように。全文はポーズの「操作の説明」）
const HELP_TOUCH_TITLE := [
	["移動・カメラ", "左半分で移動、右半分をなぞってカメラ"],
	["ボタン", "右下：ジャンプ・撃つ・斬るなど"],
	["ロックオン", "「ロック」で入り切り、払って切り替え"],
	["ポーズ・背後", "右上のボタン"],
]
## スマホの画面の操作のときの補助の文字の大きさ（UI を大きく描いたあとで 360px の高さで 14px 以上。spec）
const AUX_TOUCH := 26

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
	_root.theme = UiArt.theme()
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


func _clear() -> void:
	for c in _root.get_children():
		c.queue_free()
	buttons.clear()
	_root.visible = true


## 後ろのゲームの画面をぼかして暗くする（shader が使えないときは暗い幕）
func _backdrop(alpha: float) -> void:
	var bg := ColorRect.new()
	bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	var sh = load("res://assets/shaders/menu_backdrop.gdshader")
	if sh != null:
		var mat := ShaderMaterial.new()
		mat.shader = sh
		mat.set_shader_parameter("tint", Color(0.05, 0.045, 0.04, alpha))
		bg.material = mat
	else:
		bg.color = Color(0.05, 0.045, 0.04, alpha)
	_root.add_child(bg)


## 画面の大きさ（仮想の画面。スマホでは content_scale_factor で小さくなる）
func _view() -> Vector2:
	var v := _root.get_viewport_rect().size
	return v if v.x > 0.0 else Vector2(1920, 1080)


## 行のボタン（見た目は UiArt.theme()：ボタンの 4 状態の部品、選んでいる行は煉瓦色の札＋左にカーソル）
func _row_button(text: String, h: float, font_size: int) -> Button:
	var btn := Button.new()
	btn.text = text
	btn.custom_minimum_size = Vector2(0, h)
	btn.alignment = HORIZONTAL_ALIGNMENT_LEFT
	btn.clip_text = true
	# 入りきらない名前は途中で切らず「…」で終える（全文は右の説明に出る）
	btn.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
	btn.add_theme_font_size_override("font_size", font_size)
	btn.add_theme_constant_override("icon_max_width", 44)
	btn.expand_icon = true
	UiArt.add_cursor(btn)
	return btn


## タイトル画面とやられた画面の、縦に並ぶ選択肢
func _menu_buttons(box: Container, items: Array, width: float) -> Button:
	var first: Button = null
	for it in items:
		var btn := _row_button(String(it[0]), 64, 28)
		btn.disabled = it.size() > 2 and it[2]
		btn.custom_minimum_size.x = width
		btn.pressed.connect(func():
			chosen.emit()
			it[1].call())
		btn.focus_entered.connect(func(): moved.emit())
		btn.mouse_entered.connect(func():
			if not btn.disabled:
				btn.grab_focus())
		box.add_child(btn)
		buttons.append(btn)
		if first == null and not btn.disabled:
			first = btn
	return first


## タイトル画面（ui_title.png）：左上にロゴ、左下に選択肢、右に操作の説明。後ろは夜明けの空（main が用意する）
func show_title(has_save: bool, new_game: Callable, cont: Callable, quit_game: Callable) -> void:
	_title_args = [has_save, new_game, cont, quit_game]
	var items := [["はじめから", new_game], ["つづきから", cont, not has_save],
		["操作の設定", func(): show_controls(func(): show_title(has_save, new_game, cont, quit_game))]]
	if not OS.has_feature("web"):
		items.append(["終了", quit_game])
	_clear()
	_back = Callable()
	_controls_open = false
	_listen = ""
	var vs := _view()
	# 左側を暗くして、ロゴと文字を読みやすく
	var shade := TextureRect.new()
	var grad := Gradient.new()
	grad.set_color(0, Color(0.04, 0.035, 0.03, 0.88))
	grad.set_color(1, Color(0.04, 0.035, 0.03, 0.0))
	var gt := GradientTexture2D.new()
	gt.gradient = grad
	gt.fill_to = Vector2(1, 0)
	gt.width = 256
	gt.height = 4
	shade.texture = gt
	shade.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	shade.stretch_mode = TextureRect.STRETCH_SCALE
	shade.anchor_bottom = 1.0
	shade.anchor_right = 0.62
	_root.add_child(shade)
	var left := maxf(48.0, vs.x * 0.055)
	var logo := VBoxContainer.new()
	logo.position = Vector2(left, maxf(36.0, vs.y * 0.08))
	logo.add_theme_constant_override("separation", 0)
	_root.add_child(logo)
	# 低い画面（スマホでは UI を大きく描くので、仮想の高さが 640〜750 になる）では、ロゴを小さくして下の選択肢と重ならないように
	var low := vs.y < 900.0
	var en := Hud.make_label("A R K W A L K E R", 32 if low else 40, UiArt.PAPER, true)
	logo.add_child(en)
	var ja := Hud.make_label("アークウォーカー", 88 if low else 112, UiArt.PAPER, true)
	ja.add_theme_constant_override("outline_size", 11 if low else 14)
	ja.add_theme_color_override("font_outline_color", Color(0.12, 0.08, 0.05, 0.85))
	logo.add_child(ja)
	var line := HBoxContainer.new()
	line.add_theme_constant_override("separation", 14)
	logo.add_child(line)
	line.add_child(Hud.make_label("―　方舟は夜明けを歩く　―", 30 if low else 36, Color("#f6d9a8")))
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 10)
	box.anchor_top = 1.0
	box.anchor_bottom = 1.0
	box.offset_left = left
	box.offset_top = -40
	box.offset_bottom = -40
	box.grow_vertical = Control.GROW_DIRECTION_BEGIN
	_root.add_child(box)
	var first := _menu_buttons(box, items, 500)
	var badge := Hud.make_label("試遊版（Godot 版）", 20, UiArt.DIM_TEXT)
	Hud._pin(badge, 1, 1, -32, -24)
	_root.add_child(badge)
	# 操作の説明（右の枠）
	var help_panel := PanelContainer.new()
	help_panel.add_theme_stylebox_override("panel", UiArt.box("small", Vector4(30, 24, 30, 24), Color(1, 1, 1, 0.92)))
	Hud._pin(help_panel, 1, 1, -maxf(32.0, vs.x * 0.03), -64)
	_root.add_child(help_panel)
	var help := GridContainer.new()
	help.columns = 2
	help.add_theme_constant_override("h_separation", 24)
	help.add_theme_constant_override("v_separation", 2)
	help_panel.add_child(help)
	var rows: Array = HELP_TOUCH_TITLE if touch_mode else help_rows()
	var fs := AUX_TOUCH if touch_mode else 19
	var value_w := minf(560.0, vs.x * 0.42 - 260.0)
	if touch_mode:
		# スマホ：選択肢の右から画面の右端までを使う
		var label_w := 0.0
		for h in rows:
			label_w = maxf(label_w, UiArt.bold().get_string_size(h[0], HORIZONTAL_ALIGNMENT_LEFT, -1, fs).x)
		value_w = clampf(vs.x - (left + 540.0) - maxf(32.0, vs.x * 0.03) - 60.0 - 24.0 - label_w - 8.0, 280.0, 640.0)
	for h in rows:
		help.add_child(Hud.make_label(h[0], fs, UiArt.AMBER, true))
		var v := Hud.make_label(h[1], fs, Color("#e8dcc4"))
		v.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		v.custom_minimum_size = Vector2(value_w, 0)
		help.add_child(v)
	if first:
		_grab_later(first)



## 画面の下の一行（買った・足りないなど）。メニューを開いている間は、通知がこちらに出る
func set_note(text: String) -> void:
	if _note != null and is_instance_valid(_note):
		_note.text = text


## 2 つに分けた画面（ui_menu_pause.png などの枠と札）：左に押せる行（上下で選ぶ）、右に選んでいる行の説明。
## パッド・キーボード・タッチで同じに使える。
## rows：[{ label, right?, detail?, icon?（行の左と説明の上に出す絵）, dim?（薄く表示。押すと callback は呼ばれる）, cb }]
func _screen(title: String, sub: String, rows: Array, focus := 0, back := Callable(), footer := "") -> void:
	_clear()
	_back = back
	_controls_open = false
	_listen = ""
	_backdrop(0.62)
	var vs := _view()
	var side := clampf(vs.x * 0.04, 24.0, 80.0)
	var frame := MarginContainer.new()
	frame.set_anchors_preset(Control.PRESET_FULL_RECT)
	frame.add_theme_constant_override("margin_left", int(side))
	frame.add_theme_constant_override("margin_right", int(side))
	frame.add_theme_constant_override("margin_top", 26)
	frame.add_theme_constant_override("margin_bottom", 18)
	_root.add_child(frame)
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 12)
	frame.add_child(box)
	# 見出し：選んでいるタブの札（煉瓦色）に画面の名前、右に所持セルなど
	var head := HBoxContainer.new()
	head.add_theme_constant_override("separation", 16)
	box.add_child(head)
	var tab := PanelContainer.new()
	tab.add_theme_stylebox_override("panel", UiArt.box("tab_selected", Vector4(40, 6, 48, 6)))
	head.add_child(tab)
	var tl := Hud.make_label(title, 36, UiArt.PAPER, true)
	tl.custom_minimum_size = Vector2(200, 0)
	tl.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	tab.add_child(tl)
	var gap := Control.new()
	gap.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	head.add_child(gap)
	if sub != "":
		var sb := PanelContainer.new()
		sb.add_theme_stylebox_override("panel", UiArt.box("tab_idle", Vector4(30, 6, 34, 6)))
		sb.size_flags_vertical = Control.SIZE_SHRINK_CENTER
		head.add_child(sb)
		sb.add_child(Hud.make_label(sub, 26, UiArt.AMBER, true))
	var body := HBoxContainer.new()
	body.add_theme_constant_override("separation", 20)
	body.size_flags_vertical = Control.SIZE_EXPAND_FILL
	box.add_child(body)
	var lp := PanelContainer.new()
	lp.add_theme_stylebox_override("panel", UiArt.box("small", Vector4(16, 18, 14, 18)))
	# 狭い画面（スマホでは UI を大きく描くので仮想の幅が 1500 前後になる）では、行の名前が切れないよう左を広く
	lp.custom_minimum_size = Vector2(clampf(vs.x * (0.37 if vs.x >= 1700.0 else 0.45), 460.0, 700.0), 0)
	body.add_child(lp)
	var left := ScrollContainer.new()
	left.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	left.follow_focus = true
	lp.add_child(left)
	var list := VBoxContainer.new()
	list.add_theme_constant_override("separation", 6)
	list.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	left.add_child(list)
	var right := PanelContainer.new()
	right.add_theme_stylebox_override("panel", UiArt.box("small", Vector4(34, 26, 30, 26)))
	right.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	body.add_child(right)
	var rcol := VBoxContainer.new()
	rcol.add_theme_constant_override("separation", 12)
	right.add_child(rcol)
	# 説明の上の絵（低い画面では小さく。説明の文の場所を残す）
	var dicon := UiArt.icon_rect(null, 112.0 if vs.y >= 900.0 else 72.0)
	dicon.size_flags_horizontal = Control.SIZE_SHRINK_BEGIN
	dicon.visible = false
	rcol.add_child(dicon)
	var rscroll := ScrollContainer.new()
	rscroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	rscroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	rcol.add_child(rscroll)
	_detail = Hud.make_label("", 28, Color("#ece1c8"))
	_detail.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_detail.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_detail.add_theme_constant_override("line_spacing", 4)
	rscroll.add_child(_detail)
	_note = Hud.make_label("", 26, Color("#fff3b0"), true)
	box.add_child(_note)
	# 画面の下の帯：操作の案内
	var foot := PanelContainer.new()
	foot.add_theme_stylebox_override("panel", UiArt.strip(0.7, Vector4(24, 6, 24, 6)))
	box.add_child(foot)
	var foot_text := footer if footer != "" else ("上下：選ぶ　決定：%s ／ %s ／ タップ　戻る：%s ／ %s" % [PadConfig.keys_text("confirm").get_slice(" / ", 0), PadConfig.pad_short("confirm"), PadConfig.keys_text("back").get_slice(" / ", 0), PadConfig.pad_short("back")] if not touch_mode else "タップで選ぶ")
	var fl := Hud.make_label(foot_text, AUX_TOUCH if touch_mode else 20, Color("#d6cab2"))
	fl.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	foot.add_child(fl)
	# 行に絵が 1 つでもあれば、絵の無い行にも同じ幅の空きを置いて文字の頭をそろえる
	var any_icon := false
	for row in rows:
		if row.get("icon") != null:
			any_icon = true
	var first: Button = null
	for i in rows.size():
		var row: Dictionary = rows[i]
		var btn := _row_button(String(row.label), 64, 28)
		btn.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		var icon = row.get("icon")
		if icon != null:
			btn.icon = icon
		elif any_icon:
			btn.icon = _blank_icon()
		if row.get("dim", false):
			btn.modulate = Color(1, 1, 1, 0.55)
		if String(row.get("right", "")) != "":
			var rl := Hud.make_label(String(row.right), AUX_TOUCH if touch_mode else 24, UiArt.AMBER, true)
			rl.set_anchors_preset(Control.PRESET_FULL_RECT)
			rl.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
			rl.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
			rl.offset_right = -22
			rl.mouse_filter = Control.MOUSE_FILTER_IGNORE
			btn.add_child(rl)
			_reserve_right(btn, rl.get_minimum_size().x + 40.0)
		var detail := String(row.get("detail", ""))
		btn.focus_entered.connect(func():
			_detail.text = detail
			dicon.texture = icon
			dicon.visible = icon != null
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
			dicon.texture = icon
			dicon.visible = icon != null
	if first:
		_grab_later(first)


## ボタンの右に値段などを出すとき、行の名前が下に潜らないよう、右の余白を広げる
func _reserve_right(btn: Button, px: float) -> void:
	for st in ["normal", "hover", "pressed", "hover_pressed", "disabled", "focus"]:
		var sb: StyleBox = UiArt.theme().get_stylebox(st, "Button").duplicate()
		sb.content_margin_right = px
		btn.add_theme_stylebox_override(st, sb)


## 画面ができてから（大きさが決まってから）最初の行を選ぶ。スクロールの位置がずれないように。
## その間に別の行が選ばれていたら（テストなど）そのまま
func _grab_later(b: Button) -> void:
	await get_tree().process_frame
	if is_instance_valid(b) and b.is_inside_tree() and b.is_visible_in_tree():
		var cur := get_viewport().gui_get_focus_owner()
		if cur == null or not buttons.has(cur):
			b.grab_focus()


static var _blank: Texture2D = null


## 透明な絵（行の頭をそろえるための空き）
static func _blank_icon() -> Texture2D:
	if _blank == null:
		var img := Image.create(4, 4, false, Image.FORMAT_RGBA8)
		img.fill(Color(0, 0, 0, 0))
		_blank = ImageTexture.create_from_image(img)
	return _blank

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
		{"label": "ステータス", "detail": PauseInfo.status_text(game), "icon": UiArt.rank_icon(game.mark), "cb": func(): pass},
		{"label": "持ち物", "detail": PauseInfo.items_text(game), "icon": UiArt.tex("icon_item_repair_small"), "cb": func(): pass},
		{"label": "地図（入った部屋）", "detail": PauseInfo.map_text(game), "icon": UiArt.tex("icon_map_current"), "cb": func(): pass},
		{"label": "ギルドの依頼", "detail": PauseInfo.requests_text(game), "icon": UiArt.tex("icon_map_quest"), "cb": func(): pass},
		{"label": chip_label, "detail": "チャージ化：主武器が「長押しで溜める」型になる。押すと付け外しできる。", "dim": not has_chip, "icon": UiArt.tex("icon_item_chip"), "cb": func():
			if has_chip:
				main.toggle_chip()
				again.call(5)},
		{"label": "セーブ", "detail": "手動のセーブ（スロット 1）。ビーコンでは自動でも保存される。", "icon": UiArt.tex("icon_map_save_beacon"), "cb": func(): show_save(main, true)},
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
	rows.append({"label": "カメラの自動回り込み", "right": PadConfig.CAM_FOLLOW_TEXT[PadConfig.cam_follow],
		"detail": "歩いているとき、カメラが自動でハルの背後へ回るかどうか。\n弱い：前へ進むときだけゆっくり回る（横や後ろへ歩いてもカメラは回らない）。\n切：自動では回らない（右スティック・マウスで回す。背後のボタンで真後ろへ）。\n強い：横・後ろへ進んでも回る。\n決定で切り替える。",
		"cb": func():
			PadConfig.cycle_cam_follow()
			show_controls(back, PadConfig.ACTIONS.size() + 3, "カメラの自動回り込み：%s" % PadConfig.CAM_FOLLOW_TEXT[PadConfig.cam_follow])})
	rows.append({"label": "PS 配置（× で決定）", "detail": "PlayStation 系のコントローラーで、ブラウザが標準の割り当てにしてくれず、ボタンが番号順（□=0 ×=1 ○=2 △=3 L1=4 R1=5 L2=6 R2=7 SHARE=8 OPTIONS=9 L3=10 R3=11）で届くとき用。× がジャンプ・決定、○ がダッシュ・戻る、□ が斬る、△ が特殊武器、L2 がロックオン、R2 が撃つになる。\n標準の割り当てで届くコントローラーなら「初期に戻す」のままで × が決定になる。うまく合わないときは、各行を選んで 1 つずつ割り当てる。", "cb": func():
		PadConfig.preset_ps_raw()
		show_controls(back, PadConfig.ACTIONS.size() + 4, "PS 配置にした（×＝決定）")})
	rows.append({"label": "初期に戻す", "detail": "ボタン・キーの割り当てと、表記・スティックの遊び・カメラの自動回り込みをすべて初めの状態に戻す。", "cb": func():
		PadConfig.reset_all()
		show_controls(back, 0, "初期の割り当てに戻した")})
	rows.append({"label": "戻る", "detail": "前の画面へ戻る。", "cb": back})
	_screen("操作の設定", "ボタンの割り当て", rows, focus, back,
		"上下：選ぶ　決定：選んで、割り当てたいボタン／キーを押す　戻る：Esc ／ %s" % PadConfig.pad_short("back"))
	_controls_open = true
	_controls_row = focus
	_pad_info = Hud.make_label("", 20, Color("#9fd4c0"))
	_pad_info.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
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
	_clear()
	_back = Callable()
	_controls_open = false
	_listen = ""
	_backdrop(0.5)
	# ui_retry.png：画面の真ん中に小さな枠、選んでいる行は煉瓦色の札
	var center := CenterContainer.new()
	center.set_anchors_preset(Control.PRESET_FULL_RECT)
	_root.add_child(center)
	var col := VBoxContainer.new()
	col.add_theme_constant_override("separation", 14)
	center.add_child(col)
	var t := Hud.make_label("やられた……", 64, UiArt.PAPER, true)
	t.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	col.add_child(t)
	var s := Hud.make_label("倒したボス・開けた宝箱・立てたフラグはそのまま残っている", AUX_TOUCH if touch_mode else 24, UiArt.AMBER)
	s.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	col.add_child(s)
	var panel := PanelContainer.new()
	panel.add_theme_stylebox_override("panel", UiArt.box("small", Vector4(30, 26, 30, 26)))
	panel.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	col.add_child(panel)
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 10)
	panel.add_child(box)
	var first := _menu_buttons(box, items, 600)
	if first:
		_grab_later(first)
