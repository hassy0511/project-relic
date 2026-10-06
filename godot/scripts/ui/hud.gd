class_name Hud
extends CanvasLayer
## HUD（プレイ中の表示）と会話ウィンドウ。見た目は仮。Codex の UI デザイン（W2-08）が届いたら差し替える。

const FACE_COLORS := {
	"ヤーナ": Color("#b5452f"), "ナゴミ": Color("#ffb23e"), "ハル": Color("#c9a46a"), "バートン": Color("#4d6a8a"),
	"トルーデ": Color("#7a5a8a"), "ニコ": Color("#3f9a8a"),
}
## 顔のアイコン：モデルに貼る顔の絵（2×2 の表情の並び）から、顔の部分を切り出して使う（絵が無い人は頭文字の丸）
const FACE_ATLAS := {
	"ハル": "res://assets/models/haru_r_haru_face_base.png",
	"ヤーナ": "res://assets/models/yana_yana_face_base.png",
	"バートン": "res://assets/models/burton_burton_face_base.png",
}
## 表情 → 並びの番号（0 左上 通常、1 右上 笑い、2 左下 驚き、3 右下 険しい）
const FACE_CELL := {
	"normal": 0, "analyzing": 0, "laugh": 1, "smile": 1, "smirk": 1, "smug": 1,
	"surprised": 2, "warning": 2, "angry": 3, "serious": 3, "sad": 3,
}
const AMBER := Color("#ffb23e")
const PAPER := Color("#f3e9d2")

var device := "keyboard"
var _hint_data = ""
var _hint: Label
var _hp_fill: ColorRect
var _hp_text: Label
var _we_fill: ColorRect
var _we_name: Label
var _heals: Label
var _cells: Label
var _objective: Label
var _prompt: Label
var _reticle: Reticle
var _charge: ProgressBar
var _toast: Label
var _toast_time := 0.0
var _dmg: ColorRect
var _dmg_time := 0.0
var _last_cells := -1
var _cells_time := 0.0
var _boss_box: Control
var _boss_name: Label
var _boss_fill: ColorRect
var _boss_phase: Label
var _dlg: PanelContainer
var _dlg_face: Panel
var _dlg_face_label: Label
var _dlg_icon: TextureRect
var _sub: PanelContainer
var _sub_who: Label
var _sub_text: Label
var _sub_time := 0.0
static var _face_cache := {}
var _dlg_name: Label
var _dlg_text: Label
var _dlg_next: Label
var _dlg_choices: Label
var _fade: ColorRect
var _fade_time := 0.0


static func panel_style(bg: Color = Color(0.08, 0.06, 0.05, 0.72), radius: int = 8) -> StyleBoxFlat:
	var s := StyleBoxFlat.new()
	s.bg_color = bg
	s.set_corner_radius_all(radius)
	s.content_margin_left = 16
	s.content_margin_right = 16
	s.content_margin_top = 10
	s.content_margin_bottom = 10
	return s


## 顔のアイコン用の絵（無ければ null）。who：話し手、face：表情の名前
static func face_texture(who: String, face: String) -> Texture2D:
	if not FACE_ATLAS.has(who):
		return null
	var cell := int(FACE_CELL.get(face, 0))
	var key := "%s:%d" % [who, cell]
	if not _face_cache.has(key):
		var tex = load(FACE_ATLAS[who]) if ResourceLoader.exists(FACE_ATLAS[who]) else null
		if tex == null:
			_face_cache[key] = null
		else:
			var size: Vector2 = tex.get_size() * 0.5
			var at := AtlasTexture.new()
			at.atlas = tex
			var o := Vector2(cell % 2, cell / 2) * size
			at.region = Rect2(o + size * Vector2(0.08, 0.13), size * Vector2(0.86, 0.69))
			_face_cache[key] = at
	return _face_cache[key]


static func make_label(text: String, size: int, color: Color = PAPER, bold: bool = false) -> Label:
	var l := Label.new()
	l.text = text
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", color)
	l.add_theme_color_override("font_outline_color", Color(0, 0, 0, 0.6))
	l.add_theme_constant_override("outline_size", 4)
	if bold:
		l.add_theme_font_override("font", load("res://assets/fonts/NotoSansJP-Bold.otf"))
	return l


func _bar(parent: Control, w: float, color: Color) -> ColorRect:
	var bg := ColorRect.new()
	bg.color = Color(0, 0, 0, 0.55)
	bg.custom_minimum_size = Vector2(w, 16)
	parent.add_child(bg)
	var fill := ColorRect.new()
	fill.color = color
	fill.size = Vector2(w, 16)
	bg.add_child(fill)
	return fill


func _ready() -> void:
	var root := Control.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(root)

	var vitals := VBoxContainer.new()
	vitals.position = Vector2(32, 28)
	root.add_child(vitals)
	var hp_row := HBoxContainer.new()
	hp_row.add_theme_constant_override("separation", 12)
	vitals.add_child(hp_row)
	hp_row.add_child(make_label("HP", 22, PAPER, true))
	_hp_fill = _bar(hp_row, 320, Color("#f2b45a"))
	_hp_text = make_label("100", 22)
	hp_row.add_child(_hp_text)
	var we_row := HBoxContainer.new()
	we_row.add_theme_constant_override("separation", 12)
	vitals.add_child(we_row)
	_we_name = make_label("———", 18)
	we_row.add_child(_we_name)
	_we_fill = _bar(we_row, 200, Color("#5ad1ff"))
	_heals = make_label("補修パック ×2", 16)
	vitals.add_child(_heals)

	_cells = make_label("セル 0", 26, AMBER, true)
	_cells.set_anchors_and_offsets_preset(Control.PRESET_TOP_RIGHT)
	_cells.position += Vector2(-200, 28)
	_cells.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	_cells.custom_minimum_size = Vector2(170, 0)
	root.add_child(_cells)
	_objective = make_label("", 20)
	_objective.set_anchors_and_offsets_preset(Control.PRESET_TOP_RIGHT)
	_objective.position += Vector2(-760, 70)
	_objective.custom_minimum_size = Vector2(730, 0)
	_objective.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	_objective.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_objective.add_theme_stylebox_override("normal", panel_style(Color(0.05, 0.04, 0.03, 0.55), 8))
	root.add_child(_objective)

	_prompt = make_label("", 26, PAPER, true)
	_prompt.set_anchors_and_offsets_preset(Control.PRESET_CENTER_BOTTOM)
	_prompt.position += Vector2(-300, -330)
	_prompt.custom_minimum_size = Vector2(600, 0)
	_prompt.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	root.add_child(_prompt)

	_reticle = Reticle.new()
	root.add_child(_reticle)

	_charge = ProgressBar.new()
	_charge.show_percentage = false
	_charge.custom_minimum_size = Vector2(240, 10)
	_charge.set_anchors_and_offsets_preset(Control.PRESET_CENTER)
	_charge.position += Vector2(-120, 120)
	var fill := StyleBoxFlat.new()
	fill.bg_color = AMBER
	_charge.add_theme_stylebox_override("fill", fill)
	root.add_child(_charge)

	_hint = make_label("", 24, Color("#ffe7b8"), true)
	_hint.set_anchors_and_offsets_preset(Control.PRESET_CENTER_TOP)
	_hint.position += Vector2(-520, 215)
	_hint.custom_minimum_size = Vector2(1040, 0)
	_hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_hint.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_hint.add_theme_stylebox_override("normal", panel_style(Color(0.05, 0.04, 0.03, 0.6), 8))
	root.add_child(_hint)

	_toast = make_label("", 26, PAPER, true)
	_toast.set_anchors_and_offsets_preset(Control.PRESET_CENTER_TOP)
	_toast.position += Vector2(-500, 150)
	_toast.custom_minimum_size = Vector2(1000, 0)
	_toast.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	root.add_child(_toast)

	_sub = PanelContainer.new()
	_sub.add_theme_stylebox_override("panel", panel_style(Color(0.04, 0.03, 0.03, 0.78), 8))
	_sub.set_anchors_and_offsets_preset(Control.PRESET_CENTER_BOTTOM)
	_sub.position += Vector2(-600, -190)
	_sub.custom_minimum_size = Vector2(1200, 0)
	_sub.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_sub.visible = false
	root.add_child(_sub)
	var sub_row := HBoxContainer.new()
	sub_row.add_theme_constant_override("separation", 18)
	_sub.add_child(sub_row)
	_sub_who = make_label("", 28, Color("#ff9a5a"), true)
	sub_row.add_child(_sub_who)
	_sub_text = make_label("", 30)
	_sub_text.autowrap_mode = TextServer.AUTOWRAP_ARBITRARY
	_sub_text.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	sub_row.add_child(_sub_text)

	_dmg = ColorRect.new()
	_dmg.color = Color(0.8, 0.1, 0.05, 0.0)
	_dmg.set_anchors_preset(Control.PRESET_FULL_RECT)
	_dmg.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.add_child(_dmg)
	_fade = ColorRect.new()
	_fade.color = Color(0, 0, 0, 0)
	_fade.set_anchors_preset(Control.PRESET_FULL_RECT)
	_fade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.add_child(_fade)

	# ボスの体力バー（画面の上の真ん中。段階の境に印）
	_boss_box = Control.new()
	_boss_box.position = Vector2(460, 30)
	_boss_box.visible = false
	root.add_child(_boss_box)
	_boss_name = make_label("", 26, PAPER, true)
	_boss_box.add_child(_boss_name)
	var boss_bg := ColorRect.new()
	boss_bg.color = Color(0, 0, 0, 0.6)
	boss_bg.position = Vector2(0, 38)
	boss_bg.size = Vector2(1000, 22)
	_boss_box.add_child(boss_bg)
	_boss_fill = ColorRect.new()
	_boss_fill.color = Color("#d9503a")
	_boss_fill.size = Vector2(1000, 22)
	boss_bg.add_child(_boss_fill)
	for frac in [0.66, 0.33]:
		var notch := ColorRect.new()
		notch.color = Color(1, 1, 1, 0.8)
		notch.position = Vector2(1000.0 * frac - 1.0, -3)
		notch.size = Vector2(3, 28)
		boss_bg.add_child(notch)
	_boss_phase = make_label("", 22, AMBER)
	_boss_phase.position = Vector2(780, 0)
	_boss_phase.size = Vector2(220, 30)
	_boss_phase.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	_boss_box.add_child(_boss_phase)

	# 会話ウィンドウ
	_dlg = PanelContainer.new()
	_dlg.add_theme_stylebox_override("panel", panel_style(Color(0.1, 0.08, 0.06, 0.88), 12))
	_dlg.set_anchors_and_offsets_preset(Control.PRESET_CENTER_BOTTOM)
	_dlg.position += Vector2(-640, -250)
	_dlg.custom_minimum_size = Vector2(1280, 190)
	root.add_child(_dlg)
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 24)
	_dlg.add_child(row)
	_dlg_face = Panel.new()
	_dlg_face.custom_minimum_size = Vector2(150, 120)
	_dlg_face.clip_contents = true
	row.add_child(_dlg_face)
	_dlg_icon = TextureRect.new()
	_dlg_icon.set_anchors_preset(Control.PRESET_FULL_RECT)
	_dlg_icon.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	_dlg_icon.stretch_mode = TextureRect.STRETCH_SCALE
	_dlg_icon.visible = false
	_dlg_face_label = make_label("", 56, Color.WHITE, true)
	_dlg_face_label.set_anchors_preset(Control.PRESET_FULL_RECT)
	_dlg_face_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_dlg_face_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	_dlg_face.add_child(_dlg_face_label)
	_dlg_face.add_child(_dlg_icon)
	var body := VBoxContainer.new()
	body.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	row.add_child(body)
	_dlg_name = make_label("", 26, AMBER, true)
	body.add_child(_dlg_name)
	_dlg_text = make_label("", 28)
	_dlg_text.autowrap_mode = TextServer.AUTOWRAP_ARBITRARY
	_dlg_text.custom_minimum_size = Vector2(1060, 0)
	body.add_child(_dlg_text)
	_dlg_choices = make_label("", 26, Color("#fff3b0"))
	body.add_child(_dlg_choices)
	_dlg_next = make_label("▼", 22, AMBER)
	_dlg_next.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	body.add_child(_dlg_next)


## 画面を暗くしてから明るくする（部屋の移動）
func fade_in(seconds := 0.5) -> void:
	_fade_time = seconds


## 操作の案内（消すまで出し続ける）。hint：文字列、または { kb, pad, touch }。"" で消す
func set_hint(hint) -> void:
	_hint_data = hint


func _hint_text() -> String:
	if _hint_data is Dictionary:
		var d: Dictionary = _hint_data
		var key := "kb" if device == "keyboard" else device
		return expand_hint(String(d.get(key, d.get("kb", ""))), device)
	return expand_hint(String(_hint_data), device)


## 案内の文の {jump} {fire} などを、いまの割り当てのボタン名（パッド）／キー名に置き換える
static func expand_hint(text: String, dev: String) -> String:
	if not text.contains("{"):
		return text
	for a in PadConfig.ACTIONS:
		var id: String = a[0]
		text = text.replace("{%s}" % id, PadConfig.pad_short(id) if dev == "pad" else PadConfig.keys_text(id).get_slice(" / ", 0))
	return text


## 戦闘中の掛け合いの字幕（操作を止めない。画面の下の 1 行）
func show_subtitle(who: String, text: String, seconds := 3.4) -> void:
	_sub_who.text = who
	_sub_text.text = text
	_sub_time = seconds
	_sub.visible = true


func subtitle_text() -> String:
	return "%s：%s" % [_sub_who.text, _sub_text.text] if _sub.visible else ""


func show_toast(text: String) -> void:
	_toast.text = text
	_toast_time = 3.0


func flash_damage() -> void:
	_dmg_time = 0.4


func sync(game: GameSim, camera: Camera3D, dt: float) -> void:
	var p := game.player
	_hp_fill.size.x = 320.0 * p.hp / p.max_hp
	_hp_fill.color = Color("#e5533a") if p.hp / p.max_hp < 0.3 else Color("#f2b45a")
	_hp_text.text = str(ceili(p.hp))
	var bs := game.boss_status()
	_boss_box.visible = not bs.is_empty()
	if not bs.is_empty():
		_boss_name.text = bs.name
		_boss_fill.size.x = 1000.0 * clampf(bs.hp / bs.max_hp, 0.0, 1.0)
		_boss_fill.color = Color("#ff7a3a") if bs.overheat else Color("#d9503a")
		_boss_phase.text = "第 %d 段階%s" % [bs.phase, "　過熱" if bs.overheat else ""]
	var has_drill := game.has_item("special.drill")
	_we_name.text = "ドリル" if has_drill else "———"
	_we_fill.size.x = 200.0 * p.weapon_energy / 100.0 if has_drill else 0.0
	_heals.text = "補修パック ×%d" % p.heals

	if game.cells != _last_cells:
		_last_cells = game.cells
		_cells_time = 3.0
	_cells_time -= dt
	_cells.text = "セル %d" % game.cells
	_cells.modulate.a = 1.0 if _cells_time > 0.0 else 0.4
	_objective.text = "目的：%s" % game.objective if game.objective != "" else ""
	_objective.visible = game.objective != "" and bs.is_empty()

	# 調べる・話すの案内
	var f = game.focus
	var btn := PadConfig.pad_short("jump") if device == "pad" else ("ジャンプ" if device == "touch" else "Space")
	_prompt.text = "[%s] %s" % [btn, f.prompt] if f != null and game.story.dialogue.is_empty() else ""

	# ロックオンの照準
	var t = game.lock_on.target
	if t != null:
		var c: Vector3 = t.center() + Vector3(0, t.height * 0.1, 0)
		_reticle.visible = not camera.is_position_behind(c)
		_reticle.position = camera.unproject_position(c)
		_reticle.hp = t.hp / t.max_hp
		_reticle.scanned = game.lock_on.scanned.has(t.kind)
		_reticle.scan = game.lock_on.scan_progress()
		_reticle.weak_text = {
			"charger": "弱点：激突後の側面", "mini": "弱点：全身", "floater": "弱点：上部の核（降下のあと）",
			"shield": "弱点：背面。盾は光刃で崩す", "kannuki": "弱点：錠前核（突きが刺さったあと・叩きつけのあと）",
		}.get(t.kind, "弱点：背面の核")
		_reticle.queue_redraw()
	else:
		_reticle.visible = false

	# チャージ
	var ch := p.gun_charge
	_charge.visible = ch > 0.15
	var cfg: Dictionary = game.tuning.gun
	_charge.value = minf(1.0, ch / cfg.chargeLv2Time) * 100.0

	# 操作の案内（会話中は隠す）
	var ht := _hint_text()
	_hint.text = ht
	_hint.visible = ht != "" and game.story.dialogue.is_empty()

	# 会話
	var d: Dictionary = game.story.dialogue
	_dlg.visible = not d.is_empty()
	if not d.is_empty():
		var text: String = d.text
		_dlg_name.text = d.who
		_dlg_text.text = text.substr(0, d.shown)
		var icon := face_texture(String(d.who), String(d.get("face", "normal")))
		_dlg_icon.texture = icon
		_dlg_icon.visible = icon != null
		_dlg_face_label.visible = icon == null
		_dlg_face_label.text = String(d.who).substr(0, 1)
		_dlg_face.add_theme_stylebox_override("panel", panel_style(FACE_COLORS.get(d.who, Color("#777777")), 12 if icon != null else 60))
		_dlg_next.visible = d.shown >= text.length() and not d.has("choices")
		_dlg_choices.visible = d.has("choices") and d.shown >= text.length()
		if d.has("choices"):
			var lines := []
			for i in d.choices.size():
				lines.append("%s %s" % ["▶" if i == d.sel else "　", d.choices[i]])
			_dlg_choices.text = "\n".join(lines)

	_fade_time = maxf(0.0, _fade_time - dt)
	_fade.color.a = clampf(_fade_time / 0.5, 0.0, 1.0)
	_sub_time -= dt
	_sub.visible = _sub_time > 0.0
	_toast_time -= dt
	_toast.modulate.a = clampf(_toast_time, 0.0, 1.0)
	_dmg_time = maxf(0.0, _dmg_time - dt)
	_dmg.color.a = _dmg_time * 0.6


## ロックオンの照準：輪と体力の弧、解析の進み具合、弱点の表示
class Reticle:
	extends Control
	var hp := 1.0
	var scan := 0.0
	var scanned := false
	var weak_text := ""

	func _draw() -> void:
		var amber := Color("#ffb23e")
		draw_arc(Vector2.ZERO, 34, 0, TAU, 48, Color(amber, 0.9), 3.0, true)
		draw_arc(Vector2.ZERO, 42, -PI / 2, -PI / 2 + TAU * hp, 48, Color("#ff5a2a"), 4.0, true)
		for i in 4:
			var a := i * PI / 2 + PI / 4
			draw_line(Vector2(cos(a), sin(a)) * 22, Vector2(cos(a), sin(a)) * 30, amber, 3.0, true)
		var font := get_theme_default_font()
		if scanned:
			draw_string(font, Vector2(52, 6), weak_text, HORIZONTAL_ALIGNMENT_LEFT, -1, 20, Color("#fff3b0"))
		else:
			draw_rect(Rect2(52, -4, 90, 6), Color(0, 0, 0, 0.5))
			draw_rect(Rect2(52, -4, 90 * scan, 6), amber)
			draw_string(font, Vector2(52, 22), "解析中", HORIZONTAL_ALIGNMENT_LEFT, -1, 16, amber)
