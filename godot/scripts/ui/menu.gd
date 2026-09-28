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


func _ready() -> void:
	layer = 10
	_root = Control.new()
	_root.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(_root)
	hide_menu()


func is_open() -> bool:
	return _root.visible


func hide_menu() -> void:
	_root.visible = false
	for c in _root.get_children():
		c.queue_free()


func _build(title: String, sub: String, badge: String, items: Array, dark: bool) -> void:
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
	var t := Hud.make_label(title, 96, Color("#f3e9d2"), true)
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


func show_pause(game: GameSim, resume: Callable, toggle_chip: Callable, load_save: Callable, to_title: Callable) -> void:
	var has_chip := game.has_item("chip.charge")
	var chip_label := "チップ：まだ持っていない"
	if has_chip:
		chip_label = "チップ「チャージ化」：%s" % ("装着中（外す）" if game.charge_type() else "外している（付ける）")
	var items := [
		["ゲームに戻る", resume],
		[chip_label, func():
			toggle_chip.call()
			show_pause(game, resume, toggle_chip, load_save, to_title), not has_chip],
		["最後のセーブから再開", load_save],
		["タイトルへ", to_title],
	]
	_build("PAUSE", "セル %d　／　プレイ時間 %d 分" % [game.cells, int(game.play_time / 60.0)], "", items, false)
