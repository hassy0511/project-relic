class_name AmbientFx
extends RefCounted
## 部屋の飾りの小さなエフェクト：落砂が床に着く所の砂ぼこり（dust）と、蒸気の吹き出し（steam。数秒ごとに強く吹いて、上がりながら消える）。
## 出所はキットの "emitters"（部品 → 出し方）と部屋の "dress"（RoomKit.emitters。docs/design/42_コンテンツの書き方.md 14.2.2）。
## 粒は Vfx の今ある層（DUST・SMOKE。普通の半透明、マスクは W2-09 の粒子の素材）で描く：部屋に出所があるときだけ、その層の描画が 1 回ずつ。
## 見た目だけ：ゲームの中身（GameSim）は読まない・変えない。時刻は Fx の刻み（見た目の時計、dt の和）、乱数は自分の RandomNumberGenerator
## （部屋ごとに決まった種。Fx の乱数の並びを変えないので、ほかのエフェクトは前と同じ）。Fx.sync が毎刻み step を呼ぶ。

## 砂ぼこり・蒸気の色（砂は遺構の材質 sand の明るい面の色、蒸気は白っぽい灰色）
const DUST_COLOR := Color("#d9b892")
const STEAM_COLOR := Color("#ece6dc")
## オルドの足音で布から落ちる砂ぼこり（蒸気と見分けがつくよう、落砂より濃く赤みのある砂の色。粒の層は光を受けず、色をそのまま
## 線形の値として描くので、sRGB から直して渡す：直さないと白っぽい湯気の色に見えた）
const STEP_DUST_COLOR := Color("#c49a68")
## スマホ・ブラウザ版の描き方（gl_compatibility）だけの足音の砂ぼこりの整え（残課題 T10）：この描き方では粒の色が暗く薄く出て、
## 日よけの裏の暗い布の前でほとんど見えなかった。砂の色を sRGB のまま渡し、濃さ・砂ぼこりの大きさ・砂粒の数を少し上げる（PC は変えない）
const COMPAT_STEP_DUST := {"alpha": 1.35, "size": 1.25, "grains": 1.4}
## 1 部屋の出所の上限（多すぎる部屋でも粒が増えすぎないように）
const MAX_SOURCES := 16

var room_id := ""
var sources: Array = []
## 足音の砂ぼこりの描き方：-1 = 今の描き方に従う、0 = PC（Forward+）、1 = スマホ・ブラウザ版（gl_compatibility）。
## 確かめ（headless は Forward+ の扱い）でスマホの側の整えを確かめるためのもの
var dust_compat := -1
var _rng := RandomNumberGenerator.new()
var _t := 0.0
## オルドの足音（OrdoSteps）で砂ぼこりの落ちる所：部屋の飾りの、揺れる布（日よけ・洗濯物・垂れ幕）の下の端（ワールド）
var puffs := PackedVector3Array()
## 足音の砂ぼこり・こぼれる砂の乱数（落砂・蒸気の並びを変えない）
var _srng := RandomNumberGenerator.new()


## 部屋の出所を作り直す（部屋が変わったとき）。room_id は乱数の種にも使う（同じ部屋なら同じ並び）
func build(id: String, room: Dictionary) -> void:
	room_id = id
	_t = 0.0
	_rng.seed = hash(id) & 0x7fffffff
	sources.clear()
	puffs = OrdoSteps.puff_points(room)
	_srng.seed = (hash(id) + 77) & 0x7fffffff
	if not room.has("kit") or not room.has("dress"):
		return
	var kit := RoomKit.load_kit(String(room.kit))
	for e in RoomKit.emitters(room, kit):
		if sources.size() >= MAX_SOURCES:
			break
		var ev: Vector2 = e.every
		# 最初の吹き出しは出所ごとにずらす（同じ部屋の蒸気がそろって吹かない）。部屋に入ってすぐ見えるよう、最初だけ早め
		e["next"] = _rng.randf_range(0.2, clampf(ev.x * 0.6, 0.3, 2.2))
		e["burst"] = 0
		sources.append(e)


## 1 刻み進めて、時刻が来た出所から粒を出す
func step(dt: float, vfx: Vfx) -> void:
	if sources.is_empty() or vfx == null:
		return
	_t += dt
	for s in sources:
		if String(s.kind) == "steam":
			# 強い吹き出しは、数刻みに分けて粒を出す（一度に出すと 1 つの塊に見えた）
			if int(s.burst) > 0 and _t >= float(s.get("burst_at", 0.0)):
				_steam_puff(vfx, s, true)
				s.burst = int(s.burst) - 1
				s["burst_at"] = _t + 0.11
			# 合間は細い蒸気をときどき
			elif _t >= float(s.get("trickle", 0.0)):
				_steam_puff(vfx, s, false)
				s["trickle"] = _t + _rng.randf_range(0.55, 0.9)
		if _t < float(s.next):
			continue
		var ev: Vector2 = s.every
		s.next = _t + _rng.randf_range(ev.x, ev.y)
		match String(s.kind):
			"dust":
				_dust(vfx, s)
			"steam":
				s.burst = _rng.randi_range(4, 6)
				s["burst_at"] = _t


## 落砂の着く所：小さな砂ぼこりが横へ広がってゆっくり消える（大きさ 0.1 → 0.4 m、1.0〜1.6 秒）
func _dust(vfx: Vfx, s: Dictionary) -> void:
	var sc: float = s.scale
	for i in _rng.randi_range(1, 2):
		var a := _rng.randf() * TAU
		var out := Vector3(sin(a), 0.0, cos(a))
		var q := vfx.emit(Vfx.DUST, s.at + out * 0.08 * sc + Vector3(0, 0.02, 0),
			out * _rng.randf_range(0.18, 0.4) * sc + Vector3(0, _rng.randf_range(0.12, 0.28), 0),
			_rng.randf_range(1.0, 1.6), 0.12 * sc, _rng.randf_range(0.38, 0.55) * sc, Color(DUST_COLOR, _rng.randf_range(0.36, 0.5)))
		q.rot = _rng.randf() * TAU
		q.spin = _rng.randf_range(-0.5, 0.5)
		q.drag = 1.6
		q.fin = 0.18
		q.fpow = 1.4
		q.grav = 0.05


## 蒸気の粒：吹き出し口から向き dir へ出て、上がりながら広がって消える（強い吹き出しは速く大きく、合間は弱く）
func _steam_puff(vfx: Vfx, s: Dictionary, strong: bool) -> void:
	var sc: float = s.scale
	var dir: Vector3 = s.dir
	var side := dir.cross(Vector3.UP)
	if side.length() < 0.1:
		side = Vector3.RIGHT
	side = side.normalized()
	var up := side.cross(dir).normalized()
	var jitter := side * _rng.randf_range(-0.25, 0.25) + up * _rng.randf_range(-0.25, 0.25)
	var speed := (_rng.randf_range(1.0, 1.6) if strong else _rng.randf_range(0.45, 0.7)) * sc
	var q := vfx.emit(Vfx.SMOKE, s.at + dir * 0.12 * sc, (dir + jitter * 0.6) * speed + Vector3(0, 0.15, 0),
		_rng.randf_range(1.6, 2.3) if strong else _rng.randf_range(1.0, 1.5),
		(0.22 if strong else 0.14) * sc, (_rng.randf_range(0.9, 1.25) if strong else 0.55) * sc,
		Color(STEAM_COLOR, _rng.randf_range(0.26, 0.34) if strong else 0.14))
	q.rot = _rng.randf() * TAU
	q.spin = _rng.randf_range(-0.4, 0.4)
	q.drag = 1.1
	q.grav = -0.45      # 上がる
	q.fin = 0.12
	q.fpow = 1.2


## 今の出所の数（確認用）
func count() -> int:
	return sources.size()


## 確かめの撮影用（scripts/debug/motion_shots.gd）：どの蒸気も delay 秒後に強く吹き出す
func burst_soon(delay: float) -> void:
	for s in sources:
		if String(s.kind) == "steam":
			s.next = _t + delay


# ---------------------------------------------------------------- オルドの足音（OrdoSteps が足の着くたびに呼ぶ）

## 屋外：カメラ（cam）の前・25 m 以内の、揺れる布の下の端から n か所選び、砂が落ちる：細かい砂粒が筋になって落ち、
## 小さな砂ぼこりが少し広がりながら下へ流れて消える（湯気・煙のように漂って上がらない）。
## strength：場所の揺れの何倍か（近い脚の組・重い 1 歩ほど大きい。1 が場所のふだん）。light：明るさ（昼 1。夜・停電は暗く）。
## 選ぶのは近いもの 2n か所の中から（遠くの小さな砂ぼこりは見えないので、見える近くに出す）。粒の大きさはカメラまでの距離の 1/4 まで
## （すぐ近くで画面を覆わない。スマホの描く量も増やさない）
func step_puffs(vfx: Vfx, cam: Vector3, fwd: Vector3, n: int, strength := 1.0, light := 1.0) -> int:
	if puffs.is_empty() or vfx == null:
		return 0
	var near: Array = []
	for p in puffs:
		var d := p - cam
		var l := d.length()
		if l < 2.0 or l > 25.0 or d.dot(fwd) < 0.5 * l:
			continue
		near.append([l, p])
	near.sort_custom(func(a, b): return a[0] < b[0])
	near = near.slice(0, 2 * n)
	var big := clampf(0.55 + 0.45 * strength, 0.75, 1.5)
	var dense := clampf(0.75 + 0.25 * strength, 0.8, 1.25)
	var compat := EnvironmentSetup.is_compat() if dust_compat < 0 else dust_compat == 1
	var col := STEP_DUST_COLOR if compat else STEP_DUST_COLOR.srgb_to_linear()
	col = Color(col.r * light, col.g * light, col.b * light)
	var ka: float = COMPAT_STEP_DUST.alpha if compat else 1.0
	var ks: float = COMPAT_STEP_DUST.size if compat else 1.0
	var kg: float = COMPAT_STEP_DUST.grains if compat else 1.0
	var made := 0
	for k in mini(n, near.size()):
		var i := _srng.randi_range(0, near.size() - 1)
		var cap := float(near[i][0]) * 0.25
		var at: Vector3 = near[i][1]
		near.remove_at(i)
		# 砂粒の筋（布の縁から細かい粒が落ちる）
		for j in int(round(_srng.randi_range(6, 8) * dense * kg)):
			var g := vfx.emit(Vfx.DOT, at + Vector3(_srng.randf_range(-0.25, 0.25), -_srng.randf_range(0.0, 0.1), _srng.randf_range(-0.25, 0.25)),
				Vector3(0, -_srng.randf_range(0.3, 0.8), 0), _srng.randf_range(1.0, 1.5), 0.05 * ks, 0.07 * ks,
				Color(col, minf(_srng.randf_range(0.75, 0.95) * ka, 1.0)))
			g.grav = 2.4
			g.drag = 0.5
			g.fin = 0.1
			g.fpow = 1.6
		# 小さな砂ぼこり（下へ流れながら少し広がる）
		for j in 3:
			var a := _srng.randf() * TAU
			var out := Vector3(sin(a), 0.0, cos(a))
			var q := vfx.emit(Vfx.DUST, at + out * 0.12 + Vector3(0, -0.1, 0),
				out * _srng.randf_range(0.08, 0.2) + Vector3(0, -_srng.randf_range(0.3, 0.6), 0),
				_srng.randf_range(1.2, 1.6), 0.12, minf(_srng.randf_range(0.38, 0.55) * big * ks, cap),
				Color(col, minf(_srng.randf_range(0.5, 0.65) * dense * ka, 0.95)))
			q.rot = _srng.randf() * TAU
			q.spin = _srng.randf_range(-0.4, 0.4)
			q.drag = 1.0
			q.fin = 0.15
			q.fpow = 1.3
			q.grav = 0.7
		made += 1
	return made


## 屋内・遺構：ハル（at）の前・まわりの天井（高さ top）の n か所から、細い砂がこぼれる（細かい粒が数個ずつ落ちて消える）
func step_sift(vfx: Vfx, at: Vector3, fwd: Vector3, top: float, n: int) -> int:
	if vfx == null:
		return 0
	var side := Vector3(-fwd.z, 0.0, fwd.x)
	for k in n:
		var p := at + fwd * _srng.randf_range(1.5, 4.5) + side * _srng.randf_range(-3.0, 3.0)
		p.y = top - 0.05
		var grains := _srng.randi_range(5, 8)
		for j in grains:
			var q := vfx.emit(Vfx.DOT, p + Vector3(_srng.randf_range(-0.12, 0.12), -_srng.randf_range(0.0, 0.25), _srng.randf_range(-0.12, 0.12)),
				Vector3(0, -_srng.randf_range(0.2, 0.6), 0), _srng.randf_range(1.6, 2.4), 0.045, 0.08,
				Color(DUST_COLOR, _srng.randf_range(0.55, 0.8)))
			q.grav = 2.2
			q.drag = 0.6
			q.fin = 0.12
			q.fpow = 1.6
		# 細い砂の筋のかすみ（大きくやわらかい粒 1 つ）
		var h := vfx.emit(Vfx.DUST, p + Vector3(0, -0.3, 0), Vector3(0, -0.35, 0), 2.0, 0.08, 0.35, Color(DUST_COLOR, 0.22))
		h.grav = 0.1
		h.drag = 0.8
		h.fin = 0.2
	return n
