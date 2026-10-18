class_name UiArt
extends RefCounted
## Codex の UI の絵（W2-08、godot/assets/ui/）を画面の部品にする：9 分割の枠、ボタン・パネルの見た目（Theme）、
## ゲージ、アイコンの対応表。写し方は tools/import_ui_art.py（枠は 50%、アイコンは 128px に縮めてある）。

const DIR := "res://assets/ui/"

## 色（spec.md の色見本）
const PAPER := Color("#F3E9D2")
const AMBER := Color("#FFBC52")
const BRICK := Color("#B75B43")
const BRASS := Color("#A98749")
const GRAPHITE := Color("#444641")
const LEATHER := Color("#594333")
const DANGER := Color("#A94739")
const INK := Color(0.07, 0.065, 0.06)
const DIM_TEXT := Color("#a89c88")

## 9 分割の角（縮めたあとの画素：横, 縦）。spec.md r2 の表（元の画像で飾りの外端まで測った左右／上下の値）の半分を切り上げたもの。
## 元の画像の値：大 44／48、小 48／52、会話 42／44、名前 28／42、選択肢（旧）42／56・r2 28／24、タブ 28／34、ボタン 34／44
const SLICE := {
	"large": Vector2i(22, 24), "small": Vector2i(24, 26), "dialogue": Vector2i(21, 22), "name": Vector2i(14, 21),
	"choice": Vector2i(21, 28), "choice_r2": Vector2i(14, 12), "tab_idle": Vector2i(14, 17), "tab_selected": Vector2i(14, 17),
	"button_normal": Vector2i(17, 22), "button_focus": Vector2i(17, 22), "button_focus_r2": Vector2i(17, 22),
	"button_pressed": Vector2i(17, 22), "button_disabled": Vector2i(17, 22),
}

## ゲージの枠の中の窓（元の画像の画素。中身はこの中に描く。端は 9 分割で伸ばさない部分）
const GAUGE := {
	"hp": {"frame": "ui_parts_gauge_hp_frame", "window": Rect2(54, 28, 916, 40), "cap": 64},
	"energy": {"frame": "ui_parts_gauge_energy_frame", "window": Rect2(59, 29, 906, 37), "cap": 64},
	"boss": {"frame": "ui_parts_gauge_boss_frame", "window": Rect2(94, 26, 1349, 44), "cap": 100},
}

## アイテムの ID → アイコン
const ITEM_ICONS := {
	"special.drill": "icon_we_break_drill", "chip.charge": "icon_item_chip", "consumable.repair": "icon_item_repair_small",
	"core.kannuki": "icon_item_kannuki_core", "weapon.spark": "icon_spark_rapid", "frame.vestige": "icon_armor_body",
	"item.lifecore": "icon_item_life_core", "cells": "icon_item_cell_small",
}
## 回収屋の印 → アイコン（Cond.MARKS の順）
const RANK_ICONS := {
	"見習い": "icon_rank_apprentice", "降下許可": "icon_rank_descent", "銅の印": "icon_rank_bronze", "銀の印": "icon_rank_silver",
	"金の印": "icon_rank_gold", "一人前の印": "icon_rank_master", "白磁の印": "icon_rank_porcelain",
}

static var _tex := {}
static var _theme: Theme = null
static var _bold: Font = null


## 部品の絵（無ければ null。絵が無くても画面は出るように、使う側は null を許す）
static func tex(name: String) -> Texture2D:
	if not _tex.has(name):
		var path := DIR + name + ".png"
		_tex[name] = load(path) if ResourceLoader.exists(path) else null
	return _tex[name]


static func bold() -> Font:
	if _bold == null:
		_bold = load("res://assets/fonts/NotoSansJP-Bold.otf")
	return _bold


## 9 分割の枠。part：large / small / dialogue / name / choice / tab_idle / tab_selected / button_*。pad：中身の余白（左, 上, 右, 下）
static func box(part: String, pad := Vector4(24, 14, 24, 14), tint := Color.WHITE) -> StyleBox:
	var t := tex("ui_parts_panel_" + part)
	if t == null:
		var f := StyleBoxFlat.new()
		f.bg_color = Color(0.1, 0.09, 0.08, 0.92)
		f.set_corner_radius_all(6)
		_pad(f, pad)
		return f
	var s := StyleBoxTexture.new()
	s.texture = t
	var m: Vector2i = SLICE.get(part, Vector2i(16, 16))
	s.texture_margin_left = m.x
	s.texture_margin_right = m.x
	s.texture_margin_top = m.y
	s.texture_margin_bottom = m.y
	s.modulate_color = tint
	_pad(s, pad)
	return s


static func _pad(s: StyleBox, pad: Vector4) -> void:
	s.content_margin_left = pad.x
	s.content_margin_top = pad.y
	s.content_margin_right = pad.z
	s.content_margin_bottom = pad.w


## 平らな帯（HUD の目的・知らせ・案内の下地。絵の部品の無いところ）
static func strip(alpha := 0.62, pad := Vector4(20, 8, 20, 8), border := false) -> StyleBoxFlat:
	var s := StyleBoxFlat.new()
	s.bg_color = Color(INK, alpha)
	s.set_corner_radius_all(4)
	if border:
		s.border_color = Color(BRASS, 0.7)
		s.set_border_width_all(2)
	_pad(s, pad)
	return s


## ボタン・パネル・スクロールの見た目（メニューの画面の根元に付ける）
static func theme() -> Theme:
	if _theme != null:
		return _theme
	var th := Theme.new()
	th.default_font_size = 26
	var pad := Vector4(56, 10, 24, 10)
	th.set_stylebox("normal", "Button", box("button_normal", pad))
	th.set_stylebox("hover", "Button", box("button_normal", pad, Color(1.18, 1.14, 1.08)))
	# 押した札（フォーカスの無いとき：タッチで押した行など）。フォーカスのある行は add_cursor が行全体を暗くする
	th.set_stylebox("pressed", "Button", box("button_pressed", pad, Color(0.82, 0.82, 0.82)))
	th.set_stylebox("hover_pressed", "Button", box("button_pressed", pad, Color(0.82, 0.82, 0.82)))
	th.set_stylebox("disabled", "Button", box("button_disabled", pad))
	# フォーカス（選んでいる行）：暗い面に琥珀の縁の札（r2）。押した札（煉瓦色）とは別の見た目。カーソルの絵は Menu が左に添える
	th.set_stylebox("focus", "Button", box("button_focus_r2", pad))
	for c in ["font_color", "font_hover_color", "font_pressed_color", "font_hover_pressed_color", "font_focus_color"]:
		th.set_color(c, "Button", PAPER)
	th.set_color("font_disabled_color", "Button", Color(PAPER, 0.45))
	th.set_color("font_outline_color", "Button", Color(0, 0, 0, 0.55))
	th.set_constant("outline_size", "Button", 4)
	th.set_stylebox("panel", "PanelContainer", box("large", Vector4(30, 26, 30, 26)))
	th.set_stylebox("panel", "Panel", box("small"))
	th.set_color("font_color", "Label", PAPER)
	var sep := StyleBoxLine.new()
	sep.color = Color(BRASS, 0.8)
	sep.thickness = 2
	th.set_stylebox("separator", "HSeparator", sep)
	th.set_constant("separation", "HSeparator", 6)
	# スクロールバー：細い真鍮のつまみ（絵の部品が無いので平らな色）
	var track := StyleBoxFlat.new()
	track.bg_color = Color(0, 0, 0, 0.35)
	track.set_corner_radius_all(4)
	track.content_margin_left = 6
	track.content_margin_right = 6
	var grab := StyleBoxFlat.new()
	grab.bg_color = Color(BRASS, 0.9)
	grab.set_corner_radius_all(4)
	var grab_hi := grab.duplicate()
	grab_hi.bg_color = AMBER
	th.set_stylebox("scroll", "VScrollBar", track)
	th.set_stylebox("grabber", "VScrollBar", grab)
	th.set_stylebox("grabber_highlight", "VScrollBar", grab_hi)
	th.set_stylebox("grabber_pressed", "VScrollBar", grab_hi)
	th.set_stylebox("panel", "ScrollContainer", StyleBoxEmpty.new())
	_theme = th
	return th


## 選んでいる行の左に出すカーソル（ui_parts_cursor）。ボタンの左の余白に入る
static func add_cursor(btn: Button, size := 34.0) -> TextureRect:
	var t := tex("ui_parts_cursor")
	if t == null:
		return null
	var c := TextureRect.new()
	c.texture = t
	c.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	c.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	c.mouse_filter = Control.MOUSE_FILTER_IGNORE
	c.anchor_top = 0.5
	c.anchor_bottom = 0.5
	c.offset_left = 12
	c.offset_right = 12 + size
	c.offset_top = -size * 0.5
	c.offset_bottom = size * 0.5
	c.visible = false
	btn.add_child(c)
	btn.focus_entered.connect(func(): c.visible = true)
	btn.focus_exited.connect(func(): c.visible = false)
	# 押している間は「押した」札（煉瓦色）を見せる。Godot はフォーカスの札を状態の札の上に重ねて描くので、
	# 選んでいる行では押している間だけフォーカスの札を外す（離したら、元の札に戻す。右に値段のある行は自前の札を持つ）
	btn.button_down.connect(func():
		var cur: StyleBox = btn.get_theme_stylebox("focus") if btn.has_theme_stylebox_override("focus") else null
		if cur is StyleBoxEmpty:
			return
		if cur != null:
			btn.set_meta("focus_box", cur)
		elif btn.has_meta("focus_box"):
			btn.remove_meta("focus_box")
		btn.add_theme_stylebox_override("focus", StyleBoxEmpty.new()))
	btn.button_up.connect(func():
		if btn.has_meta("focus_box"):
			btn.add_theme_stylebox_override("focus", btn.get_meta("focus_box"))
		else:
			btn.remove_theme_stylebox_override("focus"))
	return c


static func item_icon(id: String) -> Texture2D:
	if ITEM_ICONS.has(id):
		return tex(ITEM_ICONS[id])
	if id.begins_with("relic."):
		return tex("icon_item_relic")
	return null


static func rank_icon(mark: String) -> Texture2D:
	return tex(RANK_ICONS.get(mark, "icon_rank_apprentice"))


## 主武器のアイコン：チャージ化のチップを付けていればチャージ型
static func spark_icon(charge: bool) -> Texture2D:
	return tex("icon_spark_charge" if charge else "icon_spark_rapid")


## 輪の中身（一周した輪の絵）を、上から時計回りに progress（0〜1）の分だけ描く（チャージ・解析の進み。spec r2）。
## 絵の中心から扇形に三角形を並べて絵を貼る（TextureProgressBar の円の塗りと同じ作り。ブラウザ版の描き方でもそのまま描ける）。
## 扇の外周は rect に内接する円：輪の絵は中心 (128,128) から半径 128 の内に収まっている
static func draw_radial(ci: CanvasItem, t: Texture2D, rect: Rect2, progress: float, mod := Color.WHITE) -> void:
	progress = clampf(progress, 0.0, 1.0)
	if t == null or progress <= 0.0:
		return
	if progress >= 0.999:
		ci.draw_texture_rect(t, rect, false, mod)
		return
	var c := rect.get_center()
	var steps := maxi(2, ceili(72.0 * progress))
	var pts := PackedVector2Array([c])
	var uvs := PackedVector2Array([Vector2(0.5, 0.5)])
	var idx := PackedInt32Array()
	for i in steps + 1:
		var a := -PI * 0.5 + TAU * progress * float(i) / float(steps)
		var d := Vector2(cos(a), sin(a))
		pts.append(c + d * rect.size * 0.5)
		uvs.append(Vector2(0.5, 0.5) + d * 0.5)
		if i > 0:
			idx.append_array([0, i, i + 1])
	RenderingServer.canvas_item_add_triangle_array(ci.get_canvas_item(), idx, pts, PackedColorArray([mod]), uvs,
		PackedInt32Array(), PackedFloat32Array(), t.get_rid())


## アイコンの TextureRect（大きさ固定）
static func icon_rect(t: Texture2D, size: float) -> TextureRect:
	var r := TextureRect.new()
	r.texture = t
	r.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	r.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	r.custom_minimum_size = Vector2(size, size)
	r.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return r


## 横長のゲージ（枠と中身が別の絵）。枠の窓の中に、暗い下地 → 減った分（遅れて縮む）→ 中身 の順に描き、最後に枠を重ねる。
## 大きさは元の画像の画素で持ち、Control.scale で縮めて描く（絵の細かさを保つ）。
class Gauge:
	extends Control
	var kind := "hp"
	var fill: Texture2D
	var lag_fill: Texture2D
	var value := 1.0
	## 減った分の表示（value より大きいときに見える）
	var lag := 1.0
	## 中身の左端を窓の左からずらす（ボスの名前を枠の中の左に入れるとき）
	var fill_left := 0.0
	## 段階の区切り（0〜1 の位置）
	var marks: Array = []
	var fill_modulate := Color.WHITE
	var track := Color(0.05, 0.045, 0.04, 0.85)
	var _frame: StyleBox

	func setup(k: String, fill_name: String, length: float, s: float) -> void:
		kind = k
		var g: Dictionary = GAUGE[k]
		fill = UiArt.tex(fill_name)
		var ft := UiArt.tex(g.frame)
		mouse_filter = Control.MOUSE_FILTER_IGNORE
		scale = Vector2(s, s)
		size = Vector2(length, 96)
		if ft != null:
			var sb := StyleBoxTexture.new()
			sb.texture = ft
			sb.texture_margin_left = g.cap
			sb.texture_margin_right = g.cap
			_frame = sb

	func window() -> Rect2:
		var g: Dictionary = GAUGE[kind]
		var w: Rect2 = g.window
		var tw := 1536.0 if kind == "boss" else 1024.0
		return Rect2(w.position.x, w.position.y, size.x - (tw - w.size.x), w.size.y)

	func fill_rect() -> Rect2:
		var w := window()
		return Rect2(w.position.x + fill_left, w.position.y + 2, w.size.x - fill_left, w.size.y - 4)

	func _draw() -> void:
		var w := window()
		draw_rect(w, track)
		var r := fill_rect()
		if lag > value + 0.001 and lag_fill != null:
			# 減った分は中身の右（value〜lag）だけに描く（中身の後ろに重ねると、r2 の丸い端から白磁色がのぞく）
			_bar(lag_fill, r, lag, Color.WHITE, value if fill != null else 0.0)
		if fill != null:
			_bar(fill, r, value, fill_modulate)
		if _frame != null:
			draw_style_box(_frame, Rect2(Vector2.ZERO, size))
		var div := UiArt.tex("ui_parts_gauge_boss_divider")
		for m in marks:
			var x: float = r.position.x + r.size.x * float(m)
			if div != null:
				draw_texture_rect(div, Rect2(x - 12, size.y * 0.5 - 40, 24, 80), false)
			else:
				draw_rect(Rect2(x - 2, r.position.y - 4, 4, r.size.y + 8), UiArt.PAPER)

	## 中身の絵の from〜v（0〜1）の分を、同じ割合の位置に描く
	func _bar(t: Texture2D, r: Rect2, v: float, mod: Color, from := 0.0) -> void:
		v = clampf(v, 0.0, 1.0)
		from = clampf(from, 0.0, v)
		if v - from <= 0.0:
			return
		var ts := t.get_size()
		draw_texture_rect_region(t, Rect2(r.position + Vector2(r.size.x * from, 0), Vector2(r.size.x * (v - from), r.size.y)),
			Rect2(ts.x * from, 0, ts.x * (v - from), ts.y), mod)
