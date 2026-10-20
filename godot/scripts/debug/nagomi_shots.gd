class_name NagomiShots
## ナゴミの背中のユニットへの着地（NagomiView）の確かめ：Demo（--demo=<フォルダ>）から使う。
##   --nagomi_shots                    走り出して背中へ入るコマ・止まって肩の横へ出るコマ（入り始め・出始めから 0.1 秒ごとに 6 枚）と、
##                                     肩の横・付いている（走りながら・立ったまま）の静止画
##   --nagomi_cams=game,close,side     撮るカメラ（既定は全部）：game＝ふだんのゲームのカメラ（画面の表示つき）、
##                                     close＝ハルの右後ろの近いカメラ、side＝ハルの右横のやや後ろの近いカメラ（どちらもハルの見た目の子で、いっしょに動く）
##   --nagomi_room=ch1.r08:start --nagomi_at=4,-7.5 --nagomi_look=4,10   場所（部屋と目印、立つ所、走る向き）
## 出力：<フォルダ>/nd_<カメラ>_<場面>[_<コマ>].png。カメラごとに同じ動き（ゲームは決まった入力で同じに進む）を 1 回ずつ撮る。
## 撮る間も描画とゲームの刻みを止めない（--fixed-fps 60 で 1 こま = 1 刻み）。見た目だけ：ゲームの中身には手を加えない

## 第 1 章の本筋のフラグ（駆動回廊まで：胴・左腕・脚のフレームが全部付き、ナゴミがいる）
const FLAGS := ["ch1.opening_done", "ch1.chores_started", "ch1.t_move", "ch1.t_jump", "ch1.t_shoot", "ch1.t_dash", "ch1.nico_ran",
	"ch1.nico_rescued", "ch1.scolded", "ch1.debt_scene", "ch1.night", "ch1.ordo_stopped", "ch1.plaza_done", "ch1.got_spark",
	"ch1.fell_to_b2", "ch1.chase_seen", "ch1.r07.seal_open", "ch1.frame_fitted", "ch1.r08.trained", "ch1.blade_online",
	"ch1.first_beacon", "ch1.drive_powered"]
## 近いカメラ（ハルの足元の座標：+Z が正面、-X がハルの右）：[目, 見る所, 画角]
const CAMS := {
	"close": [Vector3(-0.95, 1.85, -1.75), Vector3(-0.1, 1.2, 0.15), 45.0],
	"side": [Vector3(-2.1, 1.45, -0.55), Vector3(0.0, 1.2, -0.15), 40.0],
}

static var _cam: Camera3D = null


static func steps(d) -> Array:
	var m = d.main
	var cams := String(m.args.get("nagomi_cams", "game,close,side")).split(",", false)
	var room := String(m.args.get("nagomi_room", "ch1.r08:start")).split(":", true, 1)
	var at := _xz(String(m.args.get("nagomi_at", "4,-7.5")))
	var look := _xz(String(m.args.get("nagomi_look", "4,10")))
	var s := []
	for cam in cams:
		s.append({"ticks": 2, "setup": func():
			var g: GameSim = m.game
			g.god_mode = true
			for f in FLAGS:
				g.set_flag(f)
			g.load_room(room[0], room[1] if room.size() > 1 else "start")
			for t in g.triggers:
				t.fired = true})
		s.append({"ticks": 2, "setup": func():
			m.game.story.stop_all()
			m.game.player_locked = false
			d._stand(at, look)
			m.nagomi_view.force = ""
			_use_cam(d, cam)})
		# 肩の横で落ち着くまで待つ → 静止画
		s.append({"ticks": 100, "input": {}})
		s.append({"ticks": 1, "shot": "nd_%s_out" % cam, "input": {}})
		# 走り出す：背中へ入り始めた刻みから 0.1 秒ごとに 6 枚
		s.append({"ticks": 60, "input": {"move_y": 1.0}, "setup": func(): _strip(d, "nd_%s_dock" % cam, NagomiView.Dock.DOCKING)})
		s.append({"ticks": 14, "input": {"move_y": 1.0}})
		s.append({"ticks": 1, "shot": "nd_%s_docked_run" % cam, "input": {"move_y": 1.0}})
		# 止まる：肩の横へ出始めた刻みから 0.1 秒ごとに 6 枚
		s.append({"ticks": 110, "input": {}, "setup": func(): _strip(d, "nd_%s_undock" % cam, NagomiView.Dock.UNDOCKING)})
		s.append({"ticks": 30, "input": {}})
		s.append({"ticks": 1, "shot": "nd_%s_out_after" % cam, "input": {}})
		# 立ったまま付けた姿（確かめ用の強制 --nagomi=dock と同じ）：背中の板の光
		s.append({"ticks": 50, "input": {}, "setup": func(): m.nagomi_view.force = "dock"})
		s.append({"ticks": 1, "shot": "nd_%s_docked_stand" % cam, "input": {}})
		s.append({"ticks": 2, "input": {}, "setup": func(): m.nagomi_view.force = ""})
	s.append({"ticks": 2, "setup": func(): _release(d)})
	return s


static func _xz(t: String) -> Vector3:
	var p := t.split(",")
	return Vector3(float(p[0]), 0.0, float(p[1])) if p.size() >= 2 else Vector3.ZERO


## カメラを選ぶ：game はふだんのカメラ（画面の表示つき）、ほかはハルの見た目の子の Camera3D（表示を隠す）
static func _use_cam(d, name: String) -> void:
	var m = d.main
	if _cam != null and is_instance_valid(_cam):
		_cam.queue_free()
	_cam = null
	if not CAMS.has(name):
		m.camera.current = true
		m.hud.visible = true
		return
	var c: Array = CAMS[name]
	_cam = Camera3D.new()
	m.player_view.add_child(_cam)
	_cam.fov = float(c[2])
	# ハルの見た目の座標で置く（look_at は世界の座標なので使わない）
	var eye: Vector3 = c[0]
	var at: Vector3 = c[1]
	_cam.transform = Transform3D(Basis.looking_at(at - eye, Vector3.UP), eye)
	_cam.current = true
	m.hud.visible = false


static func _release(d) -> void:
	if _cam != null and is_instance_valid(_cam):
		_cam.queue_free()
	_cam = null
	d.main.camera.current = true
	d.main.hud.visible = true


## コマを撮る：ナゴミの状態が want になった刻み（入り始め・出始め）から 6 刻みごと（0.1 秒）に 6 枚。その間もゲームと描画は止めない
static func _strip(d, name: String, want: int) -> void:
	var nv: NagomiView = d.main.nagomi_view
	RenderingServer.render_loop_enabled = true
	for i in 200:
		await RenderingServer.frame_post_draw
		if nv.dock_state == want:
			break
	for k in 6:
		if k > 0:
			for i in 6:
				await RenderingServer.frame_post_draw
		var img: Image = d.get_viewport().get_texture().get_image()
		var path := "%s/%s_%d.png" % [d.out_dir, name, k]
		img.save_png(path)
		print("コマ：%s　状態 %s　t %.2f" % [path, NagomiView.Dock.keys()[nv.dock_state], nv._t])
	RenderingServer.render_loop_enabled = false
