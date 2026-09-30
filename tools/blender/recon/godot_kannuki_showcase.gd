extends SceneTree
## 大番機「閂」（kannuki.glb）を Godot の中で描いて、確認の画像を 1 枚にまとめる（レビュー用。ゲームにはまだ出ない）。
##   tools/godot.sh shot --resolution 1600x600 --script /abs/tools/blender/recon/godot_kannuki_showcase.gd -- <出力の PNG>
## 1 段目：ハル（155 cm）と並べた全体（腕を畳んだ待機）。
## 2 段目：真上（腕を畳んだ姿勢 | 腕を広げた姿勢）  3 段目：真横（畳んだ | 広げた）
## 4 段目：錠前核（蓋と板が閉じた | 蓋が 0.6 m 滑って板が開いた）  5 段目：削岩錐が回っている姿勢（腕を伸ばして自転 60 度）| 正面から広げた姿
## 座標は glTF（Godot）：正面（錐の前端）+Z、上 +Y。部品の回転はローカル +X が軸（元の姿勢 * Basis(RIGHT, 角度)）。

const TILE := Vector2i(800, 400)
const WIDE := Vector2i(1600, 600)
const ARMS := ["fl", "fr", "rl", "rr"]
# pose.json（kannuki.py が出す）の elbow_straight_deg：肘を伸ばす角
const ELBOW_STRAIGHT := -93.9

var out_path := ""
var cam: Camera3D
var world: Node3D
var model: Node3D
var rest := {}
var tiles: Array[Image] = []
var wide: Image


func _initialize() -> void:
	var args := OS.get_cmdline_user_args()
	out_path = args[0] if args.size() > 0 else "user://kannuki_showcase.png"
	_run.call_deferred()


func _run() -> void:
	world = Node3D.new()
	root.add_child(world)
	EnvironmentSetup.build(world)
	var floor_mesh := MeshInstance3D.new()
	var pm := PlaneMesh.new()
	pm.size = Vector2(60, 60)
	floor_mesh.mesh = pm
	var fm := StandardMaterial3D.new()
	fm.albedo_color = Color(0.42, 0.42, 0.44)
	floor_mesh.material_override = fm
	world.add_child(floor_mesh)
	model = (load("res://assets/models/kannuki.glb") as PackedScene).instantiate() as Node3D
	world.add_child(model)
	for n in model.find_children("*", "Node3D", true, false):
		rest[n.name] = n.transform
	var haru := (load("res://assets/models/haru_r.glb") as PackedScene).instantiate() as Node3D
	haru.position = Vector3(3.6, 0, 3.4)
	haru.rotation.y = deg_to_rad(-20.0)
	world.add_child(haru)
	cam = Camera3D.new()
	world.add_child(cam)
	cam.current = true

	root.size = WIDE
	cam.projection = Camera3D.PROJECTION_PERSPECTIVE
	cam.fov = 32.0
	cam.position = Vector3(10.5, 5.5, 12.5)
	cam.look_at(Vector3(0.3, 1.9, 0.6), Vector3.UP)
	await _frames()
	wide = root.get_texture().get_image()
	haru.queue_free()

	root.size = TILE
	cam.projection = Camera3D.PROJECTION_ORTHOGONAL
	# 2 段目：真上
	_pose(0.0, 0.0, 0.0, 0.0, false)
	await _shot(Vector3(0, 0, 0.2), 7.6, 90.0, 89.0)
	_pose(40.0, 25.0, ELBOW_STRAIGHT, 0.0, false)
	await _shot(Vector3(0, 0, 0.2), 10.5, 90.0, 89.0)
	# 3 段目：真横（+X 側から。前端が右）
	_pose(0.0, 0.0, 0.0, 0.0, false)
	await _shot(Vector3(0, 2.5, 0), 6.6, 90.0, 0.0)
	_pose(40.0, 25.0, ELBOW_STRAIGHT, 0.0, false)
	await _shot(Vector3(0, 2.5, 0), 7.6, 90.0, 0.0)
	# 4 段目：錠前核
	_pose(0.0, 0.0, 0.0, 0.0, false)
	await _shot(Vector3(0, 4.0, 0.2), 4.2, 60.0, 50.0)
	_pose(0.0, 0.0, 0.0, 0.0, true)
	await _shot(Vector3(0, 4.0, 0.2), 4.2, 60.0, 50.0)
	# 5 段目：削岩錐が回る姿勢（腕を伸ばして、削岩錐を 60 度回した）・正面から
	_pose(30.0, 20.0, ELBOW_STRAIGHT, 60.0, false)
	await _shot(Vector3(2.4, 2.4, 3.4), 5.0, 35.0, 12.0)
	_pose(45.0, 0.0, ELBOW_STRAIGHT * 0.5, 0.0, false)
	await _shot(Vector3(0, 2.6, 0), 8.0, 0.0, 6.0)

	var rows := int(ceil(tiles.size() / 2.0))
	var sheet := Image.create(WIDE.x, WIDE.y + TILE.y * rows, false, Image.FORMAT_RGBA8)
	wide.convert(Image.FORMAT_RGBA8)
	sheet.blit_rect(wide, Rect2i(Vector2i.ZERO, WIDE), Vector2i.ZERO)
	for k in tiles.size():
		var t: Image = tiles[k]
		t.convert(Image.FORMAT_RGBA8)
		sheet.blit_rect(t, Rect2i(Vector2i.ZERO, TILE), Vector2i((k % 2) * TILE.x, WIDE.y + (k / 2) * TILE.y))
	var err := sheet.save_png(out_path)
	print("撮影：%s（%d 枚、%s）" % [out_path, tiles.size() + 1, error_string(err)])
	quit(0 if err == OK else 1)


func _frames() -> void:
	for _i in 4:
		await process_frame
	await RenderingServer.frame_post_draw


## 姿勢：肩の縦軸（外向きが +）・肩の横軸（下向きが +）・肘・削岩錐の自転（度）。open：核の蓋を開ける
func _pose(yaw: float, pitch: float, elbow: float, spin: float, open: bool) -> void:
	for a in ARMS:
		_rot("arm_%s_yaw" % a, yaw)
		_rot("arm_%s_pitch" % a, pitch)
		_rot("arm_%s_elbow" % a, elbow)
		_rot("arm_%s_drill" % a, spin)
	var d := 0.6 if open else 0.0
	for l in ["lid_f", "lid_r"]:
		var n := model.find_child(l, true, false) as Node3D
		var r: Transform3D = rest[n.name]
		n.transform = Transform3D(r.basis, r.origin + r.basis.x * d)
	_rot("keyplate", 100.0 if open else 0.0)


func _rot(node_name: String, deg: float) -> void:
	var n := model.find_child(node_name, true, false) as Node3D
	var r: Transform3D = rest[node_name]
	n.transform = Transform3D(r.basis * Basis(Vector3.RIGHT, deg_to_rad(deg)), r.origin)


## 方位角 az 度（0 = 前端 +Z から、90 = +X 側）・仰角 el 度から正投影で 1 枚
func _shot(target: Vector3, size: float, az: float, el: float) -> void:
	var a := deg_to_rad(az)
	var e := deg_to_rad(el)
	var d := Vector3(sin(a) * cos(e), sin(e), cos(a) * cos(e))
	cam.size = size
	cam.position = target + d * 20.0
	cam.look_at(target, Vector3.UP if el < 80.0 else Vector3(-1, 0, 0))
	await _frames()
	tiles.append(root.get_texture().get_image())
