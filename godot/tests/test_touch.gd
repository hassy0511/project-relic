extends RefCounted
## スマホの画面の操作（TouchControls）が InputFrame に正しく入ることを確かめる。

var h: TestHelpers


func _init(helpers: TestHelpers) -> void:
	h = helpers


func _make() -> Array:
	InputSource.setup_actions()
	var tc := TouchControls.new()
	h.tree.root.add_child(tc)
	var src := InputSource.new()
	h.tree.root.add_child(src)
	src.touch = tc
	tc.activate()
	tc.set_shown(true)
	await h.tree.process_frame
	return [tc, src]


func _touch(tc: TouchControls, index: int, pos: Vector2, pressed: bool) -> void:
	var e := InputEventScreenTouch.new()
	e.index = index
	e.position = pos
	e.pressed = pressed
	tc._input(e)


func _drag(tc: TouchControls, index: int, pos: Vector2, rel: Vector2) -> void:
	var e := InputEventScreenDrag.new()
	e.index = index
	e.position = pos
	e.relative = rel
	tc._input(e)


func _button_pos(tc: TouchControls, name: String) -> Vector2:
	for b in tc._layout(TouchControls.BUTTONS) + tc._layout(TouchControls.TOP_BUTTONS):
		if b[0] == name:
			return b[2]
	return Vector2.ZERO


func test_touch_stick_look_buttons() -> void:
	var made: Array = await _make()
	var tc: TouchControls = made[0]
	var src: InputSource = made[1]
	var size := tc._draw.get_viewport_rect().size
	# 左半分：触れた所から上へ動かすと前進
	var o := Vector2(size.x * 0.2, size.y * 0.7)
	_touch(tc, 0, o, true)
	_drag(tc, 0, o + Vector2(0, -200), Vector2(0, -200))
	var f := src.sample(1.0 / 60.0)
	h.near(f.move_y, 1.0, 0.01, "画面のスティックを上へ倒すと前進")
	# 右半分をなぞるとカメラが回る
	var r := Vector2(size.x * 0.6, size.y * 0.3)
	_touch(tc, 1, r, true)
	_drag(tc, 1, r + Vector2(50, 0), Vector2(50, 0))
	f = src.sample(1.0 / 60.0)
	h.expect(f.look_active and f.look_x > 0.0, "右半分をなぞるとカメラが回る")
	h.expect(f.move_y > 0.9, "カメラを回しながらでも移動は続く")
	# ボタン：短く押して離しても、次の刻みで押したことになる
	var jp := _button_pos(tc, "jump")
	_touch(tc, 2, jp, true)
	_touch(tc, 2, jp, false)
	f = src.sample(1.0 / 60.0)
	h.expect(f.jump, "ジャンプのボタンを短く押しても取りこぼさない")
	f = src.sample(1.0 / 60.0)
	h.expect(not f.jump, "離したあとの刻みでは押していない")
	# ロックオンは押すたびに入り切り
	var lp := _button_pos(tc, "lock_on")
	_touch(tc, 3, lp, true)
	_touch(tc, 3, lp, false)
	f = src.sample(1.0 / 60.0)
	h.expect(f.lock_on, "ロックのボタンで入る")
	_drag(tc, 1, r + Vector2(200, 0), Vector2(150, 0))
	f = src.sample(1.0 / 60.0)
	h.expect(f.switch_right, "ロックオン中に右へ払うと対象の切り替え")
	# 指を離すと止まる
	_touch(tc, 0, o, false)
	f = src.sample(1.0 / 60.0)
	h.near(f.move_y, 0.0, 0.01, "指を離すと止まる")
	# ポーズ
	_touch(tc, 4, _button_pos(tc, "pause"), true)
	h.expect(src.take_one_shot("pause"), "ポーズのボタン")
	tc.queue_free()
	src.queue_free()
