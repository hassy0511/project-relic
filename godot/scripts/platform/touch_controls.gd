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

## ボタン：名前、表示、中心（画面の右下・右上からの位置。単位は画面の高さに対する割合）、半径（同）
const BUTTONS := [
	["jump", "ジャンプ\n調べる", Vector2(-0.14, -0.14), 0.085],
	["fire", "撃つ", Vector2(-0.33, -0.12), 0.075],
	["sword", "斬る", Vector2(-0.27, -0.30), 0.075],
	["dash", "ダッシュ", Vector2(-0.10, -0.36), 0.065],
	["special", "特殊", Vector2(-0.45, -0.27), 0.06],
	["lock_on", "ロック", Vector2(-0.44, -0.08), 0.06],
	["heal", "回復", Vector2(-0.10, -0.54), 0.05],
]
const TOP_BUTTONS := [
	["pause", "ポーズ", Vector2(-0.09, 0.08), 0.05],
	["camera_reset", "背後", Vector2(-0.21, 0.08), 0.05],
]

var active := false
## ロックオンの入り切り（押すたびに切り替え）
var lock_toggled := false
var move := Vector2.ZERO

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
	# 画面に触れると、マウスの左・右クリックとしても届く（メニューのボタンを押せるように）。
	# そのままだと触れるたびに撃ってしまうので、マウスのボタンの割り当てを外す
	for a in ["fire", "lock_on", "camera_reset"]:
		for e in InputMap.action_get_events(a):
			if e is InputEventMouseButton:
				InputMap.action_erase_event(a, e)


func set_shown(on: bool) -> void:
	visible = active and on
	if not visible:
		_release_all()


func _release_all() -> void:
	_held.clear()
	_stick_finger = -1
	_look_finger = -1
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
			_touch_up(t.index)
		_draw.queue_redraw()
		get_viewport().set_input_as_handled()
	elif event is InputEventScreenDrag:
		var d := event as InputEventScreenDrag
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
	var size := _draw.get_viewport_rect().size
	if pos.x < size.x * 0.45 and _stick_finger < 0:
		_stick_finger = index
		_stick_origin = pos
		_stick_pos = pos
		move = Vector2.ZERO
	elif _look_finger < 0:
		_look_finger = index
		_flick = 0.0


func _touch_up(index: int) -> void:
	for b in _held.keys():
		if _held[b] == index:
			_held.erase(b)
	if index == _stick_finger:
		_stick_finger = -1
		move = Vector2.ZERO
	if index == _look_finger:
		_look_finger = -1


func _layout(list: Array) -> Array:
	var size := _draw.get_viewport_rect().size
	var h := size.y
	var out := []
	for b in list:
		var off: Vector2 = b[2]
		var anchor := Vector2(size.x, size.y if off.y < 0.0 else 0.0)
		out.append([b[0], b[1], anchor + off * h, b[3] * h])
	return out


func _button_at(pos: Vector2) -> String:
	for b in _layout(BUTTONS) + _layout(TOP_BUTTONS):
		if pos.distance_to(b[2]) <= b[3] * 1.15:
			return b[0]
	return ""


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


func _on_draw() -> void:
	var font := ThemeDB.fallback_font
	var h := _draw.get_viewport_rect().size.y
	if _stick_finger >= 0:
		_draw.draw_circle(_stick_origin, STICK_RADIUS, Color(1, 1, 1, 0.12))
		_draw.draw_arc(_stick_origin, STICK_RADIUS, 0, TAU, 48, Color(1, 1, 1, 0.35), 3.0)
		var knob := _stick_origin + Vector2(move.x, -move.y) * STICK_RADIUS
		_draw.draw_circle(knob, STICK_RADIUS * 0.42, Color(1, 1, 1, 0.45))
	else:
		# 触れる前の案内
		var c := Vector2(h * 0.26, h * 0.74)
		_draw.draw_arc(c, STICK_RADIUS, 0, TAU, 48, Color(1, 1, 1, 0.18), 3.0)
		_draw.draw_string(font, c + Vector2(-60, 8), "移動", HORIZONTAL_ALIGNMENT_CENTER, 120, int(h * 0.028), Color(1, 1, 1, 0.4))
	for b in _layout(BUTTONS) + _layout(TOP_BUTTONS):
		var on: bool = button(b[0])
		var col := Color(AMBER, 0.55) if on else Color(0.08, 0.06, 0.05, 0.45)
		_draw.draw_circle(b[2], b[3], col)
		_draw.draw_arc(b[2], b[3], 0, TAU, 40, Color(1, 1, 1, 0.5), 2.0)
		var lines: PackedStringArray = String(b[1]).split("\n")
		var fs := int(b[3] * (0.42 if lines.size() == 1 else 0.36))
		for i in lines.size():
			var y: float = b[2].y + fs * 0.35 + (i - (lines.size() - 1) * 0.5) * fs * 1.1
			_draw.draw_string(font, Vector2(b[2].x - b[3], y), lines[i], HORIZONTAL_ALIGNMENT_CENTER, b[3] * 2.0, fs, Color(1, 1, 1, 0.9))
