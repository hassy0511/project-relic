class_name GameSim
extends Node3D
## ゲームの中身。描画を知らない（テストでは画面なしで動く）。
## 1 刻み（1/60 秒）ごとに step(入力) を呼ぶ。見た目・音・UI へは出来事（events）で伝える。
##
## 地形は「当たり判定用の三角形の面」と「名前つきの目印」で渡す：
##   geometry = { faces: [PackedVector3Array...], markers: { 名前: { pos: Vector3, yaw: float } } }

const ITEM_NAMES := {
	"special.drill": "特殊武器「ブレイクドリル」",
	"chip.charge": "チューニングチップ「チャージ化」",
}
const SAVE_VERSION := 2
const DT := 1.0 / 60.0

var phys: Phys
var tuning: Dictionary
var placement: Dictionary
var geometry: Dictionary
var dialogues: Dictionary
var events_data: Dictionary
var rng: Rng
var edges := InputFrame.Edges.new()
var input := InputFrame.new()
var cam: CameraOrbit
var lock_on: LockOn
var tokens: Enemy.AttackTokens
var story: Story
var player: Player
## 世界のデータ（エリア・部屋・会話・イベント・アイテム）と、今いる部屋
var world: World
var room_id := ""
var room := {}
## 部屋に入った場所（リトライの目安）と、やられたときに戻る場所 { room, pos, yaw }
var entry := {}
var respawn := {}

var enemies: Array = []
## ボス（いなければ null）。HUD の体力バーが見る
var boss = null
var shots: Array = []
var breakables: Array = []
var chests: Array = []
var npcs: Array = []
var beacons: Array = []
var pickups: Array = []
var triggers: Array = []
var checkpoints: Array = []
var doors: Array = []
var exits: Array = []
var switches: Array = []
var movers: Array = []
var terminals: Array = []
var loot: Array = []

var time := 0.0
var tick := 0
var play_time := 0.0
var hitstop := 0.0
var cells := 0
var items := {}
## 素材（id → 個数）、拾った遺物（id → true）、印（回収屋の印）、依頼（id → accepted|done）、ギルドポイント
var materials := {}
var relics := {}
var mark := "見習い"
var requests := {}
var guild_points := 0
var equipped_chips := {}
var objective := ""
var checkpoint := ""
var god_mode := false
## このフレームのジャンプボタンを「調べる」に使ったか
var consumed_jump := false
## 今「調べる」ことができる対象
var focus = null
## イベントの注視点（カメラ）と、イベント中の操作ロック
var cam_focus = null
var cam_focus_time := 0.0
var player_locked := false
## 部屋の移動の予約 { room, spawn?, at?, yaw?, autosave }。刻みの最後に実行する
var _pending_room := {}
var _load_wait := 0
var _choice_axis := 0.0
## 積まれた出来事（見た目・音・UI が取り出す）
var _events: Array = []


## init：{ world?, start?, geometry?, placement?, tuning, dialogues?, events?, seed?, save? }
## world（World）があれば部屋の移動つき。無ければ geometry + placement の 1 部屋（試しの部屋・テスト）
func setup(init: Dictionary) -> void:
	tuning = init.tuning
	if init.has("world"):
		world = init.world
	else:
		world = World.adhoc(init.placement, init.geometry, init.dialogues, init.events)
	dialogues = world.dialogues
	events_data = world.events
	rng = Rng.new(init.get("seed", 12345))
	phys = Phys.new()
	phys.name = "Phys"
	add_child(phys)
	cam = CameraOrbit.new(tuning)
	lock_on = LockOn.new(self)
	tokens = Enemy.AttackTokens.new(func(): return tuning.enemies.maxAttackers)
	story = Story.new(dialogues, events_data, self)
	var save = init.get("save")
	if save != null:
		_restore_flags(save)
		var rid := String(save.get("room", ""))
		load_room(rid if world.has_room(rid) else world.start.room, "", Vector3(save.pos[0], save.pos[1], save.pos[2]), float(save.yaw))
		_apply_save(save)
	else:
		var st: Dictionary = init.get("start", world.start)
		load_room(st.room, st.get("spawn", "start"))


func charge_type() -> bool:
	return equipped_chips.has("chip.charge")


func emit_event(e: Dictionary) -> void:
	_events.append(e)


## 積まれた出来事を取り出して空にする
func drain_events() -> Array:
	var out := _events
	_events = []
	return out


func marker(name: String) -> Dictionary:
	assert(geometry.markers.has(name), "目印が見つからない: %s" % name)
	return geometry.markers[name]


## 部屋を読み込む（今の部屋を片付けて、id の部屋を作る）。
## spawn：目印の名前（空なら部屋の playerStart か "start"）。at を渡せばその位置（やられた後の復帰・セーブからの復帰）
func load_room(id: String, spawn := "", at = null, at_yaw := 0.0) -> void:
	_unload_room()
	room_id = id
	room = world.room(id)
	geometry = world.geometry(id)
	placement = room
	for faces in geometry.faces:
		phys.add_trimesh(faces, Phys.TERRAIN)
	_build_room()
	var sp: Dictionary
	if at != null:
		sp = {"pos": at, "yaw": at_yaw}
	else:
		var nm := spawn if spawn != "" else String(room.get("playerStart", "start"))
		sp = marker(nm)
	var first := player == null
	if first:
		player = Player.new(self, sp.pos, sp.yaw)
		objective = room.get("objective", "")
		respawn = {"room": id, "pos": sp.pos, "yaw": sp.yaw}
		checkpoint = String(room.get("playerStart", spawn))
	else:
		player.teleport(sp.pos, sp.yaw)
	cam.yaw = sp.yaw
	cam.pitch = tuning.camera.defaultPitch * U.DEG
	entry = {"room": id, "pos": sp.pos, "yaw": sp.yaw}
	set_flag("visited." + id)
	emit_event({"type": "roomChanged", "id": id, "first": first})
	_load_wait = 0 if first else 2


## 今の部屋の物を全部片付ける。プレイヤーの体だけ残す
func _unload_room() -> void:
	if player != null:
		for c in phys.get_children():
			if c != player.body:
				phys.remove(c)
	for e in enemies:
		e.alive = false
	enemies = []
	boss = null
	shots = []
	pickups = []
	breakables = []
	chests = []
	npcs = []
	beacons = []
	triggers = []
	checkpoints = []
	doors = []
	exits = []
	switches = []
	movers = []
	terminals = []
	loot = []
	focus = null
	tokens = Enemy.AttackTokens.new(func(): return tuning.enemies.maxAttackers)
	if lock_on != null:
		lock_on.release()


## 目印の名前、または pos（と yaw：度）から位置と向きを得る
func place(p: Dictionary) -> Dictionary:
	if p.get("at") != null:
		return marker(p.at)
	return {"pos": RoomGeo.v3(p.get("pos", [0, 0, 0])), "yaw": float(p.get("yaw", 0.0)) * U.DEG}


func _build_room() -> void:
	for p in room.get("props", []):
		if p.has("when") and not Cond.eval(p.when, self):
			continue
		if p.has("unless") and Cond.eval(p.unless, self):
			continue
		var m := place(p)
		match p.type:
			"breakable":
				var size := RoomGeo.v3(p.size)
				var center: Vector3 = m.pos + Vector3(0, size.y / 2.0, 0)
				var b := Props.Breakable.new(p.id, center, size, m.yaw)
				b.toughness = float(p.get("toughness", 1.0))
				if flag("broken." + p.id):
					b.broken = true
				else:
					b.body = phys.add_box(center, size * 0.5, Phys.BREAKABLE, m.yaw)
					phys.set_owner_of(b.body, b)
				breakables.append(b)
			"chest":
				var c := Props.Chest.new(p.id, m.pos, m.yaw, p.contents)
				c.opened = flag("chest." + p.id)
				c.event = p.get("event", "")
				phys.add_box(m.pos + Vector3(0, 0.4, 0), Vector3(0.6, 0.4, 0.4), Phys.TERRAIN, m.yaw)
				chests.append(c)
			"npc":
				var n := Props.Npc.new(p.id, m.pos, m.yaw, p.name, p.get("talk", ""))
				n.event = p.get("event", "")
				npcs.append(n)
				n.body = phys.add_box(m.pos + Vector3(0, 0.8, 0), Vector3(0.3, 0.8, 0.3), Phys.TERRAIN)
			"beacon":
				var bc := Props.Beacon.new(p.id, m.pos)
				bc.flag = p.get("flag", "")
				bc.event = p.get("event", "")
				bc.activated = flag("beacon." + p.id)
				beacons.append(bc)
			"door":
				var d := Props.Door.new()
				d.id = p.id
				d.pos = m.pos
				d.yaw = m.yaw
				d.size = RoomGeo.v3(p.get("size", [2.5, 3.5, 0.5]))
				d.lock = p.get("lock")
				d.opens = p.get("opens", "interact")
				d.side = p.get("side", "any")
				d.consume = p.get("consume", "")
				d.lock_text = p.get("text", d.lock_text)
				d.event = p.get("event", "")
				d.prompt = p.get("prompt", d.prompt)
				d.is_open = flag("door." + p.id) or bool(p.get("open", false))
				d.open_amt = 1.0 if d.is_open else 0.0
				if not d.is_open:
					_door_body(d)
				doors.append(d)
			"exit":
				var x := Props.Exit.new()
				x.id = p.id
				var size := RoomGeo.v3(p.get("size", [3, 4, 1]))
				x.center = m.pos + Vector3(0, size.y * 0.5, 0)
				x.half = size * 0.5
				x.to = world.resolve(p.to, room_id)
				x.spawn = p.get("spawn", "start")
				x.lock = p.get("lock")
				x.lock_text = p.get("text", x.lock_text)
				exits.append(x)
			"switch":
				var sw := Props.Switch.new()
				sw.id = p.id
				sw.pos = m.pos
				sw.mode = p.get("mode", "shoot")
				sw.radius = float(p.get("radius", 0.7))
				sw.timer = float(p.get("timer", 0.0))
				sw.toggle = bool(p.get("toggle", false))
				sw.prompt = p.get("prompt", sw.prompt)
				sw.cond = p.get("cond")
				sw.on = flag("switch." + p.id)
				switches.append(sw)
			"mover":
				var mv := Props.Mover.new()
				mv.id = p.id
				mv.size = RoomGeo.v3(p.get("size", [4, 0.5, 4]))
				mv.from = m.pos
				mv.to = RoomGeo.v3(p.to) if p.has("to") else m.pos + RoomGeo.v3(p.get("move", [0, 4, 0]))
				mv.speed = float(p.get("speed", 2.0))
				mv.mode = p.get("mode", "toggle")
				mv.cond = p.get("cond")
				mv.wait = float(p.get("wait", 1.0))
				mv.t = 1.0 if mv.mode == "toggle" and Cond.eval(mv.cond, self) else 0.0
				mv.pos = mv.at_t(mv.t)
				mv.body = phys.add_box(mv.pos + Vector3(0, mv.size.y * 0.5, 0), mv.size * 0.5, Phys.TERRAIN)
				movers.append(mv)
			"terminal":
				var tm := Props.Terminal.new()
				tm.id = p.id
				tm.pos = m.pos
				tm.event = p.event
				tm.prompt = p.get("prompt", tm.prompt)
				terminals.append(tm)
				phys.add_box(m.pos + Vector3(0, 0.6, 0), Vector3(0.4, 0.6, 0.3), Phys.TERRAIN, m.yaw)
			"loot":
				var lt := Props.Loot.new()
				lt.id = p.id
				lt.pos = m.pos
				lt.contents = p.contents
				lt.taken = flag("got." + p.id)
				loot.append(lt)
	for t in room.get("triggers", []):
		var m := place(t)
		var size := RoomGeo.v3(t.get("size", [1, 1, 1]))
		var tr := Props.Trigger.new(t.id, m.pos + Vector3(0, size.y / 2.0, 0), size * 0.5, t.event, t.get("once", true))
		tr.on = t.get("on", "enter")
		tr.cond = t.get("cond")
		tr.group = t.get("group", "")
		tr.fired = flag("trigger." + t.id) and tr.once
		triggers.append(tr)
	for c in room.get("checkpoints", []):
		var m := place(c)
		checkpoints.append(Props.Checkpoint.new(c.id, m.pos, m.yaw, c.get("radius", 4.0)))
	for e in room.get("enemies", []):
		spawn_enemy_spec(e)


func _door_body(d: Props.Door) -> void:
	d.body = phys.add_box(d.pos + Vector3(0, d.size.y * 0.5, 0), d.size * 0.5, Phys.TERRAIN, d.yaw)


## 部屋のデータの敵 1 体分を出す：{ type, at|pos, yaw?, id?, group?, once?, when?, unless? }
func spawn_enemy_spec(e: Dictionary) -> Enemy:
	if e.has("when") and not Cond.eval(e.when, self):
		return null
	if e.has("unless") and Cond.eval(e.unless, self):
		return null
	if e.get("once", false) and e.has("id") and flag("defeated." + e.id):
		return null
	var m := place(e)
	var en := add_enemy(e.type, m.pos, m.yaw)
	en.id = e.get("id", "")
	en.group = e.get("group", "")
	en.once = e.get("once", false)
	if en.group != "":
		set_flag("cleared." + en.group, false)
	return en


func door_by_id(id: String):
	for d in doors:
		if d.id == id:
			return d
	return null


## 扉を開ける（フラグ door.<id> が立ち、セーブにも残る）
func open_door(id: String, persist := true) -> void:
	var d = door_by_id(id)
	if d == null or d.is_open:
		return
	d.is_open = true
	if d.body != null:
		phys.remove(d.body)
		d.body = null
	if persist:
		set_flag("door." + id)
	emit_event({"type": "doorOpened", "id": id})
	emit_event({"type": "sfx", "id": "door"})


## 扉を閉める（その部屋にいる間だけ。部屋に入り直すと元の状態）
func close_door(id: String) -> void:
	var d = door_by_id(id)
	if d == null or not d.is_open:
		return
	d.is_open = false
	set_flag("door." + id, false)
	_door_body(d)
	emit_event({"type": "doorClosed", "id": id})


## 住人を今の部屋から消す（イベントで「走り去る」演出に使う。部屋に入り直すと when・unless どおりに戻る）
func remove_npc(id: String) -> void:
	for n in npcs.duplicate():
		if n.id == id:
			npcs.erase(n)
			if n.body != null:
				phys.remove(n.body)
			emit_event({"type": "npcRemoved", "id": id})


func group_cleared(g: String) -> bool:
	return flag("cleared." + g)


## 敵を 1 体足す（型の名前から作る）。呼び出し・配置の両方で使う
func add_enemy(type: String, at: Vector3, yaw: float) -> Enemy:
	var e: Enemy
	match type:
		"sentry":
			e = Sentry.new(self, at, yaw)
		"charger":
			e = Charger.new(self, at, yaw)
		"mini":
			e = Mini.new(self, at, yaw)
		"shield":
			e = ShieldBanki.new(self, at, yaw)
		"floater":
			e = Floater.new(self, at, yaw)
		"kannuki":
			e = Kannuki.new(self, at, yaw)
			boss = e
		_:
			assert(false, "知らない敵の型: %s" % type)
	enemies.append(e)
	return e


## ボスの体力バーに出す情報。戦いが始まっていない・倒したあとは空
func boss_status() -> Dictionary:
	if boss == null or not boss.alive or boss.state == "idle":
		return {}
	return {"name": "大番機「閂」", "hp": boss.hp, "max_hp": boss.max_hp, "phase": boss.phase, "overheat": boss.overheat}


# ---------------------------------------------------------------- 1 刻み

func step(frame: InputFrame) -> void:
	input = frame
	edges.update(frame)
	consumed_jump = false

	# 部屋の読み込み直後は、物理の世界に反映されるまで 2 刻み待つ
	if _load_wait > 0:
		_load_wait -= 1
		tick += 1
		return

	# 会話中は世界を止める
	if story.blocking():
		_update_dialogue_input(frame)
		story.update(DT)
		tick += 1
		return
	story.update(DT)

	if cam_focus_time > 0.0:
		cam_focus_time -= DT
		if cam_focus_time <= 0.0:
			cam_focus = null
	if player_locked:
		# イベント中は操作を受け付けない（ボタンの押し直しの扱いのため、空の入力を 1 刻み分入れる）
		frame = InputFrame.new()
		input = frame
		edges.update(frame)

	cam.apply_look(frame)
	if frame.camera_reset:
		cam.request_recenter()

	if hitstop > 0.0:
		hitstop -= DT
		tick += 1
		return

	lock_on.update(DT)
	_update_interaction()
	_update_movers(DT)
	_update_switches(DT)
	player.update(DT)
	for e in enemies:
		e.update(DT)
	_update_shots(DT)
	_update_pickups(DT)
	_update_world_objects()
	_update_triggers()
	_update_respawn()

	var t = lock_on.target
	var cam_target = cam_focus if cam_focus != null else (t.pos if t != null else null)
	cam.update(DT, player.pos, player.yaw, player.speed(), cam_target)
	time += DT
	play_time += DT
	tick += 1
	if not _pending_room.is_empty():
		_do_pending_room()


func _do_pending_room() -> void:
	var r := _pending_room
	_pending_room = {}
	var at = r.get("at")
	load_room(r.room, r.get("spawn", ""), at, r.get("yaw", 0.0))
	if r.get("autosave", false):
		emit_event({"type": "autosave"})


## 別の部屋へ移る（刻みの最後に実行される）。spawn：移る先の部屋の目印
func go_to(room_to: String, spawn := "start", autosave := true) -> void:
	_pending_room = {"room": world.resolve(room_to, room_id), "spawn": spawn, "autosave": autosave}


## 会話中の入力：決定で送る、選択肢は上下で選ぶ
func _update_dialogue_input(frame: InputFrame) -> void:
	if story.dialogue.has("choices") and story.dialogue.shown >= String(story.dialogue.text).length():
		var ax := frame.move_y
		if absf(ax) > 0.6 and absf(_choice_axis) <= 0.6:
			story.move_choice(-1 if ax > 0.0 else 1)
		_choice_axis = ax
	if edges.pressed("jump") or edges.pressed("sword") or edges.pressed("fire"):
		story.confirm()


# ---------------------------------------------------------------- フラグ

func flag(name: String) -> bool:
	return bool(story.flags.get(name, false))


func set_flag(name: String, v := true) -> void:
	if v:
		if not story.flags.get(name, false):
			story.flags[name] = true
			emit_event({"type": "flagSet", "name": name})
	else:
		story.flags.erase(name)


# ---------------------------------------------------------------- 調べる

func _update_interaction() -> void:
	var p := player
	focus = null
	if not p.grounded or p.attack != null or p.dead:
		return
	var best = null
	var best_d := INF
	for it in chests + npcs + beacons + doors + switches + terminals:
		if not it.enabled():
			continue
		if it is Props.Door and not it.usable_from(p.pos):
			continue
		var d := U.hdist(it.pos, p.pos)
		if d > it.range_m or absf(it.pos.y - p.pos.y) > 1.5:
			continue
		if d < best_d:
			best_d = d
			best = it
	focus = best
	if best != null and edges.pressed("jump"):
		consumed_jump = true
		_interact(best)


func _interact(it) -> void:
	if it is Props.Chest:
		it.opened = true
		set_flag("chest." + it.id)
		emit_event({"type": "chestOpened", "id": it.id})
		emit_event({"type": "sfx", "id": "chest"})
		grant(it.contents)
		if it.event != "":
			story.start_event(it.event)
	elif it is Props.Npc:
		it.yaw = U.dir_to_yaw(player.pos.x - it.pos.x, player.pos.z - it.pos.z)
		player.yaw = U.dir_to_yaw(it.pos.x - player.pos.x, it.pos.z - player.pos.z)
		if it.event != "":
			story.start_event(it.event)
		else:
			var key: String = it.talk + ".done"
			var repeat: String = it.talk + ".again"
			story.start_dialogue(repeat if flag(key) and story.has_dialogue(repeat) else it.talk)
			set_flag(key)
	elif it is Props.Beacon:
		it.activated = true
		set_flag("beacon." + it.id)
		if it.flag != "":
			set_flag(it.flag)
		player.hp = player.max_hp
		player.weapon_energy = 100.0
		respawn = {"room": room_id, "pos": it.pos, "yaw": player.yaw}
		checkpoint = it.id
		emit_event({"type": "saved"})
		emit_event({"type": "sfx", "id": "save"})
		if it.event != "":
			story.start_event(it.event)
	elif it is Props.Door:
		if not Cond.eval(it.lock, self):
			emit_event({"type": "message", "text": it.lock_text})
			emit_event({"type": "sfx", "id": "locked"})
			return
		if it.consume != "":
			items.erase(it.consume)
		open_door(it.id)
		if it.event != "":
			story.start_event(it.event)
	elif it is Props.Switch:
		activate_switch(it)
	elif it is Props.Terminal:
		story.start_event(it.event)


# ---------------------------------------------------------------- 世界の仕掛け

func switch_by_id(id: String):
	for s in switches:
		if s.id == id:
			return s
	return null


## スイッチを入れる（toggle なら入り切り）
func activate_switch(sw: Props.Switch) -> void:
	if sw.on and not sw.toggle:
		return
	sw.on = not sw.on if sw.toggle else true
	sw.time_left = sw.timer if sw.on else 0.0
	set_flag("switch." + sw.id, sw.on)
	emit_event({"type": "switchChanged", "id": sw.id, "on": sw.on})
	emit_event({"type": "sfx", "id": "switch"})


func _update_switches(dt: float) -> void:
	for sw in switches:
		if sw.on and sw.timer > 0.0:
			sw.time_left -= dt
			if sw.time_left <= 0.0:
				sw.on = false
				set_flag("switch." + sw.id, false)
				emit_event({"type": "switchChanged", "id": sw.id, "on": false})


## 動く足場：乗っているプレイヤーを運ぶ
func _update_movers(dt: float) -> void:
	for m in movers:
		var run := Cond.eval(m.cond, self)
		var riding: bool = m.carries(player.pos) and not player.dead
		var target_t: float = m.t
		match m.mode:
			"toggle":
				target_t = 1.0 if run else 0.0
			"ride":
				target_t = 1.0 if run and riding else 0.0
			"pingpong":
				if m.hold > 0.0:
					m.hold -= dt
				elif run:
					target_t = 1.0 if m.dir > 0.0 else 0.0
		var nt := U.approach(m.t, target_t, m.speed * dt / m.length())
		if m.mode == "pingpong" and nt == target_t and nt != m.t:
			# 端に着いたら少し止まって、向きを変える
			m.dir = -m.dir
			m.hold = m.wait
		if nt == m.t:
			continue
		var newpos: Vector3 = m.at_t(nt)
		var delta: Vector3 = newpos - m.pos
		if riding:
			phys.move_character(player.body, delta, Phys.TERRAIN | Phys.BREAKABLE | Phys.ENEMY, delta.y <= 0.0)
			player.pos = phys.feet_of(player.body)
		m.t = nt
		m.pos = newpos
		m.body.position = newpos + Vector3(0, m.size.y * 0.5, 0)


## 置いてある拾い物・自動で開く扉・出口
func _update_world_objects() -> void:
	var p := player
	for lt in loot:
		if not lt.taken and U.hdist(lt.pos, p.pos) <= lt.radius and absf(lt.pos.y - p.pos.y) < 2.0:
			lt.taken = true
			set_flag("got." + lt.id)
			emit_event({"type": "lootTaken", "id": lt.id})
			grant(lt.contents)
	for d in doors:
		if d.opens == "auto" and not d.is_open and Cond.eval(d.lock, self):
			open_door(d.id)
	if p.dead or not _pending_room.is_empty() or story.running_event():
		return
	for x in exits:
		if not x.contains(p.pos):
			continue
		if Cond.eval(x.lock, self):
			go_to(x.to, x.spawn)
			return
		x.msg_cool -= DT
		if x.msg_cool <= 0.0:
			x.msg_cool = 2.5
			emit_event({"type": "message", "text": x.lock_text})


# ---------------------------------------------------------------- 所持品・経済

## 宝箱・拾い物・イベントの「渡す物」をまとめて受け取る：
## { cells, item, items: [..], materials: { id: 個数 }, relics: [..], heals, gp }
func grant(c: Dictionary) -> void:
	if c.has("cells"):
		give_cells(int(c.cells))
		emit_event({"type": "message", "text": "セル %d を手に入れた" % int(c.cells)})
	if c.has("item"):
		give_item(c.item)
	for it in c.get("items", []):
		give_item(it)
	for id in c.get("materials", {}):
		add_material(id, int(c.materials[id]))
	for r in c.get("relics", []):
		give_relic(r)
	if c.has("heals"):
		player.heals += int(c.heals)
		emit_event({"type": "message", "text": "補修パックを %d 個手に入れた" % int(c.heals)})
	if c.has("gp"):
		guild_points += int(c.gp)
	if c.has("mark"):
		set_mark(c.mark)


func give_item(item: String) -> void:
	items[item] = true
	if item == "chip.charge":
		equipped_chips[item] = true
	emit_event({"type": "message", "text": "%s を手に入れた" % world.item_name(item)})
	emit_event({"type": "sfx", "id": "item"})


func give_cells(n: int) -> void:
	cells += n


## セルを払う。足りなければ false（何も減らさない）
func spend_cells(n: int) -> bool:
	if cells < n:
		return false
	cells -= n
	return true


func add_material(id: String, n: int) -> void:
	materials[id] = int(materials.get(id, 0)) + n
	if materials[id] <= 0:
		materials.erase(id)
	if n > 0:
		emit_event({"type": "message", "text": "%s ×%d" % [world.item_name(id), n]})


func material_count(id: String) -> int:
	return int(materials.get(id, 0))


func give_relic(id: String) -> void:
	relics[id] = true
	emit_event({"type": "message", "text": "遺物「%s」を拾った" % world.item_name(id)})
	emit_event({"type": "sfx", "id": "item"})


func set_mark(m: String) -> void:
	if Cond.mark_rank(m) > Cond.mark_rank(mark):
		mark = m
		emit_event({"type": "message", "text": "回収屋の印が「%s」になった" % m})


func has_item(item: String) -> bool:
	return items.has(item)


func toggle_chip(chip: String) -> void:
	if not items.has(chip):
		return
	if equipped_chips.has(chip):
		equipped_chips.erase(chip)
	else:
		equipped_chips[chip] = true


## 入った部屋（地図用）：{ 部屋 id: 部屋のデータ }。入った順ではなく id 順
func visited_rooms() -> Array:
	var out := []
	for id in world.rooms:
		if flag("visited." + id):
			out.append(id)
	return out


# ---------------------------------------------------------------- 戦闘

## ロックオンしていないときの「弱い自動照準」。カメラ正面から 10° 以内の敵
func soft_aim_target():
	var chest := player.chest()
	var best = null
	var best_rel := 10.0 * U.DEG
	for e in enemies:
		if not e.alive:
			continue
		var c: Vector3 = e.center()
		if c.distance_to(chest) > tuning.gun.range * 1.2:
			continue
		var rel := absf(U.wrap_angle(U.dir_to_yaw(c.x - chest.x, c.z - chest.z) - cam.yaw))
		if rel < best_rel:
			best_rel = rel
			best = e
	return best


func damage_enemy(e, amount: float, from: Vector3, info: Dictionary) -> void:
	if not e.alive:
		return
	var r: Dictionary = e.receive(amount, from, info)
	var c: Vector3 = e.center()
	var at: Vector3 = info.get("at", c)
	emit_event({"type": "hit", "at": at, "kind": r.kind})
	emit_event({"type": "sfx", "id": "hit_weak" if r.kind == "weak" else "hit", "at": at})
	if r.killed:
		emit_event({"type": "enemyDestroyed", "at": c})
		emit_event({"type": "sfx", "id": "explode", "at": c})
		# 倒した手応え：ほんの一瞬止まる
		hitstop = maxf(hitstop, 0.06)
		if e != boss:
			_drop_loot(c)
		_on_enemy_killed(e)


func _on_enemy_killed(e) -> void:
	if e.once and e.id != "":
		set_flag("defeated." + e.id)
	if e.group != "":
		for o in enemies:
			if o.group == e.group and o.alive:
				return
		set_flag("cleared." + e.group)


func _drop_loot(at: Vector3) -> void:
	var n := rng.int_in(2, 4)
	for i in n:
		spawn_pickup("cells", rng.int_in(3, 5), at)
	if rng.chance(0.25):
		spawn_pickup("energy", 20, at)
	if rng.chance(0.15):
		spawn_pickup("repair", 15, at)


func spawn_pickup(kind: String, amount: float, at: Vector3) -> void:
	var p := Props.Pickup.new(kind, amount, at)
	var a := rng.range_f(0.0, TAU)
	p.vel = Vector3(cos(a) * 2.0, 4.0, sin(a) * 2.0)
	pickups.append(p)


func drill_breakable(b, dt: float) -> void:
	b.progress += dt
	emit_event({"type": "hit", "at": b.center, "kind": "armor"})
	if b.progress >= b.toughness and not b.broken:
		break_breakable(b)


func break_breakable(b) -> void:
	if b.broken:
		return
	b.broken = true
	if b.body != null:
		phys.remove(b.body)
	b.body = null
	set_flag("broken." + b.id)
	emit_event({"type": "wallBroken", "id": b.id})
	emit_event({"type": "sfx", "id": "wall_break"})
	emit_event({"type": "shake", "strength": 0.4})


func alert_noise(at: Vector3, radius: float) -> void:
	for e in enemies:
		if e.alive and e.state == "idle" and U.hdist(e.pos, at) <= radius:
			e.become_alert()


func spawn_player_shot(spec: Dictionary) -> void:
	shots.append(Shot.new(spec, true))


func spawn_enemy_shot(origin: Vector3, dir: Vector3, speed: float, damage: float) -> void:
	shots.append(Shot.new({
		"origin": origin, "dir": dir, "speed": speed, "range": 40.0, "damage": damage,
		"radius": 0.25, "pierce": false, "kind": "enemy",
	}, false))


func _update_shots(dt: float) -> void:
	var homing_rate: float = tuning.lockOn.homingDegPerSec * U.DEG
	for s in shots:
		if not s.alive:
			continue
		# 追尾：ロックオン対象へ緩やかに曲げる
		if s.homing != null and s.homing.alive:
			var want: Vector3 = (s.homing.center() - s.pos).normalized()
			var cur: Vector3 = s.vel.normalized()
			var angle := cur.angle_to(want)
			if angle > 1e-4:
				var t := minf(1.0, homing_rate * dt / angle)
				s.vel = cur.lerp(want, t).normalized() * s.speed
		s.prev = s.pos
		var move: Vector3 = s.vel * dt
		var l := move.length()
		var end: Vector3 = s.pos + move

		# 地形
		var terrain := phys.raycast(s.pos, move / l, l, Phys.TERRAIN | Phys.BREAKABLE)
		var stop_at: float = terrain.distance / l if not terrain.is_empty() else 1.0

		if s.from_player:
			# 撃つと入るスイッチ（動力の球・弁の輪）
			for sw in switches:
				if sw.mode != "shoot" or (sw.on and not sw.toggle) or not Cond.eval(sw.cond, self):
					continue
				var ts: float = U.segment_sphere(s.pos, end, sw.pos, sw.radius)
				if ts >= 0.0 and ts <= stop_at:
					activate_switch(sw)
					if not s.pierce:
						stop_at = ts
						s.alive = false
						break
			for e in enemies:
				if not s.alive:
					break
				if not e.alive or s.hit.has(e):
					continue
				var t: float = e.hit_segment(s.pos, end, s.radius)
				if t < 0.0 or t > stop_at:
					continue
				s.hit[e] = true
				damage_enemy(e, s.damage, s.pos, {"armorBreak": s.kind != "normal", "at": s.pos.lerp(end, t)})
				if not s.pierce:
					stop_at = t
					s.alive = false
					break
		else:
			var p := player
			var t := U.segment_sphere(s.pos, end, p.chest(), 0.45 + s.radius)
			if t >= 0.0 and t <= stop_at and not p.dead:
				# 無敵中（ダッシュや被弾直後）でも弾はプレイヤーで消す。すり抜けた弾がカメラの目の前を横切らないように
				p.take_damage(s.damage, s.pos, false)
				s.alive = false
				stop_at = t

		s.pos = s.pos.lerp(end, stop_at)
		s.traveled += l * stop_at
		if not terrain.is_empty() and stop_at < 1.0 and s.alive:
			s.alive = false
			emit_event({"type": "hit", "at": s.pos, "kind": "armor"})
		if s.traveled >= s.range_m:
			s.alive = false
	shots = shots.filter(func(s): return s.alive)


func _update_pickups(dt: float) -> void:
	var p := player
	var chest := p.chest()
	for k in pickups:
		if k.collected:
			continue
		k.age += dt
		var d: float = k.pos.distance_to(chest)
		if k.age > 0.4 and d < 3.0:
			# 近づくと吸い寄せられる
			k.pos += (chest - k.pos).normalized() * 14.0 * dt
		else:
			k.vel.y -= 18.0 * dt
			k.pos += k.vel * dt
			var hit := phys.raycast(k.pos + Vector3(0, 0.5, 0), Vector3.DOWN, 0.7, Phys.TERRAIN)
			if not hit.is_empty():
				k.pos.y = hit.point.y + 0.2
				k.vel = Vector3.ZERO
		if k.pos.distance_to(chest) < 0.8 or (k.age > 0.4 and d < 1.0):
			k.collected = true
			match k.kind:
				"cells":
					cells += int(k.amount)
				"energy":
					p.weapon_energy = minf(100.0, p.weapon_energy + k.amount)
				_:
					p.hp = minf(p.max_hp, p.hp + k.amount)
			emit_event({"type": "sfx", "id": "pickup"})
		if k.age > 30.0:
			k.collected = true
	pickups = pickups.filter(func(k): return not k.collected)


func _update_triggers() -> void:
	var pos := player.pos
	for t in triggers:
		if t.fired and t.once:
			continue
		var hit := false
		match t.on:
			"flag":
				hit = Cond.eval(t.cond, self)
			"cleared":
				hit = group_cleared(t.group)
			_:
				hit = t.contains(pos) and Cond.eval(t.cond, self)
		if hit:
			t.fired = true
			if t.once:
				set_flag("trigger." + t.id)
			story.start_event(t.event)
	for c in checkpoints:
		if c.id != checkpoint and U.hdist(c.pos, pos) <= c.radius:
			checkpoint = c.id
			respawn = {"room": room_id, "pos": c.pos, "yaw": c.yaw}


## やられたら、最後に使ったセーブビーコン（無ければ中継地点か最初の場所）から再開する。ノーマルでは何も失わない。
## 倒したボス・開けた宝箱・開いた扉・立てたフラグはそのまま。ほかの部屋なら、その部屋を最初から作り直す
func _update_respawn() -> void:
	var p := player
	if not p.dead or p.dead_time < 2.0 or not _pending_room.is_empty():
		return
	var rp := respawn
	p.dead = false
	p.hp = p.max_hp
	p.invuln = 2.0
	lock_on.release()
	if rp.room != room_id:
		_pending_room = {"room": rp.room, "at": rp.pos, "yaw": rp.yaw}
		emit_event({"type": "respawned", "room": rp.room})
		return
	p.teleport(rp.pos, rp.yaw)
	cam.yaw = rp.yaw
	for s in shots:
		if not s.from_player:
			s.alive = false
	for e in enemies.duplicate():
		e.on_player_died()
	emit_event({"type": "respawned", "room": room_id})


# ---------------------------------------------------------------- セーブ

## セーブのデータ。flags に、開けた宝箱（chest.*）・壊した壁（broken.*）・開いた扉（door.*）・スイッチ（switch.*）・
## 拾った物（got.*）・倒した敵（defeated.*）・使ったビーコン（beacon.*）・入った部屋（visited.*）も入る
func to_save(area_id := "") -> Dictionary:
	var p := player
	return {
		"version": SAVE_VERSION,
		"playTime": play_time,
		"area": area_id if area_id != "" else String(room.get("area", "")),
		"room": room_id,
		"checkpoint": checkpoint,
		"respawn": {"room": respawn.room, "pos": [respawn.pos.x, respawn.pos.y, respawn.pos.z], "yaw": respawn.yaw},
		"pos": [p.pos.x, p.pos.y, p.pos.z],
		"yaw": p.yaw,
		"hp": p.hp,
		"maxHp": p.max_hp,
		"heals": p.heals,
		"weaponEnergy": p.weapon_energy,
		"cells": cells,
		"items": items.keys(),
		"materials": materials.duplicate(),
		"relics": relics.keys(),
		"mark": mark,
		"requests": requests.duplicate(),
		"guildPoints": guild_points,
		"equippedChips": equipped_chips.keys(),
		"flags": story.flags.duplicate(),
		"scanned": lock_on.scanned.keys(),
		"objective": objective,
	}


## 部屋を作る前に、フラグを戻す（旧形式の opened・broken もフラグにする）
func _restore_flags(s: Dictionary) -> void:
	story.flags.merge(s.flags, true)
	for id in s.get("opened", []):
		story.flags["chest." + id] = true
	for id in s.get("broken", []):
		story.flags["broken." + id] = true


func _apply_save(s: Dictionary) -> void:
	var p := player
	p.teleport(Vector3(s.pos[0], s.pos[1], s.pos[2]), s.yaw)
	cam.yaw = s.yaw
	p.hp = s.hp
	p.max_hp = s.maxHp
	p.heals = int(s.heals)
	p.weapon_energy = s.weaponEnergy
	cells = int(s.cells)
	for i in s.items:
		items[i] = true
	for c in s.equippedChips:
		equipped_chips[c] = true
	for k in s.get("scanned", []):
		lock_on.scanned[k] = true
	materials = {}
	for k in s.get("materials", {}):
		materials[k] = int(s.materials[k])
	for r in s.get("relics", []):
		relics[r] = true
	mark = s.get("mark", "見習い")
	requests = s.get("requests", {}).duplicate()
	guild_points = int(s.get("guildPoints", 0))
	checkpoint = s.checkpoint
	var rp: Dictionary = s.get("respawn", {})
	if rp.is_empty():
		respawn = {"room": room_id, "pos": entry.pos, "yaw": entry.yaw}
	else:
		respawn = {"room": rp.room, "pos": Vector3(rp.pos[0], rp.pos[1], rp.pos[2]), "yaw": rp.yaw}
	play_time = s.playTime
	objective = s.objective


## 保存されたデータを読む。形式が合わなければ null（旧い形式 1 も読める）
static func parse_save(text: String):
	var d = JSON.parse_string(text)
	if typeof(d) != TYPE_DICTIONARY or int(d.get("version", 0)) < 1 or int(d.get("version", 0)) > SAVE_VERSION:
		return null
	for k in ["pos", "yaw", "hp", "items", "flags", "checkpoint"]:
		if not d.has(k):
			return null
	return d
