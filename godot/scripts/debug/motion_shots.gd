class_name MotionShots
## 飾りの動き（風で揺れる布・垂れたケーブル・落砂の流れ・蒸気。42 章 14.2.2）の確かめ：決まった向きから、決まった間隔でコマを撮る。
## Demo（--demo=<フォルダ>）から使う：
##   --motion_shots            全部の向き（motion_<名前>_<コマ>.png）
##   --motion_shots=flag,sand  名前で選ぶ
##   --motion_frames=6 --motion_every=15   コマの数と間隔（刻み。15 刻み = 0.25 秒）
## 静止画では動きが分からないので、撮る間も描画とゲームの刻みを止めない（毎こま描く。シェーダーの TIME と Fx の時計が
## ちょうど同じだけ進む：--fixed-fps 60 で 1 こま = 1 刻み = 1/60 秒）。カメラは自分の Camera3D で固定し、ハルは画面の外に立たせる。
## 見た目だけ：ゲームの中身には手を加えない（部屋を読み、ハルを置くだけ）

## [名前, 部屋, 目印, ハルの立つ所, 目, 見る所, 画角（度）]
const VIEWS := [
	["flag", "ch1.lower", "start", [26.0, 0, -9.0], [28.6, 6.5, -0.6], [30.6, 6.7, 2.6], 40.0],
	["laundry", "ch1.lower", "start", [21.0, 0, -9.0], [22.6, 2.1, -4.4], [26.4, 2.0, -0.4], 45.0],
	["mid_north", "ch1.mid", "start", [0, 0, 3.0], [0, 2.6, 6.5], [0, 5.4, 18.0], 50.0],
	["sand", "ch1.r06", "fall", [-3.0, 0, -4.0], [-0.6, 1.25, -8.0], [1.4, 1.0, -10.6], 40.0],
	["steam", "ch1.r06", "fall", [-2.0, 0, -8.0], [-3.7, 1.9, -12.3], [-5.9, 1.95, -14.2], 45.0],
	["cables", "ch1.r06", "fall", [0, 0, -6.0], [0, 4.0, -10.4], [0, 5.5, -15.0], 45.0],
]

static var _cam: Camera3D = null


static func steps(d) -> Array:
	var m = d.main
	var want := String(m.args.get("motion_shots", "1"))
	var frames := int(m.args.get("motion_frames", "6"))
	var every := int(m.args.get("motion_every", "15"))
	var s := []
	for v in VIEWS:
		if want != "1" and not want.split(",").has(String(v[0])):
			continue
		s.append({"ticks": 2, "setup": func():
			var g: GameSim = m.game
			g.god_mode = true
			if g.room_id != v[1]:
				g.load_room(v[1], v[2])
			for t in g.triggers:
				t.fired = true
			d._stand(RoomGeo.v3(v[3]), RoomGeo.v3(v[5]))
			_fix_camera(d, RoomGeo.v3(v[4]), RoomGeo.v3(v[5]), float(v[6]))})
		# 落ち着くまで待つ（砂ぼこり・蒸気の粒が出そろう。この間は描かない：撮る間だけ毎こま描く）
		s.append({"ticks": 240, "input": {}})
		s.append({"ticks": frames * every + 4, "input": {}, "setup": func(): _strip(d, String(v[0]), frames, every)})
	s.append({"ticks": 2, "setup": func(): _release(d)})
	return s


## 固定のカメラ（プレイヤーのカメラの代わりに使う）。HUD は隠す
static func _fix_camera(d, eye: Vector3, target: Vector3, fov: float) -> void:
	if _cam == null or not is_instance_valid(_cam):
		_cam = Camera3D.new()
		_cam.physics_interpolation_mode = Node.PHYSICS_INTERPOLATION_MODE_OFF
		d.main.add_child(_cam)
	_cam.fov = fov
	_cam.global_position = eye
	_cam.look_at(target, Vector3.UP)
	_cam.current = true
	d.main.hud.visible = false


static func _release(d) -> void:
	if _cam != null and is_instance_valid(_cam):
		_cam.queue_free()
	_cam = null
	d.main.camera.current = true
	d.main.hud.visible = true


## コマを撮る：今のこまから every こまごとに frames 枚（その間もゲームと描画は止めない）。
## 描画はここで入れ直す（Demo の始めの撮影「01_start」が、待つ間に描画を止めることがある）。蒸気は、撮る間に強い吹き出しが入るように合わせる
static func _strip(d, name: String, frames: int, every: int) -> void:
	RenderingServer.render_loop_enabled = true
	if name == "steam" and d.main.fx != null:
		d.main.fx.ambient.burst_soon(0.3)
	for k in frames:
		for i in (1 if k == 0 else every):
			await RenderingServer.frame_post_draw
		var img: Image = d.get_viewport().get_texture().get_image()
		var path := "%s/motion_%s_%d.png" % [d.out_dir, name, k]
		img.save_png(path)
		print("コマ：%s（%d 刻み目）　描画 %d 回" % [path, k * every,
			RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_DRAW_CALLS_IN_FRAME)])
	# 次の向きの待つ間は描かない（速く進む）
	RenderingServer.render_loop_enabled = false
