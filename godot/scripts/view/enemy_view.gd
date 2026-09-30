class_name EnemyView
extends Node3D
## 番機の見た目。banki_<型>.glb（tools/blender/recon/banki.py、npm run banki:build）を部品の階層のまま置き、
## 敵の状態（sim/enemies の state）から手続きで動かす（GLB にアニメーションはない）。
## 部品は原点が回転軸・ローカル +X が軸（ナゴミと同じ約束）：元の姿勢 * Basis(RIGHT, 角度) で回す。
## GLB がないとき（テストの環境など）は、MVP の仮の形（白い陶器・真鍮・スリットのセンサー）で代わりにする。

const MODELS := {
	"sentry": "res://assets/models/banki_sentry.glb",
	"charger": "res://assets/models/banki_charger.glb",
}
const SENSOR_NORMAL := Color("#FFBC52")
const SENSOR_ALERT := Color("#E26A4A")
const GLASS_OFF := Color("#302F2B")

## 型ごとの動きの数値（角度は度、長さは m）。部品の名前は banki.py の PARTS と同じ
const POSE := {
	"sentry": {
		"label_h": 1.6,
		"stride": 2.4,          # 1 m 進むごとの歩きの位相（rad）
		"hip_swing": 26.0,      # 太ももの前後の振り
		"knee_bend": 34.0,      # すねの曲げ（脚を前へ出すとき）
		"bob": 0.025,           # 胴の上下（歩き・待機）
		"tele_lean": -22.0,     # 予備動作：胴を後ろへ倒す（胴の原点 = 股の高さ）
		"cover_open": 40.0,     # 予備動作：砲口の蓋を開く
		"recoil": 5.0,          # 射撃中の胴の小さな反動
		"detach": ["spike", "muzzle_cover", "foot_l", "shin_r", "foot_r"],
		"collapse_drop": 0.28,  # 撃破：胴が落ちる高さ
	},
	"charger": {
		"label_h": 1.9,
		"wheel_r": 0.16,
		"bob": 0.012,
		"tele_drop": 0.09,      # 予備動作：車体を沈める
		"tele_pitch": 4.0,      # 予備動作：前へ少し傾ける
		"ram_out": 0.35,        # 予備動作〜突進：衝角を前へ伸ばす
		"cover_open": -70.0,    # 核の蓋（本人の右）：突進のあと動けない間に開く
		"detach": ["fin", "core_cover", "ram", "wheel_fr"],
		"collapse_drop": 0.10,
	},
}

var _built := {}
var _time := 0.0
var PORCELAIN := MeshKit.mat(Color("#e9e3d6"), 0.35)
var BRASS := MeshKit.mat(Color("#b08a4a"), 0.4, 0.6)
var DARK := MeshKit.mat(Color("#3a3530"), 0.7)


class Built:
	var kind := ""
	var root: Node3D
	var body: Node3D
	var shell: StandardMaterial3D
	var sensor: StandardMaterial3D
	var core: StandardMaterial3D
	var alert: Label3D
	var legs: Array = []
	var glb := false
	var parts := {}         # 名前 → Node3D（GLB の部品）
	var rest := {}          # 名前 → 元の Transform3D
	var phase := 0.0        # 歩き・車輪の位相
	var tele := 0.0         # 予備動作の度合い（0..1、なめらかに追う）
	var ram := 0.0          # 衝角の伸び（0..1）
	var cover := 0.0        # 蓋の開き（0..1）
	var debris: Array = []  # 撃破で外れた部品 {node, vel, spin, axis}
	var broken := false


# ---------------------------------------------------------------- GLB のモデル

func _make_glb(kind: String) -> Built:
	var path: String = MODELS.get(kind, "")
	if path == "" or not ResourceLoader.exists(path):
		return null
	var b := Built.new()
	b.kind = kind
	b.glb = true
	b.root = Node3D.new()
	var model := (load(path) as PackedScene).instantiate() as Node3D
	b.root.add_child(model)
	b.sensor = _glow_mat(SENSOR_NORMAL)
	b.core = _glow_mat(SENSOR_NORMAL)
	for n in model.find_children("*", "Node3D", true, false):
		b.parts[n.name] = n
		b.rest[n.name] = (n as Node3D).transform
		var mi := n as MeshInstance3D
		if mi == null:
			continue
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
		if n.name == "sensor":
			mi.material_override = b.sensor
		elif n.name == "core":
			mi.material_override = b.core
		else:
			for s in mi.mesh.get_surface_count():
				var m := mi.mesh.surface_get_material(s)
				if m and String(m.resource_name).ends_with("_shell"):
					# 部品で 1 つの複製を共有する（被弾の光・撃破の暗さをまとめて変える）
					if b.shell == null:
						b.shell = (m as StandardMaterial3D).duplicate() if m is StandardMaterial3D else StandardMaterial3D.new()
					mi.set_surface_override_material(s, b.shell)
	b.body = b.parts.get("body", model)
	if b.shell == null:
		b.shell = PORCELAIN.duplicate()
	b.alert = MeshKit.label("!", POSE[kind].label_h)
	b.root.add_child(b.alert)
	return b


func _glow_mat(c: Color) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.albedo_color = c
	m.emission_enabled = true
	m.emission = c
	m.emission_energy_multiplier = 2.0
	return m


## 部品を元の姿勢から回す（ローカル +X まわり）・ずらす（親の座標で）
func _pose(b: Built, name: String, deg: float, offset := Vector3.ZERO) -> void:
	var n: Node3D = b.parts.get(name)
	if n == null or n.get_parent() == b.root:   # 外れた部品は動かさない
		return
	var r: Transform3D = b.rest[name]
	n.transform = Transform3D(r.basis * Basis(Vector3.RIGHT, deg_to_rad(deg)), r.origin + offset)


func _set_glow(m: StandardMaterial3D, c: Color, energy: float) -> void:
	m.albedo_color = c
	m.emission = c
	m.emission_energy_multiplier = energy


func _animate_glb(b: Built, e, dt: float) -> void:
	var P: Dictionary = POSE[b.kind]
	var speed := Vector2(e.vel.x, e.vel.z).length()
	var tele_target := 1.0 if e.telegraphing() or (b.kind == "sentry" and e.state == "attack") else 0.0
	b.tele = move_toward(b.tele, tele_target, dt * 4.0)
	var hostile: bool = e.state != "idle"
	# センサー：通常は琥珀、見つけてからは赤。予備動作中は明滅（避ける合図）
	var blink := 0.5 + 0.5 * sin(_time * 30.0) if e.telegraphing() else 0.0
	_set_glow(b.sensor, SENSOR_ALERT if hostile else SENSOR_NORMAL, 2.0 + blink * 4.0)
	# 被弾の光
	b.shell.emission_enabled = e.flash > 0.01
	b.shell.emission = Color(e.flash, e.flash * 0.9, e.flash * 0.7)
	b.alert.visible = e.alerting()
	var stun_wobble := sin(_time * 30.0) * 3.0 if e.state == "stunned" or e.state == "stagger" else 0.0
	if b.kind == "sentry":
		b.phase += speed * dt * P.stride
		var walk := clampf(speed / 1.5, 0.0, 1.0)
		var s := sin(b.phase)
		var lean: float = P.tele_lean * b.tele
		var recoil: float = P.recoil * absf(sin(_time * 25.0)) if e.state == "attack" else 0.0
		var bob: float = P.bob * (absf(s) * walk + 0.3 * sin(_time * 2.2) * (1.0 - walk))
		_pose(b, "body", lean - recoil + stun_wobble, Vector3(0, bob, 0))
		for side in [["l", 1.0], ["r", -1.0]]:
			var ph: float = s * side[1]
			var hip: float = P.hip_swing * ph * walk
			# 膝は鳥のように後ろ向き：脚を前へ運ぶ間、すねを前へ振って足を上げる
			var knee: float = -P.knee_bend * maxf(0.0, -cos(b.phase) * side[1]) * walk
			# 胴を倒した分は太ももで打ち消す（足は地面に残す）。足の裏は地面と平らに
			_pose(b, "thigh_" + side[0], hip - lean)
			_pose(b, "shin_" + side[0], knee)
			_pose(b, "foot_" + side[0], -hip - knee)
		_pose(b, "muzzle_cover", P.cover_open * b.tele)
		_pose(b, "spike", 0.0)
		_set_glow(b.core, SENSOR_NORMAL, 1.6 + 0.4 * sin(_time * 3.0))
	else:
		# 突撃型：車輪は進んだ距離で回る。予備動作で車体を沈めて衝角を伸ばす
		b.phase += speed * dt / P.wheel_r
		var charging: bool = e.state == "attack"
		b.ram = move_toward(b.ram, 1.0 if (e.telegraphing() or charging) else 0.0, dt * (6.0 if charging else 2.5))
		var exposed: bool = e.state == "stunned"
		b.cover = move_toward(b.cover, 1.0 if exposed else 0.0, dt * (4.0 if exposed else 1.5))
		var drop: float = P.tele_drop * maxf(b.tele, 1.0 if charging else 0.0)
		var bob: float = P.bob * sin(_time * (18.0 if speed > 0.5 else 2.0))
		_pose(b, "body", -P.tele_pitch * b.tele + stun_wobble, Vector3(0, bob - drop, 0))
		_pose(b, "ram", 0.0, Vector3(0, 0, P.ram_out * b.ram))
		_pose(b, "core_cover", P.cover_open * b.cover)
		for w in ["wheel_fl", "wheel_fr", "wheel_rl", "wheel_rr"]:
			_pose(b, w, rad_to_deg(b.phase))
		# 核：ふだんは弱く、蓋が開くと強く脈打つ（弱点が見えている合図）
		var pulse := 0.5 + 0.5 * sin(_time * 9.0)
		_set_glow(b.core, SENSOR_NORMAL.lerp(Color(1.0, 0.9, 0.6), b.cover * pulse), 1.2 + b.cover * (3.0 + pulse * 3.0))


## 撃破：センサーと核が消え、外れる部品が落ち、胴が崩れ、しばらくして沈んで消える
func _break_glb(b: Built, e, dt: float) -> void:
	var P: Dictionary = POSE[b.kind]
	if not b.broken:
		b.broken = true
		b.alert.visible = false
		b.shell.emission_enabled = false
		b.shell.albedo_color = b.shell.albedo_color.darkened(0.25)
		for m in [b.sensor, b.core]:
			m.emission_enabled = false
			m.albedo_color = GLASS_OFF
		var i := 0
		for name in P.detach:
			var n: Node3D = b.parts.get(name)
			if n == null:
				continue
			n.reparent(b.root, true)
			var a := float(i) * 2.399 + 0.7   # 部品ごとに違う向き（決まった値。乱数を使わない）
			b.debris.append({"node": n, "vel": Vector3(cos(a) * 1.2, 2.2 + 0.4 * (i % 2), sin(a) * 1.2),
					"axis": Vector3(sin(a), 0.5, cos(a)).normalized(), "spin": 6.0 + i})
			i += 1
	var t: float = e.dead_time
	for d in b.debris:
		var n: Node3D = d.node
		if n.position.y > 0.04 or d.vel.y > 0.0:
			d.vel.y -= 9.8 * dt
			n.position += d.vel * dt
			n.rotate(d.axis, d.spin * dt)
		else:
			n.position.y = 0.04
	var k := clampf(t / 0.5, 0.0, 1.0)
	if b.kind == "sentry":
		_pose(b, "body", 18.0 * k, Vector3(0, -P.collapse_drop * k, 0))
		for side in ["l", "r"]:
			_pose(b, "thigh_" + side, -70.0 * k)
			_pose(b, "shin_" + side, 95.0 * k)
	else:
		b.body.rotation.z = deg_to_rad(8.0) * k
		_pose(b, "body", 0.0, Vector3(0, -P.collapse_drop * k, 0))
		_pose(b, "core_cover", 0.0)
	# 3 秒後から沈んで、4.5 秒で消える
	b.root.position.y = e.pos.y - maxf(0.0, t - 3.0) * 0.6
	b.root.visible = t < 4.5


# ---------------------------------------------------------------- 仮の形（GLB がないとき）

func _make_sentry() -> Built:
	var b := Built.new()
	b.kind = "sentry"
	b.root = Node3D.new()
	b.body = Node3D.new()
	b.root.add_child(b.body)
	b.shell = PORCELAIN.duplicate()
	MeshKit.add(b.body, MeshKit.cyl(0.38, 0.45, 0.55, 10), b.shell, Vector3(0, 0.72, 0))
	var cap := SphereMesh.new()
	cap.radius = 0.38
	cap.height = 0.38
	cap.is_hemisphere = true
	MeshKit.add(b.body, cap, b.shell, Vector3(0, 0.99, 0))
	MeshKit.add(b.body, MeshKit.cyl(0.46, 0.46, 0.06, 16), BRASS, Vector3(0, 0.5, 0))
	b.sensor = MeshKit.glow(Color("#ffb23e"), 3.0)
	MeshKit.add(b.body, MeshKit.box(Vector3(0.4, 0.05, 0.05)), b.sensor, Vector3(0, 0.9, 0.36))
	MeshKit.add(b.body, MeshKit.cyl(0.06, 0.06, 0.3, 8), DARK, Vector3(0, 0.7, 0.45), Vector3(PI / 2, 0, 0))
	b.core = MeshKit.glow(Color("#ffcf7a"), 2.0)
	MeshKit.add(b.body, MeshKit.sphere(0.12, 10), b.core, Vector3(0, 0.75, -0.42))
	for i in 3:
		var a := i / 3.0 * TAU
		var leg := MeshKit.add(b.root, MeshKit.box(Vector3(0.09, 0.55, 0.09)), BRASS, Vector3(sin(a) * 0.3, 0.27, cos(a) * 0.3), Vector3(cos(a) * 0.35, 0, -sin(a) * 0.35))
		b.legs.append(leg)
	b.alert = MeshKit.label("!", 1.6)
	b.root.add_child(b.alert)
	return b


func _make_charger() -> Built:
	var b := Built.new()
	b.kind = "charger"
	b.root = Node3D.new()
	b.body = Node3D.new()
	b.root.add_child(b.body)
	b.shell = PORCELAIN.duplicate()
	MeshKit.add(b.body, MeshKit.box(Vector3(1.1, 0.7, 1.7)), b.shell, Vector3(0, 0.65, 0))
	MeshKit.add(b.body, MeshKit.box(Vector3(1.2, 0.5, 0.35)), BRASS, Vector3(0, 0.6, 0.95))
	MeshKit.add(b.body, MeshKit.cyl(0.0, 0.18, 0.5, 6), BRASS, Vector3(0, 0.65, 1.3), Vector3(PI / 2, 0, 0))
	b.sensor = MeshKit.glow(Color("#ffb23e"), 3.0)
	MeshKit.add(b.body, MeshKit.box(Vector3(0.7, 0.06, 0.05)), b.sensor, Vector3(0, 0.95, 0.86))
	b.core = MeshKit.glow(Color("#ffcf7a"), 2.0)
	MeshKit.add(b.body, MeshKit.sphere(0.13, 10), b.core, Vector3(0.56, 0.65, 0))
	MeshKit.add(b.body, MeshKit.sphere(0.13, 10), b.core, Vector3(-0.56, 0.65, 0))
	for xz in [[0.45, 0.55], [-0.45, 0.55], [0.45, -0.55], [-0.45, -0.55]]:
		b.legs.append(MeshKit.add(b.root, MeshKit.box(Vector3(0.16, 0.4, 0.16)), DARK, Vector3(xz[0], 0.2, xz[1])))
	b.alert = MeshKit.label("!", 1.9)
	b.root.add_child(b.alert)
	return b


func _animate_fallback(b: Built, e) -> void:
	# 通常は琥珀、警戒・攻撃中は赤みを帯びる
	var hostile: bool = e.state != "idle"
	var sc := Color("#ff5a2a") if hostile else Color("#ffb23e")
	b.sensor.albedo_color = sc
	b.sensor.emission = sc
	# 予備動作：核が明滅する（避ける合図）
	var tele := 0.5 + 0.5 * sin(_time * 40.0) if e.telegraphing() else 0.0
	var cc := Color(1.0, 0.8 - tele * 0.5, 0.48 - tele * 0.4)
	b.core.albedo_color = cc
	b.core.emission = cc
	b.core.emission_energy_multiplier = 2.0 + tele * 4.0
	b.shell.emission_enabled = e.flash > 0.01
	b.shell.emission = Color(e.flash, e.flash * 0.9, e.flash * 0.7)
	b.alert.visible = e.alerting()
	var moving: bool = Vector2(e.vel.x, e.vel.z).length() > 0.3
	b.body.position.y = absf(sin(_time * 12.0)) * 0.05 if moving else 0.0
	b.body.rotation.z = sin(_time * 30.0) * 0.08 if e.state == "stunned" else 0.0
	for i in b.legs.size():
		b.legs[i].rotation.x = sin(_time * 12.0 + i * 2.0) * 0.4 if moving else 0.0


# ---------------------------------------------------------------- 毎刻み

func sync(enemies: Array, dt: float) -> void:
	_time += dt
	for e in enemies:
		var b: Built = _built.get(e)
		if b == null:
			b = _make_glb(e.kind)
			if b == null:
				b = _make_charger() if e.kind == "charger" else _make_sentry()
			add_child(b.root)
			_built[e] = b
		if not e.alive:
			if b.glb:
				_break_glb(b, e, dt)
			else:
				# 撃破：縮んで消える
				b.root.visible = e.dead_time < 0.3
				b.root.scale = Vector3.ONE * maxf(0.01, 1.0 - e.dead_time * 3.0)
			continue
		b.root.position = e.pos
		b.root.rotation.y = e.yaw
		if b.glb:
			_animate_glb(b, e, dt)
		else:
			_animate_fallback(b, e)
