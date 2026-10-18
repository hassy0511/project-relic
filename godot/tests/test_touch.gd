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


## ボタンの押せる範囲：360px の高さで直径 48px 以上（spec の下限）、隣のボタンの範囲と重ならない。小さいボタンの縁でも押せる
func test_touch_hit_areas() -> void:
	var made: Array = await _make()
	var tc: TouchControls = made[0]
	var src: InputSource = made[1]
	var hgt := tc._draw.get_viewport_rect().size.y
	var all: Array = tc._layout(TouchControls.BUTTONS) + tc._layout(TouchControls.TOP_BUTTONS)
	for b in all:
		h.expect(TouchControls.hit_radius(b[3], hgt) * 2.0 >= hgt * 48.0 / 360.0 - 0.01, "「%s」の押せる範囲が 48px（360px の高さで）以上" % b[0])
	for i in all.size():
		for j in range(i + 1, all.size()):
			var a: Array = all[i]
			var c: Array = all[j]
			h.expect(a[2].distance_to(c[2]) > TouchControls.hit_radius(a[3], hgt) + TouchControls.hit_radius(c[3], hgt), "「%s」と「%s」の押せる範囲が重ならない" % [a[0], c[0]])
	# 回復（小さいボタン）の見える輪の外側、押せる範囲の縁の近く
	var r: float = 0.0
	for b in all:
		if b[0] == "heal":
			r = b[3]
	var edge := (TouchControls.disc_diameter(r) * 0.5 + TouchControls.hit_radius(r, hgt)) * 0.5
	h.expect(edge > TouchControls.disc_diameter(r) * 0.5, "押す所は見える輪の外")
	var hp := _button_pos(tc, "heal") + Vector2(0, -edge)
	_touch(tc, 5, hp, true)
	var f := src.sample(1.0 / 60.0)
	h.expect(f.heal, "小さいボタンは絵より少し外を押しても効く")
	_touch(tc, 5, hp, false)
	tc.queue_free()
	src.queue_free()


## スマホの横向き（CSS の px）と画素の細かさから、main と同じ決まりで UI の画面の大きさ（UI の単位）と、UI の 1 単位の実寸（px）を求める
func _phone_view(phone: Vector2, dpr: float) -> Array:
	var win := phone * dpr
	var f := TouchControls.ui_scale_for(win.y / dpr)
	# 窓は canvas_items・expand（基準 1920×1080）：高さ 1080 を基準に横へ広げ、UI を大きく描く倍率で割る
	var vs := Vector2(1080.0 * win.x / win.y, 1080.0) / f
	return [vs, TouchControls.real_px_per_unit(win.y, dpr, vs.y)]


## 実寸の決まり（spec：タッチ可能領域 48px 以上）：よくあるスマホの横向き（844×390・667×375 など、画素の細かさ 2〜3）で、
## どのボタンも、見える輪（金の縁の外まで）と押せる範囲が実寸 48px 以上。押せる範囲どうしは重ならず、輪は画面の中
func test_touch_real_size() -> void:
	for phone in [Vector2(844, 390), Vector2(667, 375), Vector2(640, 360), Vector2(800, 360), Vector2(915, 412), Vector2(932, 430)]:
		for dpr in [2.0, 3.0]:
			var v: Array = _phone_view(phone, dpr)
			var vs: Vector2 = v[0]
			var px: float = v[1]
			var tag := "%dx%d（×%d）" % [int(phone.x), int(phone.y), int(dpr)]
			h.near(vs.y * px, phone.y, 0.5, "%s：UI の画面の高さは実寸で画面の高さ" % tag)
			var all: Array = TouchControls.layout_for(TouchControls.BUTTONS, vs) + TouchControls.layout_for(TouchControls.TOP_BUTTONS, vs)
			h.expect(all.size() == 9, "%s：ボタン 9 個" % tag)
			var ring := INF
			var hit := INF
			var inside := true
			for b in all:
				var d := TouchControls.disc_diameter(b[3])
				ring = minf(ring, d * px)
				hit = minf(hit, TouchControls.hit_radius(b[3], vs.y) * 2.0 * px)
				inside = inside and Rect2(Vector2.ZERO, vs).encloses(Rect2(b[2] - Vector2(d, d) * 0.5, Vector2(d, d)))
			h.expect(ring >= TouchControls.MIN_REAL_PX, "%s：いちばん小さいボタンの輪が実寸 %.1fpx（48px 以上）" % [tag, ring])
			h.expect(hit >= TouchControls.MIN_REAL_PX, "%s：いちばん小さい押せる範囲が実寸 %.1fpx（48px 以上）" % [tag, hit])
			h.expect(inside, "%s：ボタンの輪は画面の中" % tag)
			for i in all.size():
				for j in range(i + 1, all.size()):
					var a: Array = all[i]
					var c: Array = all[j]
					h.expect(a[2].distance_to(c[2]) > TouchControls.hit_radius(a[3], vs.y) + TouchControls.hit_radius(c[3], vs.y),
						"%s：「%s」と「%s」の押せる範囲が重ならない" % [tag, a[0], c[0]])
			# メニューの行・会話の選択肢の札の高さ（Hud.TOUCH_ROW）も実寸 48px 以上
			h.expect(Hud.TOUCH_ROW * px >= TouchControls.MIN_REAL_PX, "%s：メニューの行・選択肢の札の高さが実寸 %.1fpx（48px 以上）" % [tag, Hud.TOUCH_ROW * px])
	# 前の配置（回復・ポーズ・背後は半径 0.05）は、390px の高さで輪が約 38px だった（この決まりで落ちる）
	h.expect(TouchControls.disc_diameter(0.05) * 390.0 < TouchControls.MIN_REAL_PX, "前の小さいボタンはこの決まりを満たさない（確かめ方の確認）")


## 本物の世界（会話・店のデータ入り）のゲーム
func _world_game() -> GameSim:
	var g := GameSim.new()
	var vp := SubViewport.new()
	vp.own_world_3d = true
	vp.render_target_update_mode = SubViewport.UPDATE_DISABLED
	vp.size = Vector2i(2, 2)
	h.tree.root.add_child(vp)
	vp.add_child(g)
	g.setup({"world": World.load_manifest("res://content/world.json"), "tuning": TestHelpers.default_tuning(), "seed": 1})
	g.god_mode = true
	return g


## 会話を選択肢が出るまで進める（決定のボタンで）
func _to_choices(g: GameSim) -> void:
	for i in 2000:
		var d: Dictionary = g.story.dialogue
		if d.is_empty() or (d.has("choices") and d.shown >= String(d.text).length()):
			return
		g.step(InputFrame.of({"confirm": i % 6 < 3}))


## スマホの画面（844×390・667×375）で、ボタンの押せる範囲が HUD（左上の HP など・右上のセルと目的・上の操作の案内・
## 会話の窓と選択肢）に掛からない。選択肢の札は実寸 48px 以上の高さ
func test_touch_buttons_clear_hud() -> void:
	var g := _world_game()
	await h.settle()
	g.load_room("ch1.mid", "start")
	await h.tree.physics_frame
	g.objective = "遺構の奥へ進み、動力の中継器を探す（とても長い目的の文で、右上の枠がいちばん広くなるとき）"
	for phone in [Vector2(844, 390), Vector2(667, 375)]:
		var vs: Vector2 = _phone_view(phone, 3.0)[0]
		var vp := SubViewport.new()
		vp.size = Vector2i(vs.round())
		h.tree.root.add_child(vp)
		var hud := Hud.new()
		vp.add_child(hud)
		var cam := Camera3D.new()
		vp.add_child(cam)
		hud.compact = true
		hud.device = "touch"
		hud.set_hint({"kb": "", "touch": "左半分に触れて動かすと歩く。右下のボタンでジャンプ。② の段に登ってみよう（とても長い操作の案内の文）"})
		var tag := "%dx%d" % [int(phone.x), int(phone.y)]
		var view := Vector2(vp.size)
		var hits := []
		for b in TouchControls.layout_for(TouchControls.BUTTONS, view) + TouchControls.layout_for(TouchControls.TOP_BUTTONS, view):
			var r: float = TouchControls.hit_radius(b[3], view.y)
			hits.append([b[0], Rect2(b[2] - Vector2(r, r), Vector2(r, r) * 2.0)])
		# 歩いているとき：HP など・セル・目的・操作の案内
		for i in 3:
			hud.sync(g, cam, 0.016)
			await h.tree.process_frame
		var boxes := {"左上の HP など": hud._vitals, "右上のセル": hud._cells_box, "右上の目的": hud._objective_box, "上の操作の案内": hud._hint}
		for name in boxes:
			var c: Control = boxes[name]
			h.expect(c.is_visible_in_tree(), "%s：%sが出ている" % [tag, name])
			for hr in hits:
				h.expect(not hr[1].intersects(c.get_global_rect()), "%s：「%s」の押せる範囲が%sに掛からない" % [tag, hr[0], name])
		# 会話（選択肢つき）
		g.story.start_dialogue("ch1.debt")
		_to_choices(g)
		for i in 3:
			hud.sync(g, cam, 0.016)
			await h.tree.process_frame
		h.expect(hud._dlg_choices.is_visible_in_tree(), "%s：選択肢が出ている" % tag)
		for hr in hits:
			h.expect(not hr[1].intersects(hud._dlg.get_global_rect()), "%s：「%s」の押せる範囲が会話の窓に掛からない" % [tag, hr[0]])
		for it in hud._dlg_choice_rows:
			if it[0].visible:
				var rh: float = it[0].get_global_rect().size.y * phone.y / view.y
				h.expect(rh >= TouchControls.MIN_REAL_PX, "%s：選択肢の札の高さが実寸 %.1fpx（48px 以上）" % [tag, rh])
		g.story.dialogue = {}
		vp.queue_free()
	h.free_game(g)


## 会話の窓のタップ：表示の途中で窓をタップすると全文が出る、出し終えていれば次へ（決定のボタンと同じ）。
## 選択肢の札をタップするとその選択肢で確定する。選択肢を待っている間に札の外（窓の本文）をタップしても確定しない
func test_touch_dialogue_tap() -> void:
	var g := _world_game()
	await h.settle()
	g.load_room("ch1.mid", "start")
	await h.tree.physics_frame
	var vs: Vector2 = _phone_view(Vector2(844, 390), 3.0)[0]
	var vp := SubViewport.new()
	vp.size = Vector2i(vs.round())
	h.tree.root.add_child(vp)
	var hud := Hud.new()
	vp.add_child(hud)
	var cam := Camera3D.new()
	vp.add_child(cam)
	hud.compact = true
	InputSource.setup_actions()
	var tc := TouchControls.new()
	vp.add_child(tc)
	var src := InputSource.new()
	vp.add_child(src)
	src.touch = tc
	tc.activate()
	tc.set_shown(true)
	tc.tap_probe = hud.dialogue_tap_at
	var step := func() -> void:
		g.step(src.sample(1.0 / 60.0))
		hud.sync(g, cam, 1.0 / 60.0)
	var tap := func(pos: Vector2) -> void:
		_touch(tc, 7, pos, true)
		_touch(tc, 7, pos + Vector2(3, 2), false)
	g.story.start_dialogue("ch1.debt")
	for i in 8:
		step.call()
		await h.tree.process_frame
	var d: Dictionary = g.story.dialogue
	var text := String(d.text)
	h.expect(d.shown > 0 and d.shown < text.length(), "1 行目を表示している途中（%d／%d 字）" % [d.shown, text.length()])
	var box: Rect2 = hud._dlg.get_global_rect()
	h.expect(hud.dialogue_tap_at(box.get_center()) == -1 and hud.dialogue_tap_at(Vector2(vs.x - 10, 10)) == -2, "窓の中は「送る」、窓の外は何もしない")
	tap.call(box.position + box.size * Vector2(0.4, 0.6))
	step.call()
	h.expect(g.story.dialogue.shown == text.length() and int(g.story.dialogue.index) == 0, "表示の途中で窓をタップすると全文が出る")
	step.call()
	tap.call(box.position + box.size * Vector2(0.7, 0.5))
	step.call()
	h.expect(int(g.story.dialogue.index) == 1, "出し終えてから窓をタップすると次の行へ（%d）" % int(g.story.dialogue.index))
	# 指をずらしてから離したとき（スティックの操作）はタップにしない
	step.call()
	_touch(tc, 7, box.get_center(), true)
	_drag(tc, 7, box.get_center() + Vector2(0, -80), Vector2(0, -80))
	_touch(tc, 7, box.get_center() + Vector2(0, -80), false)
	step.call()
	h.expect(int(g.story.dialogue.index) == 1, "指をずらして離したときは送らない")
	# 窓のタップだけで選択肢まで進む
	for i in 600:
		d = g.story.dialogue
		if d.has("choices") and d.shown >= String(d.text).length():
			break
		step.call()
		if i % 3 == 0:
			await h.tree.process_frame
			tap.call(hud._dlg.get_global_rect().get_center())
	for i in 2:
		step.call()
		await h.tree.process_frame
	d = g.story.dialogue
	h.expect(d.get("id", "") == "ch1.debt" and d.has("choices") and hud._dlg_choices.is_visible_in_tree(), "窓のタップだけで選択肢まで進む")
	# 選択肢を待っている間に本文をタップしても確定しない
	tap.call(hud._dlg_text.get_global_rect().get_center())
	step.call()
	step.call()
	h.expect(g.story.dialogue.get("id", "") == "ch1.debt" and g.story.dialogue.has("choices"), "選択肢を待っている間は、札の外のタップで確定しない")
	# 2 つ目の札をタップ → その選択肢で確定（ch1.yana.debt_b へ）
	var row: Rect2 = hud._dlg_choice_rows[1][0].get_global_rect()
	h.expect(hud.dialogue_tap_at(row.get_center()) == 1, "2 つ目の札の上は 2 つ目の選択肢")
	tap.call(row.get_center())
	step.call()
	h.expect(g.story.dialogue.get("id", "") == "ch1.yana.debt_b", "2 つ目の札をタップすると、その選択肢で確定（%s）" % g.story.dialogue.get("id", ""))
	# パッド・キーボードは今までどおり（下で 2 つ目を選んで決定）
	g.story.start_dialogue("ch1.debt")
	_to_choices(g)
	g.step(InputFrame.of({}))
	g.step(InputFrame.of({"move_y": -1.0}))
	g.step(InputFrame.of({}))
	g.step(InputFrame.of({"confirm": true}))
	h.expect(g.story.dialogue.get("id", "") == "ch1.yana.debt_b", "パッド・キーボード：下で 2 つ目を選んで決定（今までどおり）")
	g.story.dialogue = {}
	tc.queue_free()
	src.queue_free()
	vp.queue_free()
	h.free_game(g)
