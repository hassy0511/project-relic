class_name EnemyView
extends Node3D
## 番機の仮の見た目（MVP と同じ形）。Codex の設定画が届いたら GLB に差し替える。
## 先史の技術の見た目の仮決め：白い陶器のような外装、真鍮の継ぎ目、スリット状のセンサー。

var _built := {}
var _time := 0.0
var PORCELAIN := MeshKit.mat(Color("#e9e3d6"), 0.35)
var BRASS := MeshKit.mat(Color("#b08a4a"), 0.4, 0.6)
var DARK := MeshKit.mat(Color("#3a3530"), 0.7)


class Built:
	var root: Node3D
	var body: Node3D
	var shell: StandardMaterial3D
	var sensor: StandardMaterial3D
	var core: StandardMaterial3D
	var alert: Label3D
	var legs: Array = []


func _make_sentry() -> Built:
	var b := Built.new()
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


func sync(enemies: Array, dt: float) -> void:
	_time += dt
	for e in enemies:
		var b: Built = _built.get(e)
		if b == null:
			b = _make_charger() if e.kind == "charger" else _make_sentry()
			add_child(b.root)
			_built[e] = b
		if not e.alive:
			# 撃破：縮んで消える
			b.root.visible = e.dead_time < 0.3
			b.root.scale = Vector3.ONE * maxf(0.01, 1.0 - e.dead_time * 3.0)
			continue
		b.root.position = e.pos
		b.root.rotation.y = e.yaw
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
		# 被弾の光
		b.shell.emission_enabled = e.flash > 0.01
		b.shell.emission = Color(e.flash, e.flash * 0.9, e.flash * 0.7)
		b.alert.visible = e.alerting()
		# 歩きの揺れ
		var moving: bool = Vector2(e.vel.x, e.vel.z).length() > 0.3
		b.body.position.y = absf(sin(_time * 12.0)) * 0.05 if moving else 0.0
		b.body.rotation.z = sin(_time * 30.0) * 0.08 if e.state == "stunned" else 0.0
		for i in b.legs.size():
			b.legs[i].rotation.x = sin(_time * 12.0 + i * 2.0) * 0.4 if moving else 0.0
