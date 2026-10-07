class_name Fx
extends Node3D
## 弾、火花、爆発、斬撃の軌跡、画面の揺れ

const SHOT_COLORS := {
	"normal": Color("#ffd27a"), "charge1": Color("#ffe7a8"), "charge2": Color("#ffffff"),
	"wave": Color("#ffcf7a"), "enemy": Color("#ff9a5a"),
}
## 見た目の太さ（当たり判定より小さめ）
const SHOT_VIS := {"normal": 0.07, "charge1": 0.16, "charge2": 0.32, "wave": 0.35, "enemy": 0.12}

var shake := 0.0
var _shots := {}
var _particles: Array = []
var _slash: MeshInstance3D
var _slash_mat: StandardMaterial3D
var _slash_life := 0.0
## 刃を振り抜く時間（秒）。3 段斬りの動作は当たり判定の始まりから 3 こま（1/60 秒 × 3）で振り抜く
const SLASH_SWEEP := 0.06
var _ball := MeshKit.sphere(1.0, 10)
var _spark := MeshKit.sphere(0.06, 4)
var _rng := RandomNumberGenerator.new()


func _ready() -> void:
	# 斬撃の弧（内径 1.2m、外径 2.2m、126 度）
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var n := 24
	for i in n:
		var a0 := lerpf(-PI * 0.35, PI * 0.35, float(i) / n)
		var a1 := lerpf(-PI * 0.35, PI * 0.35, float(i + 1) / n)
		var p := [Vector3(sin(a0) * 1.2, 0, cos(a0) * 1.2), Vector3(sin(a0) * 2.2, 0, cos(a0) * 2.2),
			Vector3(sin(a1) * 2.2, 0, cos(a1) * 2.2), Vector3(sin(a1) * 1.2, 0, cos(a1) * 1.2)]
		for idx in [0, 1, 2, 0, 2, 3]:
			st.add_vertex(p[idx])
	_slash_mat = MeshKit.glow(Color("#ffe2a0"), 3.0, 0.0)
	_slash_mat.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	_slash = MeshKit.add(self, st.commit(), _slash_mat)
	_slash.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF


func handle(e: Dictionary) -> void:
	match e.type:
		"hit":
			var kind: String = e.kind
			var color := Color("#fff3b0") if kind == "weak" else (Color("#c8c0b0") if kind == "armor" else Color("#ffb23e"))
			var n := 14 if kind == "weak" else (3 if kind == "armor" else 7)
			_burst(e.at, color, n, 6.0 if kind == "weak" else 4.0, 0.25)
		"enemyDestroyed":
			_burst(e.at, Color("#ffcf7a"), 26, 8.0, 0.6)
			_flash_ball(e.at, Color("#ffe0a0"), 1.4, 0.3)
		"shake":
			shake = maxf(shake, e.strength)


func _burst(at: Vector3, color: Color, n: int, speed: float, life: float) -> void:
	var m := MeshKit.glow(color, 3.0, 1.0)
	for i in n:
		var mi := MeshKit.add(self, _spark, m, at)
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		var v := Vector3(_rng.randf() - 0.5, _rng.randf() * 0.8, _rng.randf() - 0.5).normalized() * speed * (0.4 + _rng.randf())
		_particles.append({"mesh": mi, "vel": v, "life": life, "max": life, "grow": 0.0, "mat": m})


func _flash_ball(at: Vector3, color: Color, size: float, life: float) -> void:
	var m := MeshKit.glow(color, 4.0, 1.0)
	m.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	var mi := MeshKit.add(self, _ball, m, at)
	mi.scale = Vector3.ONE * size * 0.3
	_particles.append({"mesh": mi, "vel": Vector3.ZERO, "life": life, "max": life, "grow": size * 3.0, "mat": m})


func sync(game: GameSim, dt: float) -> void:
	# 弾：進行方向に伸びた光の筋
	var alive := {}
	for s in game.shots:
		alive[s] = true
		var mi: MeshInstance3D = _shots.get(s)
		if mi == null:
			var col: Color = SHOT_COLORS.get(s.kind, Color.WHITE)
			mi = MeshKit.add(self, _ball, MeshKit.glow(col, 4.0))
			mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
			var halo_m := MeshKit.glow(col, 2.0, 0.28)
			halo_m.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
			var halo := MeshKit.add(mi, _ball, halo_m)
			halo.scale = Vector3(2.2, 2.2, 1.2)
			halo.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
			var r: float = SHOT_VIS.get(s.kind, 0.1)
			var length := r * 0.4 if s.kind == "wave" else r * (6.0 if s.kind == "normal" else 3.0)
			mi.set_meta("scale", Vector3(1.4 if s.kind == "wave" else r, r, length))
			_shots[s] = mi
		mi.position = s.pos
		if s.vel.length() > 0.01:
			mi.look_at(s.pos + s.vel, Vector3.UP if absf(s.vel.normalized().y) < 0.99 else Vector3.RIGHT)
		mi.scale = mi.get_meta("scale")
	for s in _shots.keys():
		if not alive.has(s):
			_shots[s].queue_free()
			_shots.erase(s)

	# 粒子
	for p in _particles:
		p.life -= dt
		p.vel.y -= 9.0 * dt
		p.mesh.position += p.vel * dt
		if p.grow > 0.0:
			p.mesh.scale += Vector3.ONE * p.grow * dt
		p.mat.albedo_color.a = maxf(0.0, p.life / p.max)
		if p.mat.transparency == BaseMaterial3D.TRANSPARENCY_DISABLED:
			p.mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	var keep: Array = []
	for p in _particles:
		if p.life > 0.0:
			keep.append(p)
		else:
			p.mesh.queue_free()
	_particles = keep

	# 斬撃の軌跡：刃を振り抜く間（当たり判定の始まりから SLASH_SWEEP 秒。動作の振り抜きと同じ）だけ回して、あとは消える
	var pl := game.player
	var a := pl.attack
	if a != null and a.time >= a.active_from - 0.017 and a.time <= a.active_from + SLASH_SWEEP:
		_slash_life = 0.12
		_slash.position = pl.pos + Vector3(0, 1.0 if a.move == "combo3" else 1.05, 0)
		var sweep := -1.0 if a.move == "combo2" else 1.0
		var k := clampf((a.time - a.active_from) / SLASH_SWEEP, 0.0, 1.0)
		_slash.rotation = Vector3(PI / 2.0 if a.move == "combo3" else 0.0, pl.yaw + sweep * (k - 0.5) * 1.4, 0.0)
		_slash.scale = Vector3.ONE * (1.6 if a.move == "charge" else 1.0)
	_slash_life = maxf(0.0, _slash_life - dt)
	_slash_mat.albedo_color.a = _slash_life * 6.0
	_slash.visible = _slash_life > 0.0

	shake = maxf(0.0, shake - dt * 2.5)
