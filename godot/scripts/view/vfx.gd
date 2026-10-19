class_name Vfx
extends Node3D
## エフェクトの粒を「層」ごとにまとめて描く（W2-09 の粒子の素材 assets/vfx/vfx_tex_*.png）。
## 層 = マスク 1 枚 × 混ぜ方 1 つ = MultiMesh 1 つ = 描画 1 回。何粒・いくつのエフェクトが重なっても、層の数より描画は増えない。
## 空の層は隠す（描画しない）。粒の数には層ごとの上限があり、超えたら古い粒から消える。
## 粒は 2 種類：
##   emit()   … 寿命のある粒。位置・速さ・重力・大きさと明るさの変化をここで進める（火花・破片・煙・広がる輪）
##   sprite() … その刻みだけの板。毎刻み描き直す（弾の芯・溜めの輪・予兆の光など、動く物に付いているもの）
## 粒の向き：FACE（カメラを向く）、FLAT（basis のまま。床の輪・斬撃の帯）、STREAK（basis.y＝速さの向きに伸びる火花・弾の筋）。
## 混ぜ方は足し合わせ（光）と普通の半透明（煙・破片）だけ。掛け算（blend_mul）は gl_compatibility で黒くなるので使わない。
## シェーダー：assets/shaders/vfx_add.gdshader・vfx_mix.gdshader（中身は vfx_particle.gdshaderinc）

const FACE := 0
const FLAT := 1
const STREAK := 2

const SPARK := 0
const GRAIN := 1
const GLINT := 2
const RING := 3
const SLASH := 4
const PILLAR := 5
const HEX := 6
const SMOKE := 7
const DUST := 8
const SHARD := 9
const SHARD_GLOW := 10
const DOT := 11
const SOFT := 12
const SLASH_MIX := 13

## 層：tex（マスク）、add（足し合わせ＝光。明るい床の上では白っぽくなる）か普通の半透明（色がそのまま残る：
## 煙・破片・敵弾の芯 DOT・やわらかい色の光 SOFT・斬撃の帯の地の色 SLASH_MIX）、窓（center・scale・rot（度）：マスクの絵のある所を四角いっぱいに使う）、
## 濃さの整え（lo・hi・pow）、shade（色にマスクの濃淡を残す割合）、max（同時に描く粒の上限）
const LAYERS := [
	{"tex": "spark", "add": true, "center": Vector2(0.514, 0.469), "scale": 0.4, "rot": 38.0, "max": 256},
	{"tex": "grain", "add": true, "center": Vector2(0.5, 0.496), "scale": 0.34, "max": 320},
	{"tex": "glint", "add": true, "center": Vector2(0.498, 0.492), "scale": 0.2, "max": 48},
	{"tex": "shock_ring", "add": true, "max": 48},
	{"tex": "slash", "add": true, "max": 16, "wipe": true},
	{"tex": "pillar", "add": true, "max": 24},
	{"tex": "hex", "add": true, "center": Vector2(0.5, 0.51), "scale": 0.78, "max": 16},
	{"tex": "smoke", "add": false, "lo": 0.02, "hi": 0.75, "shade": 0.35, "max": 64},
	{"tex": "dust", "add": false, "center": Vector2(0.5, 0.48), "scale": 0.8, "lo": 0.02, "hi": 0.6, "shade": 0.3, "max": 64},
	{"tex": "shard", "add": false, "center": Vector2(0.5, 0.48), "scale": 0.8, "lo": 0.05, "hi": 0.22, "shade": 0.55, "max": 96},
	{"tex": "shard", "add": true, "center": Vector2(0.5, 0.48), "scale": 0.8, "lo": 0.03, "hi": 0.6, "max": 48},
	{"tex": "grain", "add": false, "center": Vector2(0.5, 0.496), "scale": 0.3, "lo": 0.25, "hi": 0.6, "max": 96},
	{"tex": "grain", "add": false, "center": Vector2(0.5, 0.496), "scale": 0.34, "lo": 0.02, "hi": 0.7, "max": 96},
	{"tex": "slash", "add": false, "lo": 0.04, "hi": 0.45, "max": 16, "wipe": true},
]
## 斬撃の帯（vfx_tex_slash.png）の円弧：中心（UV）・半径（UV）・尾の角度・刃先の角度（rad。UV は下向きが +y）
const SLASH_CENTER := Vector2(0.397, -0.139)
const SLASH_RADIUS := 0.732
const SLASH_A0 := 2.09
const SLASH_A1 := 0.70
## 輪（vfx_tex_shock_ring.png）の半径：四角の一辺に対する割合
const RING_FRAC := 0.445


class P:
	var pos := Vector3.ZERO
	var vel := Vector3.ZERO
	var age := 0.0
	var life := 0.3
	## 大きさ（m）：始め → 終わり。aspect = 縦 ÷ 横（FACE・STREAK）
	var s0 := 0.2
	var s1 := 0.2
	var aspect := 1.0
	## 色（明るさ込み。1 を超えてよい）。明るさは寿命の fin の割合で 0 → 最大、あとは (1 - t)^fpow で消える
	var col := Color.WHITE
	var fin := 0.08
	var fpow := 1.0
	var mode := FACE
	## FLAT の向き（大きさ 1。s をかける）
	var basis := Basis.IDENTITY
	var rot := 0.0
	var spin := 0.0
	var grav := 0.0
	var drag := 0.0
	## STREAK：速さ × stretch を長さに足す
	var stretch := 0.0
	## 拭き出し（斬撃の帯）：この秒数で円弧の尾から刃先まで出す（0 = しない）
	var wipe := 0.0
	## 床の高さ（破片が跳ねて止まる）。-INF なら床なし
	var floor_y := -INF


var _quad := QuadMesh.new()
var _layers: Array = []
var _free: Array = []
## フラッシュの強さ（設定の PadConfig.flash。Fx が入れる。1 = 見本どおり）。足し合わせの層（光）で、明るさ
## （色のいちばん強い成分 × 濃さ）が FLASH_KNEE を超える分をこの倍率に縮める。Fx は大きな光（弱点・撃破・破断）をもともと
## この倍率で暗く出す（Fx._cf）ので、ここで抑えるのは、それ以外の明るい光（銃口・ダッシュの踏み出し・警戒の閃き・光柱など）の頭だけ
var flash_scale := 1.0
## 明るさの上限を掛け始める所（見本の明るさ 0.46 × GAIN 1.3 の琥珀。通常の命中・火花・輪はこれより暗い）
const FLASH_KNEE := 0.6


class Layer:
	var mm: MultiMesh
	var mi: MultiMeshInstance3D
	var add := true
	var buf := PackedFloat32Array()
	var max := 64
	var parts: Array = []
	var spr := PackedFloat32Array()
	var n_spr := 0


func _ready() -> void:
	_quad.size = Vector2(1, 1)
	var add_shader: Shader = load("res://assets/shaders/vfx_add.gdshader")
	var mix_shader: Shader = load("res://assets/shaders/vfx_mix.gdshader")
	for cfg in LAYERS:
		var l := Layer.new()
		l.max = int(cfg.max)
		l.add = bool(cfg.add)
		var mat := ShaderMaterial.new()
		mat.shader = add_shader if cfg.add else mix_shader
		mat.set_shader_parameter("mask", load("res://assets/vfx/vfx_tex_%s.png" % cfg.tex))
		mat.set_shader_parameter("uv_center", cfg.get("center", Vector2(0.5, 0.5)))
		mat.set_shader_parameter("uv_scale", float(cfg.get("scale", 1.0)))
		mat.set_shader_parameter("uv_rot", deg_to_rad(float(cfg.get("rot", 0.0))))
		mat.set_shader_parameter("mask_lo", float(cfg.get("lo", 0.0)))
		mat.set_shader_parameter("mask_hi", float(cfg.get("hi", 1.0)))
		mat.set_shader_parameter("shade", float(cfg.get("shade", 0.0)))
		if cfg.get("wipe", false):
			mat.set_shader_parameter("wipe_center", SLASH_CENTER)
			mat.set_shader_parameter("wipe_a0", SLASH_A0)
			mat.set_shader_parameter("wipe_a1", SLASH_A1)
		l.mm = MultiMesh.new()
		l.mm.transform_format = MultiMesh.TRANSFORM_3D
		l.mm.use_colors = true
		l.mm.use_custom_data = true
		l.mm.mesh = _quad
		l.mm.instance_count = l.max
		l.mm.visible_instance_count = 0
		l.buf.resize(l.max * 20)
		l.mi = MultiMeshInstance3D.new()
		l.mi.multimesh = l.mm
		l.mi.material_override = mat
		l.mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		l.mi.gi_mode = GeometryInstance3D.GI_MODE_DISABLED
		l.mi.physics_interpolation_mode = Node.PHYSICS_INTERPOLATION_MODE_OFF
		l.mi.visible = false
		add_child(l.mi)
		_layers.append(l)


## 寿命のある粒を 1 つ出す。返した粒の値（mode・grav など）を呼んだ側で足す
func emit(layer: int, pos: Vector3, vel: Vector3, life: float, s0: float, s1: float, col: Color) -> P:
	var l: Layer = _layers[layer]
	var p: P = _free.pop_back() if not _free.is_empty() else P.new()
	p.pos = pos
	p.vel = vel
	p.age = 0.0
	p.life = maxf(life, 0.016)
	p.s0 = s0
	p.s1 = s1
	p.aspect = 1.0
	p.col = col
	p.fin = 0.08
	p.fpow = 1.0
	p.mode = FACE
	p.basis = Basis.IDENTITY
	p.rot = 0.0
	p.spin = 0.0
	p.grav = 0.0
	p.drag = 0.0
	p.stretch = 0.0
	p.wipe = 0.0
	p.floor_y = -INF
	if l.parts.size() >= l.max:
		_free.append(l.parts[0])
		l.parts.remove_at(0)
	l.parts.append(p)
	return p


## その刻みだけの板：FACE（basis は使わない。size × aspect）、FLAT（basis のまま、size をかける）、
## STREAK（axis の向きに長さ |axis|、幅 size）
func sprite(layer: int, pos: Vector3, size: float, col: Color, mode := FACE, basis := Basis.IDENTITY, rot := 0.0, aspect := 1.0) -> void:
	var l: Layer = _layers[layer]
	if l.n_spr >= l.max:
		return
	var b := basis
	if mode == FACE:
		b = Basis(Vector3(size, 0, 0), Vector3(0, size * aspect, 0), Vector3(0, 0, 1))
	elif mode == FLAT:
		b = Basis(basis.x * size, basis.y * size, basis.z * size)
	else:
		b = Basis(Vector3(size, 0, 0), basis.y, Vector3(0, 0, 1))
	var i := l.spr.size()
	l.spr.resize(i + 20)
	_write(l.spr, i, b, pos, limit(col) if l.add and flash_scale < 1.0 else col, rot, mode, 0.0)
	l.n_spr += 1


## 低フラッシュ：足し合わせの光の色の、FLASH_KNEE を超える明るさを flash_scale 倍に縮める（1 なら、そのまま）
func limit(c: Color) -> Color:
	if flash_scale >= 1.0:
		return c
	var peak := maxf(c.r, maxf(c.g, c.b)) * c.a
	if peak <= FLASH_KNEE:
		return c
	var k := (FLASH_KNEE + (peak - FLASH_KNEE) * flash_scale) / peak
	return Color(c.r * k, c.g * k, c.b * k, c.a)


## 伸びる筋（その刻みだけ）：from から to へ、幅 width
func streak(layer: int, from: Vector3, to: Vector3, width: float, col: Color) -> void:
	var d := to - from
	if d.length_squared() < 1e-6:
		return
	sprite(layer, (from + to) * 0.5, width, col, STREAK, Basis(Vector3.RIGHT, d, Vector3.BACK))


func _write(buf: PackedFloat32Array, i: int, b: Basis, o: Vector3, c: Color, rot: float, mode: int, wipe: float) -> void:
	buf[i] = b.x.x
	buf[i + 1] = b.y.x
	buf[i + 2] = b.z.x
	buf[i + 3] = o.x
	buf[i + 4] = b.x.y
	buf[i + 5] = b.y.y
	buf[i + 6] = b.z.y
	buf[i + 7] = o.y
	buf[i + 8] = b.x.z
	buf[i + 9] = b.y.z
	buf[i + 10] = b.z.z
	buf[i + 11] = o.z
	buf[i + 12] = c.r
	buf[i + 13] = c.g
	buf[i + 14] = c.b
	buf[i + 15] = c.a
	buf[i + 16] = rot
	buf[i + 17] = float(mode)
	buf[i + 18] = wipe
	buf[i + 19] = 0.0


## 粒を進めて、層ごとに描く物を渡す（1 刻みに 1 回）
func step(dt: float) -> void:
	for l: Layer in _layers:
		var n := 0
		var lo := Vector3(INF, INF, INF)
		var hi := -lo
		var big := 0.0
		# その刻みだけの板
		if l.n_spr > 0:
			var cnt := mini(l.n_spr, l.max)
			for k in cnt * 20:
				l.buf[k] = l.spr[k]
			for k in cnt:
				var o := Vector3(l.spr[k * 20 + 3], l.spr[k * 20 + 7], l.spr[k * 20 + 11])
				lo = lo.min(o)
				hi = hi.max(o)
				big = maxf(big, absf(l.spr[k * 20]) + absf(l.spr[k * 20 + 5]) + absf(l.spr[k * 20 + 9]) + absf(l.spr[k * 20 + 1]) + absf(l.spr[k * 20 + 4]))
			n = cnt
			l.spr.resize(0)
			l.n_spr = 0
		# 寿命のある粒
		var parts: Array = l.parts
		var i := 0
		while i < parts.size():
			var p: P = parts[i]
			p.age += dt
			if p.age >= p.life:
				_free.append(p)
				parts[i] = parts[parts.size() - 1]
				parts.pop_back()
				continue
			i += 1
			if p.grav != 0.0:
				p.vel.y -= p.grav * dt
			if p.drag > 0.0:
				p.vel *= maxf(0.0, 1.0 - p.drag * dt)
			p.pos += p.vel * dt
			if p.pos.y < p.floor_y:
				p.pos.y = p.floor_y
				p.vel = Vector3(p.vel.x * 0.4, absf(p.vel.y) * 0.2, p.vel.z * 0.4)
				p.spin *= 0.5
			p.rot += p.spin * dt
			if n >= l.max:
				continue
			var t := p.age / p.life
			var k := t / p.fin if t < p.fin else pow(1.0 - (t - p.fin) / (1.0 - p.fin), p.fpow)
			var s := lerpf(p.s0, p.s1, 1.0 - (1.0 - t) * (1.0 - t))
			var b: Basis
			if p.mode == FACE:
				b = Basis(Vector3(s, 0, 0), Vector3(0, s * p.aspect, 0), Vector3(0, 0, 1))
			elif p.mode == FLAT:
				b = Basis(p.basis.x * s, p.basis.y * s, p.basis.z * s)
			else:
				var sp := p.vel.length()
				var ax: Vector3 = (p.vel / sp if sp > 0.01 else p.basis.y.normalized()) * (s * p.aspect + sp * p.stretch)
				b = Basis(Vector3(s, 0, 0), ax, Vector3(0, 0, 1))
			var c := p.col
			c.a *= k
			if l.add and flash_scale < 1.0:
				c = limit(c)
			var w := clampf(p.age / p.wipe, 0.02, 1.0) if p.wipe > 0.0 else 0.0
			_write(l.buf, n * 20, b, p.pos, c, p.rot, p.mode, w)
			lo = lo.min(p.pos)
			hi = hi.max(p.pos)
			if p.mode == FLAT:
				big = maxf(big, s * (p.basis.x.length() + p.basis.y.length()))
			else:
				big = maxf(big, s * maxf(1.0, p.aspect) + p.vel.length() * p.stretch)
			n += 1
		l.mi.visible = n > 0
		if n > 0:
			RenderingServer.multimesh_set_buffer(l.mm.get_rid(), l.buf)
			l.mm.visible_instance_count = n
			var m := Vector3.ONE * (big + 0.5)
			l.mi.custom_aabb = AABB(lo - m, hi - lo + m * 2.0)


## 全部消す（部屋の移動・やり直し）
func clear() -> void:
	for l: Layer in _layers:
		for p in l.parts:
			_free.append(p)
		l.parts.clear()
		l.spr.resize(0)
		l.n_spr = 0
		l.mi.visible = false


## 今出ている粒の数（確認用）
func count() -> int:
	var n := 0
	for l: Layer in _layers:
		n += l.parts.size()
	return n


## 斬撃の帯の向き：円弧の中心 center、半径 radius（m）、円弧の真ん中へ向かう向き mid、振り抜く向き swing（どちらも単位、互いに直交）。
## 返り値：[四角の中心, basis（大きさ込み）]
static func slash_frame(center: Vector3, radius: float, mid: Vector3, swing: Vector3) -> Array:
	var size := radius / SLASH_RADIUS
	# マスクの円弧の真ん中の向き（UV、下向き +y）と、刃先の向き（接線）
	var am := (SLASH_A0 + SLASH_A1) * 0.5
	var d_mid := Vector2(cos(am), -sin(am))       # 四角の局所（上が +y）
	var d_tan := Vector2(sin(am), cos(am))         # 尾 → 刃先の向き（UV の角度が減る向き）
	var ex := (mid * d_mid.x + swing * d_tan.x) * size
	var ey := (mid * d_mid.y + swing * d_tan.y) * size
	# 円弧の中心の、四角の局所の位置（四角の中心から）
	var c_local := Vector2(SLASH_CENTER.x - 0.5, 0.5 - SLASH_CENTER.y)
	var origin := center - ex * c_local.x - ey * c_local.y
	return [origin, Basis(ex, ey, ex.cross(ey).normalized() * size)]
