class_name Phys
extends Node3D
## 物理の包み。ゲームの中身が物理エンジンの細部を知らなくて済むようにする。
## キャラクターは CharacterBody3D を move_and_collide で少しずつ動かし、
## three.js 版（Rapier のキャラクターコントローラー）と同じ規則を再現する：
## - 段差の自動乗り越え（0.35m）と地面への吸着（0.3m）は、接地中だけ有効。乗り越えは、壁とみなす向きの面のほか、
##   体の丸い底が低い段の角に当たったときも試す。上がる高さは、下ろして当たった段の上の面か角で測り、
##   動かし始めた足元（床に沿って動いた分は含める）から数える。横の壁にふさがれたら、壁に沿う向きで確かめ直す
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
## 空中で当たった床の面がこれより傾いていたら（縁の角）、面に沿って滑らせる（move_character）
const EDGE_FLAT := 0.995
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
	# 段の高さを数える元の足元。初めの量と、床に沿って滑らせた分で動いた所を足元とする（ほかの動きでは下がった分だけ数える）。
	# 段の角に沿って押し上げられた分は含めない（前は押し上げられた所から数えたので、大きな体・速い動きでは 0.36 m を超える段も上れた）
	var base_y := start.y
	var along_floor := true
	for i in 4:
		if motion.length_squared() < 1e-10:
			break
		var col := body.move_and_collide(motion, false, 0.001, false)
		base_y = body.position.y if along_floor else minf(base_y, body.position.y)
		if col == null:
			break
		var n := col.get_normal()
		var rem := col.get_remainder()
		along_floor = n.y >= FLOOR_MIN_Y
		var corner := false
		if n.y >= FLOOR_MIN_Y:
			hit_floor = true
		elif on_ground and (absf(n.y) < 0.3 or _rounded_edge(col, n)):
			if _try_step(body, rem, base_y):
				hit_floor = true
				motion = Vector3.ZERO
				break
			# 上れなかった段（高すぎる・上がふさがっている）の角や上向きの面：体を押し上げない（下の空中と同じ）。
			# 前は接地中に角へ当たり続けると、体の丸い底が刻みごとに少しずつ角の上へ押し上がり、
			# 大きな体（物理の体の半径 0.45 m 以上：歩哨型・盾型・突撃型）では 0.36 m を超える段も上った
			corner = n.y > 0.0
		var slid := rem.slide(n)
		if n.y >= FLOOR_MIN_Y and delta.y <= 0.0 and (on_ground or n.y > EDGE_FLAT):
			# 床に当たったら、残りは水平にだけ進める（坂で滑り落ちないように）。
			# 空中で傾いた面に当たったとき（体の丸い底が段・箱の縁の角に載った）は、面に沿って滑らせて縁から落とす。
			# 前は真下に床の無いまま縁の上で止まり、接地しない（跳べない）まま宙に浮いて見えた（箱の縁・溝の縁・壁ぎわの灯の上）
			slid = Vector3(rem.x, 0.0, rem.z).slide(n)
		if not on_ground or corner:
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


## 体の丸い底が低い段（約 0.1〜0.25 m）の角に当たった：法線が上を向いているが床とみなすより傾いている（y が 0.3〜0.71）。
## 壁とみなす向き（y が 0.3 未満）と同じく、段差の自動乗り越えを試す。前はどちらにもならず、角に押し当てたまま止まった（N13、2026-11-05）。
## 45 度より急な坂も同じ向きになるが、乗り越えは下ろした先が床（45 度まで）のときだけ成功するので、急な坂は今までどおり上れない。
## 試すのは地形・壊せる物の角だけ（キャラクターの体の丸い頭・肩には乗らない）
func _rounded_edge(col: KinematicCollision3D, n: Vector3) -> bool:
	if n.y < 0.3 or n.y >= FLOOR_MIN_Y:
		return false
	var o := col.get_collider() as CollisionObject3D
	return o != null and (o.collision_layer & (ENEMY | PLAYER)) == 0


## 段差の自動乗り越え：上へ持ち上げ、前へ進め、下ろして床に乗れたら成功。
## 上がる高さ（下ろして当たった段の上の面か角の高さ。base_y から数える）は STEP_HEIGHT（＋1 cm）まで
func _try_step(body: CharacterBody3D, rem: Vector3, base_y: float) -> bool:
	var fwd := Vector3(rem.x, 0.0, rem.z)
	if fwd.length() < 1e-4:
		return false
	# 少なくとも 0.2m は前へ進んで確かめる（小さな角で登らないように）
	var probe_fwd := fwd.normalized() * maxf(fwd.length(), 0.2)
	var t := body.global_transform
	if body.test_move(t, Vector3(0, STEP_HEIGHT, 0)):
		return false
	var up := t.translated(Vector3(0, STEP_HEIGHT, 0))
	var side := KinematicCollision3D.new()
	if body.test_move(up, probe_fwd, side):
		# 前が横の壁（階段の手すり・壁ぎわ）でふさがれた：壁に沿う向きに変えて、もう一度だけ確かめる。
		# 前は、壁へ斜めに歩くと階段の 1 段目を上ったあと次の段の角に載ったまま確かめが壁に当たって失敗し、
		# 接地しないまま角の上で浮いては落ちるのを繰り返して、上りきれなかった（町の下段の階段を手すりへ斜めに）
		var nw := Vector3(side.get_normal().x, 0.0, side.get_normal().z)
		if nw.length() < 1e-3:
			return false
		fwd = fwd.slide(nw.normalized())
		if fwd.length() < 1e-4:
			return false
		probe_fwd = fwd.normalized() * maxf(fwd.length(), 0.2)
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
	# 段の高さは、下ろして当たった所で測る。前は足元の高さで測っていて、0.2m 先では体の丸い底が角の上に載って
	# 足元が角より低く出るので、0.38m ほどの段まで歩いて上れた
	if res.get_position().y - base_y > STEP_HEIGHT + 0.01:
		return false
	# 実際には求められた分だけ前へ（確かめに使った 0.2m ではなく）進め、そこで下ろす。
	# 前は 0.2m 先の高さのまま置いたので、角の手前では体が角から浮き、次の刻みで角まで沈んで、上下に揺れた
	# （斜めにゆっくり当たると、浮いては沈むのを繰り返して上れなかった）
	var y := landed.origin.y
	if fwd.length() < probe_fwd.length() - 1e-4:
		var here := up.translated(fwd)
		var res2 := KinematicCollision3D.new()
		if body.test_move(here, Vector3(0, -STEP_HEIGHT - 0.05, 0), res2):
			y = here.origin.y + res2.get_travel().y
	body.position = Vector3(t.origin.x + fwd.x, y, t.origin.z + fwd.z)
	if body.test_move(body.global_transform, Vector3.ZERO):
		body.global_transform = t
		return false
	return true


## 球（中心 center、半径 radius）が mask の物に重なるか（会話のカメラ TalkCamera が、置き場所のまわりが空いているかを確かめる）。
## 物の中に丸ごと入った球は面に触れないので重ならないとみなされる（入ったかどうかは、外の点からの raycast で確かめる）
func sphere_hits(center: Vector3, radius: float, mask: int, exclude: Array[RID] = []) -> bool:
	var s := SphereShape3D.new()
	s.radius = radius
	var q := PhysicsShapeQueryParameters3D.new()
	q.shape = s
	q.transform = Transform3D(Basis.IDENTITY, center)
	q.collision_mask = mask
	q.exclude = exclude
	return not get_world_3d().direct_space_state.intersect_shape(q, 1).is_empty()


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
