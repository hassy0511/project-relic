class_name PlayerView
extends Node3D
## ハルの見た目。ゲームの中身の状態（anim）に合わせて動作を切り替え、
## 撃つ・走る・ロックオンの姿勢を HaruPose で重ねる。

const LOOPING := ["idle", "run", "fall", "drill"]
const FADE := {"combo1": 0.05, "combo2": 0.05, "combo3": 0.05, "air": 0.05, "lunge": 0.05, "charge": 0.05, "dash": 0.06, "hurt": 0.05}
const EXPRESSIONS := ["normal", "smile", "surprise", "pain"]

var model: Node3D
var anim: AnimationPlayer
var skeleton: Skeleton3D
var pose: HaruPose
var blade: Node3D = null
var blade_mat: BaseMaterial3D = null
var muzzle: Node3D = null
var meshes: Array[MeshInstance3D] = []
var face_mats: Array[BaseMaterial3D] = []
var body_mats: Array[BaseMaterial3D] = []
var current := ""
var shading := "soft"
var _visual_yaw := 0.0
var _flash_time := 0.0
var _expression := -1
var _prev_yaw := 0.0
var _prev_speed := 0.0
var _lean_roll := 0.0
var _lean_pitch := 0.0
## 外装フレーム〈ヴェスティージ〉の段（haru_r の群ごとの物体。古いモデル・仮のモデルには無い＝空のまま）
const FRAME_NODES := {"core": "Frame_core", "arm": "Frame_arm", "legs": "Frame_legs"}
var frame_nodes := {}
var _frame_state := Vector3i(-1, -1, -1)
## いま隠しているフレームの部品（点滅の処理が見せてしまわないように）
var _frame_off := {}
## 付いたばかりで、まだ隠しているフレームの部品（群の名前 → 残りの秒数）
var _reveal := {}
## 主武器の見た目：スパークを受け取る前は練習銃（W2-07b、practice_gun.glb）。haru_r のスパークは体のメッシュの
## 面（材質 spark_gun）なので、練習銃を見せる間はその面だけ透明な材質に替える。練習銃は右手の骨 hand.R に、
## スパークと同じ置き場所（握りの中心・向き）で付ける。muzzle（Fx の溜めの光の位置）も持っている銃の銃口にする
const PRACTICE_GUN_PATH := "res://assets/models/practice_gun.glb"
## 右手の手首（hand.R の元）の、銃の座標での位置（tools/blender/models/ai_character.py の HAND_WRIST_IN_GUN と同じ）。
## 銃の座標（Blender）：銃身 +X、上 +Z、+Y = 掌の側。手の骨の向きが銃身、体の内側（+X）が掌の側
const HAND_WRIST_IN_GUN := Vector3(-0.062, -0.040, -0.010)
## 銃の GLB（glTF の座標：銃身 +X、上 +Y）→ Blender の銃の座標（(x, y, z) → (x, -z, y)）
const GLTF_TO_GUN := Basis(Vector3(1, 0, 0), Vector3(0, 0, 1), Vector3(0, -1, 0))
var gun := "spark"
var spark_muzzle: Node3D = null
var practice_gun: Node3D = null
var practice_muzzle: Node3D = null
## スパークの面：[MeshInstance3D, 面の番号, 材質]
var _spark_surfaces: Array = []
var _hidden_mat: StandardMaterial3D = null


func load_model(path: String, shade: String = "soft") -> void:
	var scene: PackedScene = load(path)
	model = scene.instantiate()
	add_child(model)
	anim = model.find_child("AnimationPlayer", true, false)
	skeleton = model.find_child("Skeleton3D", true, false)
	blade = model.find_child("LightBlade", true, false)
	muzzle = model.find_child("muzzle", true, false)
	for n in model.find_children("*", "MeshInstance3D", true, false):
		var mi := n as MeshInstance3D
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
		for s in mi.mesh.get_surface_count():
			# 材質は体ごとに複製する（表情の UV のずれ・点滅・光刃の明るさを、ほかの体と共有しないように）。
			# テクスチャ（下地の色・発光）は複製した材質がそのまま参照する。glTF の読み込みでは
			# StandardMaterial3D か ORMMaterial3D になるので、共通の BaseMaterial3D で扱う
			var src := mi.mesh.surface_get_material(s)
			if src is BaseMaterial3D:
				var m: BaseMaterial3D = src.duplicate()
				mi.set_surface_override_material(s, m)
				if mi == blade:
					blade_mat = m
				elif m.resource_name.begins_with("spark_gun"):
					_spark_surfaces.append([mi, s, m])
					body_mats.append(m)
				elif m.resource_name.contains("face"):
					face_mats.append(m)
					body_mats.append(m)
				else:
					body_mats.append(m)
		if mi != blade:
			meshes.append(mi)
			# 右手の拳のシェイプキー fist（5 回目までの haru_r）。6 回目からは右手が部品で、基準の姿勢のまま握っている
			# （シェイプキーなし、ここは何もしない）。古い GLB のために残す
			var fi := mi.find_blend_shape_by_name("fist")
			if fi >= 0:
				mi.set_blend_shape_value(fi, 1.0)
	frame_nodes.clear()
	_frame_off.clear()
	_frame_state = Vector3i(-1, -1, -1)
	for k in FRAME_NODES:
		var fn := model.find_child(FRAME_NODES[k], true, false) as Node3D
		if fn:
			frame_nodes[k] = fn
	if blade:
		blade.visible = false
		(blade as MeshInstance3D).cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	if skeleton:
		pose = HaruPose.new()
		skeleton.add_child(pose)
	spark_muzzle = muzzle
	gun = "spark"
	_attach_practice_gun()
	if anim:
		for n in LOOPING:
			if anim.has_animation(n):
				anim.get_animation(n).loop_mode = Animation.LOOP_LINEAR
		_play("idle", 0.0)
	# 主武器の溜めの光は Fx が銃口（muzzle）に描く（W2-09 の shot_charge）
	set_shading(shade)


## スパークの置き場所（骨の物体の座標）：Blender の銃の座標 → 骨の物体の座標。ai_character.hand_frame と同じ式を、
## 手の骨の基準の姿勢から作る（glTF でも骨の +Y が骨の向き。Blender → glTF の座標の入れ替えは回転なので、外積の向きも同じ）
static func hand_gun_frame(sk: Skeleton3D, bone: int) -> Transform3D:
	var rest := sk.get_bone_global_rest(bone)
	var gx := rest.basis.y.normalized()
	var gy := (Vector3.RIGHT - gx * gx.x).normalized()
	var gz := gx.cross(gy)
	var rot := Basis(gx, gy, gz)
	return Transform3D(rot, rest.origin - rot * HAND_WRIST_IN_GUN)


## 練習銃を右手の骨に付ける（スパークの面と手の骨があるモデル＝haru_r だけ。ほかのモデルはスパークのまま）
func _attach_practice_gun() -> void:
	practice_gun = null
	practice_muzzle = null
	if skeleton == null or _spark_surfaces.is_empty() or not ResourceLoader.exists(PRACTICE_GUN_PATH):
		return
	var bone := skeleton.find_bone("hand.R")
	if bone < 0:
		return
	var att := BoneAttachment3D.new()
	att.name = "PracticeGunHand"
	att.bone_name = "hand.R"
	skeleton.add_child(att)
	var holder := Node3D.new()
	holder.name = "PracticeGun"
	att.add_child(holder)
	# 骨の基準の姿勢から見た置き場所（動作で手が動けば、スパークの面と同じように付いて動く）
	holder.transform = skeleton.get_bone_global_rest(bone).affine_inverse() * hand_gun_frame(skeleton, bone) \
		* Transform3D(GLTF_TO_GUN, Vector3.ZERO)
	var scene: PackedScene = load(PRACTICE_GUN_PATH)
	holder.add_child(scene.instantiate())
	practice_muzzle = holder.find_child("muzzle", true, false)
	for n in holder.find_children("*", "MeshInstance3D", true, false):
		var mi := n as MeshInstance3D
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
		for s in mi.mesh.get_surface_count():
			var src := mi.mesh.surface_get_material(s)
			if src is BaseMaterial3D:
				var m: BaseMaterial3D = src.duplicate()
				mi.set_surface_override_material(s, m)
				body_mats.append(m)
		meshes.append(mi)
	practice_gun = holder
	practice_gun.visible = false
	_hidden_mat = StandardMaterial3D.new()
	_hidden_mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA_SCISSOR
	_hidden_mat.alpha_scissor_threshold = 0.5
	_hidden_mat.albedo_color = Color(1, 1, 1, 0)
	_hidden_mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED


## 持っている銃の見た目：spark = true でスパーク、false で練習銃。練習銃の無いモデルでは何もしない（スパークのまま）。
## 毎フレーム呼んでも、変わったときだけ切り替える
func set_gun(spark: bool) -> void:
	if practice_gun == null:
		return
	var want := "spark" if spark else "practice"
	if want == gun:
		return
	gun = want
	practice_gun.visible = not spark
	for e in _spark_surfaces:
		(e[0] as MeshInstance3D).set_surface_override_material(e[1], e[2] if spark else _hidden_mat)
	muzzle = spark_muzzle if spark else practice_muzzle


## ゲームの状態から銃を選ぶ：スパークを受け取るまで（GameSim.has_ability("spark") が偽の間）は練習銃。
## 新しく始めた・セーブから再開した・フラグつきで部屋から始めた・ヤーナから受け取った、のどれも同じ式で決まる
func sync_gun(game: GameSim) -> void:
	set_gun(game.has_ability("spark"))


## 塗り方：soft（柔らかい陰影）／toon（3 段の塗り分け）。どちらも輪郭の光（リム）を少し入れる。
## 光の当たり方だけを変え、下地の色・発光のテクスチャはそのまま使う。
## 顔（肌）はつやの無い絵の肌に合わせて、リムと鏡面の照り返しをごく弱く（強いと面の折れ目ごとに
## 明るい線が出て、ガラスのような肌に見える）。服も照り返しを少し弱く
func set_shading(mode: String) -> void:
	shading = mode
	for m in body_mats:
		var is_face := face_mats.has(m)
		m.metallic = 0.0
		m.roughness = 1.0 if is_face else 0.85
		m.metallic_specular = 0.12 if is_face else 0.3
		m.rim_enabled = true
		m.rim = 0.08 if is_face else 0.3
		m.rim_tint = 0.6
		if mode == "toon":
			m.diffuse_mode = BaseMaterial3D.DIFFUSE_TOON
			m.specular_mode = BaseMaterial3D.SPECULAR_TOON
		else:
			m.diffuse_mode = BaseMaterial3D.DIFFUSE_BURLEY
			m.specular_mode = BaseMaterial3D.SPECULAR_SCHLICK_GGX


## 外装フレームの段：付いている群だけを見せる（core：胴の板と肩ひも、arm：左の籠手、legs：膝当てとすね当て）。
## 群の下の体の塗り・形はモデルの側で作業着にしてあるので、隠すだけでよい。無い物体（古いモデル）は何もしない。
## 既定は全部見せる。毎フレーム呼んでも、変わったときだけ切り替える
func set_frame_parts(core: bool, arm: bool, legs: bool) -> void:
	var st := Vector3i(int(core), int(arm), int(legs))
	if st == _frame_state:
		return
	_frame_state = st
	var on := {"core": core, "arm": arm, "legs": legs}
	_frame_off.clear()
	for k in frame_nodes:
		var fn := frame_nodes[k] as Node3D
		fn.visible = on[k]
		if not on[k]:
			_frame_off[fn] = true


## フレームの部品を secs 秒のあいだ隠す（Fx のフレームの装着：光の粒と陶器のかけらが集まってから現れる）。
## もう隠して待っている部品（台本の合図を待つ間）なら、残りの秒数を secs に置き直す
func reveal_later(part: String, secs: float) -> void:
	var fn := frame_nodes.get(part) as Node3D
	if fn == null or not (fn.visible or _reveal.has(part)):
		return
	_reveal[part] = secs
	fn.visible = false
	_frame_off[fn] = true


func _part_on(part: String) -> bool:
	match part:
		"core":
			return _frame_state.x == 1
		"arm":
			return _frame_state.y == 1
	return _frame_state.z == 1


func _is_frame_off(m: Node) -> bool:
	for fn in _frame_off:
		if fn == m or (fn as Node).is_ancestor_of(m):
			return true
	return false


## 表情：0 通常、1 笑顔、2 驚き、3 痛み。顔の材質（名前に face）のテクスチャは 2×2 の区画に 4 つの表情が
## 並び、UV は区画 0（左上）を指す。uv1_offset で区画をずらして切り替える
func set_expression(i: int) -> void:
	if i == _expression:
		return
	_expression = i
	for m in face_mats:
		m.uv1_offset = Vector3((i % 2) * 0.5, (i / 2) * 0.5, 0)


func _play(name: String, fade: float) -> void:
	if name == current or anim == null or not anim.has_animation(name):
		return
	anim.play(name, fade)
	current = name


## 毎フレーム。p：Player、aim_dir：照準の向き（ワールド）
func sync(p: Player, game: GameSim, dt: float, aim_dir: Vector3) -> void:
	position = p.pos
	# 向きは見た目だけ少し滑らかにする
	var d := U.wrap_angle(p.yaw - _visual_yaw)
	_visual_yaw += d * minf(1.0, dt * 20.0)
	rotation.y = _visual_yaw

	var a := p.anim()
	_play(a, FADE.get(a, 0.15))
	if anim:
		if game.hitstop > 0.0:
			# ヒットストップ中は中身が止まるので、見た目も止める（当たったこまで止まって見える）
			anim.speed_scale = 0.0
		elif a == "run":
			anim.speed_scale = maxf(0.6, p.speed() / 7.0)
		elif p.attack != null and anim.has_animation(a):
			# 攻撃の動作は中身の攻撃時間と同じ長さで流す。動作の振り抜きは攻撃時間の 25%（当たり判定の始まり）に
			# 置いてあるので、速さを合わせれば当たるこまと刃が合う
			var len := anim.get_animation(a).length
			anim.speed_scale = len / maxf(p.attack.duration, 0.01) if len > 0.0 else 1.0
		else:
			anim.speed_scale = 1.0

	if pose:
		# 撃つ：照準の向きをキャラクターの座標系へ
		var aiming: bool = p.aiming > 0.0 and p.attack == null
		var w := minf(1.0, p.aiming * 4.0) if aiming else 0.0
		pose.aim_weight = lerpf(pose.aim_weight, w, minf(1.0, dt * 20.0))
		pose.aim_local = aim_dir.rotated(Vector3.UP, -_visual_yaw)
		# 走る：曲がる速さと加速で体を傾ける
		var turn := U.wrap_angle(p.yaw - _prev_yaw) / maxf(dt, 1e-4)
		_prev_yaw = p.yaw
		var spd := p.speed()
		var accel := (spd - _prev_speed) / maxf(dt, 1e-4)
		_prev_speed = spd
		var run_k := clampf(spd / 7.0, 0.0, 1.0) if p.grounded else 0.0
		_lean_roll = lerpf(_lean_roll, clampf(-turn * 0.05, -0.3, 0.3) * run_k, minf(1.0, dt * 8.0))
		_lean_pitch = lerpf(_lean_pitch, clampf(accel * 0.012, -0.15, 0.15) * run_k, minf(1.0, dt * 6.0))
		pose.lean_roll = _lean_roll
		pose.lean_pitch = _lean_pitch
		# ロックオン：頭を対象へ
		var t = game.lock_on.target
		if t != null:
			pose.look_local = (t.center() - (p.pos + Vector3(0, 1.35, 0))).rotated(Vector3.UP, -_visual_yaw)
		pose.look_weight = lerpf(pose.look_weight, 1.0 if t != null else 0.0, minf(1.0, dt * 6.0))

	# 光刃は攻撃中だけ出す
	if blade:
		blade.visible = p.attack != null or p.sword_hold > 0.25
		if blade_mat:
			# 琥珀（#FFBC52）の緑が飽和してレモン色にならない明るさ（溜めきったときだけ強く）
			blade_mat.emission_energy_multiplier = 2.2 if p.sword_hold >= 0.7 else 1.2
		blade.scale = Vector3.ONE * (0.6 if p.sword_hold > 0.25 and p.attack == null else 1.0)

	# 表情：被弾と倒れたときは痛みの顔
	set_expression(3 if p.dead or a == "hurt" else 0)

	# フレームの装着のエフェクトの間は、付いたばかりの部品を隠しておく（reveal_later）
	for k in _reveal.keys():
		_reveal[k] -= dt
		if _reveal[k] <= 0.0:
			_reveal.erase(k)
			var fn := frame_nodes.get(k) as Node3D
			if fn != null and _part_on(k):
				fn.visible = true
				_frame_off.erase(fn)

	# 被弾後の無敵時間は点滅
	_flash_time += dt
	var blink: bool = p.invuln > 0.0 and not p.dead and int(_flash_time * 20.0) % 2 == 0
	for m in meshes:
		# 隠したフレームの部品は、点滅の間も隠したまま
		m.visible = not blink and not _is_frame_off(m)
