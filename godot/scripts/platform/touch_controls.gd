class_name TouchControls
extends CanvasLayer
## スマホ・タブレットでの操作（開発中の確認用。本番はキーボード＋マウスとゲームパッドが前提）。
## 画面の左半分：触れた所にスティックが出て、動かす方へ移動。右半分：なぞってカメラを回す。
## 右下のボタン：ジャンプ・ダッシュ・撃つ・斬る・特殊・回復。ロックオンは押すたびに入り切り
## （ロックオン中に右半分を左右に払うと対象の切り替え）。上のボタン：ポーズ・カメラを背後へ。
## 状態は InputSource が毎刻み読み取って InputFrame に混ぜる。

const STICK_RADIUS := 120.0
const LOOK_SENS := 0.006
const FLICK := 90.0
const AMBER := Color("#ffb23e")

## ボタン：名前、表示、中心（画面の右下・右上からの位置。単位は画面の高さに対する割合）、半径（同）。
## 絵は半径の TEX_SCALE 倍の大きさで描き、見える輪（金の縁の外まで）はその DISC 倍。
## 半径は 0.07 以上：高さ 360px のスマホで見える輪が直径 49px（spec：タッチ可能領域 48px 以上。844×390・667×375 では 51〜53px）。
## 並びは spec（ui_hud_touch.png）を元にした前の配置のまま、大きくした分だけ少し外へ広げた（2026-10-18。前は回復・ポーズ・背後が実寸約 36px）
const BUTTONS := [
	["jump", "ジャンプ\n調べる", Vector2(-0.13, -0.155), 0.092],
	["fire", "撃つ", Vector2(-0.33, -0.13), 0.08],
	["sword", "斬る", Vector2(-0.28, -0.335), 0.076],
	["dash", "ダッシュ", Vector2(-0.095, -0.375), 0.07],
	["special", "特殊", Vector2(-0.47, -0.29), 0.07],
	["lock_on", "ロック", Vector2(-0.50, -0.105), 0.07],
	["heal", "回復", Vector2(-0.115, -0.55), 0.07],
]
## 上の段（右上の「目的」の表示の下）
const TOP_BUTTONS := [
	["pause", "ポーズ", Vector2(-0.09, 0.28), 0.07],
	["camera_reset", "背後", Vector2(-0.255, 0.28), 0.07],
]
## ボタンの絵（256px）を描く大きさ（半径の何倍か）と、その中で見える輪（金の縁の外まで。ui_parts_touch_button_* の 222/256）
const TEX_SCALE := 2.25
const DISC := 222.0 / 256.0
## 押せる範囲：絵の半径の HIT_SCALE 倍。下限は画面の高さに対する割合で、360px の高さで直径 48px（spec：タッチ可能領域 48px 以上）。
## 隣どうしの範囲は重ならない（test_touch で確かめる）
const HIT_SCALE := 1.1
const MIN_HIT := 24.0 / 360.0
## 実寸の決まり（spec）：ボタンの見える輪・押せる範囲は 48px 以上（px はブラウザの CSS の px。スマホの実寸の目安）
const MIN_REAL_PX := 48.0
## 指を置いて、ほとんど動かさずに離したら「タップ」（会話を送る・選択肢を選ぶ）。動いてよい距離（画面の高さに対する割合）
const TAP_SLOP := 0.04

signal activated

var active := false
## ロックオンの入り切り（押すたびに切り替え）
var lock_toggled := false
var move := Vector2.ZERO
## 触れる前のスティックの案内を出すか（会話中は隠す。main が設定する）
var stick_hint := true
## まだ使えないボタン（適合の前のダッシュ・斬る・ロック。main が毎刻み設定する）。描かず、押せない
var unavailable: Array = []
## 会話の窓のタップの行き先を調べる（main が Hud.dialogue_tap_at を渡す）：位置 → 選択肢の番号、-1 送る（窓）、-2 なし
var tap_probe := Callable()

var _draw: Control
var _held := {}          # ボタン名 → 押している指の番号
var _pressed_once := {}  # この刻みまでに押された（短く押して離しても取りこぼさない）
var _one_shot := {}
var _stick_finger := -1
var _stick_origin := Vector2.ZERO
var _stick_pos := Vector2.ZERO
var _look_finger := -1
var _look := Vector2.ZERO
var _flick := 0.0
var _switch := 0
## 会話の窓・選択肢に置いた指（離したときにタップかどうか決める）
var _tap_finger := -1
var _tap_from := Vector2.ZERO
var _tap_target := -2
## 取り出していないタップ（-1 送る、0 以上 選んだ選択肢、-2 なし）
var _tap := -2


func _ready() -> void:
	layer = 5
	_draw = Control.new()
	_draw.set_anchors_preset(Control.PRESET_FULL_RECT)
	_draw.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_draw.draw.connect(_on_draw)
	add_child(_draw)
	visible = false


## スマホで開いたとき、または最初に画面に触れたときに有効にする
func activate() -> void:
	if active:
		return
	active = true
	activated.emit()
	# 画面に触れると、マウスの左・右クリックとしても届く（メニューのボタンを押せるように）。
	# そのままだと触れるたびに撃ってしまうので、マウスのボタンの割り当てを外す
	for a in ["fire", "lock_on", "camera_reset"]:
		for e in InputMap.action_get_events(a):
			if e is InputEventMouseButton:
				InputMap.action_erase_event(a, e)


func set_shown(on: bool) -> void:
	visible = active and on
	_draw.queue_redraw()
	if not visible:
		_release_all()


func _release_all() -> void:
	_held.clear()
	_stick_finger = -1
	_look_finger = -1
	_tap_finger = -1
	move = Vector2.ZERO


func _input(event: InputEvent) -> void:
	if event is InputEventScreenTouch and not active:
		activate()
	if not visible:
		return
	if event is InputEventScreenTouch:
		var t := event as InputEventScreenTouch
		if t.pressed:
			_touch_down(t.index, t.position)
		else:
			_touch_up(t.index, t.position)
		_draw.queue_redraw()
		get_viewport().set_input_as_handled()
	elif event is InputEventScreenDrag:
		var d := event as InputEventScreenDrag
		if d.index == _tap_finger and d.position.distance_to(_tap_from) > _tap_slop():
			_tap_finger = -1
		if d.index == _stick_finger:
			_stick_pos = d.position
			var v := _stick_pos - _stick_origin
			if v.length() > STICK_RADIUS:
				v = v.normalized() * STICK_RADIUS
			move = Vector2(v.x, -v.y) / STICK_RADIUS
			_draw.queue_redraw()
		elif d.index == _look_finger:
			_look += d.relative
			if lock_toggled:
				_flick += d.relative.x
				if absf(_flick) > FLICK:
					_switch = 1 if _flick > 0.0 else -1
					_flick = 0.0
		get_viewport().set_input_as_handled()


func _touch_down(index: int, pos: Vector2) -> void:
	var b := _button_at(pos)
	if b != "":
		if b == "lock_on":
			lock_toggled = not lock_toggled
		elif b == "pause" or b == "camera_reset":
			_one_shot[b] = true
		else:
			_held[b] = index
			_pressed_once[b] = true
		return
	# 会話の窓・選択肢の札に触れた：動かさずに離したらタップ（_touch_up）。スティック・カメラの指としても今までどおり扱う
	# （会話中のスティックの上下は選択肢のカーソル）
	if tap_probe.is_valid() and _tap_finger < 0:
		var target: int = tap_probe.call(pos)
		if target != -2:
			_tap_finger = index
			_tap_from = pos
			_tap_target = target
	var size := _draw.get_viewport_rect().size
	if pos.x < size.x * 0.45 and _stick_finger < 0:
		_stick_finger = index
		_stick_origin = pos
		_stick_pos = pos
		move = Vector2.ZERO
	elif _look_finger < 0:
		_look_finger = index
		_flick = 0.0


func _touch_up(index: int, pos: Vector2) -> void:
	if index == _tap_finger:
		if pos.distance_to(_tap_from) <= _tap_slop():
			_tap = _tap_target
		_tap_finger = -1
	for b in _held.keys():
		if _held[b] == index:
			_held.erase(b)
	if index == _stick_finger:
		_stick_finger = -1
		move = Vector2.ZERO
	if index == _look_finger:
		_look_finger = -1


func _layout(list: Array) -> Array:
	return layout_for(list, _draw.get_viewport_rect().size, unavailable)


## ボタンの位置と大きさ（画面の大きさ vs：UI の単位）。[名前, 表示, 中心, 半径] の並び。skip のボタンは除く
static func layout_for(list: Array, vs: Vector2, skip: Array = []) -> Array:
	var h := vs.y
	var out := []
	for b in list:
		if skip.has(b[0]):
			continue
		var off: Vector2 = b[2]
		var anchor := Vector2(vs.x, vs.y if off.y < 0.0 else 0.0)
		out.append([b[0], b[1], anchor + off * h, b[3] * h])
	return out


func _button_at(pos: Vector2) -> String:
	var h := _draw.get_viewport_rect().size.y
	for b in _layout(BUTTONS) + _layout(TOP_BUTTONS):
		if pos.distance_to(b[2]) <= hit_radius(b[3], h):
			return b[0]
	return ""


func _tap_slop() -> float:
	return TAP_SLOP * _draw.get_viewport_rect().size.y


## 押せる範囲の半径（r：絵の半径、h：画面の高さ）
static func hit_radius(r: float, h: float) -> float:
	return maxf(r * HIT_SCALE, h * MIN_HIT)


## 見える輪の直径（r：絵の半径）
static func disc_diameter(r: float) -> float:
	return r * TEX_SCALE * DISC


## 右下のボタンの押せる範囲が、画面の右端からどこまで届くか（画面の高さに対する割合）。
## HUD の会話の窓・ボスの体力・字幕は、これより左に置く（Hud._bottom_span）
static func bottom_reach() -> float:
	var m := 0.0
	for b in BUTTONS:
		m = maxf(m, -float(b[2].x) + hit_radius(b[3], 1.0))
	return m


## 上の段（ポーズ・背後）の押せる範囲が、画面の右端からどこまで届くか（同）。上の中央の操作の案内はこれより左で終える
static func top_reach() -> float:
	var m := 0.0
	for b in TOP_BUTTONS:
		m = maxf(m, -float(b[2].x) + hit_radius(b[3], 1.0))
	return m


## スマホで UI を大きく描く倍率（main._update_ui_scale。窓の content_scale_factor）。logical_h：画面の高さの実寸（CSS の px）。
## 文字が 1080 の高さの画面で 26px のとき、画面の高さ 390px で約 16px になるように（spec：360px 高で本文 16px 以上）。
## UI の画面の高さは 1080 / 倍率 ＝ 実寸の 1.75 倍（640〜1080）
static func ui_scale_for(logical_h: float) -> float:
	return 1080.0 / clampf(logical_h * 1.75, 640.0, 1080.0)


## UI の 1 単位が実寸（ブラウザの CSS の px）の何 px か。win_h：窓の高さ（画素）、scale：画素の細かさ（ブラウザの devicePixelRatio）、
## view_h：UI の画面の高さ（main._update_ui_scale で大きく描いたあとの単位）
static func real_px_per_unit(win_h: float, scale: float, view_h: float) -> float:
	return win_h / maxf(1.0, scale) / maxf(1.0, view_h)


## 会話のタップを取り出す（-1 送る、0 以上 選んだ選択肢、-2 なし）
func take_tap() -> int:
	var t := _tap
	_tap = -2
	return t


## ボタンが押されているか（押して離した短い押しも、この刻みでは押したことにする）
func button(name: String) -> bool:
	if name == "lock_on":
		return lock_toggled
	return _held.has(name) or _pressed_once.has(name)


## カメラの回転量（ラジアン）を取り出す
func take_look() -> Vector2:
	var v := _look * LOOK_SENS
	_look = Vector2.ZERO
	return v


## ロックオンの対象の切り替え（-1 左、1 右、0 なし）を取り出す
func take_switch() -> int:
	var s := _switch
	_switch = 0
	return s


func take_one_shot(a: String) -> bool:
	if _one_shot.has(a):
		_one_shot.erase(a)
		return true
	return false


## 1 刻み分を読み終えたら呼ぶ
func end_frame() -> void:
	_pressed_once.clear()
	if _held.size() > 0 or lock_toggled:
		_draw.queue_redraw()


## ボタンの中の記号（ui_parts_touch_symbol_*）
const SYMBOLS := {
	"jump": "jump", "fire": "fire", "sword": "slash", "dash": "dash", "special": "special", "lock_on": "lock",
	"heal": "heal", "pause": "pause", "camera_reset": "behind",
}


func _tex_at(name: String, c: Vector2, d: float, mod := Color.WHITE) -> bool:
	var t := UiArt.tex(name)
	if t == null:
		return false
	_draw.draw_texture_rect(t, Rect2(c - Vector2(d, d) * 0.5, Vector2(d, d)), false, mod)
	return true


## 見た目は Codex の部品（ui_hud_touch.png）：スティックの台座とつまみ、丸いボタン（通常・押している・ロック中）と中の記号
func _on_draw() -> void:
	var font := ThemeDB.fallback_font
	var vs := _draw.get_viewport_rect().size
	var h := vs.y
	if vs.x < vs.y:
		_draw.draw_rect(Rect2(Vector2.ZERO, vs), Color(0.05, 0.045, 0.04, 0.85))
		_tex_at("ui_parts_touch_symbol_behind", Vector2(vs.x * 0.5, vs.y * 0.42), vs.x * 0.22)
		_draw.draw_string(font, Vector2(0, vs.y * 0.55), "スマホを横向きにしてください", HORIZONTAL_ALIGNMENT_CENTER, vs.x, int(vs.x * 0.06), UiArt.PAPER)
		return
	# 台座の絵の輪の内側をつまみが動く（台座は STICK_RADIUS の約 1.25 倍）
	var base_d := STICK_RADIUS * 2.5
	var knob_d := STICK_RADIUS * 1.05
	if _stick_finger >= 0:
		if not _tex_at("ui_parts_touch_joystick_base", _stick_origin, base_d, Color(1, 1, 1, 0.9)):
			_draw.draw_arc(_stick_origin, STICK_RADIUS, 0, TAU, 48, Color(1, 1, 1, 0.35), 3.0)
		var knob := _stick_origin + Vector2(move.x, -move.y) * STICK_RADIUS
		if not _tex_at("ui_parts_touch_joystick_knob", knob, knob_d):
			_draw.draw_circle(knob, STICK_RADIUS * 0.42, Color(1, 1, 1, 0.45))
	elif stick_hint:
		# 触れる前の案内（薄く）
		var c := Vector2(h * 0.26, h * 0.72)
		if _tex_at("ui_parts_touch_joystick_base", c, base_d, Color(1, 1, 1, 0.4)):
			_tex_at("ui_parts_touch_joystick_knob", c, knob_d, Color(1, 1, 1, 0.4))
		else:
			_draw.draw_arc(c, STICK_RADIUS, 0, TAU, 48, Color(1, 1, 1, 0.18), 3.0)
		# 文字は 360px の高さで 14px 以上（spec の補助の文字）。台座の下、画面の下端に掛からないように
		var fs := int(ceilf(h * 0.04))
		var y := minf(c.y + base_d * 0.5 + fs, h - fs * 0.4)
		_draw.draw_string(font, Vector2(c.x - 80, y), "移動", HORIZONTAL_ALIGNMENT_CENTER, 160, fs, Color(1, 1, 1, 0.7))
	for b in _layout(BUTTONS) + _layout(TOP_BUTTONS):
		var on: bool = button(b[0])
		var d: float = b[3] * TEX_SCALE
		var base := "ui_parts_touch_button_pressed" if on else "ui_parts_touch_button_normal"
		if b[0] == "lock_on" and lock_toggled:
			base = "ui_parts_touch_button_lock_on"
		if not _tex_at(base, b[2], d, Color(1, 1, 1, 0.92)):
			_draw.draw_circle(b[2], b[3], Color(AMBER, 0.55) if on else Color(0.08, 0.06, 0.05, 0.45))
			var lines: PackedStringArray = String(b[1]).split("\n")
			var fs := int(b[3] * (0.42 if lines.size() == 1 else 0.36))
			for i in lines.size():
				var y: float = b[2].y + fs * 0.35 + (i - (lines.size() - 1) * 0.5) * fs * 1.1
				_draw.draw_string(font, Vector2(b[2].x - b[3], y), lines[i], HORIZONTAL_ALIGNMENT_CENTER, b[3] * 2.0, fs, Color(1, 1, 1, 0.9))
			continue
		# ロック中の台座には照準の記号が入っているので、記号は重ねない
		if not (b[0] == "lock_on" and lock_toggled):
			_tex_at("ui_parts_touch_symbol_" + SYMBOLS.get(b[0], "jump"), b[2], b[3] * 1.05)
