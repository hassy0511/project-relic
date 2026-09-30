extends SceneTree
## 番機 5 種（banki_<型>.glb）を Godot の中で描いて、確認の画像を 1 枚にまとめる（レビュー用）。
##   tools/godot.sh shot --resolution 1600x500 --script /abs/tools/blender/recon/godot_banki_showcase.gd -- <出力の PNG>
## 1 段目：ハルと 5 種を並べた姿（大きさの比較）。
## 2 段目：歩哨型（ゲームと同じ EnemyView）：待機・歩き・予備動作（後ろへ倒れて砲口の蓋が開く、赤いセンサー）・撃破。
## 3 段目：突撃型：待機・予備動作（車体を沈めて衝角を伸ばす）・激突のあと（本人の右の核の蓋が開く）・撃破。
## 4 段目：子番機・盾型・浮遊型（ゲームにはまだ出ない。モデルだけ）と浮遊型の上から。
## 座標は glTF（Godot）：正面 +Z、上 +Y。

const TILE := Vector2i(400, 400)
const WIDE := Vector2i(1600, 500)
const COLS := 4

var out_path := ""
var cam: Camera3D
var world: Node3D
var tiles: Array[Image] = []
var wide: Image


## EnemyView に渡す仮の敵（sim の Enemy と同じ名前の項目だけ）
class FakeEnemy:
	var kind := "sentry"
	var alive := true
	var dead_time := 0.0
	var pos := Vector3.ZERO
	var yaw := 0.0
	var state := "idle"
	var vel := Vector3.ZERO
	var flash := 0.0

	func telegraphing() -> bool:
		return state == "windup"

	func alerting() -> bool:
		return state == "alert"


func _initialize() -> void:
	var args := OS.get_cmdline_user_args()
	out_path = args[0] if args.size() > 0 else "user://banki_showcase.png"
	_run.call_deferred()


func _run() -> void:
	world = Node3D.new()
	root.add_child(world)
	EnvironmentSetup.build(world)
	var floor_mesh := MeshInstance3D.new()
	var pm := PlaneMesh.new()
	pm.size = Vector2(30, 30)
	floor_mesh.mesh = pm
	var fm := StandardMaterial3D.new()
	fm.albedo_color = Color(0.42, 0.42, 0.44)
	floor_mesh.material_override = fm
	world.add_child(floor_mesh)
	cam = Camera3D.new()
	world.add_child(cam)
	cam.current = true

	# 1 段目：ハルと 5 種を並べる（右前から、透視）
	root.size = WIDE
	var line := Node3D.new()
	world.add_child(line)
	var xs := {"haru": -3.3, "mini": -2.3, "sentry": -1.4, "charger": 0.3, "shield": 2.1, "floater": 3.5}
	for k in xs:
		var path := "res://assets/models/haru_r.glb" if k == "haru" else "res://assets/models/banki_%s.glb" % k
		if not ResourceLoader.exists(path):
			continue
		var n := (load(path) as PackedScene).instantiate() as Node3D
		n.position = Vector3(xs[k], 1.1 if k == "floater" else 0.0, 0)
		n.rotation.y = deg_to_rad(20.0)
		line.add_child(n)
	cam.projection = Camera3D.PROJECTION_PERSPECTIVE
	cam.fov = 30.0
	cam.position = Vector3(0.6, 2.2, 13.0)
	cam.look_at(Vector3(0.2, 0.8, 0), Vector3.UP)
	await _frames()
	wide = root.get_texture().get_image()
	line.queue_free()

	root.size = TILE
	cam.projection = Camera3D.PROJECTION_ORTHOGONAL
	# 2 段目：歩哨型
	await _enemy_shot("sentry", "idle", 25.0, 1.7, 0.6)
	await _enemy_shot("sentry", "walk", -90.0, 1.7, 0.6)
	await _enemy_shot("sentry", "windup", -60.0, 1.7, 0.6)
	await _enemy_shot("sentry", "dead", 25.0, 1.7, 0.6)
	# 3 段目：突撃型
	await _enemy_shot("charger", "idle", 30.0, 2.6, 0.6)
	await _enemy_shot("charger", "windup", -90.0, 2.6, 0.6)
	await _enemy_shot("charger", "stunned", -70.0, 2.6, 0.6)
	await _enemy_shot("charger", "dead", 30.0, 2.6, 0.6)
	# 4 段目：モデルだけの 3 種
	await _model_shot("mini", 25.0, 0.5, 0.15, 12.0)
	await _model_shot("shield", 25.0, 2.3, 0.9, 12.0)
	await _model_shot("floater", 25.0, 1.1, 0.3, 15.0)
	await _model_shot("floater", 0.0, 1.1, 0.0, 89.0)

	var rows := int(ceil(tiles.size() / float(COLS)))
	var sheet := Image.create(TILE.x * COLS, WIDE.y + TILE.y * rows, false, Image.FORMAT_RGBA8)
	wide.convert(Image.FORMAT_RGBA8)
	sheet.blit_rect(wide, Rect2i(Vector2i.ZERO, WIDE), Vector2i.ZERO)
	for k in tiles.size():
		var t: Image = tiles[k]
		t.convert(Image.FORMAT_RGBA8)
		sheet.blit_rect(t, Rect2i(Vector2i.ZERO, TILE), Vector2i((k % COLS) * TILE.x, WIDE.y + (k / COLS) * TILE.y))
	var err := sheet.save_png(out_path)
	print("撮影：%s（%d 枚、%s）" % [out_path, tiles.size() + 1, error_string(err)])
	quit(0 if err == OK else 1)


func _frames() -> void:
	for _i in 4:
		await process_frame
	await RenderingServer.frame_post_draw


## EnemyView（ゲームと同じ動き）で 1 体を描く。how：idle・walk・windup・stunned・dead
func _enemy_shot(kind: String, how: String, az: float, size: float, target_y: float) -> void:
	var ev := EnemyView.new()
	world.add_child(ev)
	var e := FakeEnemy.new()
	e.kind = kind
	match how:
		"walk":
			e.state = "engage"
			e.vel = Vector3(0, 0, 1.5)
		"windup", "stunned":
			e.state = how
		"dead":
			e.state = "engage"
	var steps := 5 if how == "walk" else 12
	for _i in steps:
		ev.sync([e], 0.1)
	if how == "dead":
		e.alive = false
		for _i in 12:
			e.dead_time += 0.1
			ev.sync([e], 0.1)
	await _shot(az, Vector3(0, target_y, 0), size, 12.0)
	ev.queue_free()


func _model_shot(kind: String, az: float, size: float, target_y: float, el: float) -> void:
	var path := "res://assets/models/banki_%s.glb" % kind
	if not ResourceLoader.exists(path):
		return
	var n := (load(path) as PackedScene).instantiate() as Node3D
	if kind == "floater":
		n.position.y = 0.3
		target_y += 0.3
	world.add_child(n)
	await _shot(az, Vector3(0, target_y, 0), size, el)
	n.queue_free()


## 方位角 az 度（0 = 正面、+ = 本人の左（+X）の側、-90 = 本人の右の真横）・仰角 el 度から正投影で描いて 1 枚に加える
func _shot(az: float, target: Vector3, size: float, el: float) -> void:
	var a := deg_to_rad(az)
	var e := deg_to_rad(el)
	var d := Vector3(sin(a) * cos(e), sin(e), cos(a) * cos(e))
	cam.size = size
	cam.position = target + d * 6.0
	cam.look_at(target, Vector3.UP if el < 80.0 else Vector3(0, 0, -1))
	await _frames()
	tiles.append(root.get_texture().get_image())
