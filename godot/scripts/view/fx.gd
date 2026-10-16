class_name Fx
extends Node3D
## 戦闘と仕掛けのエフェクト（W2-09 の見本：art/concepts/W2_vfx、結果は docs/art_orders/W2_エフェクトの結果.md）と画面の揺れ。
## 粒は Vfx（層ごとに 1 回の描画）で描く。ゲームの中身の出来事（handle）と、毎刻みの状態（sync）から出す。見た目だけで、遊びは変えない。
## 色の決まり：ハル・ナゴミ・拾い物の光は琥珀 #FFBC52。番機と閂の攻撃の予兆・敵弾は珊瑚色 #E26A4A。
## 閂の錠前核は琥珀のまま、第 3 段階（過熱）だけ珊瑚色。ふだんの銃口・命中は小さく、弱点と大技だけ短く明るく。長い全画面の光はしない。
## 明るさは見本の表（spec.md）の 0〜1 を GAIN 倍した色の強さ。大きな光（弱点・破断・撃破）は flash_scale（低フラッシュ設定用）を掛ける。

## 琥珀 #FFBC52・珊瑚色 #E26A4A（見本の色）。環境の色調（AgX）は明るい色をくすませる（#FFBC52 をそのまま渡すと黄土色に見える）ので、
## 画面で見本の色に見える、少し濃い色を渡す（ゲームと同じ環境に色を並べて写して合わせた。docs/art_orders/W2_エフェクトの結果.md）
const AMBER := Color(1.0, 0.62, 0.16)
const PALE := Color("#F3E9D2")
const CORAL := Color(0.95, 0.30, 0.16)
const BRASS := Color("#A98749")
const GRAPHITE := Color("#444641")
const IVORY := Color("#E9E3D6")
const ROCK := Color("#5c5650")
const DUST := Color("#cdbd9f")
const SMOKE := Color("#8f877d")
const GAIN := 1.3
## 閂の削岩腕の先（部品 arm_*_drill の原点から、軸（ローカル X）の向きに 1.6 m）。向きの符号は腕ごと（kannuki.glb）
const DRILL_TIP := {"fl": 1.6, "fr": -1.6, "rl": -1.6, "rr": 1.6}
const ARMS := ["fl", "fr", "rl", "rr"]

var shake := 0.0
var vfx: Vfx
## 大きな光の強さの倍率（低フラッシュ設定用。1 = 見本どおり）
var flash_scale := 1.0

var _rng := RandomNumberGenerator.new()
var _time := 0.0
var _frame := 0
var _game: GameSim = null
var _pv: PlayerView = null
var _ev: EnemyView = null
var _shots := {}
## 敵ごとの前の刻みの状態
var _est := {}
var _atk = null
var _atk_done := false
var _charge_lv := 0
var _blade_full := false
var _dashing := false
var _drill_tip := Vector3.ZERO
## 壊れた腕の煙（腕 → 残りの秒数）
var _arm_smoke := {}
## 閂のすべての腕の先（毎刻み作る）[腕, 位置, 軸]
var _tips: Array = []
## 叩きつけの輪の低い壁（輪といっしょに広がる帯）
var _band: MeshInstance3D
var _band_mat: StandardMaterial3D
## 拾い物の前の刻みの位置
var _picks := {}
var _scan_target = null
var _scan_done := false
var _frame_state := Vector3i(-1, -1, -1)
## ノードの記憶の取り込み（会話 ch1.node の間）：残りの秒数と、光の出る所
var _dlg_id := ""
var _node_t := 0.0
var _node_from := Vector3.ZERO


func _ready() -> void:
	_rng.seed = 7
	vfx = Vfx.new()
	add_child(vfx)
	_band = MeshInstance3D.new()
	_band.mesh = _ring_band(48)
	_band_mat = StandardMaterial3D.new()
	_band_mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	_band_mat.vertex_color_use_as_albedo = true
	_band_mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	_band_mat.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	_band_mat.cull_mode = BaseMaterial3D.CULL_DISABLED
	_band_mat.disable_fog = true
	_band.material_override = _band_mat
	_band.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	_band.visible = false
	add_child(_band)


## 高さ 1・半径 1 の筒の側面だけ（下の縁が明るく、上へ消える）
static func _ring_band(segs: int) -> ArrayMesh:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	for i in segs:
		var a0 := TAU * i / segs
		var a1 := TAU * (i + 1) / segs
		var p0 := Vector3(sin(a0), 0, cos(a0))
		var p1 := Vector3(sin(a1), 0, cos(a1))
		var lo := Color(1, 1, 1, 1)
		var hi := Color(1, 1, 1, 0)
		for v in [[p0, lo], [p1, lo], [p1 + Vector3.UP, hi], [p0, lo], [p1 + Vector3.UP, hi], [p0 + Vector3.UP, hi]]:
			st.set_color(v[1])
			st.add_vertex(v[0])
	return st.commit()


# ---------------------------------------------------------------- 道具

## 見本の明るさ b（0〜1）の色
func _c(col: Color, b: float, a := 1.0) -> Color:
	var e := b * GAIN
	return Color(col.r * e, col.g * e, col.b * e, a)


## 大きな光（弱点・破断・撃破）：低フラッシュ設定の倍率を掛ける
func _cf(col: Color, b: float) -> Color:
	return _c(col, b * flash_scale)


func _sphere() -> Vector3:
	var v := Vector3(_rng.randf_range(-1, 1), _rng.randf_range(-1, 1), _rng.randf_range(-1, 1))
	return v.normalized() if v.length_squared() > 1e-4 else Vector3.UP


## 向き dir のまわりの円錐（cone：0 = まっすぐ、1 = 半球）の中の向き
func _cone(dir: Vector3, cone: float) -> Vector3:
	return (dir.normalized() + _sphere() * cone).normalized()


## 向き dir を法線にした板の向き（大きさ 1）。roll：法線まわりの回転
static func _facing(dir: Vector3, roll := 0.0) -> Basis:
	var z := dir.normalized()
	var up := Vector3.UP if absf(z.y) < 0.95 else Vector3.RIGHT
	var x := up.cross(z).normalized()
	var y := z.cross(x)
	if roll != 0.0:
		var c := cos(roll)
		var s := sin(roll)
		var x2 := x * c + y * s
		y = y * c - x * s
		x = x2
	return Basis(x, y, z)


## 床に寝た板の向き（大きさ 1）
static func _flat(roll := 0.0) -> Basis:
	return _facing(Vector3.UP, roll)


## 火花（伸びる筋）
func _spark(layer: int, at: Vector3, vel: Vector3, life: float, w: float, col: Color, stretch := 0.035, grav := 6.0) -> Vfx.P:
	var q := vfx.emit(layer, at, vel, life, w, w * 0.6, col)
	q.mode = Vfx.STREAK
	q.stretch = stretch
	q.grav = grav
	q.aspect = 2.0
	q.fin = 0.05
	return q


## 破片（向きは画面に向いて回る）。floor_y の床で跳ねて止まる
func _shard(layer: int, at: Vector3, vel: Vector3, life: float, s: float, col: Color, floor_y := -INF) -> Vfx.P:
	var q := vfx.emit(layer, at, vel, life, s, s * 0.85, col)
	q.grav = 14.0
	q.spin = _rng.randf_range(-12, 12)
	q.rot = _rng.randf() * TAU
	q.fin = 0.02
	q.fpow = 0.35
	q.floor_y = floor_y
	return q


## 煙・粉じん（ふわっと広がって消える）
func _puff(layer: int, at: Vector3, vel: Vector3, life: float, s0: float, s1: float, col: Color) -> Vfx.P:
	var q := vfx.emit(layer, at, vel, life, s0, s1, col)
	q.rot = _rng.randf() * TAU
	q.spin = _rng.randf_range(-0.6, 0.6)
	q.drag = 1.5
	q.fin = 0.15
	q.fpow = 1.3
	return q


## 光る点（一瞬の光・閃き）
func _flash(layer: int, at: Vector3, s0: float, s1: float, life: float, col: Color) -> Vfx.P:
	var q := vfx.emit(layer, at, Vector3.ZERO, life, s0, s1, col)
	q.fin = 0.12
	q.fpow = 1.5
	q.rot = _rng.randf() * 0.5
	return q


## 色の残るやわらかい光（普通の半透明。明るい床の上でも琥珀・珊瑚色が白くならない）
func _soft(at: Vector3, s0: float, s1: float, life: float, col: Color, a := 0.6) -> Vfx.P:
	var q := vfx.emit(Vfx.SOFT, at, Vector3.ZERO, life, s0, s1, Color(col, a))
	q.fin = 0.12
	q.fpow = 1.3
	return q


## 広がる輪（rad0 → rad1 m。basis = null ならカメラを向く）
func _ring(at: Vector3, rad0: float, rad1: float, life: float, col: Color, basis = null) -> Vfx.P:
	var q := vfx.emit(Vfx.RING, at, Vector3.ZERO, life, rad0 / Vfx.RING_FRAC, rad1 / Vfx.RING_FRAC, col)
	q.fin = 0.1
	q.fpow = 1.4
	if basis != null:
		q.mode = Vfx.FLAT
		q.basis = basis
	return q


## 床の上の細い光の線の輪（大きな輪は輪の素材だと帯が太くぼやけるので、短い筋を並べる）。その刻みだけ
func _circle(c: Vector3, r: float, width: float, col: Color, phase := 0.0) -> void:
	var n := clampi(int(r * 3.0), 16, 48)
	var prev := c + Vector3(sin(phase), 0, cos(phase)) * r
	for i in n:
		var a := phase + TAU * (i + 1) / n
		var cur := c + Vector3(sin(a), 0, cos(a)) * r
		vfx.streak(Vfx.GRAIN, prev, cur, width, col)
		prev = cur


## 粉じんを床に（at の高さが床）
func _dust_ring(at: Vector3, n: int, rad: float, s: float, a := 0.55) -> void:
	for i in n:
		var ang := _rng.randf() * TAU
		var d := Vector3(sin(ang), 0, cos(ang))
		_puff(Vfx.DUST, at + d * rad * _rng.randf_range(0.2, 1.0) + Vector3(0, s * 0.3, 0), d * _rng.randf_range(1.0, 2.5) + Vector3(0, 0.6, 0),
			_rng.randf_range(0.6, 0.9), s * 0.6, s * 1.6, Color(DUST, a))


# ---------------------------------------------------------------- 出来事

func handle(e: Dictionary) -> void:
	match e.type:
		"hit":
			if _game != null and e.kind == "armor" and _from_enemy_shot(e.at):
				return
			if _game != null and _game.player.drilling and _is_wall_center(e.at):
				return
			if _game != null and e.kind == "armor" and not _game.player.drilling:
				for b in _game.breakables:
					if not b.broken and b.distance_to(e.at) < 0.35:
						_mark_wrong(b, e.at)
						return
			_hit(e.at, e.kind)
		"enemyDestroyed":
			var bs = _game.boss if _game != null else null
			if bs != null and not bs.alive and bs.axis_center().distance_to(e.at) < 0.2:
				return
			_banki_destroy(e.at)
		"guardBroken":
			_shield_break(e.at)
		"wallBroken":
			if _game != null:
				for b in _game.breakables:
					if b.id == e.id:
						_wall_break(b)
		"playerHurt":
			_hurt()
		"bossStuck":
			_boss_crash(e.at)
		"bossArmBroken":
			_arm_break(e.at)
			_arm_smoke[e.arm] = 1.4
		"bossSummon":
			_summon_hatch(e.at - Vector3(0, 1, 0))
		"bossPhase":
			_boss_phase(int(e.phase))
		"bossReset":
			_arm_smoke.clear()
		"sfx":
			if e.id == "heal" and _game != null:
				_heal(_game.player)
		"saved":
			_beacon_on()
		"chestOpened":
			if _game != null:
				for c in _game.chests:
					if c.id == e.id:
						_chest_open(c)
		"doorOpened":
			if _game != null and String(e.id).contains("seal"):
				for dr in _game.doors:
					if dr.id == e.id:
						_seal_open(dr)
		"roomChanged":
			if not e.first:
				vfx.clear()
				_band.visible = false
				_shots.clear()
				_est.clear()
				_picks.clear()
				_arm_smoke.clear()
		"shake":
			shake = maxf(shake, e.strength)


## その位置で消えた敵の弾があるか（敵の弾が壁に当たった "hit" は、珊瑚色の着弾で描くので重ねない）
func _from_enemy_shot(at: Vector3) -> bool:
	for s in _shots:
		if not s.from_player and not s.alive and s.pos.distance_squared_to(at) < 0.01:
			return true
	return false


## ドリルで削っている壁の中心（削るたびに "hit" が壁の中心に出る。削る火花はドリルの先で描く）
func _is_wall_center(at: Vector3) -> bool:
	for b in _game.breakables:
		if b.center.distance_squared_to(at) < 0.01:
			return true
	return false


# ---------------------------------------------------------------- 毎刻み

func sync(game: GameSim, dt: float, pv: PlayerView = null, ev: EnemyView = null) -> void:
	_time += dt
	_frame += 1
	_game = game
	_pv = pv
	_ev = ev
	if ev != null and not ev.on_land.is_valid():
		ev.on_land = debris_landed
	_sync_shots(game)
	_sync_player(game, dt)
	_sync_enemies(game, dt)
	_sync_world(game, dt)
	vfx.step(dt)
	shake = maxf(0.0, shake - dt * 2.5)


# ---------------------------------------------------------------- 弾

func _sync_shots(game: GameSim) -> void:
	var seen := {}
	for s in game.shots:
		seen[s] = true
		var info: Dictionary = _shots.get(s, {})
		if info.is_empty():
			info = _new_shot(game, s)
			_shots[s] = info
		_draw_shot(s, info)
	for s in _shots.keys():
		if not seen.has(s):
			_end_shot(game, s, _shots[s])
			_shots.erase(s)


func _new_shot(game: GameSim, s) -> Dictionary:
	var style: String = s.kind
	var bs = game.boss
	if not s.from_player and bs != null and bs.alive and bs.state == "volley" and s.origin.distance_to(bs.axis_center()) < 8.0:
		style = "debris"
	var d: Vector3 = s.vel.normalized()
	match style:
		"normal":
			_muzzle(s.origin, d, AMBER, 0.75, 0.25)
		"charge1", "charge2":
			_charge_release(s.origin, d, 2 if style == "charge2" else 1)
		"enemy":
			_muzzle(s.origin, d, CORAL, 0.75, 0.25)
		"debris":
			_flash(Vfx.GRAIN, s.origin, 0.8, 1.6, 0.18, _c(CORAL, 0.6))
			for i in 3:
				_shard(Vfx.SHARD, s.origin, _cone(d + Vector3.UP * 0.5, 0.6) * _rng.randf_range(3, 6), 0.6, _rng.randf_range(0.12, 0.25), Color(ROCK, 1.0))
	return {"style": style, "ground": s.origin.y - Player.CHEST, "rot": _rng.randf() * TAU, "spin": _rng.randf_range(-9.0, 9.0), "rad": _rng.randf_range(0.3, 0.8)}


## 銃口の光：小さな星と、前へ散る火花 2 つ（見本 shot_rapid：0.25 m、0→0.75→0.25→0、0.14 秒）
func _muzzle(at: Vector3, d: Vector3, col: Color, b: float, size: float) -> void:
	_flash(Vfx.GLINT, at, size * 2.4, size * 1.4, 0.08, _c(col, b))
	_soft(at, size * 1.4, size * 0.7, 0.07, col, 0.55)
	for i in 2:
		_spark(Vfx.SPARK, at, _cone(d, 0.35) * _rng.randf_range(5, 8), 0.08, 0.07, _c(col, b * 0.8), 0.02, 0.0)


## 溜め撃ちを放つ：銃口の輪がはじけ、星が光る（shot_charge：1 段 0.35 m、2 段 0.8 m）
func _charge_release(at: Vector3, d: Vector3, lv: int) -> void:
	var k := 1.0 if lv == 1 else 2.0
	_ring(at, 0.08 * k, 0.28 * k, 0.16, _cf(AMBER, 0.6 + 0.2 * lv), _facing(d))
	_flash(Vfx.GLINT, at, 0.6 * k, 0.4 * k, 0.12, _cf(PALE, 0.85))
	_soft(at, 0.3 * k, 0.5 * k, 0.12, AMBER, 0.6)
	for i in 4 * lv:
		_spark(Vfx.SPARK, at, _cone(d, 0.6) * _rng.randf_range(4, 9), 0.14, 0.06, _c(AMBER, 0.7), 0.025, 2.0)


func _draw_shot(s, info: Dictionary) -> void:
	var d: Vector3 = s.vel.normalized()
	var p: Vector3 = s.pos
	match info.style:
		"normal":
			vfx.streak(Vfx.DOT, p - d * 0.4, p + d * 0.05, 0.11, Color(AMBER, 0.95))
			vfx.streak(Vfx.GRAIN, p - d * 0.9, p + d * 0.08, 0.26, _c(AMBER, 0.75))
			vfx.sprite(Vfx.GRAIN, p, 0.18, _c(PALE, 0.55))
		"charge1":
			vfx.streak(Vfx.SOFT, p - d * 1.0, p + d * 0.12, 0.3, Color(AMBER, 0.8))
			vfx.streak(Vfx.GRAIN, p - d * 1.3, p + d * 0.15, 0.45, _c(AMBER, 0.8))
			vfx.sprite(Vfx.GLINT, p, 0.6, _c(PALE, 0.7), Vfx.FACE, Basis.IDENTITY, _time * 5.0)
			if _frame % 2 == 0:
				_spark(Vfx.SPARK, p, _sphere() * 2.0 - d * 2.0, 0.15, 0.04, _c(AMBER, 0.5), 0.03, 0.0)
		"charge2":
			vfx.streak(Vfx.SOFT, p - d * 2.2, p + d * 0.3, 0.7, Color(AMBER, 0.8))
			vfx.streak(Vfx.GRAIN, p - d * 2.6, p + d * 0.3, 0.9, _c(AMBER, 0.85))
			vfx.streak(Vfx.SPARK, p - d * 0.9, p + d * 0.55, 0.9, _c(PALE, 0.7))
			vfx.sprite(Vfx.GLINT, p + d * 0.2, 1.1, _c(PALE, 0.7), Vfx.FACE, Basis.IDENTITY, _time * 4.0)
			for i in 2:
				_spark(Vfx.SPARK, p - d * _rng.randf_range(0.0, 1.5), _sphere() * 3.0 - d * 3.0, 0.18, 0.06, _c(AMBER, 0.6), 0.03, 0.0)
		"wave":
			_wave_step(s, info)
		"enemy":
			# 芯は普通の半透明（明るい床の上でも珊瑚色が残る）、まわりは足し合わせのにじみ
			vfx.streak(Vfx.DOT, p - d * 0.45, p + d * 0.1, 0.28, Color(CORAL, 0.95))
			vfx.streak(Vfx.GRAIN, p - d * 1.1, p + d * 0.15, 0.6, _c(CORAL, 0.6))
		"debris":
			vfx.sprite(Vfx.SHARD, p, info.rad, Color(ROCK, 1.0), Vfx.FACE, Basis.IDENTITY, info.rot + _time * info.spin)
			vfx.streak(Vfx.GRAIN, p - d * 1.8, p, info.rad * 0.9, _c(CORAL, 0.55))
			vfx.streak(Vfx.DOT, p - d * 0.9, p - d * 0.1, info.rad * 0.35, Color(CORAL, 0.8))
			if _frame % 2 == 0:
				_spark(Vfx.SPARK, p, _sphere() * 1.5 - d * 2.0, 0.2, 0.05, _c(CORAL, 0.6), 0.03, 3.0)


## 溜め斬りの衝撃波：床を這う光の破片の列（blade_charge：前方 6 m、幅 1.5 m）
func _wave_step(s, info: Dictionary) -> void:
	var d: Vector3 = Vector3(s.vel.x, 0, s.vel.z).normalized()
	var g := Vector3(s.pos.x, info.ground, s.pos.z)
	var side := Vector3(-d.z, 0, d.x)
	vfx.sprite(Vfx.GRAIN, g + Vector3(0, 0.45, 0), 1.6, _c(AMBER, 0.7), Vfx.FACE, Basis.IDENTITY, 0.0, 0.6)
	for i in 3:
		var at := g + side * _rng.randf_range(-0.7, 0.7) + d * _rng.randf_range(-0.6, 0.2)
		var q := _shard(Vfx.SHARD_GLOW, at + Vector3(0, 0.1, 0), Vector3(0, _rng.randf_range(2.5, 5.0), 0) + d * 2.0 + side * _rng.randf_range(-1, 1),
			_rng.randf_range(0.25, 0.4), _rng.randf_range(0.18, 0.4), _c(AMBER, 0.75), info.ground)
		q.fpow = 1.0
	_spark(Vfx.SPARK, g + Vector3(0, 0.2, 0), _cone(d + Vector3.UP, 0.5) * 5.0, 0.2, 0.06, _c(PALE, 0.7))
	if _frame % 3 == 0:
		_puff(Vfx.DUST, g + Vector3(0, 0.3, 0), side * _rng.randf_range(-1.5, 1.5) + Vector3(0, 0.8, 0), 0.7, 0.6, 1.4, Color(DUST, 0.45))


func _end_shot(game: GameSim, s, info: Dictionary) -> void:
	if s.from_player:
		return   # 命中・壁は "hit" の出来事が描く
	if s.traveled >= s.range_m - 0.05:
		return   # 届かずに消えた
	if s.pos.distance_to(game.player.chest()) < 1.0:
		return   # ハルに当たった：playerHurt が描く
	if info.style == "debris":
		_flash(Vfx.GRAIN, s.pos, 0.6, 1.4, 0.15, _c(CORAL, 0.5))
		_dust_ring(s.pos, 3, 0.4, 1.0, 0.6)
		for i in 5:
			_shard(Vfx.SHARD, s.pos + Vector3(0, 0.2, 0), _cone(Vector3.UP, 0.9) * _rng.randf_range(3, 6), 0.7, _rng.randf_range(0.1, 0.25), Color(ROCK, 1.0), s.pos.y)
	else:
		# 敵弾の着弾（banki_shot：着弾 0.45、0.5 m）
		_flash(Vfx.GLINT, s.pos, 0.8, 0.5, 0.1, _c(CORAL, 0.45))
		_soft(s.pos, 0.3, 0.6, 0.15, CORAL, 0.7)
		for i in 5:
			_spark(Vfx.SPARK, s.pos, _sphere() * _rng.randf_range(2, 5), 0.18, 0.05, _c(CORAL, 0.5))
		_puff(Vfx.DUST, s.pos, Vector3(0, 0.6, 0), 0.5, 0.25, 0.7, Color(SMOKE, 0.4))


# ---------------------------------------------------------------- 命中

## 命中（hit：通常 0.5 ／ 弱点 0.9 ／ 装甲 0.25、0.15〜0.3 秒、0.2〜0.8 m）
func _hit(at: Vector3, kind: String) -> void:
	var drill := _game != null and _game.player.drilling and at.distance_to(_drill_tip) < 0.8
	if drill:
		# ドリルの多段の削り：小さな火花と陶器のかけら
		for i in 3:
			_spark(Vfx.SPARK, at, _sphere() * _rng.randf_range(3, 6), 0.16, 0.05, _c(AMBER, 0.6))
		_shard(Vfx.SHARD, at, _cone(Vector3.UP, 1.0) * _rng.randf_range(2, 4), 0.45, _rng.randf_range(0.06, 0.12), Color(IVORY, 1.0))
		if kind == "weak":
			_flash(Vfx.GLINT, at, 0.5, 0.3, 0.1, _cf(AMBER, 0.7))
		return
	match kind:
		"weak":
			_flash(Vfx.GLINT, at, 1.2, 0.7, 0.14, _cf(PALE, 0.9))
			_soft(at, 0.5, 1.0, 0.14, AMBER, 0.75)
			_flash(Vfx.GRAIN, at, 0.6, 1.1, 0.12, _cf(AMBER, 0.6))
			_ring(at, 0.15, 0.7, 0.16, _cf(AMBER, 0.6))
			for i in 9:
				_spark(Vfx.SPARK, at, _sphere() * _rng.randf_range(3, 7), _rng.randf_range(0.15, 0.3), 0.06, _c(AMBER, 0.75))
			for i in 4:
				_shard(Vfx.SHARD_GLOW, at, _sphere() * _rng.randf_range(2, 5) + Vector3(0, 1.5, 0), 0.4, _rng.randf_range(0.08, 0.15), _c(AMBER, 0.8))
		"armor":
			# 弾かれる：くすんだ小さな火花だけ
			for i in 4:
				_spark(Vfx.SPARK, at, _sphere() * _rng.randf_range(2, 5), 0.14, 0.04, _c(PALE, 0.3))
			_puff(Vfx.DUST, at, Vector3(0, 0.4, 0), 0.35, 0.15, 0.45, Color(SMOKE, 0.35))
		_:
			_flash(Vfx.GLINT, at, 0.75, 0.45, 0.09, _c(AMBER, 0.5))
			_soft(at, 0.35, 0.55, 0.09, AMBER, 0.6)
			for i in 6:
				_spark(Vfx.SPARK, at, _sphere() * _rng.randf_range(2.5, 5.5), _rng.randf_range(0.12, 0.22), 0.07, _c(AMBER, 0.55))


## 撃破（banki_destroy：核 0.3→0.9→残光 0.15→0、約 1.2 秒、機体のまわり約 2.5 m）
func _banki_destroy(at: Vector3) -> void:
	_flash(Vfx.GRAIN, at, 0.5, 2.0, 0.35, _cf(AMBER, 0.9))
	_soft(at, 0.6, 1.6, 0.3, AMBER, 0.75)
	_flash(Vfx.GLINT, at, 1.5, 0.8, 0.5, _cf(PALE, 0.6))
	var after := _flash(Vfx.GRAIN, at, 0.7, 0.5, 1.2, _c(AMBER, 0.15))
	after.fin = 0.25
	_ring(at, 0.3, 1.3, 0.3, _cf(AMBER, 0.5))
	for i in 14:
		_spark(Vfx.SPARK, at, _sphere() * _rng.randf_range(3, 8) + Vector3(0, 1.5, 0), _rng.randf_range(0.25, 0.5), 0.06, _c(AMBER, 0.7), 0.03, 8.0)
	var floor_y := at.y - 0.6
	for i in 7:
		_shard(Vfx.SHARD, at, _sphere() * _rng.randf_range(2, 5) + Vector3(0, 3, 0), _rng.randf_range(0.8, 1.2), _rng.randf_range(0.1, 0.22), Color(IVORY, 1.0), floor_y)
	for i in 3:
		_shard(Vfx.SHARD, at, _sphere() * _rng.randf_range(2, 4) + Vector3(0, 3, 0), 1.0, _rng.randf_range(0.08, 0.14), Color(GRAPHITE, 1.0), floor_y)
	for i in 3:
		_shard(Vfx.SHARD_GLOW, at, _sphere() * _rng.randf_range(1, 3) + Vector3(0, 2, 0), 0.8, 0.1, _c(AMBER, 0.5), floor_y)
	for i in 2:
		_puff(Vfx.SMOKE, at + _sphere() * 0.3, Vector3(0, 0.8, 0), 1.2, 0.5, 1.6, Color(GRAPHITE, 0.45))


## 盾が崩れる（shield_break：亀裂 0.25→破断 0.8→0、約 0.8 秒、盾約 1.2 m、破片約 2 m）
func _shield_break(at: Vector3) -> void:
	var fwd := Vector3.FORWARD
	if _game != null:
		var best := INF
		for e in _game.enemies:
			if e.kind == "shield" and e.center().distance_to(at) < best:
				best = e.center().distance_to(at)
				fwd = e.forward()
	var c := at + fwd * 0.45
	_flash(Vfx.GLINT, c, 1.4, 0.8, 0.18, _cf(PALE, 0.8))
	_flash(Vfx.GRAIN, c, 0.6, 1.4, 0.2, _cf(AMBER, 0.6))
	var slash := Vfx.slash_frame(c - fwd * 0.6, 1.0, fwd, Vector3(0.6, 0.8, 0).normalized())
	var q := vfx.emit(Vfx.SLASH, slash[0], Vector3.ZERO, 0.22, 1.0, 1.0, _cf(AMBER, 0.8))
	q.mode = Vfx.FLAT
	q.basis = slash[1]
	for i in 12:
		_shard(Vfx.SHARD, c + _sphere() * 0.4, _cone(fwd + Vector3.UP * 0.4, 0.8) * _rng.randf_range(2, 5), _rng.randf_range(0.7, 1.0),
			_rng.randf_range(0.14, 0.3), Color(IVORY, 1.0), at.y - 0.9)
	for i in 8:
		_spark(Vfx.SPARK, c, _cone(fwd, 0.9) * _rng.randf_range(3, 7), 0.25, 0.05, _c(AMBER, 0.7))


## 壁が壊れる（drill_wall：0.15→0.65→0.35→0、0.8 秒、壁約 2.5 m）
func _wall_break(b) -> void:
	var c: Vector3 = b.center
	var to_p := Vector3.ZERO
	if _game != null:
		to_p = Vector3(_game.player.pos.x - c.x, 0, _game.player.pos.z - c.z).normalized()
	var base_y: float = c.y - b.size.y * 0.5
	_flash(Vfx.GLINT, c + to_p * 0.3, 1.6, 0.9, 0.2, _cf(PALE, 0.65))
	_flash(Vfx.GRAIN, c + to_p * 0.3, 1.0, 2.2, 0.35, _cf(AMBER, 0.45))
	var w := maxf(b.size.x, b.size.z)
	for i in 16:
		var at := c + Vector3(_rng.randf_range(-0.5, 0.5) * w, _rng.randf_range(-0.4, 0.4) * b.size.y, _rng.randf_range(-0.5, 0.5) * w)
		_shard(Vfx.SHARD, at, (_cone(to_p + Vector3.UP * 0.3, 0.7)) * _rng.randf_range(1.5, 5), _rng.randf_range(1.0, 1.4),
			_rng.randf_range(0.18, 0.45), Color(DUST.darkened(0.1), 1.0), base_y)
	for i in 10:
		_spark(Vfx.SPARK, c, _cone(to_p, 1.0) * _rng.randf_range(3, 7), 0.3, 0.06, _c(AMBER, 0.6))
	for i in 7:
		var at2 := Vector3(c.x, base_y, c.z) + Vector3(_rng.randf_range(-0.6, 0.6) * w, 0.4, _rng.randf_range(-0.6, 0.6) * w) + to_p * 0.6
		_puff(Vfx.DUST, at2, to_p * _rng.randf_range(0.5, 2.0) + Vector3(0, 0.5, 0), _rng.randf_range(0.8, 1.2), 0.9, 2.4, Color(DUST, 0.6))


## 目印の反応・不正解（mark_react：0→0.2→0、0.5 秒）：壊せる壁を弾で撃っても、印が小さく光って弾くだけ（正解のドリルは _drill の印と _wall_break）
func _mark_wrong(b, at: Vector3) -> void:
	var n := Vector3(at.x - b.center.x, 0, at.z - b.center.z)
	n = n.normalized() if n.length() > 0.01 else Vector3.BACK
	var q := vfx.emit(Vfx.HEX, at + n * 0.05, Vector3.ZERO, 0.5, 0.5, 0.55, _c(AMBER, 0.2))
	q.mode = Vfx.FLAT
	q.basis = _facing(n)
	q.fin = 0.2
	for i in 3:
		_spark(Vfx.SPARK, at, _cone(n, 0.7) * _rng.randf_range(2, 4), 0.14, 0.04, _c(PALE, 0.3))


## 封印の解除（seal_open：接触 0→文様 0.55→解除 0.8→0、約 1.5 秒、扉約 2 m）：扉の文様の輪と十字の光、開く瞬間に短く光る
func _seal_open(dr) -> void:
	var c: Vector3 = dr.pos + Vector3(0, dr.size.y * 0.5, 0)
	var f := U.yaw_to_dir(dr.yaw)
	if _game != null and f.dot(_game.player.pos - c) < 0.0:
		f = -f
	var at: Vector3 = c + f * (dr.size.z * 0.5 + 0.06)
	var q := vfx.emit(Vfx.HEX, at, Vector3.ZERO, 1.5, 1.1, 1.3, _c(AMBER, 0.55))
	q.mode = Vfx.FLAT
	q.basis = _facing(f)
	q.fin = 0.35
	_ring(at, 0.3, 1.4, 0.8, _c(AMBER, 0.5), _facing(f))
	var up := _flash(Vfx.PILLAR, at, dr.size.y * 0.5, dr.size.y * 0.55, 1.2, _c(AMBER, 0.6))
	up.aspect = 2.0
	up.rot = 0.0
	up.fin = 0.4
	var side := _flash(Vfx.PILLAR, at, dr.size.x * 0.4, dr.size.x * 0.45, 1.2, _c(AMBER, 0.5))
	side.aspect = 2.0
	side.rot = PI * 0.5
	side.fin = 0.4
	_flash(Vfx.GLINT, at, 2.0, 1.2, 0.3, _cf(PALE, 0.8))
	for i in 12:
		var g := vfx.emit(Vfx.GRAIN, at + _sphere() * 0.8, f * _rng.randf_range(0.5, 1.5) + Vector3(0, 0.8, 0), _rng.randf_range(0.6, 1.2), 0.12, 0.05, _c(AMBER, 0.55))
		g.fin = 0.3


## 外れた部品が床に落ちた（EnemyView が呼ぶ）。big：閂の腕
func debris_landed(at: Vector3, big: bool) -> void:
	_dust_ring(at, 4 if big else 1, 1.5 if big else 0.3, 1.6 if big else 0.5, 0.5)
	if big:
		for i in 5:
			_shard(Vfx.SHARD, at + Vector3(0, 0.2, 0), _cone(Vector3.UP, 0.9) * _rng.randf_range(2, 4), 0.8, _rng.randf_range(0.12, 0.3), Color(ROCK, 1.0), at.y)


# ---------------------------------------------------------------- ハル

func _sync_player(game: GameSim, dt: float) -> void:
	var p := game.player
	if p.dead:
		_charge_lv = 0
		_dashing = false
		return
	_gun_charge(game, p)
	_blade(game, p)
	_drill(game, p)
	_dash(game, p)
	# 被弾のあとの無敵：琥珀の淡い光の粒（点滅 0.25 以下）
	if p.invuln > 0.0 and _frame % 3 == 0:
		var q := vfx.emit(Vfx.GRAIN, p.pos + Vector3(_rng.randf_range(-0.35, 0.35), _rng.randf_range(0.2, 1.5), _rng.randf_range(-0.35, 0.35)),
			Vector3(0, 0.6, 0), 0.35, 0.12, 0.05, _c(AMBER, 0.25))
		q.fin = 0.3


func _muzzle_pos(p: Player) -> Vector3:
	if _pv != null and is_instance_valid(_pv) and _pv.muzzle != null and _pv.muzzle.is_inside_tree():
		return _pv.muzzle.global_position
	return p.muzzle(p.yaw)


func _gauntlet_pos(p: Player) -> Vector3:
	if _pv != null and is_instance_valid(_pv) and _pv.blade != null and _pv.blade.is_inside_tree():
		return _pv.blade.global_position
	var f := U.yaw_to_dir(p.yaw)
	return p.pos + Vector3(0, 0.95, 0) + Vector3(f.z, 0, -f.x) * 0.3 + f * 0.2


## 主武器の溜め：銃口に光が集まり、0.6 秒で輪、1.2 秒で大きな二重の輪（shot_charge：0→0.4→0.85→0）
func _gun_charge(game: GameSim, p: Player) -> void:
	var ch: float = p.gun_charge
	if ch <= 0.15:
		_charge_lv = 0
		return
	var cfg: Dictionary = game.tuning.gun
	var lv := 2 if ch >= float(cfg.chargeLv2Time) else (1 if ch >= float(cfg.chargeLv1Time) else 0)
	var m := _muzzle_pos(p)
	var f := U.yaw_to_dir(p.yaw)
	if lv > _charge_lv:
		_ring(m, 0.1, 0.35 if lv == 1 else 0.6, 0.18, _c(AMBER, 0.5 + 0.2 * lv), _facing(f))
	_charge_lv = lv
	var b := 0.4 if lv < 2 else 0.85
	var off := _sphere() * (0.4 + 0.1 * lv)
	var q := vfx.emit(Vfx.GRAIN, m + off, -off / 0.2, 0.2, 0.07, 0.03, _c(AMBER, b))
	q.fin = 0.4
	var pulse := 0.85 + 0.15 * sin(_time * 18.0)
	vfx.sprite(Vfx.GRAIN, m, (0.25 + 0.15 * lv) * pulse, _c(AMBER, b))
	if lv >= 1:
		vfx.sprite(Vfx.RING, m + f * 0.05, (0.16 + 0.12 * (lv - 1)) * pulse / Vfx.RING_FRAC, _c(AMBER, b), Vfx.FLAT, _facing(f, _time * 3.0))
	if lv == 2:
		vfx.sprite(Vfx.RING, m + f * 0.12, 0.42 * (2.0 - pulse) / Vfx.RING_FRAC, _c(AMBER, 0.5), Vfx.FLAT, _facing(f, -_time * 2.0))
		if _frame % 3 == 0:
			var a := _sphere() * 0.35
			_spark(Vfx.SPARK, m + a, a.cross(f).normalized() * 3.0, 0.08, 0.04, _c(PALE, 0.6), 0.02, 0.0)


## 光刃：振り抜きの帯（当たり判定の始まりに出す）と、溜め
func _blade(game: GameSim, p: Player) -> void:
	var a = p.attack
	if a != _atk:
		_atk = a
		_atk_done = false
	if a != null:
		if a.move == "lunge" and a.time < a.active_from:
			_afterimage(p, 0.5)
		if not _atk_done and a.time >= a.active_from - 0.017:
			_atk_done = true
			_slash(p, a.move)
	if a == null and p.sword_hold > 0.25:
		_blade_charge(p, p.sword_hold >= float(game.tuning.sword.chargeTime))
	else:
		_blade_full = false


## 振り抜きの帯（blade_combo：各段 0→0.55→0、3 段目 0.85、斬線 1.8／2.2／3.1 m。blade_air：0→0.75→0.15→0、0.28 秒）
func _slash(p: Player, move: String) -> void:
	var f := U.yaw_to_dir(p.yaw)
	var r := Vector3(-f.z, 0, f.x)
	var up := Vector3.UP
	var c := p.pos + Vector3(0, 1.0, 0)
	var radius := 1.8
	var b := 0.55
	var mid := (f + up * 0.1).normalized()
	var swing := -r + up * 0.55
	var life := 0.2
	var dust := p.grounded
	match move:
		"combo2":
			radius = 2.2
			swing = r + up * 0.65
		"combo3":
			radius = 3.1
			b = 0.85
			c = p.pos + Vector3(0, 0.55, 0)
			mid = (f + up * 0.35).normalized()
			swing = up
			life = 0.28
		"air":
			radius = 2.5
			b = 0.75
			mid = (f - up * 0.2).normalized()
			swing = up * 0.85 - r * 0.5
			life = 0.28
		"dash":
			radius = 3.0
			b = 0.75
			c = p.pos + Vector3(0, 0.95, 0) - f * 1.4
			swing = -r
			life = 0.28
			_afterimage(p, 0.8)
		"lunge":
			radius = 2.5
			b = 0.75
			swing = r + up * 0.2
			life = 0.28
		"charge":
			radius = 2.8
			b = 0.9
			mid = f
			swing = r * 0.7 + up * 0.7
			life = 0.32
	swing = (swing - mid * swing.dot(mid)).normalized()
	# 帯：琥珀の地の色（普通の半透明。明るい床の上でも色が残る）を 2 枚ずらして太くし、その上に光の芯（足し合わせ）
	for k in [[1.0, Vfx.SLASH_MIX, Color(AMBER, 0.95), life], [0.93, Vfx.SLASH_MIX, Color(AMBER, 0.75), life * 0.85],
			[0.985, Vfx.SLASH, _cf(PALE, b * 1.2) if b >= 0.85 else _c(PALE, b * 1.2), life * 0.7], [0.95, Vfx.SLASH, _c(AMBER, b), life * 0.8]]:
		var fr := Vfx.slash_frame(c, radius * k[0], mid, swing)
		var q := vfx.emit(k[1], fr[0], Vector3.ZERO, k[3], 1.0, 1.03, k[2])
		q.mode = Vfx.FLAT
		q.basis = fr[1]
		q.wipe = 0.06
		q.fin = 0.22
		q.fpow = 1.6
	# 刃先から散る火花と光のかけら
	for i in (8 if b >= 0.85 else 5):
		var ang := _rng.randf_range(-0.7, 0.7)
		var out := mid * cos(ang) + swing * sin(ang)
		var tang := swing * cos(ang) - mid * sin(ang)
		_spark(Vfx.SPARK, c + out * radius, (tang * _rng.randf_range(3, 6) + out * _rng.randf_range(1, 3)), _rng.randf_range(0.15, 0.25), 0.05, _c(AMBER, b), 0.03, 5.0)
	for i in (4 if b >= 0.85 else 2):
		var ang2 := _rng.randf_range(-0.5, 0.6)
		var out2 := mid * cos(ang2) + swing * sin(ang2)
		_shard(Vfx.SHARD_GLOW, c + out2 * radius, out2 * _rng.randf_range(2, 4) + Vector3(0, 1, 0), 0.35, _rng.randf_range(0.06, 0.12), _c(AMBER, b))
	if dust:
		_puff(Vfx.DUST, p.pos + f * 0.3 + Vector3(0, 0.15, 0), -f * 1.2 + Vector3(0, 0.3, 0), 0.5, 0.35, 0.9, Color(DUST, 0.45))
	if move == "charge":
		_ring(_gauntlet_pos(p), 0.2, 0.9, 0.2, _cf(AMBER, 0.7))


## 残像の代わりの速さの筋（踏み込み・ダッシュ斬り）
func _afterimage(p: Player, b: float) -> void:
	var f := U.yaw_to_dir(p.yaw)
	for i in 2:
		var at := p.pos + Vector3(_rng.randf_range(-0.3, 0.3), _rng.randf_range(0.3, 1.4), _rng.randf_range(-0.3, 0.3)) - f * 0.6
		var q := vfx.emit(Vfx.SPARK, at, -f * 0.02, 0.16, 0.09, 0.04, _c(AMBER, b * 1.3))
		q.mode = Vfx.STREAK
		q.basis = Basis(Vector3.RIGHT, f, Vector3.BACK)
		q.aspect = 20.0


## 光刃の溜め：左の籠手に琥珀の光が集まる（blade_charge：0→0.4→0.9→0）
func _blade_charge(p: Player, full: bool) -> void:
	var g := _gauntlet_pos(p)
	var b := 0.9 if full else 0.4
	if full and not _blade_full:
		_ring(g, 0.1, 0.5, 0.18, _c(AMBER, 0.7))
	_blade_full = full
	for i in (2 if full else 1):
		var off := _sphere() * 0.5
		var q := vfx.emit(Vfx.GRAIN, g + off, -off / 0.22, 0.22, 0.07, 0.03, _c(AMBER, b))
		q.fin = 0.4
	var pl := 0.9 + 0.1 * sin(_time * 20.0)
	vfx.sprite(Vfx.SOFT, g, (0.55 if full else 0.35) * pl, Color(AMBER, 0.75 if full else 0.5))
	vfx.sprite(Vfx.GRAIN, g, (0.9 if full else 0.55) * pl, _c(AMBER, b))
	if full and _frame % 2 == 0:
		var a := _sphere() * 0.25
		_spark(Vfx.SPARK, g + a, a.cross(Vector3.UP).normalized() * 3.0, 0.1, 0.04, _c(PALE, 0.6), 0.02, 0.0)


## ブレイクドリル：先の回る光の輪と、削る火花（drill：0→0.6、連続の小さな火花、約 0.9 秒、先 0.8 m）
func _drill(game: GameSim, p: Player) -> void:
	if not p.drilling:
		return
	var f := U.yaw_to_dir(p.yaw)
	var tip := p.chest() + f * (float(game.tuning.drill.range) * 0.6)
	_drill_tip = tip
	for i in 3:
		var k := float(i)
		vfx.sprite(Vfx.RING, tip - f * (0.1 + 0.22 * k), (0.12 + 0.1 * k) / Vfx.RING_FRAC, _c(AMBER, 0.6 - 0.12 * k), Vfx.FLAT, _facing(f, _time * 30.0 + k))
	vfx.sprite(Vfx.SOFT, tip, 0.35, Color(AMBER, 0.7))
	vfx.sprite(Vfx.GRAIN, tip, 0.6, _c(PALE, 0.6))
	for i in 3:
		_spark(Vfx.SPARK, tip, _cone(-f + _sphere() * 0.2, 1.1) * _rng.randf_range(3, 7), _rng.randf_range(0.12, 0.22), 0.045, _c(AMBER, 0.6))
	# 壁を削っている：壁の印が光る（drill_wall：印 0.15→0.65）
	for b in game.breakables:
		if b.broken or b.distance_to(tip) > float(game.tuning.drill.range) * 0.7:
			continue
		var k2: float = clampf(b.progress / maxf(b.toughness, 0.01), 0.0, 1.0)
		var hit := _box_point(b, tip) - f * 0.06
		vfx.sprite(Vfx.HEX, hit, 0.55 + 0.15 * k2, _c(AMBER, 0.15 + 0.5 * k2), Vfx.FLAT, _facing(-f, _time * 0.8))
		vfx.sprite(Vfx.SOFT, hit, 0.3 + 0.2 * k2, Color(AMBER, 0.3 + 0.4 * k2))
		_spark(Vfx.SPARK, hit, _cone(-f, 0.9) * _rng.randf_range(4, 8), 0.2, 0.06, _c(PALE, 0.6))
		if _frame % 2 == 0:
			_shard(Vfx.SHARD, hit, _cone(-f + Vector3.UP * 0.5, 0.8) * _rng.randf_range(2, 4), 0.6, _rng.randf_range(0.06, 0.14), Color(DUST.darkened(0.1), 1.0), p.pos.y)
		if _frame % 6 == 0:
			_puff(Vfx.DUST, hit, -f * 0.8 + Vector3(0, 0.3, 0), 0.6, 0.3, 0.9, Color(DUST, 0.4))
		break


## 壁（壊せる箱。y 軸まわりに回っている）の、点 p にいちばん近い点（外なら表面の上）
static func _box_point(b, p: Vector3) -> Vector3:
	var rot := Basis(Vector3.UP, b.yaw)
	var l: Vector3 = rot.inverse() * (p - b.center)
	var h: Vector3 = b.size * 0.5
	l = Vector3(clampf(l.x, -h.x, h.x), clampf(l.y, -h.y, h.y), clampf(l.z, -h.z, h.z))
	return b.center + rot * l


## ダッシュ：踏み出しの光と、後ろへ流れる筋（dash：0→0.8（最初の 0.12 秒）→0.3→0、約 0.4 秒、後方約 2.5 m）
func _dash(game: GameSim, p: Player) -> void:
	if p.dash_time <= 0.0:
		_dashing = false
		return
	var m: Dictionary = game.tuning.movement
	var since: float = float(m.dashTime) - p.dash_time
	var d := Vector3(p.vel.x, 0, p.vel.z)
	d = d.normalized() if d.length() > 0.5 else U.yaw_to_dir(p.yaw)
	if not _dashing:
		_dashing = true
		var foot := p.pos + Vector3(0, 0.15, 0)
		_flash(Vfx.GLINT, foot + Vector3(0, 0.2, 0), 0.7, 0.4, 0.1, _c(AMBER, 0.8))
		for i in 6:
			_spark(Vfx.SPARK, foot, _cone(-d + Vector3.UP * 0.2, 0.5) * _rng.randf_range(3, 6), 0.18, 0.05, _c(AMBER, 0.8), 0.03, 4.0)
		for i in 2:
			_puff(Vfx.DUST, foot - d * 0.3, -d * _rng.randf_range(1, 2) + Vector3(0, 0.4, 0), 0.5, 0.4, 1.1, Color(DUST, 0.5))
	var b := 0.8 if since < 0.12 else 0.3
	for i in 3:
		var at := p.pos + Vector3(0, _rng.randf_range(0.1, 1.3), 0) + Vector3(-d.z, 0, d.x) * _rng.randf_range(-0.3, 0.3) - d * 0.4
		var q := vfx.emit(Vfx.SPARK, at, d * 0.02, 0.16, 0.13, 0.05, _c(AMBER, b * 1.25))
		q.mode = Vfx.STREAK
		q.basis = Basis(Vector3.RIGHT, d, Vector3.BACK)
		q.aspect = 18.0
	if since < 0.12:
		var tr := vfx.emit(Vfx.SOFT, p.pos + Vector3(0, 0.25, 0) - d * 0.5, d * 0.02, 0.18, 0.3, 0.12, Color(AMBER, 0.45))
		tr.mode = Vfx.STREAK
		tr.basis = Basis(Vector3.RIGHT, d, Vector3.BACK)
		tr.aspect = 8.0


## 被弾（hurt：衝突 0.55→0.15、小 0.5 秒／大 1.2 秒、体のまわり約 1.7 m）。当てたのは敵なので珊瑚色
func _hurt() -> void:
	if _game == null:
		return
	var p := _game.player
	var heavy := p.hurt_time > 0.5
	var c := p.chest()
	var away := Vector3(p.vel.x, 0, p.vel.z).normalized()
	_flash(Vfx.GLINT, c, 1.4 if heavy else 1.0, 0.6, 0.14, _cf(CORAL, 0.55))
	_soft(c, 0.5, 1.1 if heavy else 0.8, 0.16, CORAL, 0.7)
	for i in (12 if heavy else 7):
		_spark(Vfx.SPARK, c, _cone(away + Vector3.UP * 0.3, 0.8) * _rng.randf_range(3, 7), _rng.randf_range(0.15, 0.3), 0.06, _c(CORAL, 0.55))
	for i in 3:
		_spark(Vfx.SPARK, c, _sphere() * _rng.randf_range(2, 4), 0.2, 0.04, _c(AMBER, 0.4))
	if heavy:
		_dust_ring(p.pos, 4, 0.8, 1.2, 0.55)


## 回復（heal：0→0.5→0.25→0、約 1.0 秒、体の包絡約 2 m）：琥珀の帯が足元から頭へ上がり、光の粒が集まる
func _heal(p: Player) -> void:
	for i in 3:
		var q := _ring(p.pos + Vector3(0, 0.15 + 0.1 * i, 0), 0.55, 0.5, 0.9 - 0.15 * i, _c(AMBER, 0.5), _flat(i * 1.3))
		q.vel = Vector3(0, 1.3 + 0.35 * i, 0)
		q.fin = 0.25
	for i in 16:
		var ang := _rng.randf() * TAU
		var at := p.pos + Vector3(sin(ang) * 0.6, _rng.randf_range(0.1, 1.6), cos(ang) * 0.6)
		var q2 := vfx.emit(Vfx.GRAIN, at, Vector3(-sin(ang) * 0.4, 0.9, -cos(ang) * 0.4), _rng.randf_range(0.6, 1.0), 0.12, 0.05, _c(AMBER, 0.5))
		q2.fin = 0.3
	_flash(Vfx.GRAIN, p.pos + Vector3(0, 1.0, 0), 1.0, 1.6, 0.5, _c(PALE, 0.25))


# ---------------------------------------------------------------- 番機

func _sync_enemies(game: GameSim, dt: float) -> void:
	for e in game.enemies:
		var prev: String = _est.get(e, "")
		if e.kind == "kannuki":
			_boss(game, e, prev, dt)
		elif e.alive:
			_banki(game, e, prev)
		_est[e] = e.state if e.alive else "dead"
	if _frame % 120 == 0:
		for k in _est.keys():
			if not game.enemies.has(k):
				_est.erase(k)


func _part_pos(e, name: String) -> Variant:
	if _ev == null or not is_instance_valid(_ev):
		return null
	return _ev.part_pos(e, name)


## 予兆の光の出る所（弾の出る所・衝角・拳）
func _enemy_muzzle(e) -> Vector3:
	var f: Vector3 = e.forward()
	match e.kind:
		"sentry":
			return e.center() + f * (e.radius + 0.1)
		"floater":
			return e.pos + Vector3(0, 0.05, 0) + f * 0.2
		"charger":
			return e.pos + Vector3(0, 0.55, 0) + f * 1.05
		"mini":
			return e.center() + f * 0.22 + Vector3(0, 0.08, 0)
		"shield":
			var fist = _part_pos(e, "forearm_r")
			if fist != null:
				return fist
			return e.pos + Vector3(0, 1.6, 0)
	return e.center()


func _banki(game: GameSim, e, prev: String) -> void:
	var f: Vector3 = e.forward()
	# 見つけた（banki_alert：琥珀 0.25 → 珊瑚 0.8、0.35 秒）：センサーが珊瑚色に光る
	if prev == "idle" and e.state == "alert":
		var s = _part_pos(e, "sensor")
		var at: Vector3 = s if s != null else e.center() + Vector3(0, e.height * 0.3, 0) + f * e.radius
		_flash(Vfx.GLINT, at, 0.9, 0.5, 0.35, _c(CORAL, 0.8))
		_soft(at, 0.3, 0.45, 0.35, CORAL, 0.6)
		_ring(at, 0.1, 0.45, 0.25, _c(CORAL, 0.5))
	# 予兆（banki_windup：0→0.25→0.7 以上→発射で 0、0.4 秒以上）：砲口・衝角・拳に珊瑚色の光が集まる
	if e.telegraphing():
		var wt: float = float(game.tuning.enemies.get(e.kind, {}).get("windup", 0.5))
		var k := clampf(e.state_time / maxf(wt, 0.05), 0.0, 1.0)
		var m := _enemy_muzzle(e)
		var b := 0.25 + 0.5 * k
		var pulse := 0.8 + 0.2 * sin(_time * 30.0)
		vfx.sprite(Vfx.SOFT, m, (0.4 + 0.35 * k) * pulse, Color(CORAL, 0.35 + 0.3 * k))
		vfx.sprite(Vfx.GRAIN, m, (0.5 + 0.5 * k) * pulse, _c(CORAL, b))
		vfx.sprite(Vfx.DOT, m, 0.15 + 0.12 * k, Color(CORAL, 0.9))
		if k > 0.4:
			vfx.sprite(Vfx.RING, m, (0.25 + 0.35 * (1.0 - fmod(_time * 3.0, 1.0))) / Vfx.RING_FRAC, _c(CORAL, b * 0.7))
		if _frame % 2 == 0:
			var off := _sphere() * 0.5
			var q := vfx.emit(Vfx.GRAIN, m + off, -off / 0.2, 0.2, 0.08, 0.03, _c(CORAL, b))
			q.fin = 0.4
	match e.kind:
		"charger":
			if e.state == "attack":
				for i in 2:
					var at2: Vector3 = e.pos + Vector3(0, _rng.randf_range(0.2, 1.0), 0) + Vector3(-f.z, 0, f.x) * _rng.randf_range(-0.5, 0.5) - f * 0.8
					var q2 := vfx.emit(Vfx.SPARK, at2, f * 0.02, 0.14, 0.05, 0.02, _c(CORAL, 0.6))
					q2.mode = Vfx.STREAK
					q2.basis = Basis(Vector3.RIGHT, f, Vector3.BACK)
					q2.aspect = 24.0
				if _frame % 3 == 0:
					_puff(Vfx.DUST, e.pos - f * 0.6 + Vector3(0, 0.2, 0), -f * 1.5 + Vector3(0, 0.4, 0), 0.6, 0.4, 1.2, Color(DUST, 0.5))
			if e.state == "stunned":
				if prev != "stunned" and prev != "":
					_charger_crash(e)
				# 動けない 2 秒：電気の小さな火花（0.15）
				if _rng.randf() < 0.18:
					var at3: Vector3 = e.pos + Vector3(_rng.randf_range(-0.5, 0.5), _rng.randf_range(0.4, 1.0), _rng.randf_range(-0.5, 0.5))
					for i in 2:
						_spark(Vfx.SPARK, at3, _sphere() * 2.5, 0.08, 0.035, _c(AMBER if _rng.randf() < 0.5 else CORAL, 0.35), 0.02, 0.0)
		"floater":
			if e.state == "attack" and _frame % 2 == 0:
				var q3 := vfx.emit(Vfx.GRAIN, e.pos + Vector3(0, 0.25, 0), Vector3.ZERO, 0.25, 0.3, 0.1, _c(CORAL, 0.35))
				q3.fin = 0.1


## 突撃型が壁に激突（banki_crash：衝突 0.75→電気 0.15→0、衝突 0.3 秒、硬直 2 秒、火花約 1 m）
func _charger_crash(e) -> void:
	var f: Vector3 = e.forward()
	var at: Vector3 = e.pos + f * 1.0 + Vector3(0, 0.55, 0)
	_flash(Vfx.GLINT, at, 1.0, 0.6, 0.18, _cf(CORAL, 0.75))
	_flash(Vfx.GRAIN, at, 0.6, 1.2, 0.2, _c(CORAL, 0.5))
	for i in 10:
		_spark(Vfx.SPARK, at, _cone(-f + Vector3.UP * 0.4, 0.9) * _rng.randf_range(3, 7), _rng.randf_range(0.2, 0.35), 0.06, _c(CORAL, 0.75), 0.03, 8.0)
	for i in 6:
		_shard(Vfx.SHARD, at, _cone(-f + Vector3.UP * 0.6, 0.8) * _rng.randf_range(2, 4), 1.0, _rng.randf_range(0.12, 0.28), Color(ROCK, 1.0), e.pos.y)
	_dust_ring(e.pos + f * 0.9, 4, 0.8, 1.2, 0.55)


# ---------------------------------------------------------------- 閂

func _drill_tips(e) -> Array:
	_tips.clear()
	if _ev == null or not is_instance_valid(_ev):
		return _tips
	for a in ARMS:
		if e.arm_broken[a]:
			continue
		var xf = _ev.part_xform(e, "arm_%s_drill" % a)
		if xf == null:
			continue
		var t: Transform3D = xf
		var axis := t.basis.x.normalized() * signf(DRILL_TIP[a])
		_tips.append([a, t * Vector3(DRILL_TIP[a], 0, 0), axis])
	return _tips


func _boss(game: GameSim, e, prev: String, dt: float) -> void:
	var c: Dictionary = game.tuning.boss
	if not e.alive:
		_boss_dead(e, dt)
		return
	var st: String = e.state
	var f: Vector3 = e.forward()
	var tips := _drill_tips(e)
	var k := 0.0
	match st:
		"thrust_windup":
			var w: float = c.thrust.windupOverheat if e.overheat else c.thrust.windup
			k = clampf(e.state_time / w, 0.0, 1.0)
			for t in tips:
				if t[0] == "fl" or t[0] == "fr":
					_tip_warn(t, 0.3 + 0.4 * k, true)
			# 突進の通り道（床の帯は EnemyView）に流れる珊瑚色の筋
			for i in 2:
				var at: Vector3 = e.pos + f * _rng.randf_range(5.0, 22.0) + Vector3(-f.z, 0, f.x) * _rng.randf_range(-1.6, 1.6) + Vector3(0, 0.1, 0)
				var q := vfx.emit(Vfx.SPARK, at, f * 6.0, 0.25, 0.07, 0.04, _c(CORAL, 0.35 + 0.3 * k))
				q.mode = Vfx.STREAK
				q.stretch = 0.15
				q.fin = 0.3
		"thrust":
			_boss_rush(e, f, 0.7)
		"spin_windup":
			k = clampf(e.state_time / (float(c.spin.windup) * (0.75 if e.overheat else 1.0)), 0.0, 1.0)
			for t in tips:
				_tip_warn(t, 0.25 + 0.2 * k, false)
			_circle(Vector3(e.pos.x, e.pos.y + 0.08, e.pos.z), e.spin_r, 0.3, _c(CORAL, 0.35 + 0.3 * k))
		"spin":
			_circle(Vector3(e.pos.x, e.pos.y + 0.08, e.pos.z), e.spin_r, 0.35, _c(CORAL, 0.7), _time)
			for t in tips:
				var rel: Vector3 = t[1] - e.pos
				var tang := Vector3(rel.z, 0, -rel.x).normalized() * signf(e.spin_speed)
				var q2 := vfx.emit(Vfx.SPARK, t[1], tang * 0.02, 0.22, 0.34, 0.12, _c(CORAL, 0.9))
				q2.mode = Vfx.STREAK
				q2.basis = Basis(Vector3.RIGHT, tang, Vector3.BACK)
				q2.aspect = 10.0
				q2.fin = 0.05
				var q5 := vfx.emit(Vfx.SOFT, t[1], tang * 0.02, 0.25, 0.45, 0.2, Color(CORAL, 0.45))
				q5.mode = Vfx.STREAK
				q5.basis = Basis(Vector3.RIGHT, tang, Vector3.BACK)
				q5.aspect = 6.0
				if _frame % 3 == 0:
					var g := Vector3(t[1].x, e.pos.y, t[1].z)
					_puff(Vfx.DUST, g + Vector3(0, 0.3, 0), rel.normalized() * 2.0 + Vector3(0, 0.6, 0), 0.7, 0.6, 1.6, Color(DUST, 0.5))
					_shard(Vfx.SHARD, g + Vector3(0, 0.3, 0), (rel.normalized() * 3.0 + tang * 2.0 + Vector3(0, 3, 0)), 0.8, _rng.randf_range(0.12, 0.28), Color(ROCK, 1.0), e.pos.y)
		"volley_windup":
			k = clampf(e.state_time / float(c.volley.windup), 0.0, 1.0)
			var nose: Vector3 = e.axis_center() + f * (float(c.bodyHalfLen) + 0.3)
			vfx.sprite(Vfx.GRAIN, nose, 1.0 + 0.6 * k, _c(CORAL, 0.3 + 0.3 * k))
			vfx.sprite(Vfx.DOT, nose, 0.25 + 0.15 * k, Color(CORAL, 0.85))
			vfx.sprite(Vfx.PILLAR, e.axis_center() + Vector3(0, 3.0, 0), 1.6, _c(CORAL, 0.3 * k), Vfx.FACE, Basis.IDENTITY, 0.0, 4.0)
			if _frame % 4 == 0:
				var rk := _shard(Vfx.SHARD, e.axis_center() + Vector3(_rng.randf_range(-1.5, 1.5), 1.5, _rng.randf_range(-1.5, 1.5)), Vector3(0, 3.0, 0), 0.6, _rng.randf_range(0.15, 0.3), Color(ROCK, 1.0))
				rk.grav = 0.0
		"slam_windup":
			k = clampf(e.state_time / float(c.slam.windup), 0.0, 1.0)
			for t in tips:
				if t[0] == "fl" or t[0] == "fr":
					var g2 := Vector3(t[1].x, e.pos.y + 0.06, t[1].z)
					var pulse := 1.0 - fmod(_time * 2.5, 1.0)
					vfx.sprite(Vfx.RING, g2, (0.6 + 0.5 * pulse) / Vfx.RING_FRAC, _c(CORAL, 0.3 + 0.35 * k), Vfx.FLAT, _flat())
					vfx.streak(Vfx.GRAIN, g2, t[1], 0.25, _c(CORAL, 0.25 + 0.3 * k))
		"slam":
			if prev == "slam_windup":
				_slam_impact(e, tips)
		"summon_windup":
			k = clampf(e.state_time / float(c.summon.windup), 0.0, 1.0)
			var belly: Vector3 = e.axis_center() + Vector3(0, -1.2, 0)
			vfx.sprite(Vfx.SOFT, belly, 1.2 + 0.6 * k, Color(AMBER, 0.25 + 0.3 * k))
			vfx.sprite(Vfx.GRAIN, belly, 2.0 + 1.0 * k, _c(AMBER, 0.25 + 0.35 * k))
			for i in 2:
				var ang := _rng.randf() * TAU
				var to := Vector3(e.pos.x + sin(ang) * 6.0, e.pos.y + 0.1, e.pos.z + cos(ang) * 6.0)
				var q3 := vfx.emit(Vfx.GRAIN, belly, (to - belly) / 0.45, 0.45, 0.3, 0.15, _c(AMBER, 0.35 + 0.35 * k))
				q3.mode = Vfx.STREAK
				q3.stretch = 0.06
				q3.fin = 0.2
	# 叩きつけの輪（跳べる低い輪：輪 0.55、高さ約 0.4 m）
	_slam_wave(e)
	# 核が開いている：琥珀の光（背核 0.8）
	if e.core_open:
		var cp = _part_pos(e, "core")
		var at4: Vector3 = cp if cp != null else e.axis_center() + Vector3(0, 1.3, 0)
		var pl := 0.85 + 0.15 * sin(_time * 10.0)
		vfx.sprite(Vfx.GRAIN, at4 + Vector3(0, 0.3, 0), 1.4 * pl, _c(AMBER, 0.6))
		if _frame % 4 == 0:
			var q4 := vfx.emit(Vfx.GRAIN, at4 + Vector3(_rng.randf_range(-0.4, 0.4), 0.3, _rng.randf_range(-0.4, 0.4)), Vector3(0, 1.2, 0), 0.6, 0.12, 0.05, _c(AMBER, 0.5))
			q4.fin = 0.3
	# 過熱（kannuki_overheat：継手 0.25→外周 0.65→突進 0.8→0.2）：薄い蒸気。継手の珊瑚色は EnemyView
	if e.overheat and st != "shift" and _frame % 8 == 0:
		var a2: String = ARMS[_rng.randi() % 4]
		if not e.arm_broken[a2]:
			var root: Vector3 = e.axis_center().lerp(e.arm_center(a2), 0.55)
			_puff(Vfx.SMOKE, root + Vector3(0, 0.6, 0), Vector3(_rng.randf_range(-0.3, 0.3), 1.4, _rng.randf_range(-0.3, 0.3)), 1.4, 0.7, 2.4, Color(0.78, 0.76, 0.72, 0.45))
	_heat(game, e)
	# 壊れた腕の付け根の煙（1.4 秒）
	for a3 in _arm_smoke.keys():
		_arm_smoke[a3] -= dt
		if _arm_smoke[a3] <= 0.0:
			_arm_smoke.erase(a3)
			continue
		if _frame % 4 == 0:
			var stump: Vector3 = e.axis_center().lerp(e.arm_center(a3), 0.4)
			_puff(Vfx.SMOKE, stump, Vector3(_rng.randf_range(-0.4, 0.4), 1.2, _rng.randf_range(-0.4, 0.4)), 1.3, 0.8, 2.6, Color(GRAPHITE, 0.7))
			if _rng.randf() < 0.5:
				_spark(Vfx.SPARK, stump, _sphere() * 3.0, 0.15, 0.05, _c(AMBER, 0.4))


## 削岩腕の先の予兆：珊瑚色の光と、先を囲む弧
func _tip_warn(t: Array, b: float, ring: bool) -> void:
	var pulse := 0.85 + 0.15 * sin(_time * 24.0)
	vfx.sprite(Vfx.SOFT, t[1], 0.9 * pulse, Color(CORAL, 0.55))
	vfx.sprite(Vfx.GRAIN, t[1], 1.3 * pulse, _c(CORAL, b))
	vfx.sprite(Vfx.DOT, t[1], 0.3, Color(CORAL, 0.85))
	if ring:
		var ph := fmod(_time * 2.0, 1.0)
		vfx.sprite(Vfx.RING, t[1] - t[2] * (0.6 * ph), (0.45 + 0.5 * ph) / Vfx.RING_FRAC, _c(CORAL, b * (1.0 - ph)), Vfx.FLAT, _facing(t[2]))


## 突進（kannuki_thrust：腕 0.3→レール 0.7→背核 0.8→0.25、突進約 12 m）：珊瑚色の速さの筋、先の土煙、レールの火花
func _boss_rush(e, f: Vector3, b: float) -> void:
	var side := Vector3(-f.z, 0, f.x)
	for i in 3:
		var at: Vector3 = e.axis_center() + side * _rng.randf_range(-2.4, 2.4) + Vector3(0, _rng.randf_range(-1.6, 1.4), 0) - f * _rng.randf_range(0.0, 4.0)
		var q := vfx.emit(Vfx.SPARK, at, f * 0.02, 0.18, 0.14, 0.05, _c(CORAL, b * 1.2))
		q.mode = Vfx.STREAK
		q.basis = Basis(Vector3.RIGHT, f, Vector3.BACK)
		q.aspect = 28.0
	var nose: Vector3 = e.axis_center() + f * 4.6
	var g := Vector3(nose.x, e.pos.y, nose.z)
	if _frame % 2 == 0:
		_puff(Vfx.DUST, g + Vector3(0, 0.4, 0) + side * _rng.randf_range(-1.5, 1.5), (side * _rng.randf_range(-3, 3)) + Vector3(0, 1.0, 0), 0.7, 0.8, 2.0, Color(DUST, 0.5))
		_shard(Vfx.SHARD, g + Vector3(0, 0.3, 0), (side * _rng.randf_range(-4, 4) + f * 2.0 + Vector3(0, 3.5, 0)), 0.8, _rng.randf_range(0.12, 0.3), Color(ROCK, 1.0), e.pos.y)
	for i in 2:
		var foot: Vector3 = e.pos + side * (1.2 if i == 0 else -1.2) + Vector3(0, 0.1, 0)
		_spark(Vfx.SPARK, foot, _cone(-f + Vector3.UP * 0.4, 0.4) * _rng.randf_range(3, 6), 0.15, 0.05, _c(AMBER, 0.7), 0.03, 5.0)


## 突きが壁に刺さった（衝突約 3 m）
func _boss_crash(at: Vector3) -> void:
	_flash(Vfx.GLINT, at, 3.0, 1.5, 0.2, _cf(PALE, 0.7))
	_flash(Vfx.GRAIN, at, 1.5, 3.0, 0.25, _cf(AMBER, 0.5))
	_ring(at, 0.8, 3.0, 0.3, _cf(AMBER, 0.5))
	for i in 14:
		_spark(Vfx.SPARK, at, _sphere() * _rng.randf_range(4, 9), _rng.randf_range(0.25, 0.4), 0.08, _c(AMBER, 0.7), 0.03, 8.0)
	var floor_y := at.y - 2.6
	if _game != null and _game.boss != null:
		floor_y = _game.boss.pos.y
	for i in 10:
		_shard(Vfx.SHARD, at + _sphere(), _sphere() * _rng.randf_range(3, 6) + Vector3(0, 3, 0), 1.2, _rng.randf_range(0.2, 0.55), Color(ROCK, 1.0), floor_y)
	for i in 6:
		_puff(Vfx.DUST, at + _sphere() * 1.5, _sphere() * 1.5 + Vector3(0, 0.6, 0), 1.2, 1.5, 3.5, Color(DUST, 0.55))


## 叩きつけの着地（接地 0.85）
func _slam_impact(e, tips: Array) -> void:
	for t in tips:
		if t[0] != "fl" and t[0] != "fr":
			continue
		var g := Vector3(t[1].x, e.pos.y + 0.2, t[1].z)
		_flash(Vfx.GLINT, g + Vector3(0, 0.4, 0), 2.6, 1.2, 0.16, _cf(PALE, 0.85))
		_flash(Vfx.GRAIN, g + Vector3(0, 0.3, 0), 1.2, 2.6, 0.22, _cf(AMBER, 0.5))
		_ring(g, 0.4, 2.5, 0.3, _cf(AMBER, 0.5), _flat())
		for i in 7:
			_shard(Vfx.SHARD, g, _cone(Vector3.UP, 0.8) * _rng.randf_range(3, 7), 1.1, _rng.randf_range(0.15, 0.45), Color(ROCK, 1.0), e.pos.y)
		for i in 6:
			_spark(Vfx.SPARK, g, _cone(Vector3.UP, 1.0) * _rng.randf_range(4, 8), 0.3, 0.07, _c(AMBER, 0.7), 0.03, 8.0)
		_dust_ring(g - Vector3(0, 0.2, 0), 4, 1.5, 1.8, 0.6)


## 叩きつけの輪：床の輪の帯（珊瑚色）と、高さ 0.4 m の低い光の壁、輪の上の土煙
func _slam_wave(e) -> void:
	var on: bool = e.wave_r > 0.0
	var was := _band.visible
	_band.visible = on
	if not on:
		return
	var r: float = e.wave_r
	var y: float = e.pos.y
	_circle(Vector3(e.pos.x, y + 0.07, e.pos.z), r, 0.4, _c(CORAL, 0.6))
	if r < 6.0:
		vfx.sprite(Vfx.RING, Vector3(e.pos.x, y + 0.07, e.pos.z), r / Vfx.RING_FRAC, _c(CORAL, 0.55 * (1.0 - r / 6.0)), Vfx.FLAT, _flat())
	_band.position = Vector3(e.pos.x, y + 0.02, e.pos.z)
	_band.scale = Vector3(r, 0.42, r)
	if not was:
		_band.reset_physics_interpolation()
	_band_mat.albedo_color = _c(CORAL, 0.55)
	for i in 2:
		var ang := _rng.randf() * TAU
		var g := Vector3(e.pos.x + sin(ang) * r, y, e.pos.z + cos(ang) * r)
		_puff(Vfx.DUST, g + Vector3(0, 0.3, 0), Vector3(sin(ang), 0.4, cos(ang)) * 1.5, 0.5, 0.5, 1.2, Color(DUST, 0.45))
	if _frame % 2 == 0:
		var ang2 := _rng.randf() * TAU
		var g2 := Vector3(e.pos.x + sin(ang2) * r, y + 0.1, e.pos.z + cos(ang2) * r)
		_shard(Vfx.SHARD, g2, Vector3(sin(ang2) * 2.0, _rng.randf_range(2, 4), cos(ang2) * 2.0), 0.6, _rng.randf_range(0.1, 0.22), Color(ROCK, 1.0), y)


## 床の過熱：予告は外周の境界だけが脈打ち、熱いあいだは外周いっぱいに珊瑚色の熱と火の粉（中央は安全）
func _heat(game: GameSim, e) -> void:
	if e.heat_state <= 0:
		return
	var rin: float = float(game.tuning.boss.heat.radiusIn)
	var rout: float = float(game.tuning.boss.arenaRadius)
	var ctr: Vector3 = e.arena + Vector3(0, 0.06, 0)
	if e.heat_state == 1:
		var pulse := 0.5 + 0.5 * sin(_time * 14.0)
		_circle(ctr, rin, 0.35, _c(CORAL, 0.3 + 0.45 * pulse))
	else:
		_circle(ctr, rin, 0.35, _c(CORAL, 0.75))
		for i in 3:
			var ang := _rng.randf() * TAU
			var rr := _rng.randf_range(rin + 0.3, rout - 0.3)
			var at := ctr + Vector3(sin(ang) * rr, 0.0, cos(ang) * rr)
			var q := vfx.emit(Vfx.GRAIN, at, Vector3(_rng.randf_range(-0.3, 0.3), _rng.randf_range(1.0, 2.2), _rng.randf_range(-0.3, 0.3)), _rng.randf_range(0.6, 1.0), 0.14, 0.05, _c(CORAL, 0.6))
			q.fin = 0.2
		if _frame % 6 == 0:
			var ang3 := _rng.randf() * TAU
			var rr3 := _rng.randf_range(rin + 0.5, rout - 0.5)
			_puff(Vfx.SMOKE, ctr + Vector3(sin(ang3) * rr3, 0.4, cos(ang3) * rr3), Vector3(0, 1.0, 0), 1.4, 0.8, 2.4, Color(PALE, 0.18))


## 段階の変わり目：輪が広がる（第 3 段階は珊瑚色と蒸気）
func _boss_phase(phase: int) -> void:
	if _game == null or _game.boss == null:
		return
	var e = _game.boss
	var g := Vector3(e.pos.x, e.pos.y + 0.1, e.pos.z)
	_ring(g, 2.0, 10.0, 0.6, _c(CORAL if phase >= 3 else AMBER, 0.45), _flat())
	_dust_ring(g, 8, 5.0, 2.0, 0.5)
	if phase >= 3:
		for i in 8:
			_puff(Vfx.SMOKE, e.axis_center() + _sphere() * 2.5, Vector3(0, 1.6, 0) + _sphere() * 0.5, 1.6, 0.8, 2.6, Color(PALE, 0.3))


## 腕 1 本の破損（kannuki_arm_break：継手 0.2→破断 0.85→煙 0.15→0、1.4 秒／腕、腕約 4 m、破片約 3 m）
func _arm_break(at: Vector3) -> void:
	_flash(Vfx.GLINT, at, 2.4, 1.2, 0.18, _cf(PALE, 0.85))
	_flash(Vfx.GRAIN, at, 1.0, 2.4, 0.25, _cf(AMBER, 0.6))
	_ring(at, 0.4, 2.2, 0.25, _cf(AMBER, 0.5))
	for i in 12:
		_spark(Vfx.SPARK, at, _sphere() * _rng.randf_range(4, 8) + Vector3(0, 2, 0), _rng.randf_range(0.25, 0.45), 0.07, _c(AMBER, 0.75), 0.03, 8.0)
	for i in 5:
		_spark(Vfx.SPARK, at, _sphere() * _rng.randf_range(3, 6), 0.3, 0.06, _c(CORAL, 0.6), 0.03, 6.0)
	var floor_y := at.y - 3.0
	if _game != null and _game.boss != null:
		floor_y = _game.boss.pos.y
	for i in 8:
		_shard(Vfx.SHARD, at + _sphere() * 0.5, _sphere() * _rng.randf_range(2, 5) + Vector3(0, 3, 0), 1.3, _rng.randf_range(0.2, 0.45),
			Color(IVORY if i % 2 == 0 else BRASS, 1.0), floor_y)


## 呼び出しの床口（kannuki_summon：床口 0.25→上昇 0.6→0、1.5 秒、床口約 2 m）
func _summon_hatch(g: Vector3) -> void:
	var q := _ring(g + Vector3(0, 0.06, 0), 0.9, 1.2, 1.5, _c(AMBER, 0.6), _flat())
	q.fin = 0.2
	var p := _flash(Vfx.PILLAR, g + Vector3(0, 1.4, 0), 1.2, 0.9, 0.8, _c(AMBER, 0.6))
	p.aspect = 3.0
	p.rot = 0.0
	for i in 8:
		var q2 := vfx.emit(Vfx.GRAIN, g + Vector3(_rng.randf_range(-0.8, 0.8), 0.1, _rng.randf_range(-0.8, 0.8)), Vector3(0, _rng.randf_range(1.5, 3.5), 0), _rng.randf_range(0.6, 1.0), 0.12, 0.05, _c(AMBER, 0.6))
		q2.fin = 0.2
	for i in 5:
		_shard(Vfx.SHARD, g + Vector3(0, 0.1, 0), _cone(Vector3.UP, 0.7) * _rng.randf_range(2, 4), 0.8, _rng.randf_range(0.12, 0.3), Color(ROCK, 1.0), g.y)
	_dust_ring(g, 4, 1.0, 1.4, 0.55)


## 撃破（kannuki_destroy：核 0.35→開放 0.9→崩落 0.3→0、2.2 秒、胴約 10 m、残る核約 0.8 m）。撃破からの時間で進める
func _boss_dead(e, dt: float) -> void:
	_band.visible = false
	var t: float = e.dead_time
	var t0 := t - dt
	var cp = _part_pos(e, "core")
	var core: Vector3 = cp if cp != null else e.axis_center() + Vector3(0, 1.3, 0)
	var f: Vector3 = e.forward()
	if t < 0.3:
		# 封印の解放：核のまわりから光が漏れる
		var k := t / 0.3
		vfx.sprite(Vfx.GRAIN, core, 1.2 + 0.8 * k, _c(AMBER, 0.35 + 0.3 * k))
		for i in 4:
			vfx.sprite(Vfx.PILLAR, core, 0.9, _c(AMBER, 0.3 * k), Vfx.FACE, Basis.IDENTITY, i * PI / 4.0 + t, 4.0)
	var top := core + Vector3(0, 0.7, 0)
	if t >= 0.3 and t0 < 0.3:
		_flash(Vfx.GLINT, top, 4.0, 2.0, 0.3, _cf(PALE, 0.9))
		var beam := _flash(Vfx.PILLAR, top + Vector3(0, 3.0, 0), 2.0, 1.4, 0.6, _cf(AMBER, 0.7))
		beam.aspect = 4.0
		beam.rot = 0.0
		_flash(Vfx.GRAIN, core, 2.0, 5.0, 0.4, _cf(AMBER, 0.6))
		_ring(core, 1.0, 6.0, 0.45, _cf(AMBER, 0.55))
		for i in 24:
			_spark(Vfx.SPARK, core, _sphere() * _rng.randf_range(5, 11) + Vector3(0, 2, 0), _rng.randf_range(0.3, 0.6), 0.08, _c(AMBER, 0.8), 0.03, 8.0)
		for i in 10:
			_shard(Vfx.SHARD_GLOW, core, _sphere() * _rng.randf_range(3, 6) + Vector3(0, 3, 0), 1.0, _rng.randf_range(0.12, 0.25), _c(AMBER, 0.6), e.pos.y)
	if t >= 0.3 and t < 0.7:
		vfx.sprite(Vfx.GRAIN, top, 2.4, _c(AMBER, 0.6))
		vfx.sprite(Vfx.SOFT, top, 1.2, Color(AMBER, 0.6))
	if t >= 0.7 and t < 1.6:
		# 崩落：胴の長さに沿って土煙と破片
		if _frame % 2 == 0:
			var along: Vector3 = e.pos + f * _rng.randf_range(-5.0, 5.0) + Vector3(-f.z, 0, f.x) * _rng.randf_range(-2.0, 2.0)
			_puff(Vfx.SMOKE, along + Vector3(0, 0.6, 0), Vector3(_rng.randf_range(-0.8, 0.8), 1.2, _rng.randf_range(-0.8, 0.8)), 1.4, 1.6, 3.8, Color(DUST.darkened(0.15), 0.55))
		var drop: Vector3 = e.pos + f * _rng.randf_range(-4.5, 4.5) + Vector3(0, 3.5, 0)
		_shard(Vfx.SHARD, drop, _sphere() * 2.0, 1.2, _rng.randf_range(0.2, 0.5), Color(IVORY if _rng.randf() < 0.6 else ROCK, 1.0), e.pos.y)
	if t >= 0.7:
		# 残る核（琥珀 0.3）：沈んで消えるまで
		var vanish := 8.0
		if t < vanish:
			var fade := clampf((vanish - t) / 1.5, 0.0, 1.0)
			var pl := 0.9 + 0.1 * sin(_time * 3.0)
			vfx.sprite(Vfx.SOFT, top, 0.9 * pl, Color(AMBER, 0.55 * fade))
			vfx.sprite(Vfx.GRAIN, top, 1.6 * pl, _c(AMBER, (0.45 if t < 1.6 else 0.3) * fade))


# ---------------------------------------------------------------- 仕掛け・拾い物

func _sync_world(game: GameSim, dt: float) -> void:
	_node_memory(game, dt)
	# 拾い物：吸い寄せられて取れた所から、ハルの胸へ光の筋（pickup：輪 0.25→吸引 0.5→0、0.55 秒／種）
	var alive := {}
	for k in game.pickups:
		alive[k] = true
		_picks[k] = k.pos
	for k in _picks.keys():
		if not alive.has(k):
			if k.collected and k.age < 30.0:
				_pickup(_picks[k], game.player.chest())
			_picks.erase(k)
	# 解析（scan：細輪 0.3→弱点 0.65→0、1.5 秒、輪の直径約 2.5 m）：ロックオンした相手を輪が上から下へなぞる
	var t = game.lock_on.target
	if t != _scan_target:
		_scan_target = t
		_scan_done = false
	if t != null and t.alive and game.nagomi_present():
		var pr: float = game.lock_on.scan_progress()
		if pr < 1.0:
			var top: float = t.pos.y + t.height + 0.2
			var y := lerpf(top, t.pos.y + 0.1, pr)
			var rad := clampf(t.radius * 1.6, 0.6, 2.5) if t.kind != "kannuki" else 3.0
			vfx.sprite(Vfx.RING, Vector3(t.pos.x, y, t.pos.z), rad / Vfx.RING_FRAC, _c(AMBER, 0.3), Vfx.FLAT, _flat(_time))
		elif not _scan_done:
			_scan_done = true
			var wp: Vector3 = t.center()
			_flash(Vfx.GLINT, wp, 0.7, 0.4, 0.3, _c(AMBER, 0.65))
			_ring(wp, 0.2, 0.8, 0.3, _c(AMBER, 0.5))
	# フレームの部品が付いた（frame_fit：粒 0.2→部位ごと 0.5→完成 0.8→0.2、約 1.8 秒）。胴は適合、籠手は r10、脚は r12
	var fs := Vector3i(int(game.has_ability("lock_on")), int(game.has_ability("sword")), int(game.has_ability("dash")))
	if _frame_state.x >= 0 and fs != _frame_state and _pv != null and is_instance_valid(_pv):
		if fs.x > _frame_state.x:
			_frame_fit(game.player, "core")
		if fs.y > _frame_state.y:
			_frame_fit(game.player, "arm")
		if fs.z > _frame_state.z:
			_frame_fit(game.player, "legs")
	_frame_state = fs


## ノードの記憶の取り込み（node_memory：ノード 0→0.45→殻内 0.65→0、1.4 秒、流路約 2 m）：
## ナゴミが「ch1.node」を話し始めたら、注視点（台本のカメラ。無ければハルの前）からナゴミへ光の点が流れ込む
func _node_memory(game: GameSim, dt: float) -> void:
	var d: Dictionary = game.story.dialogue
	var did := "" if d.is_empty() else String(d.get("id", ""))
	if did == "ch1.node" and _dlg_id != "ch1.node" and game.nagomi_present():
		_node_t = 1.4
		var p := game.player
		_node_from = game.cam_focus if game.cam_focus is Vector3 else p.pos + U.yaw_to_dir(p.yaw) * 2.0 + Vector3(0, 1.2, 0)
	_dlg_id = did
	if _node_t <= 0.0:
		return
	_node_t -= dt
	var pl := game.player
	var to := pl.pos + Vector3(-cos(pl.yaw), 0.0, sin(pl.yaw)) * 0.4 + Vector3(0, 1.32, 0) - U.yaw_to_dir(pl.yaw) * 0.08
	var k := clampf(1.0 - _node_t / 1.4, 0.0, 1.0)
	vfx.sprite(Vfx.GRAIN, _node_from, 0.6, _c(AMBER, 0.45 * (1.0 - k * 0.6)))
	vfx.sprite(Vfx.SOFT, _node_from, 0.3, Color(AMBER, 0.5 * (1.0 - k * 0.6)))
	if _node_t > 0.35 and _frame % 2 == 0:
		var q := vfx.emit(Vfx.GRAIN, _node_from + _sphere() * 0.1, (to - _node_from) / 0.5, 0.5, 0.12, 0.07, _c(AMBER, 0.55))
		q.fin = 0.2
	if k > 0.4:
		vfx.sprite(Vfx.GRAIN, to, 0.5, _c(AMBER, 0.65 * minf(1.0, (k - 0.4) * 3.0)))


func _pickup(at: Vector3, to: Vector3) -> void:
	_ring(at, 0.15, 0.35, 0.25, _c(AMBER, 0.4), _flat())
	_flash(Vfx.GLINT, at, 0.4, 0.2, 0.2, _c(AMBER, 0.5))
	for i in 4:
		var from := at + _sphere() * 0.15
		var q := vfx.emit(Vfx.GRAIN, from, (to - from) / 0.3 + _sphere() * 0.8, 0.3, 0.1, 0.04, _c(AMBER, 0.5))
		q.mode = Vfx.STREAK
		q.stretch = 0.02
		q.fin = 0.2


## セーブビーコンの起動（beacon：0→基部 0.3→柱 0.65→定常 0.3、起動 1.5 秒、柱約 8 m）
func _beacon_on() -> void:
	if _game == null:
		return
	var best = null
	var bd := INF
	for b in _game.beacons:
		var d: float = b.pos.distance_to(_game.player.pos)
		if d < bd:
			bd = d
			best = b
	if best == null:
		return
	var g: Vector3 = best.pos
	_ring(g + Vector3(0, 0.08, 0), 0.6, 2.6, 0.9, _c(AMBER, 0.5), _flat())
	var p := _flash(Vfx.PILLAR, g + Vector3(0, 4.0, 0), 2.2, 1.6, 1.5, _c(AMBER, 0.65))
	p.aspect = 4.0
	p.rot = 0.0
	p.fin = 0.3
	for i in 12:
		var q := vfx.emit(Vfx.GRAIN, g + Vector3(_rng.randf_range(-0.6, 0.6), 0.3, _rng.randf_range(-0.6, 0.6)), Vector3(0, _rng.randf_range(2, 5), 0), _rng.randf_range(0.8, 1.4), 0.14, 0.05, _c(AMBER, 0.5))
		q.fin = 0.2


## 宝箱が開く（relic_glow：箱縁 0.2→開放 0.65→目印 0.3、約 0.8 秒）
func _chest_open(c) -> void:
	var g: Vector3 = c.pos + Vector3(0, 0.6, 0)
	_flash(Vfx.GRAIN, g, 0.6, 1.6, 0.8, _c(AMBER, 0.65))
	var p := _flash(Vfx.PILLAR, g + Vector3(0, 0.9, 0), 1.2, 0.8, 0.8, _c(AMBER, 0.5))
	p.aspect = 2.0
	p.rot = 0.0
	for i in 8:
		var q := vfx.emit(Vfx.GLINT, g + Vector3(_rng.randf_range(-0.5, 0.5), 0.0, _rng.randf_range(-0.3, 0.3)), Vector3(0, _rng.randf_range(0.8, 2.0), 0), _rng.randf_range(0.6, 1.0), 0.25, 0.1, _c(AMBER, 0.6))
		q.fin = 0.2


## フレームの装着：床から光の粒が上がり、部位のまわりに陶器の板のかけらが集まって、光って付く（カプセルなし）
func _frame_fit(p: Player, part: String) -> void:
	var f := U.yaw_to_dir(p.yaw)
	var left := Vector3(f.z, 0, -f.x)
	var at := p.pos + Vector3(0, 1.05, 0)
	match part:
		"arm":
			at = p.pos + Vector3(0, 0.82, 0) + left * 0.25
		"legs":
			at = p.pos + Vector3(0, 0.4, 0)
	_ring(p.pos + Vector3(0, 0.06, 0), 0.4, 1.2, 1.0, _c(AMBER, 0.3), _flat())
	for i in 18:
		var from := at + _sphere() * _rng.randf_range(0.8, 1.3) + Vector3(0, -0.2, 0)
		var q := vfx.emit(Vfx.GRAIN, from, (at - from) / 0.7, 0.7, 0.12, 0.05, _c(AMBER, 0.5))
		q.fin = 0.5
	for i in 8:
		var from2 := at + _sphere() * _rng.randf_range(0.6, 1.0)
		var q2 := vfx.emit(Vfx.SHARD_GLOW, from2, (at - from2) / 0.75, 0.75, 0.12, 0.06, _c(PALE, 0.5))
		q2.spin = _rng.randf_range(-6, 6)
		q2.fin = 0.4
	var fl := _flash(Vfx.GLINT, at, 1.0, 0.6, 1.1, _c(AMBER, 0.8))
	fl.fin = 0.65
	var gl := _flash(Vfx.GRAIN, at, 0.6, 1.0, 1.6, _c(AMBER, 0.2))
	gl.fin = 0.45
	if _pv != null and is_instance_valid(_pv):
		_pv.reveal_later(part, 0.8)
