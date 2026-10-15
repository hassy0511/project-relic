class_name ReachScan
extends RefCounted
## 部屋の「入れるのに出られない所（詰み）」を、形だけで探す（2026-10-15、第 1 章の詰み探し）。
## 当たり判定と同じ形（RoomGeo の箱・坂・階段・殻、宝箱・住人・端末・扉・壊せる壁の箱、動く足場）から、
## ハルの体（半径 0.35 m・高さ 1.55 m のカプセル）が立てる所（node）を 0.25 m おきに求め、
## 歩く（段差 0.35 m まで）・縁から歩いて落ちる・跳ぶ（ジャンプ・ダッシュジャンプの弧。天井・壁に当たらない弧）でつなぐ。
## 住人・端末・セーブビーコンのそばでは跳ぶボタンが「話す・調べる」になるので、そこからは跳ばない。
## 往復する足場は、行き来する間のいくつかの位置の上に node を置き、どの位置もひとつのまとまり（乗ったまま運ばれる）。
## 乗ると動く足場（ride）に乗れるのは止まっている位置だけ。
## 部屋の目印・中継地点から行ける所のうち、出口・目印・中継地点へも、奈落（Player.KILL_Y より下。落ちると直前の足場へ戻る）へも
## 行けない所を「詰み」（stuck）、限界の跳び（段 1.8 m・溝 4.5 m／ダッシュ 7.0 m を越える）でしか戻れない所を hard として返す。
## 落ちて縁の角に体が載り、立てないまま止まりそうな所（宙づり）も返す（hangs。形だけの見積もりなので、実際のゲームで確かめる）。
## 使い方：var scan := ReachScan.new(game, {"dash": game.has_ability("dash")}); var res := scan.run()
##   res = { stuck: [ { pos, y0, y1, nodes, box: [x0, z0, x1, z1] } ], hard: [同じ形], hangs: [ { pos, from, wedged } ], nodes, comps, reached, ms }
##   scan.explain(位置)：始まりからその所までのたどり方（説明用）
## 候補探しの道具（tests/scan_traps.gd）と、回帰のテスト（tests/test_traps.gd）に使う。

## 第 1 章の部屋 → 本筋の段階の名前 → 立てるフラグ（そこにいるときの扉・住人・使える力。ダッシュは GameSim.has_ability が本筋のフラグから決める）
## 終盤（オルドの再始動のあと）：本筋のフラグ（GameSim.CH1_ORDER の ch1.ordo_restarted まで）と、開いた門・近道
const CH1_LATE := ["ch1.chores_started", "ch1.nico_rescued", "ch1.scolded", "ch1.debt_scene", "ch1.ordo_stopped", "ch1.got_spark",
	"ch1.fell_to_b2", "ch1.frame_fitted", "ch1.first_beacon", "ch1.drive_powered", "ch1.shortcut_open", "ch1.diagnosis",
	"ch1.boss_defeated", "ch1.ordo_restarted", "ch1.gate_open", "ch1.blade_online"]
const CH1_STATES := {
	"ch1.opening": {"early": []},
	"ch1.training": {"early": ["ch1.chores_started"]},
	"ch1.lower": {"early": ["ch1.chores_started"], "late": CH1_LATE},
	"ch1.mid": {"early": ["ch1.chores_started"], "late": CH1_LATE},
	"ch1.upper": {"early": ["ch1.chores_started"], "late": CH1_LATE},
	"ch1.home": {"early": ["ch1.chores_started"], "late": CH1_LATE},
	"ch1.workshop": {"early": ["ch1.chores_started"], "late": CH1_LATE},
	"ch1.guild": {"early": ["ch1.chores_started"], "late": CH1_LATE},
	"ch1.mayor": {"early": ["ch1.chores_started"], "late": CH1_LATE},
	"ch1.r01": {"early": ["ch1.nico_ran"], "late": CH1_LATE},
	"ch1.r02": {"early": ["ch1.got_spark"], "late": CH1_LATE},
	"ch1.r03": {"early": ["ch1.got_spark"], "late": CH1_LATE},
	"ch1.r04": {"early": ["ch1.got_spark"], "open": ["ch1.got_spark", "switch.ch1.r04.v1", "switch.ch1.r04.v2"]},
	"ch1.r05": {"early": ["ch1.got_spark"]},
	"ch1.r06": {"early": ["ch1.fell_to_b2"]},
	"ch1.r07": {"early": ["ch1.fell_to_b2"]},
	"ch1.r08": {"early": ["ch1.fell_to_b2"], "fitted": ["ch1.frame_fitted"]},
	"ch1.r09": {"early": ["ch1.frame_fitted"]},
	"ch1.r10": {"early": ["ch1.frame_fitted", "ch1.blade_online"]},
	"ch1.r11": {"early": ["ch1.frame_fitted", "ch1.blade_online"]},
	"ch1.r12": {"early": ["ch1.first_beacon"], "powered": ["ch1.drive_powered"], "late": CH1_LATE},
	"ch1.r13": {"early": ["ch1.drive_powered"]},
	"ch1.r14": {"early": ["ch1.drive_developed"]},
	"ch1.r15": {"early": ["ch1.drive_powered"]},
	"ch1.r16": {"early": ["ch1.drive_powered"]},
	"ch1.r17": {"early": ["ch1.drive_powered"], "late": CH1_LATE},
	"ch1.r18": {"early": ["ch1.shortcut_open"], "diag": ["ch1.diagnosis"]},
	"ch1.r19": {"early": ["ch1.diagnosis"], "late": CH1_LATE},
	"ch1.r20": {"early": ["ch1.boss_defeated"]},
}

const R := 0.35
const H := 1.55
const STEP := 0.35
const CELL := 0.25
## 体が入るかを確かめる半径（形に触れているだけは許す）
const FIT := 0.33
## 落ちる体が縁の角に触れる距離。体の太さちょうど（0.7 m）のすき間でも、物理の余白で両側の角に掛かって止まる（遺構 r09 の低い箱と壁）
const R_TOUCH := 0.362
## 跳ぶ弧の途中で確かめる半径（角をかすめるのは許す）
const FIT_ARC := 0.31
## 体の真ん中が縁からこれだけ出ていても立っている（Player.GROUND_EDGE）
const EDGE := 0.04
const KILL_Y := -30.0
const HASH := 1.0
const NO_TOP := -1.0e9
## 跳ぶ相手を探す範囲（ダッシュジャンプ 10 m/s の弧の届く距離より少し長い）
const SEARCH := 9.0

var game
var opts := {}
var dash := false
var g_up := 22.0
var g_down := 29.7
var v_jump := 9.84
var jump_top := 2.2
var run_speed := 7.0
var dash_speed := 10.0

# 形：箱（y 軸まわりに回る）と坂。坂は _rh > 0（ローカルの -Z が低く +Z が高い。上面 = _y0 + _rh * (lz + hz) / (2 hz)）
var _cx := PackedFloat32Array()
var _cz := PackedFloat32Array()
var _co := PackedFloat32Array()
var _si := PackedFloat32Array()
var _hx := PackedFloat32Array()
var _hz := PackedFloat32Array()
var _y0 := PackedFloat32Array()
var _y1 := PackedFloat32Array()
var _rh := PackedFloat32Array()
## 動く足場の番号（-1 は動かない形）と、置いた時刻の番号
var _mv := PackedInt32Array()
var _mt := PackedInt32Array()
var _hash := {}

# 立てる所（node）
var nx := PackedFloat32Array()
var ny := PackedFloat32Array()
var nz := PackedFloat32Array()
var ncol: Array[Vector2i] = []
## 動く足場の上の点なら、その足場の番号と、置いた時刻の番号
var nmv := PackedInt32Array()
var nmt := PackedInt32Array()
## 柱（列）ごとの node の番号（低い順）
var _cols := {}
var _x0 := 0.0
var _z0 := 0.0
var _x1 := 0.0
var _z1 := 0.0

# 動く足場：{ id, mode, from, to, size, ts: [t...] }
var movers: Array = []

# まとまり（歩いて行き来できる node の集まり）
var _parent := PackedInt32Array()
var comp := PackedInt32Array()
var ncomp := 0
## 歩いて行ける隣の柱の向き（_N8 の番号のビット）
var _wmask := PackedInt32Array()
## まとまりごとの、歩いて行けない向きのある node（縁）
var _cedge: Array = []
## まとまりの間の道（一方通行）：comp → { comp: 種類 }
var cedges: Array = []
var _via := {}
## 跳ぶボタンが「話す・調べる」になる所：[位置, 届く距離]（いつでも使える住人・端末・セーブビーコン・入り切りのスイッチ。
## GameSim._update_interaction：接地して、届く距離の中・高さの差 1.5 m 以内なら、跳ばずに話す）
var _talkers: Array = []
var _fwd := PackedByteArray()
## 前へたどったときの、まとまりの一つ前（説明用）
var _prev := {}
## 奈落へ落ちられるまとまり
var to_void := {}
var hangs: Array = []


func _init(g, o: Dictionary = {}) -> void:
	game = g
	opts = o
	dash = bool(o.get("dash", false))
	var m: Dictionary = g.tuning.movement
	g_up = float(m.gravity)
	g_down = float(m.gravity) * float(m.fallGravityScale)
	jump_top = float(m.jumpHeight)
	v_jump = sqrt(2.0 * g_up * jump_top)
	run_speed = float(m.airMaxSpeed)
	dash_speed = float(m.dashJumpSpeed)


# ---------------------------------------------------------------- 形

func _add_solid(c: Vector3, half: Vector3, xdir: Vector3, ramp_h: float, mover: int, t_index: int = -1) -> void:
	var d := Vector2(xdir.x, xdir.z).normalized()
	_cx.append(c.x)
	_cz.append(c.z)
	_co.append(d.x)
	_si.append(-d.y)
	_hx.append(half.x)
	_hz.append(half.z)
	_y0.append(c.y - half.y)
	_y1.append(c.y + half.y if ramp_h <= 0.0 else c.y - half.y + ramp_h)
	_rh.append(ramp_h)
	_mv.append(mover)
	_mt.append(t_index)


## RoomGeo の面（箱は 36 点、坂は 24 点）から、箱・坂の中心・大きさ・向きを読み戻す（当たり判定と同じ形になる）
func _add_faces(f: PackedVector3Array) -> void:
	if f.size() == 36:
		var c0 := f[0]
		var c2 := f[1]
		var c1 := f[5]
		var c4 := f[6]
		var c7 := f[8]
		var center := (c0 + c7) * 0.5
		var ax := c1 - c0
		_add_solid(center, Vector3(ax.length() * 0.5, (c2.y - c0.y) * 0.5, (c4 - c0).length() * 0.5), ax, 0.0, -1)
	elif f.size() == 24:
		var p0 := f[0]
		var p1 := f[1]
		var p2 := f[2]
		var p3 := f[5]
		var p4 := f[11]
		var base := (p0 + p2) * 0.5
		var ax := p1 - p0
		var h := p4.y - p3.y
		# 坂の底の中心（高さは底）。_add_solid は中心から y の半分を引くので、高さ 0 の箱として足し、上面を坂にする
		_add_solid(base, Vector3(ax.length() * 0.5, 0.0, (p3 - p0).length() * 0.5), ax, h, -1)
	else:
		push_warning("ReachScan: 知らない面の数 %d" % f.size())


func _build_solids() -> void:
	var room: Dictionary = game.room
	for s in room.get("geometry", []):
		for f in RoomGeo.shape(s):
			_add_faces(f)
	# 箱の当たり判定を持つ物（宝箱・住人・端末・扉・壊せる壁）。動く足場は別
	var mover_bodies := {}
	for m in game.movers:
		mover_bodies[m.body] = m
	for c in game.phys.get_children():
		if not (c is StaticBody3D) or (c as StaticBody3D).collision_layer == 0:
			continue
		var b := c as StaticBody3D
		if mover_bodies.has(b):
			continue
		for cs in b.get_children():
			if cs is CollisionShape3D and (cs as CollisionShape3D).shape is BoxShape3D:
				var bx: BoxShape3D = (cs as CollisionShape3D).shape
				var xf := b.global_transform * (cs as CollisionShape3D).transform
				_add_solid(xf.origin, bx.size * 0.5, xf.basis.x, 0.0, -1)
	# 動く足場：往復する足場は、決まった時刻の位置の上に立てる所を作る（体を止める形としては数えない）。
	# 条件が偽で止まっている足場・決まった位置に置かれた足場は、ふつうの形
	for m in game.movers:
		var run := Cond.eval(m.cond, game)
		if m.mode == "pingpong" and not run:
			_add_solid(m.pos + Vector3(0, m.size.y * 0.5, 0), m.size * 0.5, Vector3.RIGHT, 0.0, -1)
			continue
		if m.mode == "toggle":
			var p: Vector3 = m.at_t(1.0 if run else 0.0)
			_add_solid(p + Vector3(0, m.size.y * 0.5, 0), m.size * 0.5, Vector3.RIGHT, 0.0, -1)
			continue
		var n := maxi(2, ceili(m.length() / 1.5) + 1)
		var ts: Array = []
		for k in n:
			ts.append(float(k) / float(n - 1))
		movers.append({"id": m.id, "mode": m.mode, "from": m.from, "to": m.to, "size": m.size, "ts": ts})
		var mi := movers.size() - 1
		for ti in ts.size():
			var p: Vector3 = m.from.lerp(m.to, ts[ti])
			_add_solid(p + Vector3(0, m.size.y * 0.5, 0), m.size * 0.5, Vector3.RIGHT, 0.0, mi, ti)
	# 速く探すための升目（1 m）。体の太さ分広げて登録する
	for i in _cx.size():
		var ex := absf(_hx[i] * _co[i]) + absf(_hz[i] * _si[i]) + R + 0.05
		var ez := absf(_hx[i] * _si[i]) + absf(_hz[i] * _co[i]) + R + 0.05
		for gx in range(floori((_cx[i] - ex) / HASH), floori((_cx[i] + ex) / HASH) + 1):
			for gz in range(floori((_cz[i] - ez) / HASH), floori((_cz[i] + ez) / HASH) + 1):
				var k := Vector2i(gx, gz)
				if not _hash.has(k):
					_hash[k] = PackedInt32Array()
				var arr: PackedInt32Array = _hash[k]
				arr.append(i)
				_hash[k] = arr


func _near(x: float, z: float) -> PackedInt32Array:
	return _hash.get(Vector2i(floori(x / HASH), floori(z / HASH)), PackedInt32Array())


## 形 i の上面の高さ（坂は点のところの高さ。点が坂の外なら、坂の縁の高さ）
func _top_of(i: int, lz: float) -> float:
	if _rh[i] <= 0.0:
		return _y1[i]
	var cl := clampf(lz, -_hz[i], _hz[i])
	return _y0[i] + _rh[i] * (cl + _hz[i]) / (2.0 * _hz[i])


## 足元 (x, y, z) の体（半径 rad、高さ top）が、動かない形にめり込むか
func hits(x: float, y: float, z: float, rad: float = FIT, top: float = H) -> bool:
	return _hits_in(_near(x, z), x, y, z, rad, top)


func _hits_in(list: PackedInt32Array, x: float, y: float, z: float, rad: float = FIT, top: float = H) -> bool:
	var a := y + R
	var b := y + top - R
	var rr := rad * rad
	for i in list:
		if _mv[i] >= 0:
			continue
		var dx := x - _cx[i]
		var dz := z - _cz[i]
		var lx := dx * _co[i] - dz * _si[i]
		var lz := dx * _si[i] + dz * _co[i]
		var ex := maxf(absf(lx) - _hx[i], 0.0)
		var ez := maxf(absf(lz) - _hz[i], 0.0)
		var d2 := ex * ex + ez * ez
		if d2 >= rr:
			continue
		var gap := maxf(maxf(_y0[i] - b, a - _top_of(i, lz)), 0.0)
		if d2 + gap * gap < rr:
			return true
	return false


## 柱 (x, z) の上面の高さ（下から順。重なった・接した形はまとめる）。mover >= 0 ならその足場の形だけ
func column_tops(x: float, z: float, mover: int = -1, t_index: int = -1) -> PackedFloat32Array:
	return _tops_in(_near(x, z), x, z, mover, t_index)


func _tops_in(list: PackedInt32Array, x: float, z: float, mover: int = -1, t_index: int = -1) -> PackedFloat32Array:
	var lo := PackedFloat32Array()
	var hi := PackedFloat32Array()
	for i in list:
		if _mv[i] != mover or (mover >= 0 and _mt[i] != t_index):
			continue
		var dx := x - _cx[i]
		var dz := z - _cz[i]
		var lx := dx * _co[i] - dz * _si[i]
		var lz := dx * _si[i] + dz * _co[i]
		if absf(lx) > _hx[i] or absf(lz) > _hz[i]:
			continue
		var top := _top_of(i, lz)
		# 低い順に差し込む
		var j := lo.size()
		lo.append(0.0)
		hi.append(0.0)
		while j > 0 and lo[j - 1] > _y0[i]:
			lo[j] = lo[j - 1]
			hi[j] = hi[j - 1]
			j -= 1
		lo[j] = _y0[i]
		hi[j] = top
	var out := PackedFloat32Array()
	if lo.is_empty():
		return out
	var cur_hi := hi[0]
	for j in range(1, lo.size()):
		if lo[j] <= cur_hi + 0.02:
			cur_hi = maxf(cur_hi, hi[j])
		else:
			out.append(cur_hi)
			cur_hi = hi[j]
	out.append(cur_hi)
	return out


## 柱 (x, z) で、高さ y 以下の一番高い上面（無ければ NO_TOP）
func top_below(x: float, z: float, y: float) -> float:
	var best := NO_TOP
	for t in column_tops(x, z):
		if t <= y + 0.001 and t > best:
			best = t
	return best


# ---------------------------------------------------------------- 立てる所

func _key(x: float, z: float) -> Vector2i:
	return Vector2i(roundi(x / CELL), roundi(z / CELL))


func _add_node(x: float, y: float, z: float, col: Vector2i, mover: int, t_index: int) -> int:
	nx.append(x)
	ny.append(y)
	nz.append(z)
	ncol.append(col)
	nmv.append(mover)
	nmt.append(t_index)
	var id := nx.size() - 1
	if not _cols.has(col):
		_cols[col] = PackedInt32Array()
	var arr: PackedInt32Array = _cols[col]
	# 高さの順に並べる
	var j := arr.size()
	arr.append(id)
	while j > 0 and ny[arr[j - 1]] > y:
		arr[j] = arr[j - 1]
		j -= 1
	arr[j] = id
	_cols[col] = arr
	return id


const _OFFS := [Vector2(0.1, 0), Vector2(-0.1, 0), Vector2(0, 0.1), Vector2(0, -0.1),
	Vector2(0.1, 0.1), Vector2(-0.1, 0.1), Vector2(0.1, -0.1), Vector2(-0.1, -0.1)]


## 柱の真ん中に体が入らないとき、少しずらして試す（ずらした所も同じ高さの面の上）。入れば node を作る
func _try_node(col: Vector2i, y: float, mover: int, t_index: int) -> void:
	var cx := col.x * CELL
	var cz := col.y * CELL
	for o in _OFFS:
		var x: float = cx + o.x
		var z: float = cz + o.y
		var ok := false
		for t in column_tops(x, z, mover, t_index):
			if absf(t - y) < 0.03:
				ok = true
		if ok and not hits(x, y, z):
			_add_node(x, y, z, col, mover, t_index)
			return


func _build_nodes() -> void:
	var last_key := Vector2i(1 << 30, 0)
	var list := PackedInt32Array()
	for gx in range(roundi(_x0 / CELL), roundi(_x1 / CELL) + 1):
		for gz in range(roundi(_z0 / CELL), roundi(_z1 / CELL) + 1):
			var x := gx * CELL
			var z := gz * CELL
			var hk := Vector2i(floori(x / HASH), floori(z / HASH))
			if hk != last_key:
				last_key = hk
				list = _hash.get(hk, PackedInt32Array())
			if list.is_empty():
				continue
			var col := Vector2i(gx, gz)
			for y in _tops_in(list, x, z):
				if y > KILL_Y:
					if not _hits_in(list, x, y, z):
						_add_node(x, y, z, col, -1, -1)
					else:
						_try_node(col, y, -1, -1)
	for mi in movers.size():
		var mv: Dictionary = movers[mi]
		var sz: Vector3 = mv.size
		for ti in mv.ts.size():
			var p: Vector3 = (mv.from as Vector3).lerp(mv.to, mv.ts[ti])
			var top := p.y + sz.y
			for gx in range(ceili((p.x - sz.x * 0.5) / CELL), floori((p.x + sz.x * 0.5) / CELL) + 1):
				for gz in range(ceili((p.z - sz.z * 0.5) / CELL), floori((p.z + sz.z * 0.5) / CELL) + 1):
					var x := gx * CELL
					var z := gz * CELL
					if not hits(x, top, z):
						_add_node(x, top, z, Vector2i(gx, gz), mi, ti)


func _find(a: int) -> int:
	var r := a
	while _parent[r] != r:
		r = _parent[r]
	var c := a
	while _parent[c] != r:
		var nxt := _parent[c]
		_parent[c] = r
		c = nxt
	return r


func _union(a: int, b: int) -> void:
	var ra := _find(a)
	var rb := _find(b)
	if ra != rb:
		_parent[ra] = rb


const _N8 := [Vector2i(1, 0), Vector2i(-1, 0), Vector2i(0, 1), Vector2i(0, -1), Vector2i(1, 1), Vector2i(-1, 1), Vector2i(1, -1), Vector2i(-1, -1)]
const _OPP := [1, 0, 3, 2, 7, 6, 5, 4]


## u から隣の柱の v へ歩けるか（段差 0.35 m まで。ただし BAD_STEP の段は上れない）。どちらの点にも体が入るので、間に壁は無い
## （壁の両側の点は、体の太さ 0.7 m より離れていて隣の柱にならない）
func _walkable(u: int, v: int) -> bool:
	if nmv[u] != nmv[v] or (nmv[u] >= 0 and nmt[u] != nmt[v]):
		return false
	var dy := absf(ny[v] - ny[u])
	return dy <= STEP + 0.01 and not _bad_step(dy)


## 歩いては上れない段（約 0.18〜0.24 m）：体の丸い底が段の角に当たる向きが、段差の乗り越え（壁とみなす向き）にも床にもならず、
## 角に押し当てたまま止まる（Phys.move_character。2026-10-15 に平らな床の箱で測った）。下りるのと、跳んで上がるのはできる
const BAD_STEP_LO := 0.175
const BAD_STEP_HI := 0.245


func _bad_step(dy: float) -> bool:
	return dy > BAD_STEP_LO and dy < BAD_STEP_HI


func _build_comps() -> void:
	var n := nx.size()
	_parent.resize(n)
	_wmask.resize(n)
	for i in n:
		_parent[i] = i
	for u in n:
		var c := ncol[u]
		for di in 8:
			var nb: PackedInt32Array = _cols.get(c + _N8[di], PackedInt32Array())
			for v in nb:
				if v > u and _walkable(u, v):
					_union(u, v)
					_wmask[u] |= 1 << di
					# 逆向き（_N8 は ±の対で並ぶ：0↔1、2↔3、4↔7、5↔6）
					_wmask[v] |= 1 << _OPP[di]
	# 同じ動く足場の上は、どの時刻もひとつのまとまり（乗ったまま運ばれる）
	var first_of := {}
	for u in n:
		if nmv[u] >= 0:
			if first_of.has(nmv[u]):
				_union(u, first_of[nmv[u]])
			else:
				first_of[nmv[u]] = u
	comp.resize(n)
	var ids := {}
	for u in n:
		var r := _find(u)
		if not ids.has(r):
			ids[r] = ids.size()
		comp[u] = ids[r]
	ncomp = ids.size()
	cedges.resize(ncomp)
	_cedge.resize(ncomp)
	for i in ncomp:
		cedges[i] = {}
		_cedge[i] = PackedInt32Array()
	for u in n:
		if _wmask[u] != 255:
			_cedge[comp[u]].append(u)


## a → b の道。via：[元の node, 先の node]（どこからどこへ。説明用）
func _link(a: int, b: int, kind: String, u := -1, v := -1) -> void:
	if a == b:
		return
	var e: Dictionary = cedges[a]
	if not e.has(b):
		e[b] = kind
		_via[Vector2i(a, b)] = [u, v]


# ---------------------------------------------------------------- 落ちる

## 体の底の丸みが最初に触れる形：[足元の高さ, 形の番号, 水平の距離の 2 乗, ローカル x, ローカル z]（無ければ番号 -1）
func _contact(px: float, py: float, pz: float) -> Array:
	var best_y := NO_TOP
	var best_i := -1
	var best_d2 := 0.0
	var best_lx := 0.0
	var best_lz := 0.0
	for i in _near(px, pz):
		if _mv[i] >= 0:
			continue
		var dx := px - _cx[i]
		var dz := pz - _cz[i]
		var lx := dx * _co[i] - dz * _si[i]
		var lz := dx * _si[i] + dz * _co[i]
		var ex := maxf(absf(lx) - _hx[i], 0.0)
		var ez := maxf(absf(lz) - _hz[i], 0.0)
		var d2 := ex * ex + ez * ez
		if d2 >= R_TOUCH * R_TOUCH:
			continue
		var top := _top_of(i, lz)
		# 上面が体の底の丸みの芯より上の形は、横の壁（そこへは下りない）
		if top > py + R:
			continue
		# 体の底の丸みがこの形の上の角に触れるときの足元の高さ（体の太さちょうどのすき間では、丸みの芯の高さで角に掛かる）
		var cy := top - R + sqrt(maxf(R * R - d2, 0.0))
		if cy > best_y:
			best_y = cy
			best_i = i
			best_d2 = d2
			best_lx = lx
			best_lz = lz
	# 今の高さより上で触れる形（角に寄りかかっている）：今の高さで止まっている
	if best_i >= 0 and best_y > py:
		best_y = py
	return [best_y, best_i, best_d2, best_lx, best_lz]


## 触れた所で立っているか（縁から EDGE まで、または縁の角に載って真下 0.4 m 以内に床がある：Player._ground_below）
func _grounded_at(px: float, pz: float, c: Array) -> bool:
	var d := sqrt(float(c[2]))
	if d <= EDGE:
		return true
	if d > 0.247:
		return false
	var below := top_below(px, pz, float(c[0]) + 0.3)
	return below > NO_TOP and float(c[0]) - below < 0.4


## (x, y, z) から真下へ落ちた先。縁の角に載ったら外へ滑らせる（Phys.move_character の空中の決まり）。
## 滑る先がふさがっていたら（壁ぎわの細いすき間）、その高さのまま横へ動いて抜けられる所を探す（すき間に沿って端へ）。
## 返り値：{ kind: "node", id, slid } | { kind: "void", slid } | { kind: "hang", pos }（どこへも抜けられない宙づり）。
## slid：途中で宙づりになり、横へ動いて抜けた（その所は hang_pos）
func fall(x: float, y: float, z: float) -> Dictionary:
	var px := x
	var pz := z
	var py := y
	var slid := false
	var hang_pos := Vector3.ZERO
	for iter in 80:
		var c := _contact(px, py, pz)
		var best_y: float = c[0]
		var best_i: int = c[1]
		if best_i < 0 or best_y < KILL_Y:
			return {"kind": "void", "slid": slid, "hang_pos": hang_pos}
		if _grounded_at(px, pz, c):
			var d := sqrt(float(c[2]))
			var id := _node_near(px, best_y if d <= EDGE else top_below(px, pz, best_y + 0.3), pz)
			if id >= 0:
				return {"kind": "node", "id": id, "slid": slid, "hang_pos": hang_pos}
		# 縁の角から外へ滑る：形の床の広がりで一番近い点から、体の真ん中への向き
		var qx := clampf(float(c[3]), -_hx[best_i], _hx[best_i])
		var qz := clampf(float(c[4]), -_hz[best_i], _hz[best_i])
		var llx: float = float(c[3]) - qx
		var llz: float = float(c[4]) - qz
		var dir := Vector2(llx * _co[best_i] + llz * _si[best_i], -llx * _si[best_i] + llz * _co[best_i])
		var moved := false
		if dir.length() > 1e-4:
			dir = dir.normalized()
			for cand in [dir, Vector2(dir.x, 0.0), Vector2(0.0, dir.y)]:
				if cand.length() < 0.3:
					continue
				var cd: Vector2 = cand.normalized()
				var mx := px + cd.x * 0.06
				var mz := pz + cd.y * 0.06
				if not hits(mx, best_y + 0.01, mz, 0.34) and float(_contact(mx, best_y + 0.01, mz)[0]) <= best_y + 0.005:
					px = mx
					pz = mz
					moved = true
					break
		if not moved:
			# 宙づり：その高さのまま横へ動いて、下へ抜けられる所・立てる所を探す
			var esc = _slide_out(px, best_y, pz)
			if esc == null:
				return {"kind": "hang", "pos": Vector3(px, best_y, pz)}
			if not slid:
				hang_pos = Vector3(px, best_y, pz)
			slid = true
			px = esc.x
			pz = esc.y
		py = best_y
	return {"kind": "hang", "pos": Vector3(px, py, pz)}


## 宙づりの所 (x, h, z) から、高さを変えずに横へ動いて（空中では上へは押し上げられない）、下へ抜けられる所か立てる所。無ければ null
func _slide_out(x: float, h: float, z: float) -> Variant:
	var ck := Vector3i(roundi(x * 10.0), roundi(h * 20.0), roundi(z * 10.0))
	if _slide_cache.has(ck):
		return _slide_cache[ck]
	var r = _slide_search(x, h, z)
	_slide_cache[ck] = r
	return r


var _slide_cache := {}


func _slide_search(x: float, h: float, z: float) -> Variant:
	var step := 0.08
	var seen := {Vector2i(0, 0): true}
	var q: Array[Vector2i] = [Vector2i(0, 0)]
	var qi := 0
	while qi < q.size() and qi < 800:
		var k: Vector2i = q[qi]
		qi += 1
		for d in _N8:
			var nk: Vector2i = k + d
			if seen.has(nk):
				continue
			seen[nk] = true
			var px := x + nk.x * step
			var pz := z + nk.y * step
			if hits(px, h + 0.01, pz, 0.34):
				continue
			var c := _contact(px, h + 0.01, pz)
			if float(c[0]) > h + 0.005:
				continue
			if int(c[1]) < 0 or float(c[0]) < h - 0.05 or _grounded_at(px, pz, c):
				return Vector2(px, pz)
			q.append(nk)
	return null


## (x, z) の近くで高さ y の node（同じ柱か、まわり 2 柱まで。水平に一番近いもの）
func _node_near(x: float, y: float, z: float) -> int:
	var c := _key(x, z)
	var best := -1
	var bd := INF
	for dx in range(-2, 3):
		for dz in range(-2, 3):
			for v in _cols.get(c + Vector2i(dx, dz), PackedInt32Array()):
				if nmv[v] >= 0 or absf(ny[v] - y) > 0.08:
					continue
				var dd := Vector2(nx[v] - x, nz[v] - z).length_squared()
				if dd < bd:
					bd = dd
					best = v
	return best


# ---------------------------------------------------------------- 跳ぶ

## 高さの差 dh（上が正）の所へ、水平の速さ v で届く距離（届かなければ -1）
func reach(dh: float, v: float) -> float:
	if dh > jump_top - 0.05:
		return -1.0
	var tp := v_jump / g_up
	return v * (tp + sqrt(2.0 * (jump_top - dh) / g_down))


## 「安全に」跳べる段・溝（30_レベルデザイン設計.md 1.2：段 1.8 m、溝は限界の約 0.77 倍＝通常 4.5 m／ダッシュ 7.0 m）
const SAFE_CLIMB := 1.8
const SAFE_FRAC := 0.77


## 跳んで a から b へ（弧の途中で体が形にめり込まない）。いくつかの弧の形を試す。safe なら「安全に」越えられる高さ・距離まで
func jump_ok(ax: float, ay: float, az: float, bx: float, by: float, bz: float, speed: float, safe := false) -> bool:
	var dh := by - ay
	var d := Vector2(bx - ax, bz - az).length()
	var rch := reach(dh, speed)
	if rch < 0.0 or d > rch:
		return false
	if safe and (dh > SAFE_CLIMB or d > rch * SAFE_FRAC):
		return false
	var tp := v_jump / g_up
	var tt := tp + sqrt(2.0 * (jump_top - dh) / g_down)
	for prof in ["late", "early", "linear"]:
		if _arc_clear(ax, ay, az, bx, bz, d, tt, tp, speed, prof):
			return true
	# 跳ばずに歩いて落ちる（天井が低い所）
	if dh < -0.4:
		var tf := sqrt(2.0 * -dh / g_down)
		if d <= speed * tf + 0.3 and _arc_clear(ax, ay, az, bx, bz, d, tf, 0.0, speed, "walk"):
			return true
	return false


func _arc_clear(ax: float, ay: float, az: float, bx: float, bz: float, d: float, tt: float, tp: float, speed: float, prof: String) -> bool:
	var n := maxi(4, ceili(tt * 40.0))
	var dirx := 0.0
	var dirz := 0.0
	if d > 1e-4:
		dirx = (bx - ax) / d
		dirz = (bz - az) / d
	for k in range(1, n):
		var t := tt * k / n
		var s := 0.0
		match prof:
			"late":
				s = maxf(0.0, d - speed * (tt - t))
			"early", "walk":
				s = minf(d, speed * t)
			_:
				s = d * t / tt
		var y := 0.0
		if prof == "walk":
			y = -0.5 * g_down * t * t
		elif t <= tp:
			y = v_jump * t - 0.5 * g_up * t * t
		else:
			y = jump_top - 0.5 * g_down * (t - tp) * (t - tp)
		if hits(ax + dirx * s, ay + y, az + dirz * s, FIT_ARC):
			return false
	return true


# ---------------------------------------------------------------- 全体

## 部屋を調べる。返り値は冒頭のとおり
func run() -> Dictionary:
	var t0 := Time.get_ticks_msec()
	_build_solids()
	_bounds()
	_build_nodes()
	_build_comps()
	var t1 := Time.get_ticks_msec()
	var t2 := Time.get_ticks_msec()
	_prep_jumps()
	var t3 := Time.get_ticks_msec()
	if opts.get("verbose", false):
		print("    node %d ms, drops %d ms, jumps %d ms" % [t1 - t0, t2 - t1, t3 - t2])
	var res := _judge()
	res["ms"] = {"nodes": t1 - t0, "drops": t2 - t1, "jumps": t3 - t2, "judge": Time.get_ticks_msec() - t3}
	return res


## 調べる範囲：目印・中継地点・出口から 40 m 以内の、形のある所（遠くの景色の箱は数えない）
func _bounds() -> void:
	var pts: Array = []
	for k in game.geometry.markers:
		pts.append(game.geometry.markers[k].pos)
	for c in game.checkpoints:
		pts.append(c.pos)
	for x in game.exits:
		pts.append(x.center)
	var mx0 := INF
	var mz0 := INF
	var mx1 := -INF
	var mz1 := -INF
	for p in pts:
		mx0 = minf(mx0, p.x)
		mz0 = minf(mz0, p.z)
		mx1 = maxf(mx1, p.x)
		mz1 = maxf(mz1, p.z)
	var sx0 := INF
	var sz0 := INF
	var sx1 := -INF
	var sz1 := -INF
	for i in _cx.size():
		var ex := absf(_hx[i] * _co[i]) + absf(_hz[i] * _si[i])
		var ez := absf(_hx[i] * _si[i]) + absf(_hz[i] * _co[i])
		sx0 = minf(sx0, _cx[i] - ex)
		sz0 = minf(sz0, _cz[i] - ez)
		sx1 = maxf(sx1, _cx[i] + ex)
		sz1 = maxf(sz1, _cz[i] + ez)
	_x0 = maxf(sx0, mx0 - 40.0)
	_z0 = maxf(sz0, mz0 - 40.0)
	_x1 = minf(sx1, mx1 + 40.0)
	_z1 = minf(sz1, mz1 + 40.0)


## 縁から歩いて落ちる道：隣の柱へ歩けない node から、その柱の上で落ちた先へ
## 縁から歩いて落ちる道（まとまり c の縁の node から）。行けるまとまりからだけ調べる（_judge の前へたどる所）
func _drops_from(c: int) -> void:
	for u in _cedge[c]:
		for di in 8:
			if _wmask[u] & (1 << di):
				continue
			var d: Vector2i = _N8[di]
			# 上れない段（BAD_STEP）は、下りる向きなら歩いて行ける
			for v in _cols.get(ncol[u] + d, PackedInt32Array()):
				if nmv[v] == nmv[u] and nmv[u] < 0 and _bad_step(ny[u] - ny[v]):
					_link(comp[u], comp[v], "drop", u, v)
			# 隣の柱の上（縁の外）へ出られるか。体が入らなければ、壁に触れるまで（短く）出る：
			# 壁と箱の間の細いすき間（体の太さより狭い）では、壁に触れた所が縁の外になる
			var dir := Vector2(d.x, d.y).normalized()
			var x := 0.0
			var z := 0.0
			var out := false
			for step in [CELL, 0.19, 0.13, 0.07]:
				x = nx[u] + dir.x * step
				z = nz[u] + dir.y * step
				if not hits(x, ny[u] + 0.02, z):
					out = true
					break
			if not out:
				continue
			var top := top_below(x, z, ny[u] + 0.02)
			if top > ny[u] - STEP - 0.01 and top > NO_TOP:
				continue
			var r := fall(x, ny[u], z)
			match r.kind:
				"void":
					to_void[comp[u]] = true
				"node":
					_link(comp[u], comp[r.id], "drop", u, r.id)
				"hang":
					hangs.append({"pos": r.pos, "from": Vector3(nx[u], ny[u], nz[u]), "comp": comp[u], "wedged": true})
			if r.get("slid", false):
				hangs.append({"pos": r.hang_pos, "from": Vector3(nx[u], ny[u], nz[u]), "comp": comp[u], "wedged": false})
			# 動く足場の上へも落ちられる（真下を通るとき）
			for v in _mover_nodes_below(x, z, ny[u]):
				_link(comp[u], comp[v], "drop", u, v)


func _mover_nodes_below(x: float, z: float, y: float) -> Array:
	var out: Array = []
	if movers.is_empty():
		return out
	var c := _key(x, z)
	for v in _cols.get(c, PackedInt32Array()):
		if nmv[v] >= 0 and ny[v] < y - 0.2 and _boardable(v):
			out.append(v)
	return out


## 動かない所から乗れる動く足場の点（乗ると動く足場は、止まっている位置＝時刻 0 だけ）
func _boardable(v: int) -> bool:
	if nmv[v] < 0:
		return true
	var mv: Dictionary = movers[nmv[v]]
	return mv.mode != "ride" or nmt[v] == 0


## 跳ぶ道。跳ぶ元・先は「縁の node」（歩いて行けない隣の柱がある、または隣の柱に別のまとまりの node がある）を、
## 0.5 m の升目・0.5 m の高さごとに 1 つずつ。行けるまとまりからだけ、まとまりごとに調べる（_jumps_from）。
## 先のまとまりごとに、元の 1 m 升目ごとの一番跳びやすい組を集め、跳びやすい順に JUMP_TRIES 組まで弧を確かめる
## （壁の向こうなど、跳べない組を何度も確かめないように）
const JUMP_TRIES := 8
var _csrc: Array = []
var _eg: Array = []
var _eg0 := Vector2i.ZERO
var _egw := 0
var _egh := 0
var _reach_max := 0.0


## node u では跳べない（跳ぶボタンが話す・調べるになる）
func _no_jump(u: int) -> bool:
	for t in _talkers:
		var p: Vector3 = t[0]
		if absf(p.y - ny[u]) <= 1.5 and Vector2(p.x - nx[u], p.z - nz[u]).length() <= float(t[1]):
			return true
	return false


func _prep_jumps() -> void:
	for n in game.npcs:
		_talkers.append([n.pos, n.range_m])
	for t in game.terminals:
		_talkers.append([t.pos, t.range_m])
	for b in game.beacons:
		_talkers.append([b.pos, b.range_m])
	for sw in game.switches:
		if sw.mode == "interact" and sw.toggle:
			_talkers.append([sw.pos, sw.range_m])
	_csrc.resize(ncomp)
	for i in ncomp:
		_csrc[i] = PackedInt32Array()
	_eg0 = Vector2i(floori(_x0 / HASH) - 1, floori(_z0 / HASH) - 1)
	_egw = floori(_x1 / HASH) + 2 - _eg0.x
	_egh = floori(_z1 / HASH) + 2 - _eg0.y
	_eg.resize(_egw * _egh)
	var seen := {}
	var seen_src := {}
	for u in nx.size():
		var c := ncol[u]
		var is_edge := _wmask[u] != 255
		if not is_edge:
			for d in _N8:
				for v in _cols.get(c + d, PackedInt32Array()):
					if comp[v] != comp[u]:
						is_edge = true
						break
				if is_edge:
					break
		if not is_edge:
			continue
		# 0.5 m の升目・0.5 m の高さごとに 1 つ。跳ぶ元にするのは跳べる所だけ（先にはどこでもなれる）
		var sk := Vector4i(comp[u], floori(nx[u] * 2.0), floori(nz[u] * 2.0), floori(ny[u] * 2.0))
		if not seen_src.has(sk) and not _no_jump(u):
			seen_src[sk] = true
			_csrc[comp[u]].append(u)
		if seen.has(sk):
			continue
		seen[sk] = true
		var gi := (floori(nx[u] / HASH) - _eg0.x) * _egh + (floori(nz[u] / HASH) - _eg0.y)
		if gi < 0 or gi >= _eg.size():
			continue
		if _eg[gi] == null:
			_eg[gi] = {}
		var cell: Dictionary = _eg[gi]
		var cu := comp[u]
		if not cell.has(cu):
			cell[cu] = [ny[u], PackedInt32Array()]
		var ent: Array = cell[cu]
		ent[0] = minf(ent[0], ny[u])
		var arr: PackedInt32Array = ent[1]
		arr.append(u)
		ent[1] = arr
	var speed := dash_speed if dash else run_speed
	# 下へ跳ぶときも、同じ高さへ跳ぶ距離まで（もっと遠くへ落ちる道は、縁から歩いて落ちる道で足りる）
	_reach_max = minf(SEARCH, reach(0.0, speed) + 0.3)


func _jumps_from(cu: int) -> void:
	var speed := dash_speed if dash else run_speed
	var span := ceili(_reach_max / HASH)
	var rr := _reach_max * _reach_max
	# 先のまとまり → { 元の升目: [跳びやすさ, u, v] }
	var cand := {}
	for u in _csrc[cu]:
		var ux := nx[u]
		var uy := ny[u]
		var uz := nz[u]
		var hx := floori(ux / HASH)
		var hz := floori(uz / HASH)
		var hkey := hx * 4096 + hz
		for gx in range(maxi(hx - span, _eg0.x), mini(hx + span + 1, _eg0.x + _egw)):
			var cdx := maxf(maxf(gx * HASH - ux, ux - (gx + 1) * HASH), 0.0)
			var row := (gx - _eg0.x) * _egh
			for gz in range(maxi(hz - span, _eg0.y), mini(hz + span + 1, _eg0.y + _egh)):
				var cell = _eg[row + gz - _eg0.y]
				if cell == null:
					continue
				var cdz := maxf(maxf(gz * HASH - uz, uz - (gz + 1) * HASH), 0.0)
				if cdx * cdx + cdz * cdz > rr:
					continue
				for cv in cell:
					if cv == cu:
						continue
					var ent: Array = cell[cv]
					if float(ent[0]) - uy > jump_top:
						continue
					var per: Dictionary = cand.get(cv, {})
					var best: Array = per.get(hkey, [INF, -1, -1])
					var changed := false
					for v in (ent[1] as PackedInt32Array):
						var dh := ny[v] - uy
						if dh > jump_top or dh < -12.0:
							continue
						var rch := minf(reach(dh, speed), _reach_max)
						if rch <= 0.0:
							continue
						var d := Vector2(nx[v] - ux, nz[v] - uz).length()
						if d > rch:
							continue
						# 跳びやすさ：届く距離に対する割合と、上る高さ
						var score := d / rch + maxf(dh, 0.0) * 0.2
						if score < best[0] and _boardable(v):
							best = [score, u, v]
							changed = true
					if changed:
						per[hkey] = best
						cand[cv] = per
	var linked: Dictionary = cedges[cu]
	for cv in cand:
		if linked.has(cv):
			continue
		var lst: Array = cand[cv].values()
		lst.sort_custom(func(a, b): return a[0] < b[0])
		var n := 0
		var hard := []
		for e in lst:
			var u: int = e[1]
			var v: int = e[2]
			# 安全に跳べる組を探す。限界でだけ跳べる組は「hard」
			if _jump_any(u, v, speed, true):
				_link(cu, cv, "jump", u, v)
				break
			if hard.is_empty() and _jump_any(u, v, speed, false):
				hard = [u, v]
			n += 1
			if n >= JUMP_TRIES:
				break
		if not hard.is_empty() and not linked.has(cv):
			_link(cu, cv, "hard", hard[0], hard[1])


func _jump_any(u: int, v: int, speed: float, safe: bool) -> bool:
	if jump_ok(nx[u], ny[u], nz[u], nx[v], ny[v], nz[v], speed, safe):
		return true
	return speed > run_speed and jump_ok(nx[u], ny[u], nz[u], nx[v], ny[v], nz[v], run_speed, safe)


## 行ける所・戻れる所を調べて、詰みを集める
func _judge() -> Dictionary:
	# 始まり：目印・中継地点
	var starts: Array = []
	for k in game.geometry.markers:
		starts.append(game.geometry.markers[k].pos)
	for c in game.checkpoints:
		starts.append(c.pos)
	var start_comps := {}
	for p in starts:
		var id := _node_near(p.x, top_below(p.x, p.z, p.y + 0.4), p.z)
		if id >= 0:
			start_comps[comp[id]] = true
	# 行き先：出口の中、目印・中継地点のまわり 1 m
	var goal := PackedByteArray()
	goal.resize(ncomp)
	for u in nx.size():
		var p := Vector3(nx[u], ny[u], nz[u])
		for x in game.exits:
			if x.contains(p):
				goal[comp[u]] = 1
		for s in starts:
			if absf(p.y - s.y) < 0.6 and Vector2(p.x - s.x, p.z - s.z).length() < 1.0:
				goal[comp[u]] = 1
	# 前へ：始まりから行けるまとまり
	var fwd := PackedByteArray()
	fwd.resize(ncomp)
	var q: Array = start_comps.keys()
	for c in q:
		fwd[c] = 1
	var qi := 0
	var tj := Time.get_ticks_msec()
	while qi < q.size():
		var c: int = q[qi]
		qi += 1
		_drops_from(c)
		_jumps_from(c)
		for b in cedges[c]:
			if fwd[b] == 0:
				fwd[b] = 1
				_prev[b] = c
				q.append(b)
	if opts.get("verbose", false):
		print("    jumps from %d reached groups: %d ms" % [q.size(), Time.get_ticks_msec() - tj])
	_fwd = fwd
	# 奈落へ落ちられるまとまり（前へたどる間に、縁から落ちる道で見つかる）も行き先
	for c in to_void:
		goal[c] = 1
	# 後ろへ：行き先へ行けるまとまり
	var rev: Array = []
	rev.resize(ncomp)
	for i in ncomp:
		rev[i] = []
	for a in ncomp:
		if fwd[a] == 0:
			continue
		for b in cedges[a]:
			rev[b].append([a, cedges[a][b]])
	var ok := _back(goal, rev, false)
	var ok_safe := _back(goal, rev, true)
	# 詰み：行けるのに戻れないまとまり。hard：限界の跳びでだけ戻れるまとまり
	var stuck: Array = _collect(fwd, ok)
	var hard_out: Array = []
	var ok_or := PackedByteArray()
	ok_or.resize(ncomp)
	for i in ncomp:
		ok_or[i] = 1 if ok_safe[i] == 1 or ok[i] == 0 else 0
	hard_out = _collect(fwd, ok_or)
	var hang_out: Array = []
	for hg in hangs:
		if fwd[hg.comp] == 1:
			hang_out.append(hg)
	return {"stuck": stuck, "hard": hard_out, "hangs": hang_out, "nodes": nx.size(), "comps": ncomp, "starts": start_comps.size(),
		"reached": Array(fwd).count(1)}


## 行き先へ戻れるまとまり（後ろへたどる）。safe なら限界の跳び（hard）を使わない
func _back(goal: PackedByteArray, rev: Array, safe: bool) -> PackedByteArray:
	var ok := PackedByteArray()
	ok.resize(ncomp)
	var q2: Array = []
	for i in ncomp:
		if goal[i] == 1:
			ok[i] = 1
			q2.append(i)
	var qi := 0
	while qi < q2.size():
		var c: int = q2[qi]
		qi += 1
		for e in rev[c]:
			if safe and e[1] == "hard":
				continue
			if ok[e[0]] == 0:
				ok[e[0]] = 1
				q2.append(e[0])
	return ok


## 始まりから位置 p（の近くの node）のまとまりまで、どうたどったか（説明用。run の後に呼ぶ）
func explain(p: Vector3) -> Array:
	var id := _node_near(p.x, p.y, p.z)
	if id < 0:
		return ["node が無い"]
	var out: Array = []
	var c := comp[id]
	if _fwd.is_empty() or _fwd[c] == 0:
		return ["まとまり %d（%.2f, %.2f, %.2f）は始まりから行けない" % [c, nx[id], ny[id], nz[id]]]
	var guard := 0
	while _prev.has(c) and guard < 200:
		guard += 1
		var a: int = _prev[c]
		var via: Array = _via.get(Vector2i(a, c), [-1, -1])
		var u: int = via[0]
		var v: int = via[1]
		var s := "%s → まとまり %d" % [cedges[a][c], c]
		if u >= 0 and v >= 0:
			s += "：(%.2f, %.2f, %.2f) から (%.2f, %.2f, %.2f) へ" % [nx[u], ny[u], nz[u], nx[v], ny[v], nz[v]]
		out.push_front(s)
		c = a
	out.push_front("始まりのまとまり %d" % c)
	return out


## 行ける（fwd）のに ok でないまとまりの一覧
func _collect(fwd: PackedByteArray, ok: PackedByteArray) -> Array:
	var info := {}
	for u in nx.size():
		var c := comp[u]
		if fwd[c] == 0 or ok[c] == 1:
			continue
		if not info.has(c):
			info[c] = {"comp": c, "nodes": 0, "y0": INF, "y1": -INF, "box": [INF, INF, -INF, -INF], "pos": Vector3(nx[u], ny[u], nz[u]), "mover": nmv[u]}
		var e: Dictionary = info[c]
		e.nodes += 1
		e.y0 = minf(e.y0, ny[u])
		e.y1 = maxf(e.y1, ny[u])
		e.box = [minf(e.box[0], nx[u]), minf(e.box[1], nz[u]), maxf(e.box[2], nx[u]), maxf(e.box[3], nz[u])]
	var out: Array = info.values()
	out.sort_custom(func(a, b): return a.nodes > b.nodes)
	return out
