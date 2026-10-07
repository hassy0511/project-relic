extends SceneTree
## ハル（haru_r）の外装フレームの段（PlayerView.set_frame_parts）を、Godot の中（ゲームと同じ PlayerView と光）で撮って並べる。
##   tools/godot.sh shot --script /abs/tools/blender/recon/godot_frame_stages.gd -- <出力の PNG> [モデルの res:// パス]
## 行：なし（作業着だけ）・胴・胴＋腕・全部。列：正面・右前 45 度・左の真横・背面・ゲームのカメラ（真後ろ、見下ろし 12 度）。
## 姿勢は待機の 0.5 秒。座標は glTF（Godot）：キャラクターの正面 +Z、本人の左 +X、上 +Y。

const TILE := Vector2i(300, 420)
const STATES := [[false, false, false], [true, false, false], [true, true, false], [true, true, true]]
const VIEWS := [[0.0, 4.0, 1.85], [45.0, 4.0, 1.85], [270.0, 4.0, 1.85], [180.0, 4.0, 1.85], [180.0, 12.0, 1.85]]

var out_path := ""
var model_path := "res://assets/models/haru_r.glb"
var pv: PlayerView
var cam: Camera3D


func _initialize() -> void:
	var args := OS.get_cmdline_user_args()
	out_path = args[0] if args.size() > 0 else "user://haru_frame_stages.png"
	if args.size() > 1:
		model_path = args[1]
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
	if pv.anim and pv.anim.has_animation("idle"):
		pv.anim.play("idle", 0.0)
		pv.anim.seek(0.5, true)
		pv.anim.pause()
	var sheet := Image.create(TILE.x * VIEWS.size(), TILE.y * STATES.size(), false, Image.FORMAT_RGBA8)
	for si in STATES.size():
		var s: Array = STATES[si]
		pv.set_frame_parts(s[0], s[1], s[2])
		for vi in VIEWS.size():
			var v: Array = VIEWS[vi]
			var img := await _shot(v[0], Vector3(0, 0.8, 0), v[2], v[1])
			img.convert(Image.FORMAT_RGBA8)
			sheet.blit_rect(img, Rect2i(Vector2i.ZERO, TILE), Vector2i(vi * TILE.x, si * TILE.y))
	var err := sheet.save_png(out_path)
	print("撮影：%s（%s）" % [out_path, error_string(err)])
	quit(0 if err == OK else 1)


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
