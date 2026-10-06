class_name EnemyView
extends Node3D
## 番機の見た目。banki_<型>.glb（tools/blender/recon/banki.py、npm run banki:build）を部品の階層のまま置き、
## 敵の状態（sim/enemies の state）から手続きで動かす（GLB にアニメーションはない）。
## 部品は原点が回転軸・ローカル +X が軸（ナゴミと同じ約束）：元の姿勢 * Basis(RIGHT, 角度) で回す。
## GLB がないとき（テストの環境など）は、MVP の仮の形（白い陶器・真鍮・スリットのセンサー）で代わりにする。

const MODELS := {
	"sentry": "res://assets/models/banki_sentry.glb",
	"charger": "res://assets/models/banki_charger.glb",
	"mini": "res://assets/models/banki_mini.glb",
	"shield": "res://assets/models/banki_shield.glb",
	"floater": "res://assets/models/banki_floater.glb",
	"kannuki": "res://assets/models/kannuki.glb",
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
	"mini": {
		"label_h": 0.7,
		"tele_lean": 20.0,      # 予備動作：前へかがんで身を縮める
		"tele_drop": 0.045,
		"tuck": 40.0,           # 跳んでいる間、脚を畳む
		"horn_wag": 9.0,
		"detach": ["horn_l", "foot_r", "shin_l"],
		"sink_at": 1.5, "vanish": 2.5,
	},
	"shield": {
		"label_h": 2.3,
		"stride": 1.6,
		"hip_swing": 20.0,
		"knee_bend": 28.0,
		"bob": 0.02,
		"fist_up": -115.0,      # 予備動作：拳を振りかぶる（腕の付け根の角度）
		"fist_down": 38.0,      # 振り下ろし
		"shield_open": 75.0,    # 盾が崩れたとき：盾を横へ振り出す
		"detach": ["shield", "forearm_r", "head", "foot_l"],
		"collapse_drop": 0.35,
	},
	"floater": {
		"label_h": 0.95,
		"flap": 7.0,            # 葉の羽ばたきの振れ（度）
		"open": 32.0,           # 予備動作・降下：葉を開く
		"dive_pitch": 22.0,     # 降下：前へ傾く
		"crown_open": -50.0,    # 降下のあと：上部の核の冠を開く
		"bob": 0.03,
		"detach": ["lobe_1", "muzzle", "crown"],
		"fall": true,
		"sink_at": 2.5, "vanish": 3.5,
	},
	"kannuki": {
		"label_h": 5.6,
		"elbow": -93.9,         # 肘を伸ばす角（kannuki.py の pose.json）
		"lid_slide": 0.6,
		"key_open": 100.0,
		"detach": ["arm_fl_yaw", "arm_fr_yaw", "arm_rl_yaw", "arm_rr_yaw", "keyplate", "lid_f"],
		"collapse_drop": 0.35,
		"sink_at": 5.0, "vanish": 8.0,
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
	var alert: Node3D
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
	var arm := Vector3.ZERO  # 閂：腕の姿勢（肩の縦軸・横軸・肘、度。なめらかに追う）
	var spin := 0.0          # 閂：削岩錐の自転の角度
	var open := 0.0          # 錠前核の蓋の開き（0..1）／盾の振り出し
	var brass: StandardMaterial3D = null
	var hot := 0.0           # 過熱の度合い
	var arm_gone := {}


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
				if m and b.kind == "kannuki" and String(m.resource_name) == "banki_brass":
					if b.brass == null:
						b.brass = (m as StandardMaterial3D).duplicate()
					mi.set_surface_override_material(s, b.brass)
				elif m and (String(m.resource_name).ends_with("_shell") or String(m.resource_name).ends_with("_ivory")):
					# 部品で 1 つの複製を共有する（被弾の光・撃破の暗さをまとめて変える）
					if b.shell == null:
						b.shell = (m as StandardMaterial3D).duplicate() if m is StandardMaterial3D else StandardMaterial3D.new()
					mi.set_surface_override_material(s, b.shell)
	b.body = b.parts.get("body", model)
	if b.shell == null:
		b.shell = PORCELAIN.duplicate()
	b.alert = MeshKit.alert_mark(POSE[kind].label_h)
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
	elif b.kind == "mini":
		_anim_mini(b, e, dt, P, stun_wobble)
	elif b.kind == "shield":
		_anim_shield(b, e, dt, P, speed, stun_wobble)
	elif b.kind == "floater":
		_anim_floater(b, e, dt, P)
	elif b.kind == "kannuki":
		_anim_kannuki(b, e, dt, P)
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


## 子番機：跳ねる（空中は脚を畳む）。予備動作は前へかがんで角を立てる
func _anim_mini(b: Built, e, dt: float, P: Dictionary, wobble: float) -> void:
	var air: bool = not e._grounded
	b.ram = move_toward(b.ram, 1.0 if air else 0.0, dt * 12.0)
	var crouch: float = b.tele
	_pose(b, "body", P.tele_lean * crouch + wobble, Vector3(0, -P.tele_drop * crouch, 0))
	for side in ["l", "r"]:
		_pose(b, "thigh_" + side, -P.tuck * b.ram + 10.0 * crouch)
		_pose(b, "shin_" + side, P.tuck * 1.4 * b.ram)
		_pose(b, "foot_" + side, -P.tuck * 0.4 * b.ram)
	var wag: float = P.horn_wag * (sin(_time * 9.0) if e.state != "idle" else sin(_time * 2.0) * 0.3)
	_pose(b, "horn_l", wag - 25.0 * crouch)
	_pose(b, "horn_r", -wag - 25.0 * crouch)
	_set_glow(b.core, SENSOR_NORMAL, 1.6 + 0.5 * sin(_time * 4.0))


## 盾型：重い足取り。盾は前に構えたまま。予備動作で拳を振りかぶり、盾が崩れると横へ振り出して体が傾く
func _anim_shield(b: Built, e, dt: float, P: Dictionary, speed: float, wobble: float) -> void:
	b.phase += speed * dt * P.stride
	var walk := clampf(speed / 1.2, 0.0, 1.0)
	var s := sin(b.phase)
	var broken_guard: bool = e.state == "stunned"
	b.open = move_toward(b.open, 1.0 if broken_guard else 0.0, dt * (6.0 if broken_guard else 2.0))
	var bob: float = P.bob * absf(s) * walk
	_pose(b, "body", -14.0 * b.open + wobble * 0.5, Vector3(0, bob - 0.06 * b.open, 0))
	for side in [["l", 1.0], ["r", -1.0]]:
		var ph: float = s * side[1]
		_pose(b, "thigh_" + side[0], -P.hip_swing * ph * walk)
		_pose(b, "shin_" + side[0], P.knee_bend * maxf(0.0, -cos(b.phase) * side[1]) * walk)
	var fist: float = 0.0
	if e.state == "windup":
		fist = P.fist_up * b.tele
	elif e.state == "attack":
		fist = lerpf(P.fist_up, P.fist_down, clampf(e.state_time / 0.15, 0.0, 1.0))
	elif e.state == "recover":
		fist = lerpf(P.fist_down, 0.0, clampf(e.state_time / 0.5, 0.0, 1.0))
	_pose(b, "upperarm_r", fist)
	_pose(b, "head", 12.0 * b.tele - 10.0 * b.open)
	# 盾の守り：削られるほど盾の傷みで前後に揺れる（小さく）
	var gw: float = 0.0 if e.guard >= game_guard_max(e) else sin(_time * 22.0) * 2.5 * (1.0 - e.guard / game_guard_max(e))
	_pose(b, "shield", P.shield_open * b.open + gw)
	_set_glow(b.core, SENSOR_NORMAL.lerp(Color(1.0, 0.9, 0.6), b.open), 1.6 + b.open * 4.0)


func game_guard_max(e) -> float:
	return float(e.game.tuning.enemies.shield.guard)


## 浮遊型：葉を羽ばたかせて浮かぶ。予備動作・降下で葉を開き、降下のあとは冠を開いて核を見せる
func _anim_floater(b: Built, e, dt: float, P: Dictionary) -> void:
	var diving: bool = e.state == "attack"
	b.ram = move_toward(b.ram, 1.0 if diving else 0.0, dt * 6.0)
	var exposed: bool = e.state == "recover"
	b.cover = move_toward(b.cover, 1.0 if exposed else 0.0, dt * (5.0 if exposed else 2.0))
	var open := maxf(b.tele, b.ram)
	var bob: float = P.bob * sin(_time * 2.4 + e.pos.x)
	_pose(b, "body", P.dive_pitch * b.ram + sin(_time * 30.0) * 3.0 * float(e.state == "stagger"), Vector3(0, bob, 0))
	for i in 3:
		_pose(b, "lobe_%d" % i, P.flap * sin(_time * 5.0 + i * 2.1) + P.open * open)
	_pose(b, "crown", P.crown_open * b.cover)
	_pose(b, "muzzle", 0.0, Vector3(0, -0.04 * open, 0))
	var pulse := 0.5 + 0.5 * sin(_time * 9.0)
	_set_glow(b.core, SENSOR_NORMAL.lerp(Color(1.0, 0.9, 0.6), b.cover * pulse), 1.4 + b.cover * (3.0 + pulse * 3.0))


## 閂：技ごとに腕・蓋・錠前の板・削岩錐の自転を動かす
func _anim_kannuki(b: Built, e, dt: float, P: Dictionary) -> void:
	var st: String = e.state
	var el: float = P.elbow
	var tgt := Vector3.ZERO     # 肩の縦軸・肩の横軸・肘
	var spin_rate := 40.0
	match st:
		"engage":
			spin_rate = 220.0
		"thrust_windup":
			tgt = Vector3(0.0, 8.0, el * 0.85)
			spin_rate = 500.0 + 500.0 * b.tele
		"thrust":
			tgt = Vector3(0.0, 0.0, el)
			spin_rate = 1000.0
		"spin_windup":
			tgt = Vector3(45.0, 0.0, el)
			spin_rate = 700.0
		"spin":
			tgt = Vector3(45.0, 0.0, el)
			spin_rate = 1100.0
		"volley_windup", "volley":
			tgt = Vector3(12.0, 8.0, el * 0.25)
			spin_rate = 400.0
		"slam_windup":
			tgt = Vector3(15.0, -55.0, el * 0.65)
			spin_rate = 400.0
		"slam":
			tgt = Vector3(15.0, 70.0, el)
			spin_rate = 800.0
		"summon_windup":
			tgt = Vector3(30.0, -30.0, el * 0.4)
			spin_rate = 150.0
		"stuck", "slam_open":
			tgt = Vector3(25.0, 35.0, el * 0.3)
			spin_rate = 20.0
		"shift":
			tgt = Vector3(20.0 + 10.0 * sin(_time * 18.0), 10.0, el * 0.5)
			spin_rate = 500.0
		"dead":
			tgt = Vector3(30.0, 40.0, el * 0.2)
			spin_rate = 0.0
	if e.overheat:
		spin_rate += 250.0
	_update_debris(b, dt)
	b.arm = b.arm.lerp(tgt, 1.0 - exp(-8.0 * dt))
	b.spin += spin_rate * dt
	# 壊れた腕は外れて落ちる（やり直しで戻る）
	for a in e.ARMS:
		var nm := "arm_%s_yaw" % a
		var node: Node3D = b.parts.get(nm)
		if node == null:
			continue
		if e.arm_broken[a] and not b.arm_gone.get(a, false):
			b.arm_gone[a] = true
			node.reparent(b.root, true)
			var ang := float(a.hash() % 100) * 0.063
			b.debris.append({"node": node, "vel": Vector3(cos(ang) * 2.0, 4.0, sin(ang) * 2.0),
					"axis": Vector3(sin(ang), 0.5, cos(ang)).normalized(), "spin": 4.0})
		elif not e.arm_broken[a] and b.arm_gone.get(a, false):
			b.arm_gone[a] = false
			for d in b.debris.duplicate():
				if d.node == node:
					b.debris.erase(d)
			node.reparent(b.body, false)
			node.transform = b.rest[nm]
		if not b.arm_gone.get(a, false):
			_pose(b, nm, b.arm.x)
			_pose(b, "arm_%s_pitch" % a, b.arm.y)
			_pose(b, "arm_%s_elbow" % a, b.arm.z)
			_pose(b, "arm_%s_drill" % a, b.spin)
	# 錠前核：蓋が滑って離れ、板が起きる（核が露出している間）
	b.open = move_toward(b.open, 1.0 if e.core_open else 0.0, dt * 3.0)
	for l in ["lid_f", "lid_r"]:
		var n: Node3D = b.parts.get(l)
		if n != null and n.get_parent() == b.body:
			var r: Transform3D = b.rest[l]
			n.transform = Transform3D(r.basis, r.origin + r.basis.x * P.lid_slide * b.open)
	_pose(b, "keyplate", P.key_open * b.open)
	var pulse := 0.5 + 0.5 * sin(_time * 10.0)
	_set_glow(b.core, SENSOR_NORMAL.lerp(Color(1.0, 0.9, 0.6), b.open * pulse), 1.2 + b.open * (3.0 + pulse * 4.0))
	# 過熱：真鍮の部分が赤熱する
	b.hot = move_toward(b.hot, 1.0 if e.overheat else 0.0, dt * 0.8)
	if b.brass != null:
		b.brass.emission_enabled = b.hot > 0.01
		b.brass.emission = Color("#ff4a1a") * (0.6 + 0.4 * sin(_time * 6.0))
		b.brass.emission_energy_multiplier = b.hot * 2.5
	_pose(b, "body", 0.0, Vector3(0, 0.03 * sin(_time * 1.6), 0))
	b.alert.visible = false


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
			if n == null or n.get_parent() == b.root:
				continue
			n.reparent(b.root, true)
			var a := float(i) * 2.399 + 0.7   # 部品ごとに違う向き（決まった値。乱数を使わない）
			b.debris.append({"node": n, "vel": Vector3(cos(a) * 1.2, 2.2 + 0.4 * (i % 2), sin(a) * 1.2),
					"axis": Vector3(sin(a), 0.5, cos(a)).normalized(), "spin": 6.0 + i})
			i += 1
	var t: float = e.dead_time
	_update_debris(b, dt)
	var k := clampf(t / 0.5, 0.0, 1.0)
	match b.kind:
		"sentry":
			_pose(b, "body", 18.0 * k, Vector3(0, -P.collapse_drop * k, 0))
			for side in ["l", "r"]:
				_pose(b, "thigh_" + side, -70.0 * k)
				_pose(b, "shin_" + side, 95.0 * k)
		"charger":
			b.body.rotation.z = deg_to_rad(8.0) * k
			_pose(b, "body", 0.0, Vector3(0, -P.collapse_drop * k, 0))
			_pose(b, "core_cover", 0.0)
		"mini":
			b.body.rotation.z = deg_to_rad(70.0) * k
			_pose(b, "body", 0.0, Vector3(0, -0.03 * k, 0))
		"shield":
			_pose(b, "body", -30.0 * k, Vector3(0, -P.collapse_drop * k, 0))
			for side in ["l", "r"]:
				_pose(b, "thigh_" + side, 50.0 * k)
				_pose(b, "shin_" + side, 70.0 * k)
		"floater":
			b.body.rotation.z = deg_to_rad(40.0) * k
		"kannuki":
			_pose(b, "body", 4.0 * k, Vector3(0, -P.collapse_drop * k, 0))
			b.open = move_toward(b.open, 1.0, dt * 2.0)
			for l in ["lid_r"]:
				var n: Node3D = b.parts.get(l)
				var r: Transform3D = b.rest[l]
				n.transform = Transform3D(r.basis, r.origin + r.basis.x * P.lid_slide * b.open)
			if b.brass != null:
				b.brass.emission_enabled = false
	var sink_at: float = P.get("sink_at", 3.0)
	var vanish: float = P.get("vanish", 4.5)
	# 浮遊型は落ちる。ほかは時間がたつと沈んで消える
	if P.get("fall", false):
		b.root.position.y = maxf(0.0, e.pos.y - 0.5 * 14.0 * t * t) - maxf(0.0, t - sink_at) * 0.5
	else:
		b.root.position.y = e.pos.y - maxf(0.0, t - sink_at) * 0.6
	b.root.visible = t < vanish


## 外れた部品を落とす（撃破・腕の破壊）
func _update_debris(b: Built, dt: float) -> void:
	for d in b.debris:
		var n: Node3D = d.node
		if n.position.y > 0.04 or d.vel.y > 0.0:
			d.vel.y -= 9.8 * dt
			n.position += d.vel * dt
			n.rotate(d.axis, d.spin * dt)
		else:
			n.position.y = 0.04


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
	b.alert = MeshKit.alert_mark(1.6)
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
	b.alert = MeshKit.alert_mark(1.9)
	b.root.add_child(b.alert)
	return b


## 子番機・盾型・浮遊型・閂の仮の形（GLB がないとき）。箱と球だけ
func _make_simple(kind: String) -> Built:
	var b := Built.new()
	b.kind = kind
	b.root = Node3D.new()
	b.body = Node3D.new()
	b.root.add_child(b.body)
	b.shell = PORCELAIN.duplicate()
	b.sensor = MeshKit.glow(Color("#ffb23e"), 3.0)
	b.core = MeshKit.glow(Color("#ffcf7a"), 2.0)
	var label_h := 1.0
	match kind:
		"mini":
			MeshKit.add(b.body, MeshKit.sphere(0.16, 8), b.shell, Vector3(0, 0.16, 0))
			MeshKit.add(b.body, MeshKit.box(Vector3(0.14, 0.03, 0.03)), b.sensor, Vector3(0, 0.2, 0.14))
			label_h = 0.7
		"shield":
			MeshKit.add(b.body, MeshKit.box(Vector3(0.7, 1.4, 0.4)), b.shell, Vector3(0, 0.95, 0))
			MeshKit.add(b.body, MeshKit.box(Vector3(1.2, 1.6, 0.12)), BRASS, Vector3(0.5, 0.95, 0.5))
			MeshKit.add(b.body, MeshKit.box(Vector3(0.3, 0.05, 0.04)), b.sensor, Vector3(0, 1.55, 0.2))
			label_h = 2.3
		"floater":
			MeshKit.add(b.body, MeshKit.sphere(0.3, 10), b.shell, Vector3(0, 0.3, 0))
			MeshKit.add(b.body, MeshKit.cyl(0.4, 0.4, 0.03, 16), BRASS, Vector3(0, 0.3, 0))
			MeshKit.add(b.body, MeshKit.sphere(0.08, 8), b.core, Vector3(0, 0.55, 0))
			label_h = 0.95
		"kannuki":
			MeshKit.add(b.body, MeshKit.cyl(1.75, 1.75, 10.0, 16), b.shell, Vector3(0, 2.6, 0), Vector3(PI / 2, 0, 0))
			for xz in [[2.2, 3.4], [-2.2, 3.4], [2.2, -3.35], [-2.2, -3.35]]:
				MeshKit.add(b.body, MeshKit.box(Vector3(0.6, 0.6, 3.0)), BRASS, Vector3(xz[0], 3.0, xz[1]))
			MeshKit.add(b.body, MeshKit.sphere(0.45, 10), b.core, Vector3(0, 4.3, 0))
			label_h = 5.6
	b.alert = MeshKit.alert_mark(label_h)
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
				match e.kind:
					"charger":
						b = _make_charger()
					"sentry":
						b = _make_sentry()
					_:
						b = _make_simple(e.kind)
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
	# いなくなった敵（やり直しで消えた呼び出しなど）の見た目を片付ける
	var present := {}
	for e in enemies:
		present[e] = true
		if e.kind == "kannuki":
			_sync_hazards(e)
	for k in _built.keys():
		if not present.has(k):
			_built[k].root.queue_free()
			_built.erase(k)


# ---------------------------------------------------------------- 閂の危険な範囲の表示

var _haz := {}


func _hazard(key: String, mesh: Mesh, color: Color) -> MeshInstance3D:
	var mi: MeshInstance3D = _haz.get(key)
	if mi == null:
		var m := MeshKit.glow(color, 2.0, 0.3)
		m.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
		m.cull_mode = BaseMaterial3D.CULL_DISABLED
		mi = MeshKit.add(self, mesh, m)
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		_haz[key] = mi
	return mi


## 避ける合図を床に出す：突進の通り道・回転薙ぎの範囲・衝撃波の輪・過熱する床
func _sync_hazards(e) -> void:
	var red := Color("#ff4a2a")
	var cyl := CylinderMesh.new()
	cyl.top_radius = 1.0
	cyl.bottom_radius = 1.0
	cyl.height = 0.04
	cyl.radial_segments = 40
	var spin := _hazard("spin", _haz_mesh("spin", cyl), red)
	spin.visible = e.alive and e.spin_r > 0.0
	if spin.visible:
		spin.position = Vector3(e.pos.x, e.pos.y + 0.06, e.pos.z)
		spin.scale = Vector3(e.spin_r, 1.0, e.spin_r)
		(spin.material_override as StandardMaterial3D).albedo_color.a = 0.22 if e.state == "spin_windup" else 0.4
	var lane_box := BoxMesh.new()
	lane_box.size = Vector3(3.5, 0.04, 24.0)
	var lane := _hazard("lane", _haz_mesh("lane", lane_box), red)
	lane.visible = e.alive and e.lane
	if lane.visible:
		var f: Vector3 = e.forward()
		lane.position = Vector3(e.pos.x + f.x * 12.0, e.pos.y + 0.06, e.pos.z + f.z * 12.0)
		lane.rotation.y = e.yaw
		(lane.material_override as StandardMaterial3D).albedo_color.a = 0.15 + 0.2 * (0.5 + 0.5 * sin(_time * 30.0))
	var wave := _hazard("wave", _haz_mesh("wave", TorusMesh.new()), Color("#ffb23e"))
	wave.visible = e.alive and e.wave_r > 0.0
	if wave.visible:
		var tm: TorusMesh = wave.mesh
		tm.inner_radius = maxf(0.1, e.wave_r - 0.5)
		tm.outer_radius = e.wave_r + 0.5
		wave.position = Vector3(e.pos.x, e.pos.y + 0.1, e.pos.z)
		wave.scale = Vector3(1.0, 0.25, 1.0)
	var heat_mesh := TorusMesh.new()
	heat_mesh.inner_radius = 11.5
	heat_mesh.outer_radius = 16.0
	heat_mesh.rings = 48
	var heat := _hazard("heat", _haz_mesh("heat", heat_mesh), Color("#ff6a1a"))
	heat.visible = e.alive and e.heat_state > 0
	if heat.visible:
		heat.position = Vector3(e.arena.x, e.arena.y + 0.05, e.arena.z)
		heat.scale = Vector3(1.0, 0.02, 1.0)
		var a := 0.12 + 0.12 * (0.5 + 0.5 * sin(_time * 14.0)) if e.heat_state == 1 else 0.45 + 0.1 * sin(_time * 8.0)
		(heat.material_override as StandardMaterial3D).albedo_color.a = a


## 範囲の表示の形は 1 度だけ作る（毎刻み新しく作らない）
var _haz_meshes := {}


func _haz_mesh(key: String, m: Mesh) -> Mesh:
	if not _haz_meshes.has(key):
		_haz_meshes[key] = m
	return _haz_meshes[key]
