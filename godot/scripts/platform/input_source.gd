class_name InputSource
extends Node
## キーボード・マウス・ゲームパッドの入力を集めて、ゲームの中身用の InputFrame にする。
## 操作の割り当てはここで InputMap に登録する（設定画面での変更に備える）。
## マウスは固定（キャプチャ）中だけカメラを回す。

const MOUSE_SENS := 0.0025
const PAD_SENS := 3.2
const KEY_LOOK := 2.4
## スティックの形（shape_stick）：左（移動）と右（カメラ）のデッドゾーン、外側、上下左右に吸い付く角度
const STICK_INNER := 0.15
const CAM_INNER := 0.2
const STICK_OUTER := 0.95
const STICK_SNAP := 10.0
const BUTTONS := ["jump", "dash", "fire", "sword", "special", "lock_on", "heal"]

## 最後に使われた機器（ボタン表示の切り替えに使う）："keyboard" / "pad"
var last_device := "keyboard"
var enabled := true
var invert_y := false
var _latched := {}
var _mouse := Vector2.ZERO
var _flick_accum := 0.0
var _flick_cooldown := 0.0
var _pad_flick_ready := true
var _one_shot := {}
## スマホの画面の操作（main が作って渡す。無いときは null）
var touch: TouchControls = null


static func setup_actions() -> void:
	# 移動・カメラのキー（割り当ては変えられない）
	var keys := {
		"move_left": [KEY_A], "move_right": [KEY_D], "move_up": [KEY_W], "move_down": [KEY_S],
		"cam_left": [KEY_LEFT], "cam_right": [KEY_RIGHT], "cam_up": [KEY_UP], "cam_down": [KEY_DOWN],
	}
	var mouse := {"fire": [MOUSE_BUTTON_LEFT], "lock_on": [MOUSE_BUTTON_RIGHT], "camera_reset": [MOUSE_BUTTON_MIDDLE]}
	var names := {}
	for d in [keys, mouse]:
		for k in d:
			names[k] = true
	for a in names:
		if not InputMap.has_action(a):
			InputMap.add_action(a, 0.3)
	for a in keys:
		InputMap.action_erase_events(a)
		for k in keys[a]:
			var e := InputEventKey.new()
			e.physical_keycode = k
			InputMap.action_add_event(a, e)
	for a in mouse:
		for e in InputMap.action_get_events(a):
			if e is InputEventMouseButton:
				InputMap.action_erase_event(a, e)
		for b in mouse[a]:
			var e := InputEventMouseButton.new()
			e.button_index = b
			InputMap.action_add_event(a, e)
	# ボタン・キーの割り当て（設定画面で変えたもの。user://input.cfg）を読んで反映する
	PadConfig.load_file()
	PadConfig.apply()


## スティックの形を整える：円形のデッドゾーン（inner より小さい倒しは 0）、そこから outer までを 0〜1 に引き伸ばす。
## 上下左右の真上から snap_deg 度以内なら、ぴったり上下左右の向きにする（倒し具合はそのまま）。
## 「まっすぐ倒したつもり」の数度のずれで、進む向きがふらつかないようにする。
static func shape_stick(raw: Vector2, inner := 0.15, outer := 0.95, snap_deg := 10.0) -> Vector2:
	var len := raw.length()
	if len <= inner + 0.0001:
		return Vector2.ZERO
	var m := clampf((len - inner) / (outer - inner), 0.0, 1.0)
	var dir := raw / len
	if snap_deg > 0.0:
		var ang := atan2(dir.y, dir.x)
		var card := roundf(ang / (PI * 0.5)) * (PI * 0.5)
		if absf(ang - card) <= deg_to_rad(snap_deg):
			dir = Vector2(roundf(cos(card)), roundf(sin(card)))
	return dir * m


## つながっているパッドのうち、いちばん大きく倒している 1 台のスティック（生の値。y は上が +）
static func read_stick(axis_x: int, axis_y: int) -> Vector2:
	var best := Vector2.ZERO
	for d in Input.get_connected_joypads():
		var v := Vector2(Input.get_joy_axis(d, axis_x), -Input.get_joy_axis(d, axis_y))
		if v.length() > best.length():
			best = v
	return best


func _input(event: InputEvent) -> void:
	if event is InputEventJoypadButton or (event is InputEventJoypadMotion and absf(event.axis_value) > 0.3):
		last_device = "pad"
	elif event is InputEventKey or (event is InputEventMouseButton and not (touch and touch.active)):
		last_device = "keyboard"
	if event is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		_mouse += event.relative
		if Input.is_action_pressed("lock_on"):
			_flick_accum += event.relative.x
	for a in BUTTONS:
		if event.is_action_pressed(a):
			_latched[a] = true
	if event.is_action_pressed("ui_accept"):
		_latched["confirm"] = true
	for a in ["pause", "map", "camera_reset"]:
		if event.is_action_pressed(a):
			_one_shot[a] = true


## 一度だけの操作（ポーズ等）を取り出す
func take_one_shot(a: String) -> bool:
	if touch and touch.take_one_shot(a):
		return true
	if _one_shot.has(a):
		_one_shot.erase(a)
		return true
	return false


## この刻みの入力を作る
func sample(dt: float) -> InputFrame:
	var f := InputFrame.new()
	if not enabled:
		_mouse = Vector2.ZERO
		_latched.clear()
		return f
	var mv := Input.get_vector("move_left", "move_right", "move_down", "move_up")
	var stick := shape_stick(read_stick(JOY_AXIS_LEFT_X, JOY_AXIS_LEFT_Y), STICK_INNER, STICK_OUTER, STICK_SNAP)
	if stick != Vector2.ZERO:
		mv = stick
	if mv.length() > 1.0:
		mv = mv.normalized()
	f.move_x = mv.x
	f.move_y = mv.y
	var inv := -1.0 if invert_y else 1.0
	f.look_x = _mouse.x * MOUSE_SENS
	f.look_y = _mouse.y * MOUSE_SENS * inv
	f.look_active = _mouse != Vector2.ZERO
	_mouse = Vector2.ZERO
	# 矢印キーでもカメラを回せる
	var kx := Input.get_axis("cam_left", "cam_right")
	var ky := Input.get_axis("cam_up", "cam_down")
	if kx != 0.0 or ky != 0.0:
		f.look_x += kx * KEY_LOOK * dt
		f.look_y += ky * KEY_LOOK * 0.6 * dt * inv
		f.look_active = true
	for b in BUTTONS:
		f.set(b, Input.is_action_pressed(b) or _latched.has(b))
	# 決定（メニュー・会話）：割り当ては設定画面の「決定」（ui_accept）
	f.confirm = Input.is_action_pressed("ui_accept") or _latched.has("confirm")
	_latched.clear()

	# マウスを大きく横に振ると、ロックオン対象の切り替え
	_flick_cooldown = maxf(0.0, _flick_cooldown - dt)
	if Input.is_action_pressed("lock_on") and _flick_cooldown <= 0.0 and absf(_flick_accum) > 60.0:
		if _flick_accum > 0.0:
			f.switch_right = true
		else:
			f.switch_left = true
		_flick_cooldown = 0.25
		_flick_accum = 0.0
	if not Input.is_action_pressed("lock_on"):
		_flick_accum = 0.0
	_flick_accum *= 0.9

	# 右スティック：ロックオン中は弾いて対象の切り替え、それ以外はカメラ
	var rs := shape_stick(read_stick(JOY_AXIS_RIGHT_X, JOY_AXIS_RIGHT_Y), CAM_INNER, STICK_OUTER, STICK_SNAP)
	var rx := rs.x
	var ry := -rs.y
	if Input.is_action_pressed("lock_on"):
		if _pad_flick_ready and absf(rx) > 0.6:
			if rx > 0.0:
				f.switch_right = true
			else:
				f.switch_left = true
			_pad_flick_ready = false
		if absf(rx) < 0.3:
			_pad_flick_ready = true
	elif rx != 0.0 or ry != 0.0:
		f.look_x += rx * absf(rx) * PAD_SENS * dt
		f.look_y += ry * absf(ry) * PAD_SENS * 0.7 * dt * inv
		f.look_active = true
	if touch and touch.visible:
		_merge_touch(f)
	if take_one_shot("camera_reset"):
		f.camera_reset = true
	return f


## 画面の操作を混ぜる（スティックが倒れていればそちらを優先）
func _merge_touch(f: InputFrame) -> void:
	if touch.move.length() > 0.08:
		f.move_x = touch.move.x
		f.move_y = touch.move.y
		last_device = "touch"
	var lk := touch.take_look()
	if lk != Vector2.ZERO:
		f.look_x += lk.x
		f.look_y += lk.y * (-1.0 if invert_y else 1.0)
		f.look_active = true
	for b in BUTTONS:
		if touch.button(b):
			f.set(b, true)
			last_device = "touch"
	var sw := touch.take_switch()
	if sw != 0:
		f.switch_left = sw < 0
		f.switch_right = sw > 0
	touch.end_frame()
