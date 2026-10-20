class_name HaruMotionShots
## ハルの 2 次の動き（髪・ポーチの揺れ HaruSway、足の接地 FootIK）の確かめ。同じ場面を、切った（off）・入れた（on）の
## 2 通りで撮る（PlayerView.set_secondary。ゲームの中身は同じに進む）。Demo（--demo=<フォルダ>）から使う：
##   --haru_motion_shots                          全部
##   --haru_motion_shots=runstop,landing,dash,stairs,ramp   名前で選ぶ
## 動き（runstop・landing・dash）：6 こま、0.1 秒（6 刻み）ずつ。haru_<名前>_<off|on>_<こま>.png。カメラはハルの横から、
## 水平にだけ付いて動く（高さは床に固定。跳ぶ・着地の上下が見える）。--fixed-fps 60 で 1 こま = 1 刻み。
## 止まった絵（stairs・ramp）：階段の段の縁・坂に横向きに立ち、足もとを前から撮る。haru_<名前>_<off|on>.png。
## 見た目だけ：ゲームの中身には手を加えない（部屋を読み、ハルを置き、入力を渡すだけ）。ナゴミは隠す（止まるとハルの頭の後ろに来て、
## 後ろの房を隠すので）

## 動きの場面：[名前, 部屋:目印, 立つ所, 見る所（向き）, 入力の並び [[刻み数, 入力]...], 撮り始めの合図]
## 合図 "end"：入力の並びの最後の段の始め、"land"：空中から着地した刻み、"start"：動きの段の始め
const MOTIONS := [
	["runstop", "sample.gym:from_hub", [-8.0, 0.0, 6.0], [10.0, 0.0, 6.0], [[72, {"move_y": 1.0}], [60, {}]], "end"],
	["landing", "sample.gym:from_hub", [-4.0, 0.0, 6.0], [10.0, 0.0, 6.0], [[30, {"jump": true}], [110, {}]], "land"],
	["dash", "sample.gym:from_hub", [-8.0, 0.0, 6.0], [10.0, 0.0, 6.0], [[2, {"dash": true}], [58, {}]], "start"],
]
## カメラ：ハルからの横のずれ（世界）、見る高さ、目の高さ、画角
const TRACK_SIDE := Vector3(0.0, 0.0, -2.0)
const TRACK_LOOK_Y := 1.1
const TRACK_EYE_Y := 1.25
const TRACK_FOV := 38.0
## 止まった場面：[名前, 部屋:目印, 立つ所, 見る所（向き）, 全身のカメラ [目, 見る所, 画角], 足もとのカメラ [目, 見る所, 画角]]
## 階段（ch1.lower、1 段 0.3125 m・奥行き 0.75 m）：5 段目の前の縁（z 19.75）のすぐ上に立つ。左足（-z）は 4 段目の上。
## 足もとは下の段の側から低く撮る（前は左足の下のすき間が見える）
## 坂（ch1.training、23.8 度）：坂の中ほどに横向きに立つ。左足（-z）が坂の上の側。カメラはハルの正面（+x）から
const STILLS := [
	["stairs", "ch1.lower:start", [0.0, 1.875, 19.80], [6.0, 1.875, 19.80],
		[[2.6, 2.45, 19.80], [0.0, 2.35, 19.80], 48.0], [[1.3, 1.78, 19.45], [0.0, 1.72, 19.75], 40.0]],
	["ramp", "ch1.training:start", [0.0, -0.6, 27.7], [6.0, -0.6, 27.7],
		[[2.6, -0.15, 27.7], [0.0, -0.05, 27.7], 48.0], [[1.25, -0.45, 27.7], [0.0, -0.68, 27.7], 40.0]],
]
const FRAMES := 6
const EVERY := 6

static var _cam: Camera3D = null
static var _follow := false
static var _offset := TRACK_SIDE
static var _look_y := TRACK_LOOK_Y
static var _capturing := false
## 置いたあとに描くこまの数：描かない刻みのあとの最初の十数こまは、空の光が前の部屋のまま残る（空の放射の図は描くこまの間に
## 作り直される）。切った・入れたの 2 回で明るさがそろうように、撮る前に描いて落ち着かせる
const WARM_FRAMES := 24


static func steps(d) -> Array:
	var m = d.main
	var want := String(m.args.get("haru_motion_shots", "1"))
	# --haru_motion_view=back：横ではなく、ゲームのカメラに近い後ろ斜め上から（ハルは +x を向く）
	# --haru_motion_view=pouch：右の後ろ斜めから腰の高さで（右のポーチ。前からは銃を持つ右手に、左は籠手の腕に隠れる）
	var view := String(m.args.get("haru_motion_view", "side"))
	_offset = TRACK_SIDE
	_look_y = TRACK_LOOK_Y
	if view == "back":
		_offset = Vector3(-2.3, 0.45, -1.1)
	elif view == "pouch":
		_offset = Vector3(-0.45, -0.35, 0.95)
		_look_y = 0.80
	var s := []
	for v in MOTIONS:
		if want != "1" and not want.split(",").has(String(v[0])):
			continue
		for mode in ["off", "on"]:
			s.append({"ticks": 2, "setup": func(): _place(d, v[1], RoomGeo.v3(v[2]), RoomGeo.v3(v[3]), mode == "on")})
			# 待機で落ち着かせる（描かない）
			s.append({"ticks": 90, "input": {}})
			var seq: Array = v[4]
			for i in seq.size():
				var step := {"ticks": int(seq[i][0]), "input": seq[i][1]}
				var cue: String = v[5]
				if (cue == "start" and i == 0) or (cue == "end" and i == seq.size() - 1) or (cue == "land" and i == 0):
					var nm := "haru_%s_%s" % [v[0], mode]
					step["setup"] = func(): _strip(d, nm, cue == "land")
				s.append(step)
	for v in STILLS:
		if want != "1" and not want.split(",").has(String(v[0])):
			continue
		for mode in ["off", "on"]:
			var full: Array = v[4]
			var feet: Array = v[5]
			s.append({"ticks": 2, "setup": func():
				_place(d, v[1], RoomGeo.v3(v[2]), RoomGeo.v3(v[3]), mode == "on")
				_fix_camera(d, RoomGeo.v3(full[0]), RoomGeo.v3(full[1]), float(full[2]))})
			s.append({"ticks": 50, "input": {}})
			s.append({"ticks": 6, "input": {}, "setup": func(): _still(d, "haru_%s_%s" % [v[0], mode])})
			s.append({"ticks": 8, "input": {}, "setup": func():
				_fix_camera(d, RoomGeo.v3(feet[0]), RoomGeo.v3(feet[1]), float(feet[2]))})
			s.append({"ticks": 6, "input": {}, "setup": func(): _still(d, "haru_%s_%s_feet" % [v[0], mode])})
			s.append({"ticks": 8, "input": {}})
	s.append({"ticks": 2, "setup": func(): _release(d)})
	return s


## --haru_secondary_bench：混んだ町の部屋（中段の広場）で、ゲームのカメラのまま、ハルを円く走らせ・止め・跳ばせながら
## 2 次の動きを切った（off）・入れた（on）で BENCH_TICKS こまずつ描き（off → on → off → on）、1 こまの実時間・処理・物理の刻み・
## 2 次の動きの時間（HaruSway・FootIK の修飾、足の接地の光線）を出す。画面なし（tools/godot.sh run）でも動き、そのときは
## 描かない 1 こま（CPU だけ）の時間になる。--bench_pairs=<n> で組の数
const BENCH_ROOM := "ch1.mid:start"
const BENCH_TICKS := 150
static var _bench := {}


static func bench_steps(d) -> Array:
	var s := []
	# --bench_pairs=<n>：切った・入れたの組の数（既定 2。描く計測は 1 組で約 6 分）
	var modes := []
	for k in maxi(1, int(String(d.main.args.get("bench_pairs", "2")))):
		modes.append_array(["off", "on"])
	for mode in modes:
		s.append({"ticks": 2, "setup": func():
			var m = d.main
			var g: GameSim = m.game
			var parts := BENCH_ROOM.split(":")
			if g.room_id != parts[0]:
				g.load_room(parts[0], parts[1])
			for t in g.triggers:
				t.fired = true
			g.god_mode = true
			var mk: Dictionary = g.marker(parts[1])
			d._stand(mk.pos, mk.pos + U.yaw_to_dir(mk.yaw))
			m.player_view.set_secondary(mode == "on")
			m.camera.current = true
			m.hud.visible = true})
		s.append({"ticks": 90, "input_fn": func(i): return _bench_input(i)})
		s.append({"ticks": BENCH_TICKS, "input_fn": func(i): return _bench_input(i + 90), "setup": func(): _bench_run(d, mode)})
		s.append({"ticks": 4, "input": {}})
	return s


## 円く走る 2 秒 → 止まる 1 秒 → 跳ぶ → 待つ（4 秒で一回り）
static func _bench_input(i: int) -> Dictionary:
	var k := i % 240
	if k < 120:
		var a := i * 0.035
		return {"move_x": sin(a), "move_y": cos(a)}
	if k == 180 or k == 181:
		return {"jump": true}
	return {}


static func _bench_run(d, mode: String) -> void:
	RenderingServer.render_loop_enabled = true
	HaruSway.prof_usec = 0
	HaruSway.prof_calls = 0
	FootIK.prof_usec = 0
	FootIK.prof_calls = 0
	PlayerView.prof_sync_usec = 0
	HaruSway.profile = true
	FootIK.profile = true
	# 画面なしでは描かないので、こまの区切りは process_frame で取る
	var tick: Signal = RenderingServer.frame_post_draw
	if DisplayServer.get_name() == "headless":
		tick = (d.main as Node).get_tree().process_frame
	await tick
	var frames := []
	var proc := 0.0
	var phys := 0.0
	var last := Time.get_ticks_usec()
	for k in BENCH_TICKS - 8:
		await tick
		var now := Time.get_ticks_usec()
		frames.append(now - last)
		last = now
		proc += Performance.get_monitor(Performance.TIME_PROCESS) * 1000.0
		phys += Performance.get_monitor(Performance.TIME_PHYSICS_PROCESS) * 1000.0
	HaruSway.profile = false
	FootIK.profile = false
	var n := frames.size()
	var sorted := frames.duplicate()
	sorted.sort()
	var sum := 0.0
	for f in frames:
		sum += f
	var key := "%s_%s" % [mode, RenderingServer.get_current_rendering_method()]
	var r := {"frame_ms": sum / n / 1000.0, "p95_ms": float(sorted[int(n * 0.95)]) / 1000.0, "process_ms": proc / n,
		"physics_ms": phys / n, "sway_us": float(HaruSway.prof_usec) / n, "ik_us": float(FootIK.prof_usec) / n,
		"sync_us": float(PlayerView.prof_sync_usec) / n, "sway_calls": float(HaruSway.prof_calls) / n}
	if not _bench.has(key):
		_bench[key] = []
	_bench[key].append(r)
	print("計測 %s（%d こま、%s %s %s）：1 こま 平均 %.2f ms・95%% %.2f ms／処理 %.3f ms・物理の刻み %.3f ms／揺れ %.1f µs（%.1f 回）・足の接地 %.1f µs・光線 %.1f µs（1 こまあたり）" % [
		mode, n, DisplayServer.get_name(), RenderingServer.get_current_rendering_method(), str(DisplayServer.window_get_size()),
		r.frame_ms, r.p95_ms, r.process_ms, r.physics_ms, r.sway_us,
		r.sway_calls, r.ik_us, r.sync_us])
	RenderingServer.render_loop_enabled = false


## 部屋を読み（違うときだけ）、ハルを置き、2 次の動きを入れる・切る。動作は待機の頭から
static func _place(d, room: String, at: Vector3, look: Vector3, on: bool) -> void:
	var m = d.main
	var g: GameSim = m.game
	g.god_mode = true
	var parts := room.split(":")
	if g.room_id != parts[0]:
		g.load_room(parts[0], parts[1] if parts.size() > 1 else "")
	for t in g.triggers:
		t.fired = true
	d._stand(at, look)
	var pv: PlayerView = m.player_view
	pv.set_secondary(on)
	if pv.anim:
		pv.current = ""
		pv.anim.play("idle", 0.0)
		pv.anim.seek(0.0, true)
		pv.current = "idle"
	m.hud.visible = false
	_hide_nagomi(d, true)
	# エフェクトの乱数を同じ種から：切った・入れたの 2 回でダッシュの光の筋などが同じに出る（比べの違いの行に混ざらない）
	if m.fx != null:
		m.fx._rng.seed = 20261020
		m.fx.ambient._rng.seed = 20261020
	_warm_render()


## 置いたあと WARM_FRAMES こま描く（撮る間でなければ、描くのをまた止める）
static func _warm_render() -> void:
	if DisplayServer.get_name() == "headless":
		return
	RenderingServer.render_loop_enabled = true
	for i in WARM_FRAMES:
		await RenderingServer.frame_post_draw
	if not _capturing:
		RenderingServer.render_loop_enabled = false


## ナゴミ（止まるとハルの頭の後ろに浮く）を隠す・戻す：後ろの房を隠さないように（撮影だけ。中身・ほかの見た目は変えない）
static func _hide_nagomi(d, hide: bool) -> void:
	var nv: NagomiView = d.main.nagomi_view
	if nv == null:
		return
	if nv.model != null:
		nv.model.visible = not hide
	if nv.glow != null:
		nv.glow.visible = not hide


## ハルの横から付いて動くカメラ（水平だけ。高さは床から決める）。描く直前（process_frame）に、描かれるハルの位置へ置く
static func _track_camera(d) -> void:
	if not _follow or _cam == null or not is_instance_valid(_cam):
		return
	var pv: PlayerView = d.main.player_view
	var p := pv.get_global_transform_interpolated().origin
	var ground: float = d.main.game.player.pos.y if d.main.game.player.grounded else _cam.get_meta("ground", p.y)
	_cam.set_meta("ground", ground)
	var base := Vector3(p.x, ground, p.z)
	_cam.global_position = base + _offset + Vector3(0, TRACK_EYE_Y, 0)
	_cam.look_at(base + Vector3(0, _look_y, 0), Vector3.UP)


static func _ensure_camera(d) -> void:
	if _cam == null or not is_instance_valid(_cam):
		_cam = Camera3D.new()
		_cam.physics_interpolation_mode = Node.PHYSICS_INTERPOLATION_MODE_OFF
		d.main.add_child(_cam)
		d.get_tree().process_frame.connect(func(): _track_camera(d))
	_cam.current = true
	d.main.hud.visible = false


static func _fix_camera(d, eye: Vector3, target: Vector3, fov: float) -> void:
	_ensure_camera(d)
	_follow = false
	_cam.fov = fov
	_cam.global_position = eye
	_cam.look_at(target, Vector3.UP)


## 動きのこま：撮り始めの合図から EVERY 刻みごとに FRAMES 枚（その間もゲームと描画は止めない）。land：着地の刻みまで待つ
static func _strip(d, name: String, land: bool) -> void:
	_ensure_camera(d)
	_cam.fov = TRACK_FOV
	if _cam.has_meta("ground"):
		_cam.remove_meta("ground")
	_follow = true
	_capturing = true
	RenderingServer.render_loop_enabled = true
	var g: GameSim = d.main.game
	if land:
		# 跳んで、空中にいる間を待ち、着地した刻みから撮る
		var air := false
		for i in 240:
			await RenderingServer.frame_post_draw
			if not g.player.grounded:
				air = true
			elif air:
				break
	var pv: PlayerView = d.main.player_view
	for k in FRAMES:
		for i in (1 if k == 0 else EVERY):
			await RenderingServer.frame_post_draw
		var img: Image = d.get_viewport().get_texture().get_image()
		var path := "%s/%s_%d.png" % [d.out_dir, name, k]
		img.save_png(path)
		var line := "こま：%s　速さ %.1f　接地 %s　動作 %s" % [path, g.player.speed(), str(g.player.grounded), pv.current]
		if pv.sway != null:
			line += "　揺れの最大 %.1f 度" % rad_to_deg(pv.sway.last_max)
		print(line)
	_capturing = false
	RenderingServer.render_loop_enabled = false


## 止まった絵：描いて撮る。足の接地の値も出す
static func _still(d, name: String) -> void:
	_capturing = true
	RenderingServer.render_loop_enabled = true
	for i in 3:
		await RenderingServer.frame_post_draw
	var img: Image = d.get_viewport().get_texture().get_image()
	var path := "%s/%s.png" % [d.out_dir, name]
	img.save_png(path)
	var pv: PlayerView = d.main.player_view
	var g: GameSim = d.main.game
	var ik := pv.foot_ik
	print("止まった絵：%s　位置 %s　接地 %s　足の接地の効き %.2f　腰 %.3f m　足の上げ 左 %.3f・右 %.3f m" % [path, str(g.player.pos),
		str(g.player.grounded), ik.weight if ik else 0.0, ik.last_drop if ik else 0.0, ik.last_lift[0] if ik else 0.0,
		ik.last_lift[1] if ik else 0.0])
	_capturing = false
	RenderingServer.render_loop_enabled = false


static func _release(d) -> void:
	_follow = false
	if _cam != null and is_instance_valid(_cam):
		_cam.queue_free()
	_cam = null
	d.main.camera.current = true
	d.main.hud.visible = true
	d.main.player_view.set_secondary(PlayerView.secondary_default)
	_hide_nagomi(d, false)
