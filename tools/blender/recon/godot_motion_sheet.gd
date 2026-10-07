extends SceneTree
## ハル（haru_r）の動作のこまを、Godot の中（ゲームと同じ PlayerView と光）で撮って 1 枚にまとめる。
##   tools/godot.sh shot --script /abs/tools/blender/recon/godot_motion_sheet.gd -- <出力の PNG> [動作=combo1] [こま間隔=1] [モデルの res:// パス]
## 上の段：ゲームのカメラに近い真後ろ（仰角 12 度）。下の段：左前 45 度。横に時間（60fps のこま）。1 行は最大 10 こま。
## 座標は glTF（Godot）：キャラクターの正面 +Z、本人の左 +X、上 +Y。

const TILE := Vector2i(220, 260)
const COLS := 10
const FPS := 60.0

var out_path := ""
var clip := "combo1"
var every := 1
var model_path := "res://assets/models/haru_r.glb"
var pv: PlayerView
var cam: Camera3D


func _initialize() -> void:
	var args := OS.get_cmdline_user_args()
	out_path = args[0] if args.size() > 0 else "user://haru_motion.png"
	if args.size() > 1:
		clip = args[1]
	if args.size() > 2:
		every = maxi(1, int(args[2]))
	if args.size() > 3:
		model_path = args[3]
	_run.call_deferred()


func _run() -> void:
	root.size = TILE
	var world := Node3D.new()
	root.add_child(world)
	EnvironmentSetup.build(world)
	var floor_mesh := MeshInstance3D.new()
	var pm := PlaneMesh.new()
	pm.size = Vector2(6, 6)
	floor_mesh.mesh = pm
	var fm := StandardMaterial3D.new()
	fm.albedo_color = Color(0.42, 0.42, 0.44)
	floor_mesh.material_override = fm
	world.add_child(floor_mesh)
	pv = PlayerView.new()
	world.add_child(pv)
	pv.load_model(model_path, "soft")
	pv.set_expression(0)
	cam = Camera3D.new()
	cam.projection = Camera3D.PROJECTION_ORTHOGONAL
	world.add_child(cam)
	cam.current = true
	if not pv.anim or not pv.anim.has_animation(clip):
		print("動作が無い：", clip)
		quit(1)
		return
	var length: float = pv.anim.get_animation(clip).length
	var n := int(round(length * FPS))
	var frames: Array[int] = []
	for f in range(0, n + 1, every):
		frames.append(f)
	var views := [[180.0, 12.0], [45.0, 10.0]]
	var rows: Array = []
	for v in views:
		var tiles: Array[Image] = []
		for f in frames:
			_pose(clip, minf(length - 0.001, f / FPS), true)
			tiles.append(await _shot(v[0], Vector3(0, 0.85, 0), 2.1, v[1]))
		rows.append(tiles)
	# 並べる：方向ごとに、1 行 COLS こま
	var per_view := int(ceil(frames.size() / float(COLS)))
	var sheet := Image.create(TILE.x * mini(COLS, frames.size()), TILE.y * per_view * views.size(), false, Image.FORMAT_RGBA8)
	sheet.fill(Color(0.13, 0.13, 0.14))
	for vi in rows.size():
		var tiles: Array[Image] = rows[vi]
		for k in tiles.size():
			var t: Image = tiles[k]
			t.convert(Image.FORMAT_RGBA8)
			var x: int = (k % COLS) * TILE.x
			var y: int = (vi * per_view + k / COLS) * TILE.y
			sheet.blit_rect(t, Rect2i(Vector2i.ZERO, TILE), Vector2i(x, y))
	var err := sheet.save_png(out_path)
	print("撮影：%s（%s、%d こま × %d 方向、%s）" % [out_path, clip, frames.size(), views.size(), error_string(err)])
	quit(0 if err == OK else 1)


## 動作 name の t 秒の姿勢で止める。blade は光刃を出すか
func _pose(name: String, t: float, blade := false) -> void:
	if pv.anim and pv.anim.has_animation(name):
		pv.anim.play(name, 0.0)
		pv.anim.seek(t, true)
		pv.anim.pause()
	if pv.blade:
		pv.blade.visible = blade


## 方位角 az 度（0 = 正面、90 = 本人の右の真横、180 = 背面）・仰角 el 度から正投影で描く
func _shot(az: float, target: Vector3, size: float, el: float) -> Image:
	var a := deg_to_rad(az)
	var e := deg_to_rad(el)
	var d := Vector3(-sin(a) * cos(e), sin(e), cos(a) * cos(e))
	cam.size = size
	cam.position = target + d * 4.0
	cam.look_at(target, Vector3.UP)
	for _i in 3:
		await process_frame
	await RenderingServer.frame_post_draw
	return root.get_texture().get_image()
