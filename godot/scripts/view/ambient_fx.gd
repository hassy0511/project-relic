class_name AmbientFx
extends RefCounted
## 部屋の飾りの小さなエフェクト：落砂が床に着く所の砂ぼこり（dust）と、蒸気の吹き出し（steam。数秒ごとに強く吹いて、上がりながら消える）。
## 出所はキットの "emitters"（部品 → 出し方）と部屋の "dress"（RoomKit.emitters。docs/design/42_コンテンツの書き方.md 14.2.2）。
## 粒は Vfx の今ある層（DUST・SMOKE。普通の半透明、マスクは W2-09 の粒子の素材）で描く：部屋に出所があるときだけ、その層の描画が 1 回ずつ。
## 見た目だけ：ゲームの中身（GameSim）は読まない・変えない。時刻は Fx の刻み（見た目の時計、dt の和）、乱数は自分の RandomNumberGenerator
## （部屋ごとに決まった種。Fx の乱数の並びを変えないので、ほかのエフェクトは前と同じ）。Fx.sync が毎刻み step を呼ぶ。

## 砂ぼこり・蒸気の色（砂は遺構の材質 sand の明るい面の色、蒸気は白っぽい灰色）
const DUST_COLOR := Color("#c99a6e")
const STEAM_COLOR := Color("#ece6dc")
## 1 部屋の出所の上限（多すぎる部屋でも粒が増えすぎないように）
const MAX_SOURCES := 16

var room_id := ""
var sources: Array = []
var _rng := RandomNumberGenerator.new()
var _t := 0.0


## 部屋の出所を作り直す（部屋が変わったとき）。room_id は乱数の種にも使う（同じ部屋なら同じ並び）
func build(id: String, room: Dictionary) -> void:
	room_id = id
	_t = 0.0
	_rng.seed = hash(id) & 0x7fffffff
	sources.clear()
	if not room.has("kit") or not room.has("dress"):
		return
	var kit := RoomKit.load_kit(String(room.kit))
	for e in RoomKit.emitters(room, kit):
		if sources.size() >= MAX_SOURCES:
			break
		var ev: Vector2 = e.every
		# 最初の吹き出しは出所ごとにずらす（同じ部屋の蒸気がそろって吹かない）
		e["next"] = _rng.randf_range(0.2, maxf(ev.y, 0.3))
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
			_rng.randf_range(1.0, 1.6), 0.1 * sc, _rng.randf_range(0.32, 0.48) * sc, Color(DUST_COLOR, _rng.randf_range(0.3, 0.42)))
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
