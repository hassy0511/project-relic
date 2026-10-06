class_name Hud
extends CanvasLayer
## HUD（プレイ中の表示）と会話ウィンドウ。見た目は Codex の UI デザイン（W2-08、ui_hud.png・ui_dialogue.png・ui_node_memory.png）の部品
## （godot/assets/ui/。読み方は UiArt）。配置は 1920×1080 の画面の見本に合わせ、画面の大きさが変わっても端からの位置で決める。

const FACE_COLORS := {
	"ヤーナ": Color("#b5452f"), "ナゴミ": Color("#ffb23e"), "ハル": Color("#c9a46a"), "バートン": Color("#4d6a8a"),
	"トルーデ": Color("#7a5a8a"), "ニコ": Color("#3f9a8a"), "閂": Color("#7a2a1e"),
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
## ノードの記憶を取り込む会話（ui_node_memory.png の見た目：上に取り込みの進み具合、会話の枠を古い記録の色に）
const MEMORY_DIALOGUES := ["ch1.node"]
const AMBER := Color("#ffb23e")
const PAPER := Color("#f3e9d2")
## HUD の外周の余白（spec：24px）
const EDGE := 28.0
## ゲージの縮尺（元の画像 1024×96 → 画面で約 530×50）
const GAUGE_SCALE := 0.52

var device := "keyboard"
## スマホの画面の操作が出ているとき（main が設定する）。右下のボタンの弧と左下のスティックを避けて並べる
var compact := false
var _compact_now := false
var _vitals: Control
var _hint_data = ""
var _root: Control
var _hint: Label
var _hp: UiArt.Gauge
var _hp_label: Label
var _hp_text: Label
var _hp_lag := 1.0
var _hp_lag_wait := 0.0
var _we_row: Control
var _we_icon: TextureRect
var _we: UiArt.Gauge
var _heals: Label
var _spark_tile: Control
var _spark_icon: TextureRect
var _cells_box: PanelContainer
var _cells: Label
var _objective_box: PanelContainer
var _objective: Label
var _prompt_box: PanelContainer
var _prompt_key: Label
var _prompt: Label
var _reticle: Reticle
var _charge: ChargeRing
var _toast_box: PanelContainer
var _toast: Label
var _toast_time := 0.0
var _dmg: ColorRect
var _dmg_time := 0.0
var _last_cells := -1
var _cells_time := 0.0
var _boss_box: Control
var _boss: UiArt.Gauge
var _boss_name: Label
var _boss_phase: Label
var _dlg: PanelContainer
var _dlg_face: Control
var _dlg_face_frame: TextureRect
var _dlg_face_label: Label
var _dlg_face_disc: Panel
var _dlg_icon: TextureRect
var _dlg_name_box: PanelContainer
var _dlg_name: Label
var _dlg_text: Label
var _dlg_next: TextureRect
var _dlg_choices: VBoxContainer
var _dlg_choice_rows: Array = []
var _dlg_memory := false
var _mem_box: PanelContainer
var _mem: UiArt.Gauge
var _mem_pct: Label
var _sub: PanelContainer
var _sub_face: Control
var _sub_icon: TextureRect
var _sub_letter: Label
var _sub_disc: Panel
var _sub_who: Label
var _sub_text: Label
var _sub_time := 0.0
static var _face_cache := {}
var _fade: ColorRect
var _fade_time := 0.0
var _time := 0.0


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
			# 正方形に切り出す（顔の枠が正方形のため）
			var side: float = size.x * 0.84
			at.region = Rect2(o + Vector2((size.x - side) * 0.5, size.y * 0.1), Vector2(side, side))
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
		l.add_theme_font_override("font", UiArt.bold())
	return l


## 端に寄せる：右上・下中央など（anchor と伸びる向き）
static func _pin(c: Control, ax: float, ay: float, ox: float, oy: float) -> void:
	c.anchor_left = ax
	c.anchor_right = ax
	c.anchor_top = ay
	c.anchor_bottom = ay
	c.offset_left = ox
	c.offset_right = ox
	c.offset_top = oy
	c.offset_bottom = oy
	c.grow_horizontal = Control.GROW_DIRECTION_BEGIN if ax >= 1.0 else (Control.GROW_DIRECTION_BOTH if ax > 0.0 else Control.GROW_DIRECTION_END)
	c.grow_vertical = Control.GROW_DIRECTION_BEGIN if ay >= 1.0 else Control.GROW_DIRECTION_END


## ゲージを入れ物に入れる（ゲージは元の画像の画素で持ち、縮めて描くため、入れ物に縮めたあとの大きさを持たせる）
static func _gauge(kind: String, fill: String, length: float, s: float) -> Array:
	var holder := Control.new()
	holder.mouse_filter = Control.MOUSE_FILTER_IGNORE
	holder.custom_minimum_size = Vector2(length, 96) * s
	var g := UiArt.Gauge.new()
	g.setup(kind, fill, length, s)
	holder.add_child(g)
	return [holder, g]


## 顔の枠（ui_parts_face_frame）：中に顔の絵、無い人は頭文字の丸
static func _face_slot(px: float) -> Dictionary:
	var slot := Control.new()
	slot.custom_minimum_size = Vector2(px, px)
	slot.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var k := px / 256.0
	# 枠の窓（元の 256px の画像で x 36〜218、y 44〜216）
	var win := Rect2(Vector2(38, 44) * k, Vector2(180, 172) * k)
	var bg := ColorRect.new()
	bg.color = Color(0.1, 0.09, 0.08)
	bg.position = win.position
	bg.size = win.size
	slot.add_child(bg)
	var disc := Panel.new()
	disc.position = win.position + win.size * 0.1
	disc.size = win.size * 0.8
	disc.mouse_filter = Control.MOUSE_FILTER_IGNORE
	slot.add_child(disc)
	var letter := make_label("", int(px * 0.3), Color.WHITE, true)
	letter.position = win.position
	letter.size = win.size
	letter.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	letter.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	slot.add_child(letter)
	var icon := TextureRect.new()
	icon.position = win.position
	icon.size = win.size
	icon.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	icon.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
	icon.clip_contents = true
	icon.visible = false
	slot.add_child(icon)
	var frame := TextureRect.new()
	frame.texture = UiArt.tex("ui_parts_face_frame")
	frame.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	frame.size = Vector2(px, px)
	frame.mouse_filter = Control.MOUSE_FILTER_IGNORE
	slot.add_child(frame)
	return {"slot": slot, "icon": icon, "letter": letter, "disc": disc, "frame": frame}


## 顔の枠に話し手の顔（または頭文字の丸）を入れる
static func _fill_face(f: Dictionary, who: String, face: String) -> void:
	var tex := face_texture(who, face)
	f.icon.texture = tex
	f.icon.visible = tex != null
	f.letter.visible = tex == null
	f.disc.visible = tex == null
	f.letter.text = who.substr(0, 1)
	var disc := StyleBoxFlat.new()
	disc.bg_color = FACE_COLORS.get(who, Color("#777777"))
	disc.set_corner_radius_all(200)
	f.disc.add_theme_stylebox_override("panel", disc)


func _ready() -> void:
	_root = Control.new()
	_root.set_anchors_preset(Control.PRESET_FULL_RECT)
	_root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_root)
	var root := _root

	# --- 左上：HP、特殊武器とエネルギー、補修パック、主武器 ---
	var vitals := VBoxContainer.new()
	_vitals = vitals
	vitals.position = Vector2(EDGE, EDGE - 6)
	vitals.add_theme_constant_override("separation", 4)
	vitals.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.add_child(vitals)
	var hp_row := HBoxContainer.new()
	hp_row.add_theme_constant_override("separation", 8)
	vitals.add_child(hp_row)
	var hp_made := _gauge("hp", "ui_parts_gauge_hp_fill_full", 1024, GAUGE_SCALE)
	_hp = hp_made[1]
	_hp.lag_fill = UiArt.tex("ui_parts_gauge_hp_fill_damaged")
	_hp.fill_left = 64
	hp_row.add_child(hp_made[0])
	_hp_label = make_label("HP", 22, PAPER, true)
	_hp_label.position = Vector2(60 * GAUGE_SCALE + 2, 6)
	hp_made[0].add_child(_hp_label)
	_hp_text = make_label("100", 22, PAPER, true)
	_hp_text.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	hp_row.add_child(_hp_text)

	var row2 := HBoxContainer.new()
	row2.add_theme_constant_override("separation", 10)
	vitals.add_child(row2)
	_we_row = HBoxContainer.new()
	_we_row.add_theme_constant_override("separation", 4)
	row2.add_child(_we_row)
	var we_tile := _tile(UiArt.tex("icon_we_break_drill"), 44)
	_we_icon = we_tile.get_child(0)
	_we_row.add_child(we_tile)
	var we_made := _gauge("energy", "ui_parts_gauge_energy_fill", 600, GAUGE_SCALE)
	_we = we_made[1]
	we_made[0].size_flags_vertical = Control.SIZE_SHRINK_CENTER
	_we_row.add_child(we_made[0])
	var heal_box := PanelContainer.new()
	heal_box.add_theme_stylebox_override("panel", UiArt.box("name", Vector4(12, 2, 16, 2)))
	row2.add_child(heal_box)
	var heal_row := HBoxContainer.new()
	heal_row.add_theme_constant_override("separation", 6)
	heal_box.add_child(heal_row)
	heal_row.add_child(UiArt.icon_rect(UiArt.tex("icon_item_repair_small"), 40))
	_heals = make_label("2", 26, PAPER, true)
	heal_row.add_child(_heals)

	var row3 := HBoxContainer.new()
	row3.add_theme_constant_override("separation", 6)
	vitals.add_child(row3)
	_spark_tile = _tile(UiArt.spark_icon(false))
	_spark_icon = _spark_tile.get_child(0)
	row3.add_child(_spark_tile)
	row3.add_child(_tile(UiArt.tex("icon_blade")))

	# --- 右上：所持セル、その下に今の目的 ---
	_cells_box = PanelContainer.new()
	_cells_box.add_theme_stylebox_override("panel", UiArt.box("name", Vector4(14, 2, 22, 2)))
	_pin(_cells_box, 1, 0, -EDGE, EDGE - 4)
	root.add_child(_cells_box)
	var cells_row := HBoxContainer.new()
	cells_row.add_theme_constant_override("separation", 8)
	_cells_box.add_child(cells_row)
	cells_row.add_child(UiArt.icon_rect(UiArt.tex("icon_item_cell_small"), 40))
	_cells = make_label("0", 28, PAPER, true)
	_cells.custom_minimum_size = Vector2(90, 0)
	_cells.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	cells_row.add_child(_cells)

	_objective_box = PanelContainer.new()
	_objective_box.add_theme_stylebox_override("panel", UiArt.strip(0.62, Vector4(14, 8, 22, 8)))
	_pin(_objective_box, 1, 0, -EDGE, EDGE + 62)
	root.add_child(_objective_box)
	var obj_row := HBoxContainer.new()
	obj_row.add_theme_constant_override("separation", 10)
	_objective_box.add_child(obj_row)
	var obj_icon := UiArt.icon_rect(UiArt.tex("icon_map_destination"), 32)
	obj_icon.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	obj_row.add_child(obj_icon)
	_objective = make_label("", 24)
	_objective.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_objective.custom_minimum_size = Vector2(0, 0)
	obj_row.add_child(_objective)

	# --- 画面中央の下：調べる・話すの案内 ---
	_prompt_box = PanelContainer.new()
	_prompt_box.add_theme_stylebox_override("panel", UiArt.strip(0.66, Vector4(10, 6, 24, 6), true))
	_pin(_prompt_box, 0.5, 1, 0, -300)
	root.add_child(_prompt_box)
	var pr := HBoxContainer.new()
	pr.add_theme_constant_override("separation", 12)
	_prompt_box.add_child(pr)
	var key_box := PanelContainer.new()
	var kb := StyleBoxFlat.new()
	kb.bg_color = PAPER
	kb.set_corner_radius_all(18)
	kb.content_margin_left = 12
	kb.content_margin_right = 12
	key_box.add_theme_stylebox_override("panel", kb)
	pr.add_child(key_box)
	_prompt_key = make_label("", 22, Color("#2a2622"), true)
	_prompt_key.remove_theme_constant_override("outline_size")
	key_box.add_child(_prompt_key)
	_prompt = make_label("", 28, PAPER, true)
	pr.add_child(_prompt)

	_reticle = Reticle.new()
	root.add_child(_reticle)
	_charge = ChargeRing.new()
	_charge.size = Vector2(84, 84)
	_charge.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.add_child(_charge)

	# --- 上の中央：拾った物などの知らせ、その下に操作の案内 ---
	_toast_box = PanelContainer.new()
	_toast_box.add_theme_stylebox_override("panel", UiArt.strip(0.66, Vector4(28, 8, 28, 8)))
	_pin(_toast_box, 0.5, 0, 0, EDGE)
	root.add_child(_toast_box)
	_toast = make_label("", 28, PAPER, true)
	_toast.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_toast_box.add_child(_toast)

	_hint = make_label("", 26, Color("#ffe7b8"), true)
	_hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_hint.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_hint.add_theme_stylebox_override("normal", UiArt.strip(0.66, Vector4(24, 10, 24, 10), true))
	_pin(_hint, 0.5, 0, 0, 200)
	root.add_child(_hint)

	# --- ボスの体力（画面の下。名前は枠の中の左、段階の区切り 2 本） ---
	_boss_box = Control.new()
	_boss_box.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_boss_box.visible = false
	root.add_child(_boss_box)
	var boss_made := _gauge("boss", "ui_parts_gauge_boss_fill", 1536, 0.62)
	_boss = boss_made[1]
	_boss.marks = [0.33, 0.66]
	_boss_box.add_child(boss_made[0])
	_boss_name = make_label("", 26, PAPER, true)
	_boss_box.add_child(_boss_name)
	_boss_phase = make_label("", 22, AMBER, true)
	_boss_phase.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	_boss_box.add_child(_boss_phase)

	# --- 戦闘中のひと言（画面の左下。顔の小さな枠＋名前＋1 行。操作は止めない） ---
	_sub = PanelContainer.new()
	_sub.add_theme_stylebox_override("panel", UiArt.strip(0.62, Vector4(8, 6, 28, 6)))
	_sub.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_sub.visible = false
	root.add_child(_sub)
	var sub_row := HBoxContainer.new()
	sub_row.add_theme_constant_override("separation", 16)
	_sub.add_child(sub_row)
	var sf := _face_slot(104)
	_sub_face = sf.slot
	_sub_icon = sf.icon
	_sub_letter = sf.letter
	_sub_disc = sf.disc
	sub_row.add_child(_sub_face)
	var sub_body := VBoxContainer.new()
	sub_body.alignment = BoxContainer.ALIGNMENT_CENTER
	sub_row.add_child(sub_body)
	_sub_who = make_label("", 24, AMBER, true)
	sub_body.add_child(_sub_who)
	_sub_text = make_label("", 30)
	_sub_text.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_sub_text.custom_minimum_size = Vector2(620, 0)
	sub_body.add_child(_sub_text)

	_dmg = ColorRect.new()
	_dmg.color = Color(0.8, 0.1, 0.05, 0.0)
	_dmg.set_anchors_preset(Control.PRESET_FULL_RECT)
	_dmg.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.add_child(_dmg)

	# --- ノードの記憶の取り込み（右上の枠：見出し・説明・進み具合） ---
	_mem_box = PanelContainer.new()
	_mem_box.add_theme_stylebox_override("panel", UiArt.box("small", Vector4(30, 22, 30, 24)))
	_pin(_mem_box, 1, 0, -EDGE, 150)
	_mem_box.visible = false
	root.add_child(_mem_box)
	var mem_col := VBoxContainer.new()
	mem_col.add_theme_constant_override("separation", 6)
	_mem_box.add_child(mem_col)
	var mem_head := HBoxContainer.new()
	mem_head.add_theme_constant_override("separation", 14)
	mem_col.add_child(mem_head)
	mem_head.add_child(UiArt.icon_rect(UiArt.tex("icon_map_current"), 48))
	var mem_titles := VBoxContainer.new()
	mem_titles.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	mem_head.add_child(mem_titles)
	mem_titles.add_child(make_label("ノードの記憶", 32, PAPER, true))
	mem_titles.add_child(make_label("ナゴミがこの場所の記録を取り込んでいる", 20, Color("#d8c9a8")))
	_mem_pct = make_label("0%", 30, PAPER, true)
	_mem_pct.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	mem_head.add_child(_mem_pct)
	var mem_made := _gauge("hp", "ui_parts_gauge_hp_fill_full", 1100, 0.5)
	_mem = mem_made[1]
	mem_col.add_child(mem_made[0])

	# --- 会話ウィンドウ（画面の下：左に顔の枠、名前の札、本文、送りの印、右に選択肢） ---
	_dlg = PanelContainer.new()
	_dlg.add_theme_stylebox_override("panel", UiArt.box("dialogue", Vector4(26, 22, 30, 20)))
	_pin(_dlg, 0.5, 1, 0, -40)
	_dlg.custom_minimum_size = Vector2(1500, 276)
	root.add_child(_dlg)
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 26)
	_dlg.add_child(row)
	var df := _face_slot(220)
	# 入れ物に入れる（入れ物の中なら縮尺を変えられる。スマホの操作のときは小さく描く）
	_dlg_face = Control.new()
	_dlg_face.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_dlg_face.custom_minimum_size = Vector2(220, 220)
	_dlg_face.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	_dlg_face.add_child(df.slot)
	_dlg_icon = df.icon
	_dlg_face_label = df.letter
	_dlg_face_disc = df.disc
	_dlg_face_frame = df.frame
	_dlg_face.set_meta("slot", df)
	row.add_child(_dlg_face)
	var body := VBoxContainer.new()
	body.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	body.add_theme_constant_override("separation", 10)
	row.add_child(body)
	_dlg_name_box = PanelContainer.new()
	_dlg_name_box.add_theme_stylebox_override("panel", UiArt.box("name", Vector4(30, 4, 30, 4)))
	_dlg_name_box.size_flags_horizontal = Control.SIZE_SHRINK_BEGIN
	body.add_child(_dlg_name_box)
	_dlg_name = make_label("", 28, PAPER, true)
	_dlg_name.custom_minimum_size = Vector2(150, 0)
	_dlg_name.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_dlg_name_box.add_child(_dlg_name)
	_dlg_text = make_label("", 32)
	_dlg_text.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_dlg_text.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_dlg_text.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_dlg_text.add_theme_constant_override("line_spacing", 6)
	body.add_child(_dlg_text)
	_dlg_next = TextureRect.new()
	_dlg_next.texture = UiArt.tex("ui_parts_advance")
	_dlg_next.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	_dlg_next.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	_dlg_next.custom_minimum_size = Vector2(36, 36)
	_dlg_next.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	body.add_child(_dlg_next)
	_dlg_choices = VBoxContainer.new()
	_dlg_choices.add_theme_constant_override("separation", 8)
	_dlg_choices.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	_dlg_choices.custom_minimum_size = Vector2(620, 0)
	row.add_child(_dlg_choices)

	_fade = ColorRect.new()
	_fade.color = Color(0, 0, 0, 0)
	_fade.set_anchors_preset(Control.PRESET_FULL_RECT)
	_fade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.add_child(_fade)


## アイコンの小さな札（主武器・光刃）
func _tile(t: Texture2D, px := 40.0) -> PanelContainer:
	var p := PanelContainer.new()
	p.add_theme_stylebox_override("panel", UiArt.box("name", Vector4(8, 2, 8, 2)))
	p.add_child(UiArt.icon_rect(t, px))
	return p


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


## 戦闘中の掛け合いの字幕（操作を止めない。画面の左下）
func show_subtitle(who: String, text: String, seconds := 3.4) -> void:
	_sub_who.text = who
	_sub_text.text = text
	_sub_time = seconds
	_sub.visible = true
	_fill_face({"icon": _sub_icon, "letter": _sub_letter, "disc": _sub_disc}, who, "normal")
	_sub_face.visible = who != ""


func subtitle_text() -> String:
	return "%s：%s" % [_sub_who.text, _sub_text.text] if _sub.visible else ""


func show_toast(text: String) -> void:
	_toast.text = text
	_toast_time = 3.0


func flash_damage() -> void:
	_dmg_time = 0.4


## 弱点が今あいているか（解析済みの敵の、狙い時）
static func weak_open(t) -> bool:
	match String(t.kind):
		"kannuki":
			return t.core_open
		"charger", "shield":
			return t.state == "stunned"
		"floater":
			return t.state == "recover"
	return false


func sync(game: GameSim, camera: Camera3D, dt: float) -> void:
	_time += dt
	var vs := _root.size
	var p := game.player
	var ratio := clampf(p.hp / p.max_hp, 0.0, 1.0)
	# HP：減った分は少し遅れて縮む（ui_parts_gauge_hp_fill_damaged）。3 割を切ると危険の色を明滅させる
	if ratio < _hp_lag:
		_hp_lag_wait -= dt
		if _hp_lag_wait <= 0.0:
			_hp_lag = move_toward(_hp_lag, ratio, dt * 0.7)
	else:
		_hp_lag = ratio
		_hp_lag_wait = 0.45
	if ratio < _hp.value - 0.001:
		_hp_lag_wait = 0.45
	_hp.value = ratio
	_hp.lag = _hp_lag
	var danger := ratio < 0.3
	_hp.fill = UiArt.tex("ui_parts_gauge_hp_fill_danger" if danger else "ui_parts_gauge_hp_fill_full")
	# 危険の中身の絵は満タンの色とほぼ同じなので、ゲーム側で明るく脈打たせて見分ける（絵の描き直しを頼んでいる）
	var pulse := 0.5 + 0.5 * sin(_time * 9.0)
	_hp.fill_modulate = Color(1.0 + 0.9 * pulse, 1.0 + 0.25 * pulse, 1.0 + 0.2 * pulse) if danger else Color.WHITE
	_hp_label.add_theme_color_override("font_color", Color("#ff8a6a") if danger else PAPER)
	_hp.queue_redraw()
	_hp_text.text = str(ceili(p.hp))
	var has_drill := game.has_item("special.drill")
	_we_row.visible = has_drill
	_we.value = p.weapon_energy / 100.0
	_we.queue_redraw()
	_heals.text = "%d" % p.heals
	_spark_tile.visible = game.has_item("weapon.spark")
	_spark_icon.texture = UiArt.spark_icon(game.charge_type())

	var bs := game.boss_status()
	_boss_box.visible = not bs.is_empty()
	if not bs.is_empty():
		# スマホの操作のときは、左下のスティックと右下のボタンの間に収める
		var span := _bottom_span(vs)
		var bw: float = minf(1536.0, (span.y - span.x) / 0.62)
		_boss.size.x = bw
		_boss.get_parent().custom_minimum_size = Vector2(bw, 96) * 0.62
		_boss_box.position = Vector2((span.x + span.y - bw * 0.62) * 0.5, vs.y - EDGE - 96 * 0.62)
		_boss_name.text = bs.name
		_boss_name.position = Vector2(100 * 0.62, 96 * 0.62 * 0.5 - 19)
		_boss.fill_left = (_boss_name.get_minimum_size().x + 26.0) / 0.62
		_boss.value = clampf(bs.hp / bs.max_hp, 0.0, 1.0)
		_boss.fill_modulate = Color(1.3 + 0.3 * pulse, 1.05, 0.8) if bs.overheat else Color.WHITE
		_boss.queue_redraw()
		_boss_phase.text = "第 %d 段階%s" % [bs.phase, "　過熱" if bs.overheat else ""]
		_boss_phase.position = Vector2(bw * 0.62 - 300, -30)
		_boss_phase.size = Vector2(290, 30)

	if game.cells != _last_cells:
		_last_cells = game.cells
		_cells_time = 3.0
	_cells_time -= dt
	_cells.text = _comma(game.cells)
	_cells_box.modulate.a = 1.0 if _cells_time > 0.0 else 0.55
	if compact != _compact_now:
		_set_compact(compact)
	_objective.text = game.objective
	_objective.custom_minimum_size.x = minf(_objective.get_theme_font("font").get_string_size(game.objective, HORIZONTAL_ALIGNMENT_LEFT, -1, 24).x + 4.0, minf(720.0, vs.x * 0.36))
	_objective_box.visible = game.objective != "" and bs.is_empty()
	_fit(_objective_box)

	# 調べる・話すの案内
	var f = game.focus
	var btn := PadConfig.pad_short("jump") if device == "pad" else ("ジャンプ" if device == "touch" else "Space")
	var show_prompt: bool = f != null and game.story.dialogue.is_empty()
	_prompt_box.visible = show_prompt
	if show_prompt:
		_prompt_key.text = btn
		_prompt.text = f.prompt
		_fit(_prompt_box)

	# ロックオンの照準
	var t = game.lock_on.target
	if t != null:
		var c: Vector3 = t.center() + Vector3(0, t.height * 0.1, 0)
		_reticle.visible = not camera.is_position_behind(c)
		_reticle.position = camera.unproject_position(c)
		_reticle.hp = t.hp / t.max_hp
		_reticle.scanned = game.lock_on.scanned.has(t.kind)
		_reticle.scan = game.lock_on.scan_progress()
		_reticle.weak = _reticle.scanned and weak_open(t)
		_reticle.weak_text = {
			"charger": "弱点：激突後の側面", "mini": "弱点：全身", "floater": "弱点：上部の核（降下のあと）",
			"shield": "弱点：背面。盾は光刃で崩す", "kannuki": "弱点：錠前核（突きが刺さったあと・叩きつけのあと）",
		}.get(t.kind, "弱点：背面の核")
		_reticle.time = _time
		_reticle.queue_redraw()
	else:
		_reticle.visible = false

	# チャージ（主武器のチャージ型・光刃の溜め斬り）。照準のそば（画面の中央の右）
	var cfg: Dictionary = game.tuning.gun
	var gun := p.gun_charge
	var sw := p.sword_hold if p.sword_hold > 0.2 else 0.0
	if gun > 0.15:
		_charge.progress = minf(1.0, gun / cfg.chargeLv2Time)
		_charge.stage = 2 if gun >= cfg.chargeLv2Time else (1 if gun >= cfg.chargeLv1Time else 0)
	elif sw > 0.0:
		var st: float = game.tuning.sword.chargeTime
		_charge.progress = minf(1.0, sw / st)
		_charge.stage = 2 if sw >= st else 0
	_charge.visible = gun > 0.15 or sw > 0.0
	_charge.position = vs * 0.5 + Vector2(96, -70) - _charge.size * 0.5
	_charge.queue_redraw()

	# 操作の案内（会話中は隠す）
	var ht := _hint_text()
	_hint.text = ht
	_hint.custom_minimum_size.x = minf(1100.0, vs.x - 200.0)
	_hint.visible = ht != "" and game.story.dialogue.is_empty()
	_fit(_hint)

	# 会話
	var d: Dictionary = game.story.dialogue
	_dlg.visible = not d.is_empty()
	if not d.is_empty():
		_sync_dialogue(d, vs)
	else:
		_mem_box.visible = false

	_fade_time = maxf(0.0, _fade_time - dt)
	_fade.color.a = clampf(_fade_time / 0.5, 0.0, 1.0)
	_sub_time -= dt
	_sub.visible = _sub_time > 0.0
	if _sub.visible:
		var bottom := vs.y - EDGE - (96 * 0.62 + 20.0 if _boss_box.visible else 0.0)
		var span := _bottom_span(vs)
		_sub_text.custom_minimum_size.x = clampf(span.y - span.x - 170.0, 300.0, 620.0)
		_sub.reset_size()
		_sub.position = Vector2(span.x if compact else EDGE, bottom - _sub.size.y - 12.0)
	_toast_time -= dt
	_toast_box.modulate.a = clampf(_toast_time, 0.0, 1.0)
	_toast_box.visible = _toast_time > 0.0 and _toast.text != ""
	_toast_box.offset_top = EDGE
	_toast_box.offset_bottom = EDGE
	_fit(_toast_box)
	# 左上・右上の表示と重なる（狭い画面）ときは、左上の表示の下へ
	var tr := _toast_box.get_rect()
	if tr.position.x < _vitals.get_rect().end.x + 12.0 or tr.end.x > _cells_box.get_rect().position.x - 12.0:
		_toast_box.offset_top = _vitals.get_rect().end.y + 10.0
		_toast_box.offset_bottom = _toast_box.offset_top
		_fit(_toast_box)
	_dmg_time = maxf(0.0, _dmg_time - dt)
	_dmg.color.a = _dmg_time * 0.6


func _sync_dialogue(d: Dictionary, vs: Vector2) -> void:
	var text: String = d.text
	var who := String(d.who)
	var memory: bool = MEMORY_DIALOGUES.has(String(d.id))
	if memory != _dlg_memory:
		_dlg_memory = memory
		# ノードの記憶：古い記録らしく、枠を褪せた琥珀色に
		_dlg.add_theme_stylebox_override("panel", UiArt.box("dialogue", Vector4(26, 22, 30, 20), Color(1.2, 1.0, 0.72) if memory else Color.WHITE))
	_mem_box.visible = memory
	if memory and compact:
		_mem_box.offset_top = _vitals.get_rect().end.y + 10.0
		_mem_box.offset_bottom = _mem_box.offset_top
		_fit(_mem_box)
	if memory:
		var prog := float(int(d.get("index", 0)) + 1) / maxf(1.0, float(d.get("total", 1)))
		_mem.value = prog
		_mem.queue_redraw()
		_mem_pct.text = "%d%%" % int(round(prog * 100.0))
	if compact:
		# 右下のボタンの弧に掛からないよう、左に寄せて狭く
		var right := vs.x - 0.58 * vs.y
		_dlg.custom_minimum_size.x = right - EDGE
		_dlg.offset_left = EDGE - vs.x * 0.5
		_dlg.offset_right = right - vs.x * 0.5
	else:
		_dlg.custom_minimum_size.x = minf(1760.0, vs.x - 2.0 * 48.0)
		_dlg.offset_left = -_dlg.custom_minimum_size.x * 0.5
		_dlg.offset_right = _dlg.custom_minimum_size.x * 0.5
	_fit(_dlg)
	_dlg_name.text = who
	_dlg_name_box.visible = who != ""
	_dlg_text.text = text.substr(0, d.shown)
	_dlg_face.visible = who != ""
	var slot: Dictionary = _dlg_face.get_meta("slot")
	_fill_face(slot, who, String(d.get("face", "normal")))
	var done: bool = d.shown >= text.length()
	var has_choices: bool = d.has("choices")
	_dlg_next.visible = done and not has_choices
	_dlg_next.position.y += 0.0
	_dlg_next.modulate.a = 0.65 + 0.35 * sin(_time * 6.0)
	_dlg_choices.visible = has_choices and done
	# 選択肢を待つ間は、話し手の枠を「待っている人」の枠に
	_dlg_face_frame.texture = UiArt.tex("ui_parts_face_frame_wait" if has_choices and done else "ui_parts_face_frame")
	if has_choices:
		_sync_choices(d.choices, int(d.sel))


## 選択肢の札（ui_parts_panel_choice）。選んでいる札は煉瓦色＋カーソル
func _sync_choices(choices: Array, sel: int) -> void:
	while _dlg_choice_rows.size() < choices.size():
		var p := PanelContainer.new()
		var r := HBoxContainer.new()
		r.add_theme_constant_override("separation", 10)
		p.add_child(r)
		var cur := TextureRect.new()
		cur.texture = UiArt.tex("ui_parts_cursor")
		cur.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		cur.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		cur.custom_minimum_size = Vector2(30, 30)
		r.add_child(cur)
		var l := make_label("", 28)
		r.add_child(l)
		_dlg_choices.add_child(p)
		_dlg_choice_rows.append([p, cur, l])
	for i in _dlg_choice_rows.size():
		var it: Array = _dlg_choice_rows[i]
		it[0].visible = i < choices.size()
		if i >= choices.size():
			continue
		var on := i == sel
		it[0].add_theme_stylebox_override("panel", UiArt.box("button_focus" if on else "choice", Vector4(18, 10, 24, 10)))
		it[1].modulate.a = 1.0 if on else 0.0
		it[2].text = String(choices[i])


## 画面の下の段で使える左右の範囲（x 始め, x 終わり）。スマホの操作のときはスティックとボタンの弧を避ける
func _bottom_span(vs: Vector2) -> Vector2:
	if compact:
		return Vector2(0.47 * vs.y, vs.x - 0.6 * vs.y)
	return Vector2(EDGE + 20.0, vs.x - EDGE - 20.0)


## スマホの操作の配置に切り替える（目的は 1 行に、会話の顔と選択肢は小さく、記憶の枠は上の中央へ）
func _set_compact(on: bool) -> void:
	_compact_now = on
	_objective.autowrap_mode = TextServer.AUTOWRAP_OFF if on else TextServer.AUTOWRAP_WORD_SMART
	_objective.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS if on else TextServer.OVERRUN_NO_TRIMMING
	var k := 0.72 if on else 1.0
	var slot: Dictionary = _dlg_face.get_meta("slot")
	slot.slot.scale = Vector2(k, k)
	_dlg_face.custom_minimum_size = Vector2(220, 220) * k
	_dlg_choices.custom_minimum_size.x = 400.0 if on else 620.0
	if on:
		_pin(_mem_box, 0, 0, EDGE, 160)
	else:
		_pin(_mem_box, 1, 0, -EDGE, 150)


## 中身に合わせた大きさにする（端に寄せた向きを保つ：右寄せは右端、中央は中央を動かさない）
static func _fit(c: Control) -> void:
	var m := c.get_combined_minimum_size()
	match c.grow_horizontal:
		Control.GROW_DIRECTION_BEGIN:
			c.offset_left = c.offset_right - m.x
		Control.GROW_DIRECTION_END:
			c.offset_right = c.offset_left + m.x
		_:
			var mid := (c.offset_left + c.offset_right) * 0.5
			c.offset_left = mid - m.x * 0.5
			c.offset_right = mid + m.x * 0.5
	match c.grow_vertical:
		Control.GROW_DIRECTION_BEGIN:
			c.offset_top = c.offset_bottom - m.y
		_:
			c.offset_bottom = c.offset_top + m.y


static func _comma(n: int) -> String:
	var s := str(absi(n))
	var out := ""
	while s.length() > 3:
		out = "," + s.substr(s.length() - 3) + out
		s = s.substr(0, s.length() - 3)
	return ("-" if n < 0 else "") + s + out


## ロックオンの照準（ui_parts_lockon_*）：解析中（ナゴミの解析の進み）・通常・弱点があいているとき。頭上に敵の体力
class Reticle:
	extends Control
	var hp := 1.0
	var scan := 0.0
	var scanned := false
	var weak := false
	var weak_text := ""
	var time := 0.0

	func _draw() -> void:
		var amber := UiArt.AMBER
		var font := get_theme_default_font()
		var part := "ui_parts_lockon_weakpoint" if weak else ("ui_parts_lockon_normal" if scanned else "ui_parts_lockon_analyzing")
		var s := 112.0 if not scanned else (118.0 + 6.0 * sin(time * 10.0) if weak else 100.0)
		var t := UiArt.tex(part)
		if t != null:
			draw_texture_rect(t, Rect2(-s * 0.5, -s * 0.5, s, s), false)
		else:
			draw_arc(Vector2.ZERO, 34, 0, TAU, 48, Color(amber, 0.9), 3.0, true)
		# 敵の体力（照準の上の小さなゲージ。枠と中身はプレイヤーの HP と同じ部品を小さく）
		var fr := UiArt.tex("ui_parts_gauge_hp_frame")
		var fl := UiArt.tex("ui_parts_gauge_hp_fill_full")
		var bar := Rect2(-66, -s * 0.5 - 30, 132, 14)
		if fl != null and fr != null:
			draw_rect(bar.grow(-2), Color(0.05, 0.04, 0.04, 0.85))
			var inner := Rect2(bar.position + Vector2(8, 3.5), Vector2(116 * clampf(hp, 0.0, 1.0), 7))
			draw_texture_rect_region(fl, inner, Rect2(0, 0, 960 * clampf(hp, 0.0, 1.0), 36))
			draw_texture_rect(fr, bar, false)
		var vw := get_viewport_rect().size.x
		if scanned:
			if weak_text != "":
				var w := font.get_string_size(weak_text, HORIZONTAL_ALIGNMENT_LEFT, -1, 22).x
				var pos := Vector2(s * 0.5 + 10, 8)
				# 画面の右端からはみ出すなら照準の左に
				if position.x + pos.x + w + 16.0 > vw - 16.0:
					pos.x = -s * 0.5 - 10.0 - w
				draw_rect(Rect2(pos + Vector2(-8, -24), Vector2(w + 16, 34)), Color(0.06, 0.05, 0.05, 0.7))
				draw_string(font, pos, weak_text, HORIZONTAL_ALIGNMENT_LEFT, -1, 22, UiArt.PAPER if not weak else amber)
		else:
			# 解析の進み（絵の弧は固定なので、進み具合はゲーム側の平らな色の弧で仮に出す。輪と中身の絵を頼んでいる）
			draw_arc(Vector2.ZERO, s * 0.5 + 6, -PI / 2, -PI / 2 + TAU, 48, Color(0, 0, 0, 0.45), 5.0, true)
			draw_arc(Vector2.ZERO, s * 0.5 + 6, -PI / 2, -PI / 2 + TAU * scan, 48, amber, 5.0, true)
			var label := "解析中 %d%%" % int(scan * 100.0)
			var w := font.get_string_size(label, HORIZONTAL_ALIGNMENT_LEFT, -1, 20).x
			var pos := Vector2(s * 0.5 + 14, 8)
			if position.x + pos.x + w + 16.0 > vw - 16.0:
				pos.x = -s * 0.5 - 14.0 - w
			draw_rect(Rect2(pos + Vector2(-8, -22), Vector2(w + 16, 30)), Color(0.06, 0.05, 0.05, 0.7))
			draw_string(font, pos, label, HORIZONTAL_ALIGNMENT_LEFT, -1, 20, amber)


## チャージの溜まり具合：1 段目（半円）・2 段目（輪）の絵。途中の進み具合は、絵が枠と中身に分かれていないので平らな色の弧で仮に出す
class ChargeRing:
	extends Control
	var progress := 0.0
	var stage := 0

	func _draw() -> void:
		var c := size * 0.5
		var r := size.x * 0.4
		draw_arc(c, r, 0, TAU, 48, Color(0.05, 0.04, 0.04, 0.55), size.x * 0.11, true)
		draw_arc(c, r, -PI / 2, -PI / 2 + TAU * progress, 48, Color(UiArt.AMBER, 0.9), size.x * 0.09, true)
		var part := "ui_parts_gauge_charge_stage2" if stage >= 2 else ("ui_parts_gauge_charge_stage1" if stage == 1 else "")
		if part != "":
			var t := UiArt.tex(part)
			if t != null:
				draw_texture_rect(t, Rect2(Vector2.ZERO, size), false)
