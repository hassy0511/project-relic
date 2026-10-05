class_name Menu
extends CanvasLayer
## タイトルとポーズのメニュー。キーボード・ゲームパッド・マウスで選べる（Godot のフォーカス移動を使う）

const HELP := [
	["移動", "WASD ／ 左スティック"],
	["カメラ", "マウス（画面をクリックで固定）／ 矢印キー ／ 右スティック"],
	["ジャンプ・調べる", "Space ／ A"],
	["ダッシュ", "Shift ／ B"],
	["主武器", "左クリック ／ RT（チャージ型は長押しで溜め）"],
	["光刃", "E ／ X（連打でコンボ、長押しで溜め斬り）"],
	["特殊武器", "Q ／ Y（押しっぱなし）"],
	["ロックオン", "右クリック ／ LT（押している間）"],
	["対象の切り替え", "ロックオン中にマウスを横に振る ／ 右スティックを弾く"],
	["回復", "R ／ 十字キー上"],
	["カメラを背後へ", "C ／ R3"],
	["ポーズ", "Esc ／ Start"],
	["性能の表示", "F1"],
	["ハルの見た目の切り替え", "F2"],
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
	for h in (HELP_TOUCH if touch_mode else HELP):
		help.add_child(Hud.make_label(h[0], 18, Color("#ffb23e"), true))
		help.add_child(Hud.make_label(h[1], 18, Color("#e8dcc4")))
	if first:
		first.call_deferred("grab_focus")


func show_title(has_save: bool, new_game: Callable, cont: Callable, quit_game: Callable) -> void:
	var items := [["はじめから", new_game], ["つづきから", cont, not has_save]]
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
	var foot_text := footer if footer != "" else ("上下：選ぶ　決定：Space ／ A ／ タップ　戻る：Esc ／ B" if not touch_mode else "タップで選ぶ")
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
		{"label": "タイトルへ", "detail": "タイトル画面に戻る（保存していない進みは失われる）。", "cb": main.to_title},
	]
	_screen("PAUSE", "セル %d　／　%s" % [game.cells, PauseInfo.play_time_text(game.play_time)], rows, focus)


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
