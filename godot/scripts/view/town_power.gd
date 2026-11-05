class_name TownPower
extends Node
## 町の電気の見た目（停電の夜。docs/design/42_コンテンツの書き方.md 14.8、30_レベルデザイン設計.md の第 1 章の夜）。
## 正本はゲームの中身の GameSim.powered()（部屋の "grid" と world.json の "power" の条件。フラグだけから決まるので、セーブから戻しても・
## 場面をスキップしても同じ）。ここは見た目だけで、ゲームの中身は読むだけ：
##   ・電気の灯（部屋の明かり・飾りの明かりの "source": "electric"、キットの材質の "source": "electric"）を消す・点ける
##   ・油の灯（"source": "oil"）は灯ったまま、ゆっくり揺らぐ（本物の光の明るさと、にじみ・床の輪の安い光 make_glows）
##   ・停電の間だけの物（"blackout": true の明かり・飾り）は、部屋を作るときに電気が切れていれば置く（begin_room → RoomView.build）
##   ・空と光：キットの "light" の "<雰囲気>_blackout"（停電の夜）・"interior_night"（夜の屋内）を選ぶ（light_for。main._apply_mood）。
##     波の間は、電気のある光と停電の光を波の進み（level_now）で混ぜて、毎こま入れる（main._apply_light。消えた直後に青い光へ跳ねない）
##   ・変わり目：部屋にいる間に電気が切れたら、灯がちらついて消える（約 1 秒。停止の場面の終わり、ハルの家）。再始動（町の外で電気が戻る）
##     のあとは、町の部屋に戻っても消えたままにして、歓声の合図（fx: town_power_on）で原点から波のように点いていく（ちらつきつき）。
##     スキップ（skipped・合図の skipped）は、すぐ終わりの姿
## 町の遠景（オルドの背の町の窓・灯）は level_now() で消し・点ける（_sync_back_windows）。オルドの琥珀の灯は set_amber で非常灯の明るさに。
## 灯ごとのばらつきの乱数（seed_hash）は、部品 1 つの置き場所から決める（材質 kit_surface.gdshaderinc の v_power_h と同じ。灯の芯と光が一緒に点く）。
## 画面なしのテストでは材質の値を読み返せないので、最後に入れた値を last_params に持つ

const GLOW_SHADER := preload("res://assets/shaders/oil_glow.gdshader")
## 波（点く・消える）の既定：進む速さの下限（m/秒）、灯ごとのばらつき（秒）、波にかける秒（いちばん遠い灯まで）
const WAVE_MIN_SPEED := 8.0
const WAVE_SPREAD := 0.8
const WAVE_TIME := 2.2
## 部屋にいる間に電気が切れたとき：灯がちらついて消えるまでの秒（ばらつき）。波の速さはとても速く（ほぼ同時）
const OUT_SPREAD := 0.9
## ちらつく長さ（秒。シェーダーの power_k と同じ）
const FLICKER := 0.5
## 電気が切れている間のオルドの琥珀の灯の明るさ（停止の場面の終わりと同じ非常灯）
const ORDO_EMERGENCY := 0.3
## 再始動の波の間の、遠景の窓のちらつき（0〜1。OrdoView.set_back_lights）
const BACK_FLICKER := 0.35

var main
## 電気の灯の明るさ（波の無いとき。0 = 消えている、1 = 点いている）と、今の部屋を暗く（停電の物を置いて）作ったか
var level := 1.0
var built_dark := false
## 波：向き（1 点いていく・-1 消えていく・0 なし）、始めてからの秒、原点（ワールド）、速さ（m/秒）、ばらつき（秒）、終わる秒
var wave_dir := 0
var wave_t := 0.0
var wave_origin := Vector3.ZERO
var wave_speed := 14.0
var wave_spread := WAVE_SPREAD
var wave_end := 0.0
## 電気の網ごとの「町の外で電気が戻って、まだ見せていない」（再始動のあと、歓声の合図を待つ）
var pending := {}
## 最後に電気の材質へ入れた値（テスト用。power_state・power_origin）
var last_params := {}
## 今の部屋の明かり：[Light3D, 元の明るさ, 出所, 乱数 0〜1（電気：点く・消える時のばらつき、油：揺らぎの位相）]
var _lights: Array = []
## 今の部屋の電気の材質を使う部品の置き場所（ワールド）と広がり（AABB。波がいちばん遠い窓まで届くように）
var _seeds := PackedVector3Array()
var _boxes: Array = []
var _game: GameSim = null
## 今描いている部屋の電気の網（begin_room で覚える。フラグと部屋の移動が同じ刻みに来ても、描いている部屋で決める）
var _grid := ""
var _was_on := {}
## 前のこまに場面（CineDirector）の途中だったか（場面が終わったら、場面が触った遠景の窓・部屋の明かりを町の電気の値に戻す）
var _cine_was := false
## 油の灯の揺らぎの時計（秒）。シェーダーの TIME と同じく、エンジンを始めてからの秒（こまの秒を足していく。1 時間で巻き戻る）
var _time := fmod(Time.get_ticks_msec() * 0.001, 3600.0)


func _init(m = null) -> void:
	main = m
	name = "TownPower"


# ---------------------------------------------------------------- 部屋を作るとき

## 部屋を作る前に呼ぶ：この部屋を暗く作るか（電気の網があり、電気が切れているか、戻ったのをまだ見せていない）。
## 波を止め、灯の明るさをその状態にする。新しいゲーム（セーブから・はじめから）になったら、見せていない分を忘れる
func begin_room(game: GameSim) -> bool:
	if game != _game:
		_game = game
		pending.clear()
		_was_on.clear()
	_remember(game)
	_grid = String(game.room.get("grid", ""))
	wave_dir = 0
	wave_t = 0.0
	built_dark = dark_at_build(game)
	level = 0.0 if built_dark else 1.0
	return built_dark


## 部屋を暗く作るか（begin_room の中身。電気の網のある部屋だけ）
func dark_at_build(game: GameSim) -> bool:
	var grid := String(game.room.get("grid", ""))
	if grid == "":
		return false
	return not game.grid_powered(grid) or pending.get(grid, false)


## 部屋を作ったあと：電気の材質の部品と明かりを集めて、今の状態を入れる。
## 電気の明かりの乱数は、飾りの部品の明かりならその部品の置き場所（メタ "power_at"）、部屋の明かりなら 6 m 以内のいちばん近い
## 電気の部品の置き場所（家の天井の灯なら家の部品）から。油の明かりは、にじみ（make_glows）と同じ自分の位置の升から
func room_built(root: Node) -> void:
	_lights.clear()
	_seeds = PackedVector3Array()
	_boxes.clear()
	if root != null:
		_collect_electric(root)
		for l in root.find_children("*", "Light3D", true, false):
			if not l.has_meta("source"):
				continue
			var src := String(l.get_meta("source"))
			var p := _pos(l)
			var seed := p
			if src == "electric":
				if l.has_meta("power_at"):
					var par = l.get_parent()
					seed = (_xform(par) if par is Node3D else Transform3D.IDENTITY) * (l.get_meta("power_at") as Vector3)
				else:
					seed = _nearest_seed(p, 6.0)
			_lights.append([l, float(l.get_meta("energy", l.light_energy)), src, seed_hash(seed)])
	_apply()


## 電気の材質（キットの "source": "electric"）を使う部品・面の、置き場所（MultiMesh なら 1 粒ずつ）と広がり
func _collect_electric(root: Node) -> void:
	for gi in root.find_children("*", "GeometryInstance3D", true, false):
		var mesh: Mesh = null
		if gi is MeshInstance3D:
			mesh = gi.mesh
		elif gi is MultiMeshInstance3D and gi.multimesh != null:
			mesh = gi.multimesh.mesh
		if mesh == null or not (_is_electric(gi.material_override) or _mesh_electric(mesh)):
			continue
		var xf := _xform(gi)
		if gi is MultiMeshInstance3D:
			var mm: MultiMesh = gi.multimesh
			for i in mm.instance_count:
				var ixf := xf * mm.get_instance_transform(i)
				_seeds.append(ixf.origin)
				_boxes.append(ixf * mesh.get_aabb())
		else:
			_seeds.append(xf.origin)
			_boxes.append(xf * mesh.get_aabb())


static func _is_electric(m: Material) -> bool:
	return m is ShaderMaterial and String(m.get_meta("source", "")) == "electric"


static func _mesh_electric(mesh: Mesh) -> bool:
	for i in mesh.get_surface_count():
		if _is_electric(mesh.surface_get_material(i)):
			return true
	return false


## p から max_d 以内のいちばん近い電気の部品の置き場所（無ければ p）
func _nearest_seed(p: Vector3, max_d: float) -> Vector3:
	var best := p
	var bd := max_d
	for s in _seeds:
		var d := s.distance_to(p)
		if d <= bd:
			bd = d
			best = s
	return best


## 灯ごとの乱数 0〜1：位置の 2 m の升から（kit_surface.gdshaderinc の power_hash・oil_glow の位相と同じ式）
static func seed_hash(p: Vector3) -> float:
	return fposmod(sin(Vector3(floor(p.x * 0.5), floor(p.y * 0.5), floor(p.z * 0.5)).dot(Vector3(12.9898, 78.233, 37.719))) * 43758.5453, 1.0)


## キットの "light" の表から、今の部屋・雰囲気の空と光の上書きを選ぶ（main._apply_mood）：
## 停電の夜は "<雰囲気>_blackout"、夜の屋内は "interior_night"。表に無ければ雰囲気そのものの項目（前と同じ）。
## 波の間は、電気のある光と停電の光を波の進み level_now() で混ぜる（blend_light。消える波は電気のある光から少しずつ停電の光へ、
## 点く波はその逆。波の終わりの _set_steady の main._apply_mood と同じ値で終わるので、跳ねない）。
## スマホ・ブラウザ版の描き方だけの値（項目の "compat"）は EnvironmentSetup.resolve_light で重ねてから混ぜる
func light_for(game: GameSim, mood: String, table: Dictionary) -> Dictionary:
	var key := light_key(game, mood)
	var cur: Dictionary = EnvironmentSetup.resolve_light(table.get(key, table.get(mood, {})))
	var dark_key := mood + "_blackout"
	if wave_dir == 0 or _grid == "" or game == null or not table.has(dark_key):
		return cur
	var lit_key := _lit_key(game, mood)
	var lit: Dictionary = EnvironmentSetup.resolve_light(table.get(lit_key, table.get(mood, {})))
	return blend_light(EnvironmentSetup.resolve_light(table[dark_key]), lit, level_now())


## light_for の項目の名前
func light_key(game: GameSim, mood: String) -> String:
	if game == null:
		return mood
	if _grid != "" and dark():
		return mood + "_blackout"
	return _lit_key(game, mood)


## 電気のあるときの項目の名前（夜の屋内は interior_night）
func _lit_key(game: GameSim, mood: String) -> String:
	if mood == "interior" and game.flag("ch1.night"):
		return "interior_night"
	return mood


## 光の上書き 2 つを t（0 = a、1 = b）で混ぜる：数は直線で、色（"#…" か Color）は色で。片方にしか無い項目は、ある方の値のまま
static func blend_light(a: Dictionary, b: Dictionary, t: float) -> Dictionary:
	var out := {}
	for k in a:
		out[k] = a[k]
	for k in b:
		if not out.has(k):
			out[k] = b[k]
			continue
		var va = a[k]
		var vb = b[k]
		if (va is float or va is int) and (vb is float or vb is int):
			out[k] = lerpf(float(va), float(vb), t)
		elif (va is String or va is Color) and (vb is String or vb is Color):
			out[k] = Color(va).lerp(Color(vb), t)
		else:
			out[k] = vb if t >= 0.5 else va
	return out


## 今の見た目で、電気の灯が消えているか（波の途中は、点いていく波なら終わるまで消えている側）
func dark() -> bool:
	if wave_dir > 0:
		return true
	if wave_dir < 0:
		return false
	return level < 0.5


# ---------------------------------------------------------------- 出来事

func handle(e: Dictionary) -> void:
	match String(e.get("type", "")):
		"flagSet":
			_on_flags()
		"fx":
			if String(e.get("id", "")) == "town_power_on":
				power_on(e.get("at", null), e.get("skipped", false))
		"skipped":
			_finish_wave()


## フラグが変わった：今の部屋の網の電気が変わったら、灯を消す（ちらついて）・点ける（波で）。町の外にいる間に戻ったら、見せずに覚えておく
func _on_flags() -> void:
	var game := _game_now()
	if game == null:
		return
	var grid := _grid
	for g in (game.world.power.keys() if game.world != null else []):
		var on := game.grid_powered(g)
		var was: bool = _was_on.get(g, true)
		if on and not was and g != grid:
			pending[g] = true
		elif not on:
			pending.erase(g)
	_remember(game)
	if grid == "":
		return
	var on_now := game.grid_powered(grid)
	var skipping := game.story.skipping
	if not on_now and not dark():
		if skipping:
			_set_steady(0.0)
		else:
			_start_wave(-1, _player_pos() + Vector3(0, 0, 200), 2000.0, OUT_SPREAD)
	elif on_now and dark() and wave_dir == 0 and not pending.get(grid, false):
		# 部屋にいる間に戻った（確かめ用にフラグを立てたときなど）：その場で波で点ける
		power_on(null, skipping)


## 電気の灯を点ける（歓声の合図 fx: town_power_on。at：波の原点、無ければハルのいる所の下）。skipped ならすぐ点いた姿
func power_on(at = null, skipped := false) -> void:
	pending.erase(_grid)
	if not dark() and wave_dir == 0:
		return
	if skipped:
		_set_steady(1.0)
		return
	var origin: Vector3 = at if at is Vector3 else _player_pos() + Vector3(0, -8, 0)
	_start_wave(1, origin, maxf(WAVE_MIN_SPEED, far_from(origin) / WAVE_TIME), WAVE_SPREAD)


## 原点から、いちばん遠い電気の灯（部屋の明かりと、電気の材質の部品・面の広がりの角）までの距離（m）
func far_from(origin: Vector3) -> float:
	var far := 0.0
	for l in _lights:
		if l[2] == "electric" and is_instance_valid(l[0]):
			far = maxf(far, _pos(l[0]).distance_to(origin))
	for b in _boxes:
		var box: AABB = b
		var c := box.get_center()
		var e := box.size * 0.5
		var far_pt := c + Vector3(e.x * signf(c.x - origin.x), e.y * signf(c.y - origin.y), e.z * signf(c.z - origin.z))
		far = maxf(far, far_pt.distance_to(origin))
	return far


func _start_wave(dir: int, origin: Vector3, speed: float, spread: float) -> void:
	wave_dir = dir
	wave_t = 0.0
	wave_origin = origin
	wave_speed = speed
	wave_spread = spread
	# いちばん遠い灯（部屋の明かり・電気の材質の窓や灯の芯）+ ばらつき + ちらつき + 余白
	wave_end = minf(far_from(origin), 60.0) / speed + spread + FLICKER + 0.4
	_apply()


## 波を終わりの姿にする（スキップ）
func _finish_wave() -> void:
	if wave_dir != 0:
		_set_steady(1.0 if wave_dir > 0 else 0.0)


func _set_steady(v: float) -> void:
	var was_dark := dark()
	wave_dir = 0
	wave_t = 0.0
	level = v
	_apply()
	if was_dark != dark() and main != null and main.has_method("_apply_mood") and main.game != null:
		main._apply_mood()


func _remember(game: GameSim) -> void:
	if game.world == null:
		return
	for g in game.world.power:
		_was_on[g] = game.grid_powered(g)


static func _pos(n: Node3D) -> Vector3:
	return n.global_position if n.is_inside_tree() else n.position


## ワールドの変換（木の外なら親をたどって掛ける）
static func _xform(n: Node3D) -> Transform3D:
	if n.is_inside_tree():
		return n.global_transform
	var xf := n.transform
	var p := n.get_parent()
	while p is Node3D:
		xf = (p as Node3D).transform * xf
		p = p.get_parent()
	return xf


func _game_now() -> GameSim:
	if main != null and main.get("game") != null:
		return main.game
	return _game


func _player_pos() -> Vector3:
	var g := _game_now()
	return g.player.pos if g != null and g.player != null else Vector3.ZERO


# ---------------------------------------------------------------- 毎こま

func _process(dt: float) -> void:
	# 場面が終わった：場面が灯した遠景の窓（CineDirector._ready_ordo）や、部屋を隠して出し直したときに見えた電気の明かり
	# （CineDirector._set_room_visible）を、町の電気の値に戻す
	var cine_on := _cine_active()
	if _cine_was and not cine_on:
		_apply()
	_cine_was = cine_on
	# 波はポーズの間は止める（遊びの間だけ進む）
	if wave_dir != 0 and (main == null or main.get("state") == null or main.state == "playing"):
		wave_t += dt
		if wave_t >= wave_end:
			_set_steady(1.0 if wave_dir > 0 else 0.0)
		else:
			_apply()
			# 空と光も、電気のある光と停電の光の間を波の進みで移す（light_for）
			if _grid != "" and main != null and main.has_method("_apply_light") and main.get("game") != null:
				main._apply_light()
	elif dark() and main != null and main.has_method("_ordo"):
		# 場面のカメラがあとから出した背の町の灯（TownLights）も、停電の間は消しておく（場面の途中は場面の値のまま）
		var o: OrdoView = main._ordo()
		if o != null and not _cine_active():
			_sync_town_lights(o, 0.0)
	# 油の灯の本物の光：シェーダー（にじみ oil_glow・油の材質）と同じ式・同じ時計（_time）で、ゆっくり揺らぐ
	_time = fmod(_time + dt, 3600.0)
	for l in _lights:
		if l[2] == "oil" and is_instance_valid(l[0]):
			var h: float = float(l[3]) * 40.0
			(l[0] as Light3D).light_energy = float(l[1]) * (0.88 + 0.12 * sin(_time * 6.1 + h) * sin(_time * 2.3 + h * 0.37))


func _cine_active() -> bool:
	return main != null and main.get("cine") != null and main.cine != null and main.cine.active()


## 電気の灯 1 つの明るさ 0〜1（ワールドの位置 p。シェーダーの power_k と同じ式）。h は灯ごとの乱数（seed_hash。負なら p から）
func wave_k(p: Vector3, h := -1.0) -> float:
	if wave_dir == 0:
		return level
	if h < 0.0:
		h = seed_hash(p)
	var t := wave_t - (p.distance_to(wave_origin) / maxf(wave_speed, 0.01) + h * wave_spread)
	var on := 1.0 if t >= FLICKER else 0.0
	if t >= 0.0 and t < FLICKER:
		var r := fposmod(sin((floor(wave_t * 20.0) + h * 97.0) * 12.9898) * 43758.5453, 1.0)
		on = 1.0 if r <= 0.25 + t * 1.3 else 0.0
	return on if wave_dir > 0 else 1.0 - on


## 全体の明るさ 0〜1（波の進み。遠景・オルドの琥珀の灯に使う）
func level_now() -> float:
	if wave_dir == 0:
		return level
	var k := clampf(wave_t / maxf(wave_end, 0.01), 0.0, 1.0)
	return k if wave_dir > 0 else 1.0 - k


## 今の状態を、電気の材質（キットの "source": "electric"）・部屋の明かり・オルドの琥珀の灯・遠景へ入れる
func _apply() -> void:
	var state := Vector4(level, float(wave_dir), wave_t, wave_speed)
	var origin := Vector4(wave_origin.x, wave_origin.y, wave_origin.z, wave_spread)
	last_params = {"power_state": state, "power_origin": origin}
	for m in RoomKit.electric_materials():
		(m as ShaderMaterial).set_shader_parameter("power_state", state)
		(m as ShaderMaterial).set_shader_parameter("power_origin", origin)
	for l in _lights:
		if l[2] != "electric" or not is_instance_valid(l[0]):
			continue
		var light: Light3D = l[0]
		var k := wave_k(light.global_position, float(l[3])) if light.is_inside_tree() else level
		light.light_energy = float(l[1]) * k
		# 消えた灯は描かない（スマホの描き方では、光ごとに照らす物の描画が 1 回ずつ増える）
		light.visible = k > 0.001
	_apply_ordo(level_now())


## 部屋のオルド：琥珀の灯（体の帯・梁の灯）を非常灯の明るさに、背の上の町の灯（場面で出したとき）と遠景の窓を消す
func _apply_ordo(lv: float) -> void:
	if main == null or not main.has_method("_ordo"):
		return
	# オルドの体を置かない部屋の背の上の町（上段の BackTownView）も、同じく窓を消し・点ける
	var bt: Node = main._back_town() if main.has_method("_back_town") else null
	if bt != null:
		_sync_back_windows(bt, lv)
	var o: OrdoView = main._ordo()
	if o == null:
		return
	if lv < 1.0 or o.has_meta("power_dimmed"):
		o.set_meta("power_dimmed", true)
		o.set_amber(lerpf(ORDO_EMERGENCY, 1.0, lv))
	_sync_town_lights(o, lv)
	_sync_back_windows(o, lv)


## 部屋のオルドの背の上の遠くの町の窓（OrdoView・BackTownView の set_back_lights）：電気のある町なら灯し、停電の間は消し、
## 再始動の波では消えた順の逆にちらつきながら戻す。電気の網のある部屋だけ。場面の途中は場面（CineDirector）の値のまま。
## 窓の光は雰囲気の明るさを掛けるので、昼は見えない（夜明け 0.6・夜 1）
func _sync_back_windows(o: Node, lv: float) -> void:
	if _grid == "" or _cine_active():
		return
	o.call("set_back_lights", 1.0, BACK_FLICKER if lv > 0.0 and lv < 1.0 else 0.0, 1.0 - lv)


## 背の上の町の灯（TownLights。場面のカメラが出したときだけある）：電気の明るさ lv のとき、消えた灯の割合 out を 1 - lv に
func _sync_town_lights(o: OrdoView, lv: float) -> void:
	var tl = o.town_lights
	if tl == null or tl.get("out") == null:
		return
	if lv >= 1.0 and not tl.has_meta("power_out"):
		return
	var want := 1.0 - lv
	if absf(float(tl.get("out")) - want) > 0.001:
		tl.set_meta("power_out", true)
		tl.set("out", want)
		if tl.has_method("apply"):
			tl.call("apply")


# ---------------------------------------------------------------- 油の灯の安い光（部屋を作るときに RoomView が呼ぶ）

## 部屋の明かりの "glow"（灯のまわりのにじみの半径 m）・"pool"（床の明るい輪 [半径 m, 床の高さ y]）から、
## 油の灯の安い光を 1 つの MultiMesh で作る（描画 1 回。無ければ null）
static func make_glows(entries: Array) -> MultiMeshInstance3D:
	var items: Array = []   # [変換, Color(形, 位相, 強さ, 0)]
	for l in entries:
		var p := RoomGeo.v3(l.pos)
		var h := seed_hash(p)
		var amt := float(l.get("glow_strength", 1.0))
		if l.has("glow"):
			items.append([Transform3D(Basis.IDENTITY.scaled(Vector3.ONE * float(l.glow)), p), Color(0.0, h, amt, 0.0)])
		if l.has("pool"):
			var pl: Array = l.pool
			items.append([Transform3D(Basis.IDENTITY.scaled(Vector3.ONE * float(pl[0])), Vector3(p.x, float(pl[1]), p.z)), Color(1.0, h, amt, 0.0)])
	if items.is_empty():
		return null
	var mm := MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.use_custom_data = true
	var q := QuadMesh.new()
	q.size = Vector2(1, 1)
	mm.mesh = q
	mm.instance_count = items.size()
	var lo := Vector3(INF, INF, INF)
	var hi := -lo
	for i in items.size():
		var xf: Transform3D = items[i][0]
		mm.set_instance_transform(i, xf)
		mm.set_instance_custom_data(i, items[i][1])
		var r := xf.basis.get_scale().x + 0.5
		lo = lo.min(xf.origin - Vector3.ONE * r)
		hi = hi.max(xf.origin + Vector3.ONE * r)
	var mi := MultiMeshInstance3D.new()
	mi.name = "OilGlow"
	mi.multimesh = mm
	var mat := ShaderMaterial.new()
	mat.shader = GLOW_SHADER
	mi.material_override = mat
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	mi.gi_mode = GeometryInstance3D.GI_MODE_DISABLED
	# 板はシェーダーでカメラへ向けるので、広がりは灯の置き場所 + 大きさ
	mi.custom_aabb = AABB(lo, hi - lo)
	return mi
