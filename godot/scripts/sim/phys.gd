class_name Phys
extends Node3D
## 物理の包み。ゲームの中身が物理エンジンの細部を知らなくて済むようにする。
## キャラクターは CharacterBody3D を move_and_collide で少しずつ動かし、
## three.js 版（Rapier のキャラクターコントローラー）と同じ規則を再現する：
## - 段差の自動乗り越え（0.35m）と地面への吸着（0.3m）は、接地中だけ有効
## - 空中では、カプセルの丸い底が段の角に乗り上げて押し上げられる分を打ち消す
## - 45 度までの坂は床として扱う

const TERRAIN := 1
const PLAYER := 2
const ENEMY := 4
const BREAKABLE := 8
## 体だけを止める地形（部屋の形の "cam": false。細い柱・露店の屋根の上をふさぐ箱など）。キャラクターの体は止めるが、
## カメラの壁よけ・弾・照準の線は通す（細い柱が後ろを横切るたびにカメラが前へ跳ねないように）。
## キャラクターを動かすときは TERRAIN を含むマスクに自動で足す（create_character・move_character）。足元の確かめは Player._ground_below
const PROP := 16

const STEP_HEIGHT := 0.35
const SNAP := 0.3
const FLOOR_MIN_Y := 0.7071  # cos(45°)
const MARGIN := 0.02


func _static_body(layer: int) -> StaticBody3D:
	var b := StaticBody3D.new()
	b.collision_layer = layer
	b.collision_mask = 0
	add_child(b)
	return b


func add_trimesh(faces: PackedVector3Array, layer: int = TERRAIN) -> StaticBody3D:
	var b := _static_body(layer)
	var shape := ConcavePolygonShape3D.new()
	shape.backface_collision = true
	shape.set_faces(faces)
	var cs := CollisionShape3D.new()
	cs.shape = shape
	b.add_child(cs)
	return b


func add_box(center: Vector3, half: Vector3, layer: int = TERRAIN, yaw: float = 0.0) -> StaticBody3D:
	var b := _static_body(layer)
	b.position = center
	b.rotation.y = yaw
	var shape := BoxShape3D.new()
	shape.size = half * 2.0
	var cs := CollisionShape3D.new()
	cs.shape = shape
	b.add_child(cs)
	return b


func remove(body: Node) -> void:
	if body == null or not is_instance_valid(body):
		return
	(body as CollisionObject3D).collision_layer = 0
	remove_child(body)
	body.queue_free()


func set_owner_of(body: Node, obj: Object) -> void:
	body.set_meta("owner", obj)


## キャラクター（カプセル）を作る。位置はカプセルの足元
func create_character(feet: Vector3, radius: float, height: float, layer: int, mask: int) -> CharacterBody3D:
	var b := CharacterBody3D.new()
	b.collision_layer = layer
	b.collision_mask = body_mask(mask)
	b.safe_margin = 0.001
	var shape := CapsuleShape3D.new()
	shape.radius = radius
	shape.height = height
	var cs := CollisionShape3D.new()
	cs.shape = shape
	cs.position.y = height * 0.5
	b.add_child(cs)
	add_child(b)
	b.position = feet
	return b


## キャラクターの体のマスク：地形（TERRAIN）を含むなら、体だけを止める地形（PROP）も足す
static func body_mask(mask: int) -> int:
	return mask | PROP if mask & TERRAIN else mask


func feet_of(body: CharacterBody3D) -> Vector3:
	return body.position


func set_feet(body: CharacterBody3D, feet: Vector3) -> void:
	body.position = feet


## キャラクターを動かす。返り値：{ moved: 実際に動いた量, grounded: 接地しているか }
func move_character(body: CharacterBody3D, delta: Vector3, mask: int, on_ground: bool = true) -> Dictionary:
	body.collision_mask = body_mask(mask)
	var start := body.position
	var motion := delta
	var hit_floor := false
	for i in 4:
		if motion.length_squared() < 1e-10:
			break
		var col := body.move_and_collide(motion, false, 0.001, false)
		if col == null:
			break
		var n := col.get_normal()
		var rem := col.get_remainder()
		if n.y >= FLOOR_MIN_Y:
			hit_floor = true
		elif on_ground and absf(n.y) < 0.3 and _try_step(body, rem):
			hit_floor = true
			motion = Vector3.ZERO
			break
		var slid := rem.slide(n)
		if n.y >= FLOOR_MIN_Y and delta.y <= 0.0:
			# 床に当たったら、残りは水平にだけ進める（坂で滑り落ちないように）
			slid = Vector3(rem.x, 0.0, rem.z).slide(n)
		if not on_ground:
			# 空中：段の角で上へ押し上げられる分を打ち消す
			slid.y = minf(slid.y, maxf(delta.y, 0.0))
		motion = slid
	# 地面への吸着（接地中だけ）
	if on_ground:
		var down := body.move_and_collide(Vector3(0, -SNAP, 0), true, 0.001, false)
		if down != null and down.get_normal().y >= FLOOR_MIN_Y:
			body.position += down.get_travel()
			hit_floor = true
	var grounded := hit_floor
	if not grounded:
		var probe := body.move_and_collide(Vector3(0, -0.03, 0), true, 0.001, false)
		grounded = probe != null and probe.get_normal().y >= FLOOR_MIN_Y and delta.y <= 0.01
	return {"moved": body.position - start, "grounded": grounded}


## 段差の自動乗り越え：上へ持ち上げ、前へ進め、下ろして床に乗れたら成功
func _try_step(body: CharacterBody3D, rem: Vector3) -> bool:
	var fwd := Vector3(rem.x, 0.0, rem.z)
	if fwd.length() < 1e-4:
		return false
	# 少なくとも 0.2m は前へ進んで確かめる（小さな角で登らないように）
	var probe_fwd := fwd.normalized() * maxf(fwd.length(), 0.2)
	var t := body.global_transform
	if body.test_move(t, Vector3(0, STEP_HEIGHT, 0)):
		return false
	var up := t.translated(Vector3(0, STEP_HEIGHT, 0))
	if body.test_move(up, probe_fwd):
		return false
	var ahead := up.translated(probe_fwd)
	var res := KinematicCollision3D.new()
	if not body.test_move(ahead, Vector3(0, -STEP_HEIGHT - 0.05, 0), res):
		return false
	if res.get_normal().y < FLOOR_MIN_Y:
		return false
	var landed := ahead.translated(res.get_travel())
	if landed.origin.y - t.origin.y < 0.02:
		return false
	# 実際には求められた分だけ前へ（確かめに使った 0.2m ではなく）
	body.position = Vector3(t.origin.x + fwd.x, landed.origin.y, t.origin.z + fwd.z)
	if body.test_move(body.global_transform, Vector3.ZERO):
		body.global_transform = t
		return false
	return true


## レイキャスト。mask に含めたレイヤーだけに当たる。当たらなければ空の辞書
func raycast(origin: Vector3, dir: Vector3, max_dist: float, mask: int, exclude: Array[RID] = []) -> Dictionary:
	var q := PhysicsRayQueryParameters3D.create(origin, origin + dir * max_dist, mask, exclude)
	q.hit_from_inside = false
	var hit := get_world_3d().direct_space_state.intersect_ray(q)
	if hit.is_empty():
		return {}
	var owner_obj: Object = null
	var col: Object = hit.collider
	if col != null and col.has_meta("owner"):
		owner_obj = col.get_meta("owner")
	return {
		"distance": origin.distance_to(hit.position),
		"point": hit.position,
		"normal": hit.normal,
		"owner": owner_obj,
	}
