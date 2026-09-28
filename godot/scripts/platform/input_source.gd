class_name InputSource
extends Node
## キーボード・マウス・ゲームパッドの入力を集めて、ゲームの中身用の InputFrame にする。
## 操作の割り当てはここで InputMap に登録する（設定画面での変更に備える）。
## マウスは固定（キャプチャ）中だけカメラを回す。

const MOUSE_SENS := 0.0025
const PAD_SENS := 3.2
const KEY_LOOK := 2.4
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


static func setup_actions() -> void:
	var keys := {
		"move_left": [KEY_A], "move_right": [KEY_D], "move_up": [KEY_W], "move_down": [KEY_S],
		"cam_left": [KEY_LEFT], "cam_right": [KEY_RIGHT], "cam_up": [KEY_UP], "cam_down": [KEY_DOWN],
		"jump": [KEY_SPACE], "dash": [KEY_SHIFT], "sword": [KEY_E, KEY_K], "special": [KEY_Q],
		"heal": [KEY_R], "camera_reset": [KEY_C], "lock_on": [KEY_F, KEY_L], "fire": [KEY_J],
		"pause": [KEY_ESCAPE], "map": [KEY_TAB],
	}
	# Xbox 配置：A=0 B=1 X=2 Y=3 Back=4 Start=6 R3=8 十字キー上=11
	var pads := {
		"jump": [JOY_BUTTON_A], "dash": [JOY_BUTTON_B], "sword": [JOY_BUTTON_X], "special": [JOY_BUTTON_Y],
		"heal": [JOY_BUTTON_DPAD_UP], "camera_reset": [JOY_BUTTON_RIGHT_STICK], "pause": [JOY_BUTTON_START],
		"map": [JOY_BUTTON_BACK],
	}
	var mouse := {"fire": [MOUSE_BUTTON_LEFT], "lock_on": [MOUSE_BUTTON_RIGHT], "camera_reset": [MOUSE_BUTTON_MIDDLE]}
	var axes := {"lock_on": [JOY_AXIS_TRIGGER_LEFT, 1.0], "fire": [JOY_AXIS_TRIGGER_RIGHT, 1.0]}
	var names := {}
	for d in [keys, pads, mouse, axes]:
		for k in d:
			names[k] = true
	for a in names:
		if not InputMap.has_action(a):
			InputMap.add_action(a, 0.3)
	for a in keys:
		for k in keys[a]:
			var e := InputEventKey.new()
			e.physical_keycode = k
			InputMap.action_add_event(a, e)
	for a in pads:
		for b in pads[a]:
			var e := InputEventJoypadButton.new()
			e.button_index = b
			InputMap.action_add_event(a, e)
	for a in mouse:
		for b in mouse[a]:
			var e := InputEventMouseButton.new()
			e.button_index = b
			InputMap.action_add_event(a, e)
	for a in axes:
		var e := InputEventJoypadMotion.new()
		e.axis = axes[a][0]
		e.axis_value = axes[a][1]
		InputMap.action_add_event(a, e)


func _input(event: InputEvent) -> void:
	if event is InputEventJoypadButton or (event is InputEventJoypadMotion and absf(event.axis_value) > 0.3):
		last_device = "pad"
	elif event is InputEventKey or event is InputEventMouseButton:
		last_device = "keyboard"
	if event is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		_mouse += event.relative
		if Input.is_action_pressed("lock_on"):
			_flick_accum += event.relative.x
	for a in BUTTONS:
		if event.is_action_pressed(a):
			_latched[a] = true
	for a in ["pause", "map", "camera_reset"]:
		if event.is_action_pressed(a):
			_one_shot[a] = true


## 一度だけの操作（ポーズ等）を取り出す
func take_one_shot(a: String) -> bool:
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
	var stick := Vector2(Input.get_joy_axis(0, JOY_AXIS_LEFT_X), -Input.get_joy_axis(0, JOY_AXIS_LEFT_Y))
	if stick.length() > 0.18:
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
	var rx := Input.get_joy_axis(0, JOY_AXIS_RIGHT_X)
	var ry := Input.get_joy_axis(0, JOY_AXIS_RIGHT_Y)
	rx = 0.0 if absf(rx) < 0.18 else rx
	ry = 0.0 if absf(ry) < 0.18 else ry
	if Input.get_joy_axis(0, JOY_AXIS_TRIGGER_LEFT) > 0.3:
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
	if take_one_shot("camera_reset"):
		f.camera_reset = true
	return f
