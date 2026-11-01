class_name OrdoSteps
extends Node
## 町で感じる巡礼機オルドの歩み（30 章 4.2「町の中では歩行の揺れを周期的な振動と音で感じさせる」。結果は 30 章 4.2.1）。見た目と音だけ。
## オルドの足が 120 m 下の砂に着くたびに（2 本ずつ、20 秒ごと）、町のどの部屋でも：
##   遠い低い地響き（耳より体で感じる音。近い脚ほど大きい）・画面のごく小さな沈みと揺れ（場面の揺れよりずっと小さい）・
##   布・旗・吊り札・吊り灯が少し揺れる（キットの材質の "jolt"。揺れの重み = 頂点の色のアルファ。吊り灯には部品を読むときに重みを足す）・
##   日よけ・洗濯物から砂ぼこりが少し落ちる（屋外）／天井から砂がこぼれ、器が小さく鳴る（屋内）／鉄の胴の重い響き（遺構）。
## 止まる：停止の夜（ch1.ordo_stopped。場面の「動力が切れる」合図 fx: ordo_stop から）から再始動（ch1.ordo_restarted）までは足音が無い
##   （いつもの足音がしない静けさ）。
##   再始動の刻みに部屋にいれば、restart_first_s 秒後に重い最初の 1 歩（「止まっていた足音が、ゆっくりと、また始まった」）。
## 時計：オルドの歩きの周期の位置（phase。OrdoView と同じ。1 周 CYCLE_S 秒、足が着くのは PHASE + SWING_FRAC）。部屋を移っても続く。
##   部屋にオルド（OrdoView。下段・中段・オープニング）がいる間は、そのオルドの時計に従い、足が着いた知らせ（foot_planted）で鳴らす
##   （見える脚と音がそろう）。部屋を作ったとき、その部屋のオルドに今の位置を渡す（部屋の "ordo" に "phase" があれば、それを使う）。
##   オルドのいない部屋（家の中・上段・訓練場・遺構）は、ここが決まった刻み（main の 1/60 秒）で時計を進め、同じ時刻に鳴らす。
## 決まり：ゲームの中身（GameSim）は読むだけ。時刻はゲームの刻みの dt の和（描画の速さに関係しない）。乱数は自分の種。
## 映画のような場面の間（CineDirector.active()）は鳴らさない（場面が自分で ordo_step を鳴らす）。画面の揺れは設定の「画面の揺れ」
## （CameraRig.shake_scale）を掛ける。部屋ごとの音・強さ・場所は content/ordo_steps.json。

const CONFIG_PATH := "res://content/ordo_steps.json"
## OrdoView の既定（cycle_s・swing_frac）と同じ（tests/test_steps.gd が確かめる）
const CYCLE_S := 80.0
const SWING_FRAC := 0.24
## 揺れの続く秒数（これより後は材質・カメラに 0 を入れて止める）
const JOLT_S := 6.0
const CAMERA_S := 4.0

var main
## 歩きの周期の位置（0〜1）と、歩いているか（フラグから）
var phase := 0.0
var walking := true
## 確かめ用：鳴らした足音の数・最後の足音 { "tags", "db", "sound", "place", "heavy", "time" }・今の部屋の場所の種類
var steps_heard := 0
var last := {}
var place_name := ""
var time := 0.0

var _game = null
var _room_id := ""
var _place := {}
var _room_cfg := {}
var _bound: OrdoView = null
var _pending: Array = []
var _heavy_next := false
## 停止の場面の「動力が切れる」合図（fx: ordo_stop）を受けた：フラグ ch1.ordo_stopped が立つ前（場面の外の舞台が消えてから数秒）も鳴らさない
var _cue_stop := false
var _rng := RandomNumberGenerator.new()
## 揺れ：カメラ（経過の秒・幅 m・横揺れの角）と材質（経過の秒・幅 m・向き）
var _cam_t := 99.0
var _cam_amp := 0.0
var _cam_roll := 0.0
var _jolt_t := 99.0
var _jolt_amp := 0.0
var _jolt_dir := Vector2(0, 1)
var _jolt_live := false
var _mats: Array = []
## 遅れて鳴らす音・出すもの [残りの秒, 種類, 値]
var _later: Array = []

static var _config := {}
## 部品ごとの、揺れる布の下の端（砂ぼこりの出る所。部品の中の位置）："キット|部品" → PackedVector3Array
static var _puff_cache := {}


func _init(m = null) -> void:
	main = m
	_rng.seed = 4021


static func config() -> Dictionary:
	if _config.is_empty():
		var d = U.load_json(CONFIG_PATH)
		_config = d if d is Dictionary else {"places": {}, "rooms": {}}
	return _config


# ---------------------------------------------------------------- 時計（OrdoView と同じ決まり）

## 脚の足が着く周期の位置（振り出しの始め PHASE + 振り出しの長さ）
static func plant_phase(tag: String) -> float:
	return fposmod(float(OrdoView.PHASE[tag]) + SWING_FRAC, 1.0)


## 周期の位置が p0 から p1 へ進む間（p0 < 位置 ≦ p1。p1 は 1 を超えてよい）に足が着く脚
static func plants_between(p0: float, p1: float) -> Array:
	var out := []
	if p1 <= p0:
		return out
	for tag in OrdoView.LEGS:
		var pp := plant_phase(tag)
		while pp <= p0:
			pp += 1.0
		if pp <= p1:
			out.append(tag)
	return out


## 今の位置から次に足が着くまでの周期の割合（0〜1）
static func to_next_plant(p: float) -> float:
	var best := 1.0
	for tag in OrdoView.LEGS:
		var d := fposmod(plant_phase(tag) - p, 1.0)
		if d < 1e-6:
			d = 1.0
		best = minf(best, d)
	return best


## 歩いているか：停止の夜から再始動までは止まっている
static func walk_flag(g) -> bool:
	return not g.flag("ch1.ordo_stopped") or g.flag("ch1.ordo_restarted")


# ---------------------------------------------------------------- 毎刻み

## main._physics_process から、場面のカメラ（cine.sync）の次に呼ぶ
func sync(dt: float) -> void:
	var g = main.game if main != null else null
	if g == null:
		return
	if g != _game:
		_reset(g)
	time += dt
	if String(g.room_id) != _room_id:
		_enter_room(g)
	if _cue_stop and g.flag("ch1.ordo_restarted"):
		_cue_stop = false
	var w := walk_flag(g) and not _cue_stop
	if w != walking:
		_walk_changed(w)
	var tags: Array = []
	var o := _room_ordo()
	if o != null:
		if o != _bound:
			_bind(o)
		phase = o.phase
		tags = _pending
		_pending = []
	elif walking and not _place.is_empty():
		var p1 := phase + dt / CYCLE_S
		tags = plants_between(phase, p1)
		phase = fposmod(p1, 1.0)
	elif walking:
		phase = fposmod(phase + dt / CYCLE_S, 1.0)
	if not walking:
		tags = []
	if not tags.is_empty() and not _place.is_empty() and not _cine_active():
		_step(tags)
	_run_later(dt)
	_apply_jolt(dt)
	_apply_camera(dt)


## ゲームの出来事（main._handle_events から）：停止の場面の「動力が切れる」合図
func handle(e: Dictionary) -> void:
	if String(e.get("type", "")) == "fx" and String(e.get("id", "")) == "ordo_stop":
		_cue_stop = true


## 新しいゲーム・ロード：時計はプレイ時間から（セーブから続けても、毎回同じ所から）
func _reset(g) -> void:
	_game = g
	_cue_stop = false
	phase = fposmod(float(g.play_time) / CYCLE_S, 1.0)
	walking = walk_flag(g)
	_room_id = ""
	_pending.clear()
	_later.clear()
	_heavy_next = false
	_cam_t = 99.0
	_jolt_t = 99.0
	_bound = null


func _enter_room(g) -> void:
	_room_id = String(g.room_id)
	_clear_jolt()
	_room_cfg = room_config(_room_id, g.room)
	place_name = String(_room_cfg.get("place", ""))
	_place = config().get("places", {}).get(place_name, {})
	_mats = jolt_materials(g.room)
	_pending.clear()
	_bound = null
	_cam_t = 99.0


## 部屋の設定：content/ordo_steps.json の "rooms"（部屋の id）、無ければ "kits"（キットの id。遺構の階層）。どちらにも無ければ {}（鳴らさない）
static func room_config(room_id: String, room: Dictionary) -> Dictionary:
	var c := config()
	if c.get("rooms", {}).has(room_id):
		return c.rooms[room_id]
	return c.get("kits", {}).get(String(room.get("kit", "")), {})


func _room_ordo() -> OrdoView:
	if main == null or not main.has_method("_ordo"):
		return null
	var o: OrdoView = main._ordo()
	if o == null or not is_instance_valid(o) or o.model == null:
		return null
	return o


## 部屋のオルドに時計を合わせる（部屋の "ordo" に "phase" があればそれに従う：オープニングの場面の足の時刻）
func _bind(o: OrdoView) -> void:
	_bound = o
	if not o.foot_planted.is_connected(_on_planted):
		o.foot_planted.connect(_on_planted)
	var r: Dictionary = _game.room if _game != null else {}
	if r.get("ordo", {}).has("phase"):
		phase = o.phase
	elif walking and o.walking and o.speed >= 0.999:
		o.phase = phase
		o._init_gait()
		o._apply()


func _on_planted(tag: String, _at: Vector3) -> void:
	# ポーズ・メニューの間（main が刻みを進めていない）は数えない
	if main != null and "state" in main and String(main.state) != "playing":
		return
	if not _pending.has(tag):
		_pending.append(tag)


func _cine_active() -> bool:
	if main == null or not ("cine" in main) or main.cine == null:
		return false
	return main.cine.active()


## 止まる・歩き出す。歩き出したときオルドのいない部屋なら、restart_first_s 秒後に重い最初の 1 歩が来るよう時計を合わせる
func _walk_changed(w: bool) -> void:
	walking = w
	_pending.clear()
	if not w:
		return
	_heavy_next = true
	if _room_ordo() == null:
		var first := float(config().get("restart_first_s", 2.5))
		phase = fposmod(phase + to_next_plant(phase) - first / CYCLE_S, 1.0)


# ---------------------------------------------------------------- 1 歩

## 聞く所（オルドの座標）：部屋のオルドがいればハルの位置をオルドの座標に、いなければ部屋の "at" ＋ハルの位置（部屋の向きはオルドと同じとみなす）
func listener() -> Vector3:
	var p: Vector3 = _game.player.pos if _game != null else Vector3.ZERO
	var o := _room_ordo()
	if o != null:
		return o.global_transform.affine_inverse() * p
	var at = _room_cfg.get("at", [0, 0, 0])
	return RoomGeo.v3(at) + p


## 脚の音の大きさ（dB）：肩（脚の付け根。足の揺れが骨組みに入る所）までの距離で。ref_m で db、近いほど大きく、range_db の中
static func leg_db(place: Dictionary, tag: String, at: Vector3) -> float:
	var s := RoomGeo.v3(config().get("shoulders", {}).get(tag, [0, -35, 0]))
	var d := maxf(at.distance_to(s), 1.0)
	var rel := 20.0 * log(float(place.get("ref_m", 100.0)) / d) / log(10.0)
	var r: Array = place.get("range_db", [-9.0, 5.0])
	return float(place.get("db", -9.0)) + clampf(rel, float(r[0]), float(r[1]))


func _step(tags: Array) -> void:
	var at := listener()
	var power := 0.0
	var best := ""
	var best_db := -INF
	for tag in tags:
		var gdb := leg_db(_place, tag, at)
		power += pow(10.0, gdb / 10.0)
		if gdb > best_db:
			best_db = gdb
			best = tag
	# 同じ所に立っていても毎回少しずつ違う（±1 dB）
	var db := 10.0 * log(power) / log(10.0) + _rng.randf_range(-1.0, 1.0)
	var heavy := _heavy_next
	_heavy_next = false
	if heavy:
		db += 3.0
	var k := pow(10.0, (db - float(_place.get("db", -9.0))) / 20.0)
	var sound := String(_place.get("sound", "ordo_thud"))
	if main.audio != null:
		main.audio.play_gain(sound, db, 0.84 if heavy else _rng.randf_range(0.95, 1.04))
	# 器・道具が小さく鳴る（家の中。少し遅れて、ときどき）
	if _place.has("rattle") and _rng.randf() < float(_place.get("rattle_chance", 0.7)):
		_later.append([_rng.randf_range(0.3, 0.55), "sound", [String(_place.rattle), float(_place.get("rattle_db", -19.0)) + (db - float(_place.get("db", -9.0))), _rng.randf_range(0.92, 1.08)]])
	# 画面：ごく小さな沈みと揺れ。材質：布・吊り灯が近い脚の側から押されて揺れる（前へよろめく向きを少し混ぜる）
	_cam_t = 0.0
	_cam_amp = float(_place.get("camera", 0.01)) * k * (1.6 if heavy else 1.0)
	_cam_roll = deg_to_rad(float(_place.get("roll_deg", 0.08))) * k * (1.6 if heavy else 1.0) * (1.0 if _rng.randf() < 0.5 else -1.0)
	var s := RoomGeo.v3(config().get("shoulders", {}).get(best, [0, -35, 0]))
	var away := Vector2(at.x - s.x, at.z - s.z)
	var dir := away.normalized() if away.length() > 0.1 else Vector2(0, 1)
	_jolt_dir = (dir + Vector2(0, 0.6)).normalized()
	_jolt_t = 0.0
	_jolt_amp = float(_place.get("jolt", 0.05)) * k * (1.5 if heavy else 1.0)
	# 砂ぼこり（屋外：日よけ・洗濯物の下の端）・天井からこぼれる砂（屋内・遺構）。足音の少しあと
	if int(_place.get("puffs", 0)) > 0:
		_later.append([0.12, "puffs", int(_place.puffs)])
	if int(_place.get("sift", 0)) > 0:
		_later.append([0.18, "sift", int(_place.sift)])
	steps_heard += 1
	last = {"tags": tags, "db": db, "sound": sound, "place": place_name, "heavy": heavy, "time": time, "near": best, "k": k}


func _run_later(dt: float) -> void:
	if _later.is_empty():
		return
	var keep := []
	for it in _later:
		it[0] = float(it[0]) - dt
		if float(it[0]) > 0.0:
			keep.append(it)
			continue
		match String(it[1]):
			"sound":
				if main.audio != null:
					main.audio.play_gain(String(it[2][0]), float(it[2][1]), float(it[2][2]))
			"puffs":
				_puffs(int(it[2]))
			"sift":
				_sift(int(it[2]))
	_later = keep


## 今、画面を描いているカメラ（ふだんは遊びのカメラ。撮影の固定カメラのときはそれ）
func _view_cam() -> Camera3D:
	var c: Camera3D = get_viewport().get_camera_3d() if is_inside_tree() else null
	if c == null and main != null:
		c = main.camera
	return c


## 屋外：カメラの前の近く（25 m 以内、近いものから）の、揺れる布の下の端から、砂ぼこりを少し
func _puffs(n: int) -> void:
	var cam := _view_cam()
	if main.fx == null or main.fx.vfx == null or cam == null:
		return
	var amb: AmbientFx = main.fx.ambient
	if amb == null:
		return
	amb.step_puffs(main.fx.vfx, cam.global_position, -cam.global_transform.basis.z, n, clampf(_jolt_amp / 0.07, 0.5, 1.6))


## 屋内・遺構：ハルの前・まわりの天井から、細い砂がこぼれる。高さは部屋の "ceiling"（ハルの足元からの高さ m。遺構の縦坑のような
## 高い部屋でも、ハルの上から落ちる。本当の天井より上から出た粒は天井に隠れ、天井の面から出てくるように見える）
func _sift(n: int) -> void:
	if main.fx == null or main.fx.vfx == null or _game == null:
		return
	var amb: AmbientFx = main.fx.ambient
	if amb == null:
		return
	var p: Vector3 = _game.player.pos
	var top := p.y + float(_room_cfg.get("ceiling", 4.5))
	var cam := _view_cam()
	var fwd := Vector3(0, 0, 1)
	if cam != null:
		fwd = -cam.global_transform.basis.z
		fwd.y = 0.0
		fwd = fwd.normalized() if fwd.length() > 0.01 else Vector3(0, 0, 1)
	amb.step_sift(main.fx.vfx, p, fwd, top, n)


# ---------------------------------------------------------------- 揺れ

## 材質の揺れ（kit_motion.gdshaderinc の jolt）：x, y = 揺れの向き（ワールドの水平）、z = 着いてからの秒、w = 重み 1 の頂点の揺れの幅
func _apply_jolt(dt: float) -> void:
	_jolt_t += dt
	if _jolt_t < JOLT_S and _jolt_amp > 0.0:
		var v := Vector4(_jolt_dir.x, _jolt_dir.y, _jolt_t, _jolt_amp)
		for m in _mats:
			(m as ShaderMaterial).set_shader_parameter("jolt", v)
		_jolt_live = true
	elif _jolt_live:
		_clear_jolt()


func _clear_jolt() -> void:
	for m in _mats:
		if is_instance_valid(m):
			(m as ShaderMaterial).set_shader_parameter("jolt", Vector4.ZERO)
	_jolt_live = false


## 部屋のキットの材質のうち、揺れの重みを使うもの（"sway" のある材質と、重みを足した吊り灯の芯 amber）
static func jolt_materials(room: Dictionary) -> Array:
	var out := []
	if not room.has("kit"):
		return out
	var kit := RoomKit.load_kit(String(room.kit))
	var mats: Dictionary = kit.get("mats", {})
	for k in mats:
		var m = mats[k]
		if m is ShaderMaterial and m.shader != null and m.shader.get_mode() == Shader.MODE_SPATIAL:
			var a = m.get_shader_parameter("sway_amp")
			if a is Vector4 and (a as Vector4).x + (a as Vector4).y > 0.0:
				out.append(m)
	return out


## 画面のごく小さな揺れ：足が着くと少し沈んでから戻り、ゆっくり横へ揺れ、わずかに傾く（場面の揺れの 1/5 くらい）
func camera_offset(t: float, amp: float, roll: float) -> Array:
	if t >= CAMERA_S or amp <= 0.0:
		return [Vector3.ZERO, 0.0]
	var on := 1.0 - exp(-t * 22.0)
	var dip := -amp * on * exp(-t * 2.2) * sin(TAU * 1.4 * t + 0.35)
	var side := amp * 0.55 * on * exp(-t * 1.1) * sin(TAU * 0.55 * t)
	var r := roll * on * exp(-t * 1.3) * sin(TAU * 0.7 * t + 0.5)
	return [Vector3(side, dip, 0.0), r]


func _apply_camera(dt: float) -> void:
	_cam_t += dt
	if _cam_t >= CAMERA_S or main.camera == null or _cine_active():
		return
	var cam: Camera3D = main.camera
	var sc := float(cam.get("shake_scale")) if "shake_scale" in cam else 1.0
	if sc <= 0.0:
		return
	var o: Array = camera_offset(_cam_t, _cam_amp * sc, _cam_roll * sc)
	var off: Vector3 = o[0]
	var b := cam.global_transform.basis
	cam.global_position += b.x * off.x + Vector3.UP * off.y
	cam.rotate_object_local(Vector3(0, 0, 1), float(o[1]))


# ---------------------------------------------------------------- 部品を読むとき（RoomKit.part_mesh から）

## 部品の面（材質の名前 → 配列）を読んだときに 1 回：吊り灯に揺れの重みを足し（"hang"）、揺れる布の下の端を覚える（"puffs"）
static func part_loaded(part: String, surfs: Dictionary, kit: Dictionary) -> void:
	var c := config()
	var key := "%s|%s" % [kit.get("id", ""), part]
	if c.get("puffs", []).has(part):
		_puff_cache[key] = _cloth_edges(surfs)
	var h: Dictionary = c.get("hang", {}).get(part, {})
	if not h.is_empty() and surfs.has("amber"):
		if weight_lanterns(surfs, float(h.get("w", 0.35)), h.get("chains", [])) > 0:
			# 芯（amber）にも布・金物と同じ風の揺れを入れる（重みの無い芯は動かない。吊り灯の芯だけ、籠と一緒に動く）
			var mats: Dictionary = kit.get("mats", {})
			var src = mats.get("metal", mats.get("flat"))
			var dst = mats.get("amber")
			if src is ShaderMaterial and dst is ShaderMaterial:
				dst.set_shader_parameter("sway_amp", src.get_shader_parameter("sway_amp"))
				dst.set_shader_parameter("sway_wind", src.get_shader_parameter("sway_wind"))


## 吊り灯（P.lantern：琥珀の芯の筒・真鍮の籠・笠・吊り金具）を芯の形で見つけ、上の吊り金具から下へ揺れの重み（下の端で w）を足す。
## chains：[x, z, 天井の高さ] の灯は、鎖ごと天井から揺らす。返り値：見つけた灯の数
static func weight_lanterns(surfs: Dictionary, w: float, chains: Array) -> int:
	var amber: Array = surfs.amber
	var av: PackedVector3Array = amber[Mesh.ARRAY_VERTEX]
	# 芯の頂点を、近いもの同士（最初の点から 0.45 m 以内）でまとめる
	var groups: Array = []   # [最初の点, AABB]
	for v in av:
		var found := false
		for gr in groups:
			if (gr[0] as Vector3).distance_to(v) < 0.45:
				gr[1] = (gr[1] as AABB).expand(v)
				found = true
				break
		if not found:
			groups.append([v, AABB(v, Vector3.ZERO)])
	var lamps := []   # [軸の x, 軸の z, 吊る点の y, 下の端の y, 半径]
	for gr in groups:
		var b: AABB = gr[1]
		var sx := b.size.x
		var sz := b.size.z
		var sy := b.size.y
		# 芯の筒：半径 0.075 s・高さ 0.25 s（s = 0.72〜1.4。小さな携行灯は置いてあるので外す）。上から見て丸い（壁の平たい灯 _sconce は外す）
		if sx < 0.08 or sx > 0.3 or sz < 0.08 or sz > 0.3 or sy < 0.18 or sy > 0.4 or sy < 1.2 * maxf(sx, sz):
			continue
		if maxf(sx, sz) > 1.25 * minf(sx, sz):
			continue
		var s := sy / 0.25
		var cpos := b.get_center()
		var pivot := cpos.y + 0.34 * s
		for ch in chains:
			if Vector2(float(ch[0]) - cpos.x, float(ch[1]) - cpos.z).length() < 0.1:
				pivot = float(ch[2])
		lamps.append([cpos.x, cpos.z, pivot, cpos.y - 0.2 * s, 0.155 * s])
	if lamps.is_empty():
		return 0
	# 灯のまわりの箱（ここに入らない頂点はすぐ飛ばす：大きな部屋の部品でも速い）
	var box := AABB()
	for i in lamps.size():
		var l: Array = lamps[i]
		var lb := AABB(Vector3(float(l[0]) - float(l[4]), float(l[3]) - 0.02, float(l[1]) - float(l[4])),
			Vector3(2.0 * float(l[4]), float(l[2]) - float(l[3]) + 0.02, 2.0 * float(l[4])))
		box = lb if i == 0 else box.merge(lb)
	box = box.grow(0.01)
	for name in ["flat", "metal", "amber"]:
		if not surfs.has(name):
			continue
		var arr: Array = surfs[name]
		var vs: PackedVector3Array = arr[Mesh.ARRAY_VERTEX]
		var cols = arr[Mesh.ARRAY_COLOR]
		var col: PackedColorArray = cols if cols is PackedColorArray and (cols as PackedColorArray).size() == vs.size() else PackedColorArray()
		if col.is_empty():
			col.resize(vs.size())
			col.fill(Color.WHITE)
		var changed := false
		for i in vs.size():
			var v := vs[i]
			if not box.has_point(v):
				continue
			for l in lamps:
				if v.y > float(l[2]) or v.y < float(l[3]) - 0.02:
					continue
				var dx := v.x - float(l[0])
				var dz := v.z - float(l[1])
				if dx * dx + dz * dz > float(l[4]) * float(l[4]):
					continue
				var k := clampf((float(l[2]) - v.y) / maxf(float(l[2]) - float(l[3]), 0.05), 0.0, 1.0) * w
				var c := col[i]
				if 1.0 - c.a < k:
					c.a = 1.0 - k
					col[i] = c
					changed = true
				break
		if changed:
			arr[Mesh.ARRAY_COLOR] = col
	return lamps.size()


## 揺れる布（重み 0.2 以上）の、高さ 1.8〜4.8 m の所を 1.2 m の升に分けて、升ごとにいちばん低い点（砂ぼこりが落ちる縁）
static func _cloth_edges(surfs: Dictionary) -> PackedVector3Array:
	var out := PackedVector3Array()
	var cells := {}
	for name in ["flat", "metal"]:
		if not surfs.has(name):
			continue
		var arr: Array = surfs[name]
		var vs: PackedVector3Array = arr[Mesh.ARRAY_VERTEX]
		var cols = arr[Mesh.ARRAY_COLOR]
		if not (cols is PackedColorArray) or (cols as PackedColorArray).size() != vs.size():
			continue
		var col: PackedColorArray = cols
		for i in vs.size():
			if col[i].a > 0.8:
				continue
			var v := vs[i]
			if v.y < 1.8 or v.y > 4.8:
				continue
			var key := Vector3i(floori(v.x / 1.2), floori(v.y / 1.2), floori(v.z / 1.2))
			if not cells.has(key) or (cells[key] as Vector3).y > v.y:
				cells[key] = v
	for key in cells:
		out.append(cells[key])
	return out


## 部屋の飾りの、砂ぼこりの出る所（ワールド）。AmbientFx.build が部屋ごとに呼ぶ（部品はもう読んである：RoomKit.dress のあと）
static func puff_points(room: Dictionary) -> PackedVector3Array:
	var out := PackedVector3Array()
	if not room.has("kit") or not room.has("dress"):
		return out
	var kit := RoomKit.load_kit(String(room.kit))
	for d in room.get("dress", []):
		var part := String(d.get("part", ""))
		var key := "%s|%s" % [kit.get("id", ""), part]
		if not _puff_cache.has(key):
			continue
		var pts: PackedVector3Array = _puff_cache[key]
		for xf in RoomKit.dress_xforms(d):
			for p in pts:
				out.append(xf * p)
				if out.size() >= 400:
					return out
	return out
