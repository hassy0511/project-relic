extends SceneTree
## 絵から起こした住人（ヤーナ yana.glb など、持ち物なし）を Godot の中で描いて、確認の画像を 1 枚にまとめる（レビュー用）。
##   tools/godot.sh shot --resolution 400x450 --script /abs/tools/blender/recon/godot_npc_showcase.gd -- <出力の PNG> [モデルの res:// パス] [顔の高さ m]
## ゲームの PropsView と同じ読み込み方（材質の複製・表情の uv1_offset）と同じ光（EnvironmentSetup）で描く。
## 上の段：全身（正面・右前 39 度・右真横・背面、idle）。中の段：顔の近写を 4 表情。
## 下の段：左真横・左前 33 度（idle）、idle の途中、走り。
## 座標は glTF（Godot）：キャラクターの正面 +Z、本人の左 +X、上 +Y。

const TILE := Vector2i(400, 450)
const COLS := 4

var out_path := ""
var model_path := "res://assets/models/yana.glb"
var face_y := 1.50
var model: Node3D
var anim: AnimationPlayer
var face_mats: Array[BaseMaterial3D] = []
var cam: Camera3D
var tiles: Array[Image] = []


func _initialize() -> void:
	var args := OS.get_cmdline_user_args()
	out_path = args[0] if args.size() > 0 else "user://npc_showcase.png"
	if args.size() > 1:
		model_path = args[1]
	if args.size() > 2:
		face_y = float(args[2])
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
	var scene: PackedScene = load(model_path)
	model = scene.instantiate()
	world.add_child(model)
	for n in model.find_children("*", "MeshInstance3D", true, false):
		var mi := n as MeshInstance3D
		for s in mi.mesh.get_surface_count():
			var src := mi.mesh.surface_get_material(s)
			if src is BaseMaterial3D:
				var m: BaseMaterial3D = src.duplicate()
				mi.set_surface_override_material(s, m)
				if m.resource_name.contains("face"):
					face_mats.append(m)
	anim = model.find_child("AnimationPlayer", true, false)
	cam = Camera3D.new()
	cam.projection = Camera3D.PROJECTION_ORTHOGONAL
	world.add_child(cam)
	cam.current = true
	var mid := face_y * 0.52
	var full := face_y * 1.25

	for az in [0.0, 39.0, 90.0, 180.0]:
		_pose("idle", 0.0)
		await _shot(az, Vector3(0, mid, 0), full, 12.0)
	for i in 4:
		_pose("idle", 0.0)
		_face(i)
		await _shot(0.0, Vector3(0, face_y, 0), 0.46, 0.0)
	_face(0)
	for az in [-90.0, -33.0]:
		_pose("idle", 0.0)
		await _shot(az, Vector3(0, mid, 0), full, 12.0)
	_pose("idle", 1.0)
	await _shot(20.0, Vector3(0, mid, 0), full, 12.0)
	_pose("run", 0.10)
	await _shot(31.0, Vector3(0, mid, 0), full * 1.05, 12.0)

	var rows := int(ceil(tiles.size() / float(COLS)))
	var sheet := Image.create(TILE.x * COLS, TILE.y * rows, false, Image.FORMAT_RGBA8)
	for k in tiles.size():
		var t: Image = tiles[k]
		t.convert(Image.FORMAT_RGBA8)
		sheet.blit_rect(t, Rect2i(Vector2i.ZERO, TILE), Vector2i((k % COLS) * TILE.x, (k / COLS) * TILE.y))
	var err := sheet.save_png(out_path)
	print("撮影：%s（%d 枚、%s）" % [out_path, tiles.size(), error_string(err)])
	quit(0 if err == OK else 1)


func _face(i: int) -> void:
	for m in face_mats:
		m.uv1_offset = Vector3((i % 2) * 0.5, (i / 2) * 0.5, 0)


## 動作 name の t 秒の姿勢で止める
func _pose(name: String, t: float) -> void:
	if anim and anim.has_animation(name):
		anim.play(name, 0.0)
		anim.seek(t, true)
		anim.pause()


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
