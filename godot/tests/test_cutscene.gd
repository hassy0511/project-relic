extends RefCounted
## イベントの黒帯（上下の帯）と長押しのスキップのテスト（docs/design/20_ゲームシステム設計.md 20 章「イベントの黒帯とスキップ」）
## ・第 1 章の黒帯の場面（台本がカメラを取るイベント・"cutscene" のイベント）を、見たときと、始まってすぐ・途中でスキップしたときで、
##   終わりの状態（フラグ・持ち物・セル・素材・依頼・部屋・位置と向き・住人・敵・扉・曲・昼夜・セーブ・目的・案内）が同じ
## ・選択肢でスキップが止まる（選んだあと、押したままなら続ける）。遊び（敵の全滅待ち）の手前で止まる。何も止まったままにならない
## ・黒帯はカメラの場面だけ（会話のカメラの会話・戦闘中のひと言・ふつうの入室の会話では出ない）
## ・HUD は隠れて戻る。スマホでは帯は細く、会話の窓に掛からない。右上の「スキップ」は実寸 48px 以上
## ・入力：キーボード（Esc）・パッド（Start）・タッチの長押し。黒帯の場面で短く押せばポーズ（今までどおり）。割り当ては変えられる

var h: TestHelpers

const DT := 1.0 / 60.0
## 黒帯の場面が終わり、何も起きない（会話・台本・部屋の移動が無い）状態がこの刻みだけ続いたら比べる（その間に着地・敵の動きもそろう）
const SETTLE := 90
const MAX_TICKS := 9000
## 第 1 章の本筋のフラグ（立つ順）。場面の前の状態は、その場面のフラグより前を全部立てて作る
const TIMELINE := ["ch1.opening_done", "ch1.chores_started", "ch1.t_move", "ch1.t_jump", "ch1.t_shoot", "ch1.t_dash", "ch1.nico_ran",
	"ch1.nico_rescued", "ch1.scolded", "ch1.debt_scene", "ch1.night", "ch1.ordo_stopped", "ch1.plaza_done", "ch1.got_spark",
	"ch1.fell_to_b2", "ch1.chase_seen", "ch1.r07.seal_open", "ch1.frame_fitted", "ch1.r08.trained", "ch1.blade_online",
	"ch1.first_beacon", "ch1.drive_powered", "ch1.shortcut_open", "ch1.diagnosis", "ch1.boss_intro", "ch1.boss_defeated",
	"ch1.ordo_restarted", "ch1.morning", "ch1.descent_permit", "ch1.drill_developed", "ch1.complete"]


func _init(helpers: TestHelpers) -> void:
	h = helpers


# ---------------------------------------------------------------- 場面の表

## flag より前の本筋のフラグ（朝のあとは夜を消す）
static func _upto(flag: String) -> Array:
	var out: Array = TIMELINE.slice(0, TIMELINE.find(flag))
	if out.has("ch1.morning"):
		out.erase("ch1.night")
	return out


## 第 1 章の黒帯の場面：{ event（始めるイベント）, covers（中で走る黒帯のイベント）, room, flags, pos?, yaw?, pre?（先に走らせるイベント）, pre_pos?, choice? }
static func scenes() -> Array:
	return [
		{"event": "ch1.opening", "room": "ch1.opening", "flags": []},
		{"event": "ch1.nico_run", "room": "ch1.training", "flags": _upto("ch1.nico_ran"), "pos": [4, 0, 36]},
		{"event": "ch1.scold", "room": "ch1.guild", "flags": _upto("ch1.scolded"), "pos": [0, 0, -2]},
		{"event": "ch1.debt", "room": "ch1.workshop", "flags": _upto("ch1.debt_scene"), "pos": [0, 0, -2], "choice": 1},
		{"event": "ch1.sleep", "covers": ["ch1.stop"], "room": "ch1.home", "flags": _upto("ch1.night"), "pos": [-3, 0, 3.5], "yaw": 270},
		{"event": "ch1.plaza", "room": "ch1.mid", "flags": _upto("ch1.plaza_done"), "pos": [0, 0, 3]},
		{"event": "ch1.yana_gun", "room": "ch1.lower", "flags": _upto("ch1.got_spark"), "pos": [-37, 0, 0], "yaw": 90},
		{"event": "ch1.ordo_legs", "room": "ch1.lower", "flags": _upto("ch1.scolded"), "pos": [68.8, 0, -10.5], "yaw": 90, "tag": "昼"},
		{"event": "ch1.ordo_legs", "room": "ch1.lower", "flags": _upto("ch1.plaza_done"), "pos": [68.8, 0, -10.5], "yaw": 90, "tag": "夜"},
		{"event": "ch1.collapse", "room": "ch1.r05", "flags": _upto("ch1.fell_to_b2"), "pos": [0, 0, 3]},
		{"event": "ch1.r07.dead", "room": "ch1.r07", "flags": _upto("ch1.r07.seal_open"), "pre": "ch1.chase", "pre_pos": [0, 0, -12], "pos": [0, 0, 14]},
		{"event": "ch1.frame_fit", "room": "ch1.r08", "flags": _upto("ch1.frame_fitted"), "pos": [0, 0, -4]},
		{"event": "ch1.r12.powered", "room": "ch1.r12", "flags": _upto("ch1.drive_powered") + ["switch.ch1.r12.s1", "switch.ch1.r12.s2"], "pos": [5, 0, -12]},
		{"event": "ch1.diagnosis", "room": "ch1.r18", "flags": _upto("ch1.diagnosis"), "pos": [0, 0, -3]},
		{"event": "ch1.r19.enter", "room": "ch1.r19", "flags": _upto("ch1.boss_intro")},
		{"event": "ch1.boss_down", "room": "ch1.r19", "flags": _upto("ch1.boss_defeated") + ["ch1.boss_defeated"], "pos": [0, 0, 6]},
		{"event": "ch1.restart", "covers": ["ch1.cheer", "ch1.dawn"], "room": "ch1.r20", "flags": _upto("ch1.ordo_restarted"), "pos": [0.9, 0, -6.3]},
		{"event": "ch1.cheer", "covers": ["ch1.dawn"], "room": "ch1.mid", "flags": _upto("ch1.morning")},
		{"event": "ch1.dawn", "room": "ch1.mid", "flags": _upto("ch1.morning")},
		{"event": "ch1.scope", "covers": ["ch1.ending"], "room": "ch1.upper", "flags": _upto("ch1.complete"), "pos": [0, 0, 22.6]},
	]


# ---------------------------------------------------------------- 道具

func _world_game() -> GameSim:
	var g := GameSim.new()
	var vp := SubViewport.new()
	vp.own_world_3d = true
	vp.render_target_update_mode = SubViewport.UPDATE_DISABLED
	vp.size = Vector2i(2, 2)
	h.tree.root.add_child(vp)
	vp.add_child(g)
	g.setup({"world": World.load_manifest("res://content/world.json"), "tuning": TestHelpers.default_tuning(), "seed": 1})
	return g


func _ticks(g: GameSim, n: int, input := {}) -> void:
	for i in n:
		await h.tree.physics_frame
		g.step(InputFrame.of(input))


## 場面の前の状態を作り（フラグ・部屋・立つ所）、イベントを始める（start が偽なら始めない）。部屋のトリガーは走らせない（イベントは直接始める）
func _prepare(sc: Dictionary, start := true) -> GameSim:
	var g := _world_game()
	await h.settle()
	for f in sc.flags:
		g.set_flag(f)
	g.load_room(sc.room, String(sc.get("spawn", "")))
	for t in g.triggers:
		t.fired = true
	await _ticks(g, 4)
	if sc.has("pre"):
		g.player.teleport(_v(sc.pre_pos), 0.0)
		g.story.start_event(sc.pre)
		for i in 600:
			if not g.story.running_event() and g.story.dialogue.is_empty():
				break
			await _ticks(g, 1, {"confirm": i % 6 < 3})
	if sc.has("pos"):
		var yaw := deg_to_rad(float(sc.get("yaw", 0.0)))
		g.player.teleport(_v(sc.pos), yaw)
		g.cam.yaw = yaw
	await _ticks(g, 6)
	g.drain_events()
	if start:
		g.story.start_event(sc.event)
	return g


static func _v(a: Array) -> Vector3:
	return Vector3(a[0], a[1], a[2])


## 何も起きていない（会話・黒帯の場面・スキップ・部屋の移動が無く、台本は終わったか遊びの待ち）
static func _idle(g: GameSim) -> bool:
	if not g.story.dialogue.is_empty() or g.cinematic() or g.story.skipping or not g.room_settled():
		return false
	return not g.story.running_event() or (g.story._has_wait_cond and not Cond.eval(g.story._wait_cond, g))


## 場面を 1 回通す。hold_at：スキップのボタンを押し始める刻み（-1 は見るだけ：会話は決定で送る。押している間は送らない）。
## skip_at：この刻みから、スキップできるようになった最初の刻みで Story.begin_skip を呼ぶ（長押しの 1 秒を待たない。-1 は呼ばない）。
## 選択肢は sc.choice 番目を選ぶ。
## 返り値：{ state, seq（出来事の並び）, saves（オートセーブの中身）, skipped, cine（黒帯の刻み数）, cine_end（黒帯が終わった刻み）, ticks, choice_stop }
func _play(sc: Dictionary, hold_at := -1, skip_at := -1) -> Dictionary:
	var g: GameSim = await _prepare(sc)
	var out := {"seq": [], "saves": [], "skipped": false, "cine": 0, "cine_end": -1, "ticks": 0, "choice_stop": false}
	var seen := false
	var over := false
	var idle := 0
	var choice := int(sc.get("choice", 0))
	for i in MAX_TICKS:
		var f := {}
		var d: Dictionary = g.story.dialogue
		var holding := hold_at >= 0 and i >= hold_at and not over
		if holding:
			f["skip"] = true
		if not d.is_empty():
			if d.has("choices") and int(d.shown) >= String(d.text).length():
				# 選択肢：choice 番目まで下へ動かして決定（スキップを押していても同じ）
				if int(d.sel) != choice:
					f["move_y"] = -1.0 if i % 4 < 2 else 0.0
				else:
					f["confirm"] = i % 4 < 2
			elif not holding:
				f["confirm"] = i % 6 < 3
		await h.tree.physics_frame
		if skip_at >= 0 and i >= skip_at and not out.skipped and g.story.skippable():
			g.story.begin_skip()
		g.step(InputFrame.of(f))
		if g.story.skipping:
			out.skipped = true
			out.choice_stop = out.choice_stop or g.story.skip_at_choice
		_record(g, out)
		if g.cinematic():
			seen = true
			out.cine += 1
		elif seen and not over:
			over = true
			out.cine_end = i
		idle = idle + 1 if over and _idle(g) else 0
		out.ticks = i
		if idle >= SETTLE:
			break
	out["state"] = _state(g)
	h.free_game(g)
	return out


## 刻みの出来事を並びに残す（効果音・揺れ・見た目だけのものは除く。スキップでは鳴らさないので）
func _record(g: GameSim, out: Dictionary) -> void:
	for e in g.drain_events():
		match String(e.type):
			"message":
				out.seq.append("message:" + String(e.text))
			"flagSet":
				out.seq.append("flag:" + String(e.name))
			"hint":
				out.seq.append("hint:" + str(e.text))
			"npcRemoved":
				out.seq.append("npc-:" + String(e.id))
			"roomChanged":
				out.seq.append("room:" + String(e.id))
			"fx":
				out.seq.append("fx:%s:%s" % [e.id, e.get("part", "")])
			"ui":
				out.seq.append("ui:%s:%s" % [e.kind, e.id])
			"doorOpened", "doorClosed":
				out.seq.append("%s:%s" % [e.type, e.id])
			"music":
				out.seq.append("music:" + String(e.id))
			"saved":
				out.seq.append("saved")
			"skipped":
				# スキップは 1 刻みのうちに終わることが多い（Story.end_skip が知らせる）
				out.skipped = true
			"autosave":
				out.seq.append("autosave")
				var s := g.to_save()
				s.erase("playTime")
				out.saves.append(s)


## 比べる状態
static func _state(g: GameSim) -> Dictionary:
	var flags := g.story.flags.keys().filter(func(k): return g.story.flags[k])
	flags.sort()
	var items: Array = g.items.keys()
	items.sort()
	var relics: Array = g.relics.keys()
	relics.sort()
	var chips: Array = g.equipped_chips.keys()
	chips.sort()
	var npcs: Array = g.npcs.map(func(n): return String(n.id))
	npcs.sort()
	var doors := {}
	for d in g.doors:
		doors[d.id] = d.is_open
	return {
		"room": g.room_id, "flags": flags, "items": items, "cells": g.cells, "materials": g.materials.duplicate(), "relics": relics,
		"mark": g.mark, "requests": g.requests.duplicate(), "guild_points": g.guild_points, "chips": chips,
		"objective": g.objective, "music": g.music_id(), "music_override": g.music_override,
		"checkpoint": g.checkpoint, "respawn_room": String(g.respawn.room), "respawn_pos": g.respawn.pos, "respawn_yaw": float(g.respawn.yaw),
		"npcs": npcs, "enemies": g.enemies.map(func(e): return "%s|%s|%s|%s" % [e.kind, e.id, e.group, e.alive]),
		"enemy_pos": g.enemies.map(func(e): return e.pos), "doors": doors,
		"pos": g.player.pos, "yaw": g.player.yaw, "hp": g.player.hp, "max_hp": g.player.max_hp, "heals": g.player.heals,
		"energy": g.player.weapon_energy, "dead": g.player.dead, "locked": g.player_locked,
		"cutscene": g.story.cutscene, "skipping": g.story.skipping, "running": g.story.running_event(),
		"dialogue": String(g.story.dialogue.get("id", "")), "focus": g.cam_focus != null, "eye": g.cam_eye != null,
		"abilities": ["spark", "lock_on", "sword", "dash"].filter(func(a): return g.has_ability(a)),
	}


## 値が同じか（位置・向き・数は 2cm・0.02 まで）
static func _eq(a, b) -> bool:
	if a is Vector3 and b is Vector3:
		return a.distance_to(b) <= 0.02
	if (a is float or a is int) and (b is float or b is int):
		return absf(float(a) - float(b)) <= 0.02
	if a is Array and b is Array:
		if a.size() != b.size():
			return false
		for i in a.size():
			if not _eq(a[i], b[i]):
				return false
		return true
	if a is Dictionary and b is Dictionary:
		if a.size() != b.size():
			return false
		for k in a:
			if not b.has(k) or not _eq(a[k], b[k]):
				return false
		return true
	return a == b


## 見た通しとスキップした通しの終わりが同じか
func _same(tag: String, watch: Dictionary, run: Dictionary) -> void:
	var diffs := []
	for k in watch.state:
		if not _eq(watch.state[k], run.state[k]):
			diffs.append("%s: %s ≠ %s" % [k, str(watch.state[k]), str(run.state[k])])
	h.expect(diffs.is_empty(), "%s：終わりの状態が見たときと同じ（%s）" % [tag, "; ".join(diffs)])
	var first := -1
	for i in maxi(watch.seq.size(), run.seq.size()):
		if i >= watch.seq.size() or i >= run.seq.size() or watch.seq[i] != run.seq[i]:
			first = i
			break
	h.expect(first < 0, "%s：出来事（通知・フラグ・案内・部屋・合図・セーブ）が同じ順に出る（%d 番目：%s ≠ %s）" % [tag, first,
		str(watch.seq[first]) if first >= 0 and first < watch.seq.size() else "-", str(run.seq[first]) if first >= 0 and first < run.seq.size() else "-"])
	var saves_ok: bool = watch.saves.size() == run.saves.size()
	for i in mini(watch.saves.size(), run.saves.size()):
		saves_ok = saves_ok and _eq(watch.saves[i], run.saves[i])
	h.expect(saves_ok, "%s：オートセーブの回数と中身が同じ（%d 回／%d 回）" % [tag, watch.saves.size(), run.saves.size()])


# ---------------------------------------------------------------- 見たときとスキップしたときで同じ

## 第 1 章の黒帯の場面（カメラの手順を持つ・"cutscene" のイベント）がすべて、この表で確かめられている
func test_cutscene_table_covers_chapter1() -> void:
	var g := _world_game()
	await h.settle()
	var covered := {}
	for sc in scenes():
		covered[sc.event] = true
		for c in sc.get("covers", []):
			covered[c] = true
	var missing := []
	var found := 0
	for id in g.events_data:
		if not String(id).begins_with("ch1."):
			continue
		var steps: Array = g.events_data[id].steps
		if g.story.event_is_cutscene(id) or g.story._steps_cam(steps, {}):
			found += 1
			if not covered.has(id):
				missing.append(id)
	h.expect(found >= 19 and missing.is_empty(), "第 1 章の黒帯の場面 %d 本を、見る・スキップで比べる（表に無い：%s）" % [found, missing])
	# 黒帯にしないもの：住人に話しかけて始まる会話・入室のひと言・戦闘の波
	for id in ["ch1.permit", "ch1.burton.guild", "ch1.r02.enter", "ch1.r10.enter", "ch1.r09.wave2", "ch1.nico_fight", "ch1.chase", "ch1.beacon"]:
		h.expect(not g.story.event_uses_camera(id), "%s は黒帯の場面ではない" % id)
	h.free_game(g)


## どの場面も、見たときと、スキップしたときで終わりの状態が同じ。スキップは：
## ・始まってすぐ長押し（1 秒押し続けた所でスキップ）
## ・最初の刻み（黒帯になった最初の刻みで、長押しを待たずに）
## ・途中（見たときの黒帯の場面のちょうど真ん中の刻みで）
## ・途中の長押し（真ん中でスキップになるよう、その 1 秒前から押す。残りが短くて押し切る前に終わったときは、そのまま見たのと同じ）
func test_skip_matches_watching() -> void:
	var t0 := Time.get_ticks_msec()
	for sc in scenes():
		var tag := "%s%s" % [sc.event, "（%s）" % sc.tag if sc.has("tag") else ""]
		var watch: Dictionary = await _play(sc)
		h.expect(watch.cine > 0 and watch.cine_end > 0 and not watch.skipped, "%s：黒帯の場面になり、終わる（%d 刻み）" % [tag, watch.cine])
		var mid: int = maxi(1, watch.cine_end / 2)
		var runs := [["始まってすぐ", await _play(sc, 0), true], ["最初の刻み", await _play(sc, -1, 0), true],
			["途中", await _play(sc, -1, mid), true], ["途中の長押し", await _play(sc, maxi(0, mid - 60)), false]]
		for r in runs:
			var run: Dictionary = r[1]
			if r[2]:
				h.expect(run.skipped, "%s（%sでスキップ）：スキップした" % [tag, r[0]])
			_same("%s（%sでスキップ）" % [tag, r[0]], watch, run)
		print("    %s：見る %d 刻み（黒帯 %d）／すぐ %d・最初 %d・途中 %d・途中の長押し %d 刻み%s" % [tag, watch.ticks, watch.cine,
			runs[0][1].ticks, runs[1][1].ticks, runs[2][1].ticks, runs[3][1].ticks, "" if runs[3][1].skipped else "（押し切る前に終わった）"])
	print("    第 1 章の黒帯の場面 %d 本 × 5 通り（%.1f 秒）" % [scenes().size(), (Time.get_ticks_msec() - t0) / 1000.0])


# ---------------------------------------------------------------- 選択肢・長押し・遊びの手前

static func _scene(event: String, tag := "") -> Dictionary:
	for sc in scenes():
		if sc.event == event and (tag == "" or sc.get("tag", "") == tag):
			return sc
	return {}


## 選択肢：スキップは選択肢で止まり、プレイヤーが選ぶ（勝手に選ばない）。選んだときにまだ押していれば続けて終わりまで、
## 離していればスキップは終わり、選んだ先の会話からふだんどおり見る
func test_skip_stops_at_choice() -> void:
	var sc := _scene("ch1.debt")
	for keep in [true, false]:
		var g: GameSim = await _prepare(sc)
		var stopped := false
		for i in 600:
			await _ticks(g, 1, {"skip": true})
			if g.story.skip_at_choice:
				stopped = true
				break
		var d: Dictionary = g.story.dialogue
		h.expect(stopped and d.get("id", "") == "ch1.debt" and d.has("choices") and int(d.shown) == String(d.text).length(),
			"長押しでスキップすると、選択肢の行（全文）で止まる")
		h.expect(g.story.skipping and g.cinematic() and not g.flag("ch1.debt_scene"), "まだ場面の途中（ch1.debt_scene はまだ）")
		await _ticks(g, 90, {"skip": keep})
		h.expect(g.story.skip_at_choice and g.story.dialogue.has("choices") and int(g.story.dialogue.sel) == 0,
			"%s、選ぶまでは止まったまま（勝手に選ばない）" % ("押し続けても" if keep else "離しても"))
		await _ticks(g, 1, {"skip": keep, "move_y": -1.0})
		await _ticks(g, 1, {"skip": keep})
		h.expect(int(g.story.dialogue.sel) == 1, "選択肢を動かせる（スキップのボタンを%s）" % ("押したまま" if keep else "離して"))
		await _ticks(g, 1, {"skip": keep, "confirm": true})
		if keep:
			h.expect(g.flag("ch1.debt_scene") and not g.cinematic() and not g.story.skipping and g.story.dialogue.is_empty(),
				"選んだときに押していれば、続けて終わりまで飛ばす")
			h.expect(g.objective.contains("家に帰って"), "最後の手順（目的）まで走る（%s）" % g.objective)
		else:
			d = g.story.dialogue
			h.expect(not g.story.skipping and d.get("id", "") == "ch1.yana.debt_b" and int(d.shown) < String(d.text).length(),
				"離して選ぶとスキップは終わり、選んだ先の会話がふだんどおり 1 文字ずつ出る（%s）" % d.get("id", ""))
			h.expect(g.cinematic() and not g.flag("ch1.debt_scene"), "黒帯の場面は続く")
			await _ticks(g, 2)
			h.expect(g.skippable(), "もう一度長押しすれば飛ばせる（案内が出る）")
			for i in 900:
				if g.flag("ch1.debt_scene") and not g.story.running_event():
					break
				await _ticks(g, 1, {"confirm": i % 6 < 3})
			h.expect(g.flag("ch1.debt_scene") and not g.cinematic(), "見て進めると、終わりまで進む")
		h.free_game(g)


## 長押し：1 秒に届くまではスキップしない（途中で離すと 0 から）。スキップしたあと押したままでは、次の黒帯の場面を飛ばさない
func test_skip_needs_full_hold_and_release() -> void:
	var g: GameSim = await _prepare(_scene("ch1.ordo_legs", "昼"))
	await _ticks(g, 2)
	h.expect(g.cinematic() and g.skippable() and g.player_locked, "見下ろす場面：黒帯で、スキップできる")
	await _ticks(g, 30, {"skip": true})
	h.near(g.skip_hold, 0.5, 0.02, "押している秒数を数える")
	await _ticks(g, 1)
	h.expect(g.skip_hold == 0.0 and g.cinematic(), "途中で離すと数え直し")
	await _ticks(g, 59, {"skip": true})
	h.expect(g.cinematic() and g.cam_eye != null, "1 秒に届くまではスキップしない（%.2f 秒）" % g.skip_hold)
	await _ticks(g, 1, {"skip": true})
	h.expect(not g.cinematic() and not g.story.running_event() and not g.player_locked and g.cam_eye == null and g.cam_focus == null,
		"1 秒押し続けるとスキップ（カメラも操作も戻る）")
	g.story.start_event("ch1.ordo_legs")
	await _ticks(g, 120, {"skip": true})
	h.expect(g.cinematic() and g.skip_hold == 0.0, "押したまま次の場面になっても、離すまでは数えない（続けて飛ばさない）")
	await _ticks(g, 1)
	await _ticks(g, 60, {"skip": true})
	h.expect(not g.cinematic() and not g.story.running_event(), "離してからもう一度 1 秒押すと飛ばせる")
	h.free_game(g)


## 試しの部屋：台本 events を持つ 1 部屋の世界（会話 t.a・t.b・t.c）
func _test_world(events: Dictionary, npcs: Array = []) -> GameSim:
	var room := {"name": "t", "playerStart": "start", "geometry": [{"t": "box", "pos": [0, -1, 0], "size": [60, 1, 60]}],
		"markers": {"start": {"pos": [0, 0, 0], "yaw": 0}}, "props": npcs, "enemies": [], "checkpoints": [], "triggers": []}
	var line := func(who: String, text: String) -> Dictionary: return {"who": who, "face": "normal", "text": text}
	var g := h.make_world_game({"start": {"room": "t.r", "spawn": "start"}, "areas": [{"id": "t", "name": "t", "rooms": {"r": room}}],
		"dialogues": {"t.a": {"lines": [line.call("ナゴミ", "来るよ"), line.call("ハル", "わかった")]},
			"t.b": {"lines": [line.call("ナゴミ", "やったね")]}, "t.c": {"lines": [line.call("アオ", "やあ")]}},
		"events": events})
	await h.settle()
	await _ticks(g, 3)
	return g


## スキップは遊びの手前で止まる：封印室は操作が戻る所（freeze false）まで（ナゴミの訓練の会話はふだんどおり出る）。
## 操作できる間の敵の全滅待ち（wait_until）では止まり、黒帯も終わる。操作が止まったままの待ちでは黒帯は続くが、待つ間はスキップできない
func test_skip_stops_where_play_resumes() -> void:
	var g: GameSim = await _prepare(_scene("ch1.frame_fit"))
	await _ticks(g, 2)
	g.story.begin_skip()
	await _ticks(g, 1)
	h.expect(g.flag("ch1.frame_fitted") and g.has_item("frame.vestige") and g.has_ability("lock_on"), "封印室：適合までの手順が走る")
	var d: Dictionary = g.story.dialogue
	h.expect(not g.cinematic() and not g.story.skipping and not g.player_locked, "操作が戻る所でスキップが止まる")
	h.expect(d.get("id", "") == "ch1.fit.t1" and int(d.shown) < String(d.text).length(), "訓練の説明（ch1.fit.t1）は飛ばさずに出る（%s）" % d.get("id", ""))
	for i in 600:
		if g.story.dialogue.is_empty():
			break
		await _ticks(g, 1, {"confirm": i % 6 < 3})
	await _ticks(g, 3)
	h.expect(g.enemies.size() == 1 and g.enemies[0].group == "r08_t1" and not g.skippable() and not g.cinematic(), "標的が出て、遊びに戻る（黒帯なし）")
	h.free_game(g)
	# 操作できる間の全滅待ち
	g = await _test_world({"t.fight": {"cutscene": true, "steps": [{"say": "t.a"}, {"spawn": [{"type": "mini", "pos": [0, 0, 8], "group": "g1"}]},
		{"wait_until": {"cleared": "g1"}}, {"say": "t.b"}, {"flag": "t.done"}]}})
	g.story.start_event("t.fight")
	await _ticks(g, 2)
	h.expect(g.cinematic() and g.skippable(), "黒帯の場面（会話）")
	await _ticks(g, 60, {"skip": true})
	h.expect(not g.story.skipping and not g.cinematic() and g.enemies.size() == 1 and g.story.dialogue.is_empty() and not g.flag("t.done"),
		"敵の全滅待ちの手前で止まる（敵は出ている。続きの会話はまだ）")
	h.expect(not g.skippable(), "遊びの間はスキップの案内を出さない")
	g.damage_enemy(g.enemies[0], 9999.0, Vector3.ZERO, {})
	await _ticks(g, 3)
	h.expect(g.story.dialogue.get("id", "") == "t.b" and not g.cinematic(), "倒すと続きの会話がふだんどおり出る（黒帯は戻らない）")
	h.free_game(g)
	# 操作が止まったままの待ち
	g = await _test_world({"t.frozen": {"cutscene": true, "steps": [{"freeze": true}, {"say": "t.a"}, {"wait_until": "t.go"}, {"say": "t.b"},
		{"freeze": false}, {"flag": "t.end"}]}})
	g.story.start_event("t.frozen")
	await _ticks(g, 2)
	await _ticks(g, 60, {"skip": true})
	h.expect(g.cinematic() and not g.story.skipping and not g.skippable() and g.player_locked and not g.flag("t.end"),
		"操作が止まったまま条件を待つ間：黒帯は続くが、スキップは止まり、案内も出さない")
	await _ticks(g, 30, {"skip": true})
	h.expect(not g.story.skipping and g.skip_hold == 0.0, "待っている間は長押しを数えない")
	g.set_flag("t.go")
	await _ticks(g, 2)
	h.expect(g.skippable(), "条件が満ちると、またスキップできる")
	await _ticks(g, 1)
	await _ticks(g, 60, {"skip": true})
	h.expect(g.flag("t.end") and not g.player_locked and not g.cinematic(), "残りを飛ばして操作が戻る")
	h.free_game(g)


## スキップの間は効果音・画面の揺れを出さない（曲は終わりの状態から決まる）。通知・フラグ・見た目の合図（skipped つき）は出る
func test_skip_drops_sound_cues() -> void:
	var g: GameSim = await _test_world({"t.noisy": {"cutscene": true, "steps": [{"freeze": true}, {"say": "t.a"}, {"sfx": "alert"}, {"shake": 0.9},
		{"music": "none"}, {"message": "ゴゴゴ"}, {"fx": "frame_fit", "part": "legs"}, {"wait": 2.0}, {"music": "bgm_end"}, {"sfx": "item"},
		{"freeze": false}]}})
	g.story.start_event("t.noisy")
	await _ticks(g, 2)
	g.drain_events()
	g.story.begin_skip()
	await _ticks(g, 1)
	var ev := g.drain_events()
	var types := ev.map(func(e): return String(e.type))
	h.expect(not types.has("sfx") and not types.has("shake"), "効果音・揺れは出さない（%s）" % str(types))
	var fxs: Array = ev.filter(func(e): return e.type == "fx")
	h.expect(types.has("message") and fxs.size() == 1 and fxs[0].get("skipped", false) and types.has("skipped"),
		"通知と、skipped の付いた見た目の合図・スキップの知らせは出る")
	h.expect(g.music_override == "bgm_end" and g.music_id() == "bgm_end", "曲は最後に指定した曲（%s）" % g.music_id())
	await _ticks(g, 1)
	g.drain_events()
	g.emit_event({"type": "sfx", "id": "item"})
	h.expect(g.drain_events().size() == 1, "スキップが終われば効果音は今までどおり")
	h.free_game(g)


## 見た目の終わりの姿：フレームの部品はすぐ付き（装着の光の粒を出さない。合図を待ったままにならない）、記憶の光は流さない
func test_skip_view_end_states() -> void:
	var g: GameSim = await _prepare(_scene("ch1.r12.powered"), false)
	var pv := PlayerView.new()
	h.tree.root.add_child(pv)
	pv.load_model("res://assets/models/haru_r.glb")
	var fx := Fx.new()
	h.tree.root.add_child(fx)
	var view := func(game: GameSim) -> void:
		for e in game.drain_events():
			fx.handle(e)
		pv.set_frame_parts(game.has_ability("lock_on"), game.has_ability("sword"), game.has_ability("dash"))
		fx.sync(game, DT, pv, null)
		pv.sync(game.player, game, DT, Vector3.FORWARD)
	for i in 3:
		await h.tree.physics_frame
		g.step(InputFrame.new())
		view.call(g)
	g.story.start_event("ch1.r12.powered")
	for i in 3:
		await h.tree.physics_frame
		g.step(InputFrame.new())
		view.call(g)
	var legs: Node3D = pv.frame_nodes.get("legs")
	h.expect(legs != null and not legs.visible and g.cinematic() and g.has_ability("dash") and fx._fit_wait.has("legs"),
		"駆動回廊：動力の場面、脚の部品は合図を待って隠れている")
	g.story.begin_skip()
	await h.tree.physics_frame
	g.step(InputFrame.new())
	view.call(g)
	var burst := fx.vfx.count()
	for i in 3:
		await h.tree.physics_frame
		g.step(InputFrame.new())
		view.call(g)
	h.expect(g.has_ability("dash") and legs.visible and fx._fit_wait.is_empty(), "スキップすると脚の部品はすぐ付く（合図を待ったままにならない）")
	h.expect(burst < 6, "装着の光の粒・かけらは出さない（%d 粒）" % burst)
	h.free_game(g)
	# 炉心：ノードの記憶の合図を飛ばすと、光は流さない
	g = await _prepare(_scene("ch1.restart"))
	for i in 2:
		await h.tree.physics_frame
		g.step(InputFrame.new())
		view.call(g)
	g.story.begin_skip()
	for i in 40:
		await h.tree.physics_frame
		g.step(InputFrame.new())
		view.call(g)
	h.expect(g.room_id == "ch1.home" and g.flag("ch1.morning") and fx._node_t <= 0.0, "再始動を飛ばすと翌朝の家へ。記憶の光は流れない")
	fx.queue_free()
	pv.queue_free()
	h.free_game(g)


# ---------------------------------------------------------------- 入力（キーボード・パッド）とポーズ

const TEST_CFG := "user://test_input_cutscene.cfg"


func _key(code: int, pressed := true) -> InputEventKey:
	var e := InputEventKey.new()
	e.physical_keycode = code
	e.pressed = pressed
	return e


## 初期の割り当て：キーボードは Esc、パッドは Start（ポーズと同じボタン）。黒帯の場面で短く押すと離したときにポーズ、
## 押し続けるとポーズにしない（スキップの長押し）。黒帯でなければ押した瞬間にポーズ（今までどおり）。設定画面で割り当てを変えられる
func test_skip_inputs_and_pause() -> void:
	PadConfig.path = TEST_CFG
	DirAccess.remove_absolute(TEST_CFG)
	InputSource.setup_actions()
	h.expect(PadConfig.keys.get("skip", []) == [KEY_ESCAPE] and PadConfig.pad.get("skip", "") == "b6", "初期：スキップは Esc と Start（ポーズと同じ）")
	var start := InputEventJoypadButton.new()
	start.button_index = 6
	start.pressed = true
	h.expect(start.is_action_pressed("skip") and start.is_action_pressed("pause") and _key(KEY_ESCAPE).is_action_pressed("skip"),
		"Start・Esc は、スキップとポーズの両方の割り当てに当たる")
	h.expect(Hud.skip_key_text("keyboard") == "Esc" and Hud.skip_key_text("pad") == "Start", "案内のボタン名：Esc ／ Start")
	PadConfig.style = "ps"
	h.expect(Hud.skip_key_text("pad") == "OPTIONS", "PlayStation 表記では OPTIONS")
	PadConfig.style = "auto"
	var src := InputSource.new()
	h.tree.root.add_child(src)
	Input.action_press("skip")
	h.expect(src.sample(DT).skip, "押している間、入力の skip が立つ")
	Input.action_release("skip")
	h.expect(not src.sample(DT).skip, "離すと skip は消える")
	# 黒帯の場面で短く押す（0.1 秒）→ 離したときにポーズ
	src._input(_key(KEY_ESCAPE))
	Input.action_press("skip")
	var opened := false
	for i in 6:
		opened = opened or src.take_pause(true, DT)
	h.expect(not opened, "黒帯の場面では、押した瞬間にはポーズを開かない")
	Input.action_release("skip")
	h.expect(src.take_pause(true, DT), "すぐ離すとポーズが開く（短く押せば今までどおりポーズ）")
	# 押し続ける（0.7 秒）→ 離してもポーズにしない
	src._input(_key(KEY_ESCAPE))
	Input.action_press("skip")
	for i in 42:
		opened = opened or src.take_pause(true, DT)
	Input.action_release("skip")
	opened = opened or src.take_pause(true, DT)
	h.expect(not opened, "押し続けてから離しても、ポーズは開かない（スキップの長押し）")
	# 黒帯でないとき
	src._input(_key(KEY_ESCAPE))
	Input.action_press("skip")
	h.expect(src.take_pause(false, DT), "黒帯の場面でなければ、押した瞬間にポーズ（今までどおり）")
	Input.action_release("skip")
	# 割り当ての変更：スキップは別の組なので、地図（Tab）・ポーズ（Esc）と入れ替わらない
	h.expect(PadConfig.assign_key("skip", KEY_TAB) == "" and PadConfig.keys.map == [KEY_TAB] and PadConfig.keys.pause == [KEY_ESCAPE],
		"スキップを Tab にしても、地図・ポーズの割り当てはそのまま")
	h.expect(_key(KEY_TAB).is_action_pressed("skip") and not _key(KEY_ESCAPE).is_action_pressed("skip"), "InputMap にも反映される")
	src._input(_key(KEY_ESCAPE))
	h.expect(src.take_pause(true, DT), "スキップを別のキーにすると、Esc は黒帯の場面でもすぐポーズ")
	h.expect(PadConfig.assign_pad("skip", "b3") == "" and PadConfig.pad.special == "b3" and PadConfig.pad.skip == "b3", "パッドもほかの操作と重ねられる（Y）")
	PadConfig.load_file()
	h.expect(PadConfig.keys.skip == [KEY_TAB] and PadConfig.pad.skip == "b3", "保存して読み直しても同じ")
	# 設定の画面・操作の説明
	var menu := Menu.new()
	h.tree.root.add_child(menu)
	await h.tree.process_frame
	menu.show_controls(func(): pass)
	await h.tree.process_frame
	var row := menu.buttons.filter(func(b): return b.text == "スキップ（長押し）")
	h.expect(row.size() == 1, "操作の設定に「スキップ（長押し）」の行がある")
	if row.size() == 1:
		row[0].pressed.emit()
		h.expect(menu.feed_event(_key(KEY_BACKSPACE)), "行を決定して押したキーが割り当たる")
		h.expect(PadConfig.keys.skip == [KEY_BACKSPACE], "スキップ：Backspace")
	h.expect(PauseInfo.help_text(false).contains("場面のスキップ") and PauseInfo.help_text(true).contains("「スキップ」を長押し"), "ポーズの操作の説明に出る")
	menu.queue_free()
	PadConfig.reset_all()
	h.expect(PadConfig.keys.skip == [KEY_ESCAPE] and PadConfig.pad.skip == "b6", "初期に戻すと Esc・Start")
	src.queue_free()
	DirAccess.remove_absolute(TEST_CFG)
	PadConfig.path = PadConfig.PATH
	InputSource.setup_actions()


# ---------------------------------------------------------------- 黒帯と HUD

## 試しの HUD：大きさ size の画面に Hud とカメラを置く。compact はスマホの配置
func _hud(size: Vector2, compact := false) -> Array:
	var vp := SubViewport.new()
	vp.size = Vector2i(size.round())
	h.tree.root.add_child(vp)
	var hud := Hud.new()
	vp.add_child(hud)
	var cam := Camera3D.new()
	vp.add_child(cam)
	hud.compact = compact
	await h.tree.process_frame
	return [vp, hud, cam]


func _sync_hud(hud: Hud, g: GameSim, cam: Camera3D, frames: int) -> void:
	for i in frames:
		hud.sync(g, cam, DT)
	await h.tree.process_frame


## 黒帯はカメラを取る場面・"cutscene" の場面だけ。住人に話しかけた会話（会話のカメラ）・入室のひと言・戦闘中のひと言では出ない
func test_letterbox_only_for_cutscenes() -> void:
	var g: GameSim = await _prepare({"event": "", "room": "ch1.mid", "flags": _upto("ch1.debt_scene")}, false)
	var made: Array = await _hud(Vector2(1920, 1080))
	var hud: Hud = made[1]
	var cam: Camera3D = made[2]
	# 雑貨屋の店主に話しかける（会話のカメラ）
	var n = g.npcs.filter(func(x): return x.id == "npc_shopkeeper")[0]
	g.player.teleport(Vector3(24, 0, 3.0), U.dir_to_yaw(n.pos.x - 24.0, n.pos.z - 3.0))
	await _ticks(g, 6)
	await _ticks(g, 1, {"jump": true})
	await _ticks(g, 20)
	h.expect(g.talk_npc == "npc_shopkeeper" and not g.story.dialogue.is_empty() and not g.cinematic(), "住人との会話は黒帯の場面ではない（会話のカメラ）")
	h.expect(TalkCamera.partner(g) != null, "会話のカメラは使う")
	await _sync_hud(hud, g, cam, 30)
	h.expect(hud.cinema_amount() == 0.0 and not hud._bars[0].visible and hud._play.visible, "黒帯は出ず、HUD はそのまま")
	g.story.dialogue = {}
	g.story._event_queue.clear()
	g.story._waiting_dialogue = false
	await _ticks(g, 2)
	# 入室のひと言（トリガーの会話。カメラを取らない）
	g.story.start_event("ch1.r02.enter")
	await _ticks(g, 2)
	h.expect(not g.story.dialogue.is_empty() and not g.cinematic(), "入室のひと言（ch1.r02.enter）は黒帯の場面ではない")
	await _sync_hud(hud, g, cam, 30)
	h.expect(hud.cinema_amount() == 0.0 and not hud._bars[0].visible, "入室のひと言では黒帯は出ない")
	for i in 300:
		if not g.story.running_event() and g.story.dialogue.is_empty():
			break
		await _ticks(g, 1, {"confirm": i % 6 < 3})
	# 戦闘中のひと言（字幕）
	hud.show_subtitle("閂", "侵入者を排除する")
	await _sync_hud(hud, g, cam, 10)
	h.expect(hud._sub.is_visible_in_tree() and hud.cinema_amount() == 0.0 and not hud._bars[0].visible, "戦闘中のひと言では黒帯は出ない")
	# カメラを取る場面（中段から見えるものは無いので、台本のカメラだけの試しのイベント）→ 黒帯
	g.events_data["t.cam"] = {"steps": [{"camera": {"pos": [0, 0, 20], "height": 2.0, "time": 1.5}}, {"camera": {}}]}
	g.story.start_event("t.cam")
	await _ticks(g, 1)
	h.expect(g.cinematic() and g.cam_focus != null, "台本のカメラの手順で黒帯の場面になる")
	await _sync_hud(hud, g, cam, 10)
	h.between(hud.cinema_amount(), 0.4, 0.7, "黒帯は 0.3 秒で出す（10 刻みで途中）")
	await _sync_hud(hud, g, cam, 10)
	var vs: Vector2 = hud._root.size
	h.expect(hud.cinema_amount() == 1.0 and hud._bars[0].visible and absf(hud._bars[0].size.y - hud.cinema_bar(vs)) < 0.5, "出しきると帯の太さ %.0f" % hud._bars[0].size.y)
	await _ticks(g, 100)
	h.expect(not g.cinematic(), "台本が終わると黒帯の場面も終わる")
	await _sync_hud(hud, g, cam, 30)
	h.expect(hud.cinema_amount() == 0.0 and not hud._bars[0].visible and hud._play.visible, "黒帯は 0.3 秒で引っ込み、HUD が戻る")
	made[0].queue_free()
	h.free_game(g)
	# 住人に話しかけて始まるイベントが黒帯の場面（"cutscene" のイベント）を呼ぶなら、会話のカメラは使わない
	g = await _test_world({"t.npc": {"steps": [{"say": "t.c"}, {"event": "t.scene"}]}, "t.scene": {"cutscene": true, "steps": [{"say": "t.b"}]}},
		[{"type": "npc", "id": "npc_a", "name": "アオ", "pos": [0, 0, 2], "yaw": 180, "event": "t.npc"}])
	await _ticks(g, 1, {"jump": true})
	await _ticks(g, 2)
	h.expect(g.talk_npc == "" and TalkCamera.partner(g) == null, "黒帯の場面を呼ぶ住人のイベントでは、会話のカメラを使わない")
	h.free_game(g)


## HUD：黒帯の間は遊びの表示（HP・セル・目的・案内など）を隠し、会話の窓は残す。終わると戻る。スキップの案内（キーボード・パッド）は右上の帯の中。
## スマホ（844×390）：帯は細く（下の帯は会話の窓の下のすき間に収まる）、右上の「スキップ」は実寸 48px 以上で、会話の窓に掛からない。
## ほかの画面のボタンは押せない。会話の窓のタップは今までどおり送れる
func test_hud_hidden_and_restored() -> void:
	var sc := _scene("ch1.frame_fit")
	var g: GameSim = await _prepare(sc, false)
	g.objective = "奥へ進む"
	var made: Array = await _hud(Vector2(1920, 1080))
	var hud: Hud = made[1]
	var cam: Camera3D = made[2]
	await _sync_hud(hud, g, cam, 3)
	h.expect(hud._play.visible and hud._vitals.is_visible_in_tree() and hud._objective_box.is_visible_in_tree() and not hud._bars[0].visible,
		"場面の前：HP・目的が出ていて、黒帯は無い")
	g.story.start_event(sc.event)
	await _ticks(g, 2)
	await _sync_hud(hud, g, cam, 24)
	var vs: Vector2 = hud._root.size
	h.expect(not hud._play.visible and not hud._vitals.is_visible_in_tree() and not hud._objective_box.is_visible_in_tree(),
		"黒帯の間：HP・ゲージ・目的などの遊びの表示は隠れる")
	h.expect(hud._bars[0].visible and hud._bars[1].visible and absf(hud._bars[1].position.y + hud._bars[1].size.y - vs.y) < 0.5
		and absf(hud._bars[0].size.y - vs.y * Hud.CINE_BAR) < 0.5, "上下に黒帯（画面の高さの %.1f%%）" % (Hud.CINE_BAR * 100.0))
	h.expect(hud._skip_box.is_visible_in_tree() and hud._skip_key.text == "Esc" and hud._skip_label.text == "長押しでスキップ", "長押しでスキップの案内（Esc）")
	var sr: Rect2 = hud._skip_box.get_global_rect()
	h.expect(sr.position.y >= 0.0 and sr.end.y <= hud._bars[0].size.y + 0.5 and sr.end.x <= vs.x, "案内は右上、上の帯の中")
	hud.device = "pad"
	await _sync_hud(hud, g, cam, 1)
	h.expect(hud._skip_key.text == "Start", "パッドでは Start")
	hud.device = "keyboard"
	# 会話の窓は残り、帯より上に描く
	for i in 400:
		if not g.story.dialogue.is_empty():
			break
		await _ticks(g, 1)
	await _sync_hud(hud, g, cam, 2)
	h.expect(hud._dlg.is_visible_in_tree() and hud._dlg.get_index() > hud._bars[1].get_index(), "会話の窓は出たまま（帯の上に描く）")
	# 長押しの進み
	await _ticks(g, 30, {"skip": true})
	await _sync_hud(hud, g, cam, 1)
	h.near(hud._skip_ring.progress, 0.5, 0.03, "押している間、進みの輪が回る")
	await _ticks(g, 31, {"skip": true})
	await _ticks(g, 2)
	h.expect(not g.cinematic() and g.flag("ch1.frame_fitted"), "1 秒でスキップ")
	await _sync_hud(hud, g, cam, 24)
	h.expect(hud._play.visible and hud._vitals.is_visible_in_tree() and not hud._bars[0].visible and not hud._skip_box.is_visible_in_tree(),
		"黒帯が終わると、遊びの表示が戻る（案内も消える）")
	h.expect(hud._dlg.is_visible_in_tree(), "続きの会話（訓練の説明）は出る")
	made[0].queue_free()
	# スマホ（844×390、画素の細かさ 3）
	var win := Vector2(844, 390) * 3.0
	var f := TouchControls.ui_scale_for(390.0)
	var pvs := Vector2(1080.0 * win.x / win.y, 1080.0) / f
	var px := TouchControls.real_px_per_unit(win.y, 3.0, pvs.y)
	made = await _hud(pvs, true)
	hud = made[1]
	cam = made[2]
	var vp: SubViewport = made[0]
	InputSource.setup_actions()
	var tc := TouchControls.new()
	vp.add_child(tc)
	var src := InputSource.new()
	vp.add_child(src)
	src.touch = tc
	tc.activate()
	tc.set_shown(true)
	tc.tap_probe = hud.dialogue_tap_at
	h.free_game(g)
	g = await _prepare(sc)
	var step := func() -> void:
		tc.cinema = g.cinematic()
		tc.skip_shown = g.skippable() or g.story.skipping
		tc.skip_progress = g.skip_hold / GameSim.SKIP_HOLD
		g.step(src.sample(DT))
		hud.sync(g, cam, DT)
	for i in 400:
		step.call()
		if i % 10 == 0:
			await h.tree.process_frame
		if not g.story.dialogue.is_empty() and hud.cinema_amount() >= 1.0:
			break
	await h.tree.process_frame
	for i in 3:
		step.call()
	await h.tree.process_frame
	var bar: Rect2 = hud._bars[1].get_global_rect()
	var dlg: Rect2 = hud._dlg.get_global_rect()
	h.expect(hud._bars[1].visible and bar.size.y <= pvs.y * Hud.CINE_BAR_TOUCH + 0.5, "スマホの帯は細い（%.1f px）" % (bar.size.y * px))
	h.expect(hud._dlg.is_visible_in_tree() and bar.position.y >= dlg.end.y and not hud._bars[0].get_global_rect().intersects(dlg),
		"下の帯は会話の窓の下のすき間に収まり、窓にも文字にも掛からない（帯の上 %.0f、窓の下 %.0f）" % [bar.position.y, dlg.end.y])
	h.expect(not hud._skip_box.is_visible_in_tree(), "スマホでは HUD の案内の代わりに、右上のボタン")
	var b: Array = TouchControls.skip_layout(pvs)
	var ring: float = TouchControls.disc_diameter(b[3]) * px
	var hit: float = TouchControls.hit_radius(b[3], pvs.y)
	h.expect(ring >= TouchControls.MIN_REAL_PX and hit * 2.0 * px >= TouchControls.MIN_REAL_PX, "「スキップ」の輪 %.1fpx・押せる範囲 %.1fpx（48px 以上）" % [ring, hit * 2.0 * px])
	var hit_rect := Rect2(b[2] - Vector2(hit, hit), Vector2(hit, hit) * 2.0)
	h.expect(not hit_rect.intersects(dlg) and Rect2(Vector2.ZERO, pvs).encloses(hit_rect) and b[2].x > pvs.x * 0.75 and b[2].y < pvs.y * 0.3,
		"「スキップ」は右上で、会話の窓に掛からず、画面の中")
	h.expect(b[2].y - hit >= hud._bars[0].size.y, "上の帯の下に置く")
	# ほかのボタンは押せない（跳ぶ・撃つの所に触れても何も起きない）。「スキップ」は押している間 skip
	var jump_at: Vector2 = TouchControls.layout_for(TouchControls.BUTTONS, pvs)[0][2]
	_touch(tc, 1, jump_at, true)
	_touch(tc, 2, b[2], true)
	var fr := src.sample(DT)
	h.expect(not fr.jump and fr.skip and tc.button("skip") and not tc.button("jump"), "黒帯の間は「スキップ」だけ押せる")
	_touch(tc, 1, jump_at, false)
	_touch(tc, 2, b[2], false)
	h.expect(not src.sample(DT).skip, "離すと skip は消える")
	# 会話の窓のタップで送れる
	var d: Dictionary = g.story.dialogue
	var idx := int(d.index)
	var text := String(d.text)
	var tap := func(pos: Vector2) -> void:
		_touch(tc, 7, pos, true)
		_touch(tc, 7, pos + Vector2(2, 2), false)
	for i in 2:
		tap.call(dlg.get_center())
		step.call()
		step.call()
	h.expect(String(g.story.dialogue.get("text", "")) != text or int(g.story.dialogue.get("index", -1)) != idx or g.story.dialogue.is_empty(),
		"黒帯の間も、会話の窓のタップで送れる")
	# 「スキップ」を 1 秒押す
	_touch(tc, 2, b[2], true)
	for i in 62:
		step.call()
	_touch(tc, 2, b[2], false)
	step.call()
	h.expect(g.flag("ch1.frame_fitted") and not g.cinematic(), "「スキップ」を 1 秒押すと飛ばせる")
	tc.queue_free()
	src.queue_free()
	vp.queue_free()
	h.free_game(g)


func _touch(tc: TouchControls, index: int, pos: Vector2, pressed: bool) -> void:
	var e := InputEventScreenTouch.new()
	e.index = index
	e.position = pos
	e.pressed = pressed
	tc._input(e)
