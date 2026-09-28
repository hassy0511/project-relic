extends SceneTree
## 絵から起こしたハル（haru_r）を Godot の中で描いて、確認の画像を 1 枚にまとめる（レビュー用）。
##   tools/godot.sh shot --script /abs/tools/blender/recon/godot_showcase.gd -- <出力の PNG> [モデルの res:// パス]
## ゲームと同じ PlayerView（材質の複製・表情の uv1_offset・光刃・目印）と同じ光（EnvironmentSetup）で描く。
## 上の段：全身（正面・右前斜め 31 度・右真横・背面、idle）。中の段：顔の近写を 4 表情。
## 下の段：run（銃）・combo1（光刃）・charge（光刃）・構え（右前斜め）。
## 座標は glTF（Godot）：キャラクターの正面 +Z、本人の左 +X、上 +Y。

const TILE := Vector2i(400, 450)
const COLS := 4

var out_path := ""
var model_path := "res://assets/models/haru_r.glb"
var pv: PlayerView
var cam: Camera3D
var tiles: Array[Image] = []


func _initialize() -> void:
	var args := OS.get_cmdline_user_args()
	out_path = args[0] if args.size() > 0 else "user://haru_showcase.png"
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

	# 全身（idle の 1 フレーム目）
	for az in [0.0, 31.0, 90.0, 180.0]:
		_pose("idle", 0.0)
		await _shot(az, Vector3(0, 0.80, 0), 1.75, 12.0)
	# 顔の近写（正面）を 4 表情
	for i in 4:
		_pose("idle", 0.0)
		pv.set_expression(i)
		await _shot(0.0, Vector3(0, 1.33, 0), 0.42, 0.0)
	pv.set_expression(0)
	# 動作
	_pose("run", 0.10)
	await _shot(31.0, Vector3(0, 0.80, 0), 1.9, 12.0)
	_pose("combo1", 0.17, true)
	await _shot(31.0, Vector3(0, 0.80, 0), 1.9, 12.0)
	_pose("charge", 0.40, true)
	await _shot(31.0, Vector3(0, 0.80, 0), 1.9, 12.0)
	_pose("combo3", 0.27, true)
	await _shot(-40.0, Vector3(0, 0.80, 0), 1.9, 12.0)

	var rows := int(ceil(tiles.size() / float(COLS)))
	var sheet := Image.create(TILE.x * COLS, TILE.y * rows, false, Image.FORMAT_RGBA8)
	for k in tiles.size():
		var t: Image = tiles[k]
		t.convert(Image.FORMAT_RGBA8)
		sheet.blit_rect(t, Rect2i(Vector2i.ZERO, TILE), Vector2i((k % COLS) * TILE.x, (k / COLS) * TILE.y))
	var err := sheet.save_png(out_path)
	print("撮影：%s（%d 枚、%s）" % [out_path, tiles.size(), error_string(err)])
	quit(0 if err == OK else 1)


## 動作 name の t 秒の姿勢で止める。blade は光刃を出すか
func _pose(name: String, t: float, blade := false) -> void:
	if pv.anim and pv.anim.has_animation(name):
		pv.anim.play(name, 0.0)
		pv.anim.seek(t, true)
		pv.anim.pause()
	if pv.blade:
		pv.blade.visible = blade


## 方位角 az 度（0 = 正面、90 = 本人の右の真横、180 = 背面）・仰角 el 度から正投影で描いて 1 枚に加える
func _shot(az: float, target: Vector3, size: float, el: float) -> void:
	var a := deg_to_rad(az)
	var e := deg_to_rad(el)
	var d := Vector3(-sin(a) * cos(e), sin(e), cos(a) * cos(e))
	cam.size = size
	cam.position = target + d * 4.0
	cam.look_at(target, Vector3.UP)
	for _i in 4:
		await process_frame
	await RenderingServer.frame_post_draw
	tiles.append(root.get_texture().get_image())
