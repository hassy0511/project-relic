extends RefCounted
## 詰み（入れるのに出られない所）と宙づりの回帰テスト（2026-10-15、第 1 章の詰み探し）。
## 形だけの調べ（ReachScan）で第 1 章の全部屋を、そこにいるときの本筋の段階（ReachScan.CH1_STATES）ごとに調べる：
## - 目印・中継地点から行ける所は、どこからでも出口・目印・中継地点か、奈落（Player.KILL_Y より下。落ちると直前の足場へ戻る）へ行ける
## - 限界の跳び（段 1.8 m・溝 4.5 m／ダッシュ 7.0 m を越える）でしか出られない所が無い
## - 落ちて縁の角に体が載りそうな所（形の調べの宙づりの候補）に実際のゲームで体を置いても、立つか下へ落ちる（宙に止まらない）
## 実際に歩いて確かめる個別のテスト：家のベッドと壁、ギルドのバートンと受付台・掲示板の端末と板・2 つの受付台の間、
## 縦坑（r11）の上の足場の壁ぎわ、伝導路（r15）の宝箱と壁（どれも前は、歩いて下りると縁に引っかかって宙づりのまま出られなかった）

var h: TestHelpers
var _world: World

## 意図した「戻れない所」（今は無い）。"部屋|段階" → [[x0, z0, x1, z1], ...]：この範囲の詰みは許す
const ALLOW_STUCK := {}


func _init(helpers: TestHelpers) -> void:
	h = helpers


## 部屋を段階のフラグで読み込む。トリガーは走らせない、敵は消す。keep_exits でなければ出口も消す（歩いて確かめる間に部屋を移らない）
func _game(room: String, flags: Array, keep_exits := false) -> GameSim:
	if _world == null:
		_world = World.load_manifest("res://content/world.json")
	var g := GameSim.new()
	var vp := SubViewport.new()
	vp.own_world_3d = true
	vp.render_target_update_mode = SubViewport.UPDATE_DISABLED
	vp.size = Vector2i(2, 2)
	h.tree.root.add_child(vp)
	vp.add_child(g)
	g.setup({"world": _world, "tuning": TestHelpers.default_tuning(), "seed": 1})
	for f in flags:
		g.set_flag(f)
	g.load_room(room)
	g.god_mode = true
	for t in g.triggers:
		t.fired = true
	if not keep_exits:
		g.exits = []
	for e in g.enemies.duplicate():
		e.alive = false
		g.phys.remove(e.body)
	g.enemies = []
	return g


func _allowed(key: String, p: Vector3) -> bool:
	for b in ALLOW_STUCK.get(key, []):
		if p.x >= b[0] and p.x <= b[2] and p.z >= b[1] and p.z <= b[3]:
			return true
	return false


## 位置 p に体を置いて 0.5 秒：立つか、下へ落ちる（縁の角に載って宙に止まらない）
func _settles(g: GameSim, p: Vector3) -> Dictionary:
	g.player.teleport(p + Vector3(0, 0.05, 0), 0.0)
	await h.run(g, 30, {})
	var q: Vector3 = g.player.pos
	return {"ok": g.player.grounded or q.y < p.y - 0.3, "pos": q}


## 第 1 章の全部屋：行ける所から必ず戻れる（形の調べ）。宙づりの候補は、実際に体を置いて確かめる
func test_ch1_rooms_no_traps() -> void:
	var rooms := 0
	var hang_checked := 0
	for room in ReachScan.CH1_STATES:
		for st in ReachScan.CH1_STATES[room]:
			var g := _game(room, ReachScan.CH1_STATES[room][st], true)
			await h.settle()
			var scan := ReachScan.new(g, {"dash": g.has_ability("dash")})
			var res := scan.run()
			g.exits = []
			rooms += 1
			var key := "%s|%s" % [room, st]
			for s in res.stuck:
				if not _allowed(key, s.pos):
					h.expect(false, "%s：行けるのに出口・目印へ戻れない所がある（高さ %.2f〜%.2f、x %.1f〜%.1f、z %.1f〜%.1f、%d 点。道：%s）" % [key, s.y0, s.y1,
						s.box[0], s.box[2], s.box[1], s.box[3], s.nodes, " / ".join(scan.explain(s.pos))])
			for s in res.hard:
				h.expect(false, "%s：限界の跳びでしか戻れない所がある（高さ %.2f〜%.2f、x %.1f〜%.1f、z %.1f〜%.1f）" % [key, s.y0, s.y1,
					s.box[0], s.box[2], s.box[1], s.box[3]])
			var seen := {}
			for hg in res.hangs:
				# 0.1 m ごとに 1 つ（近くても止まる所と落ちる所がある：r02 の山の角と柱の角）
				var k := Vector3i(roundi(hg.pos.x * 10), roundi(hg.pos.y * 10), roundi(hg.pos.z * 10))
				if seen.has(k):
					continue
				seen[k] = true
				hang_checked += 1
				var r: Dictionary = await _settles(g, hg.pos)
				h.expect(r.ok, "%s：(%.2f, %.2f, %.2f) で体が縁に引っかかって宙に止まる（(%.2f, %.2f, %.2f) から下りた所。止まった所 (%.2f, %.2f, %.2f)）" % [key,
					hg.pos.x, hg.pos.y, hg.pos.z, hg.from.x, hg.from.y, hg.from.z, r.pos.x, r.pos.y, r.pos.z])
			h.free_game(g)
			await h.tree.physics_frame
	h.expect(rooms >= 40, "第 1 章の部屋を段階ごとに調べた（%d）" % rooms)
	print("    部屋と段階 %d、宙づりの候補を実際に確かめた %d" % [rooms, hang_checked])


## 形の調べが、分かりきった詰み（深さ 3 m の穴）と宙づり（壁と箱の間の 0.5 m のすき間）を見つける。
## 浅い穴（1.5 m）・広いすき間（1 m）は見つけない
func test_reach_scan_finds_known_traps() -> void:
	var cases := [
		# [穴の深さ, すき間, 詰みがある, 宙づりがある]
		[3.0, 1.0, true, false],
		[1.5, 1.0, false, false],
		[1.5, 0.5, false, true],
	]
	for c in cases:
		var depth: float = c[0]
		var gap: float = c[1]
		var room := {"name": "t", "playerStart": "start", "markers": {"start": {"pos": [0, 0, -8]}},
			"geometry": [
				# 床 20 × 20 の真ん中に 4 × 4 の穴
				{"t": "box", "pos": [0, -depth, -6], "size": [20, depth, 8]},
				{"t": "box", "pos": [0, -depth, 6], "size": [20, depth, 8]},
				{"t": "box", "pos": [-6, -depth, 0], "size": [8, depth, 4]},
				{"t": "box", "pos": [6, -depth, 0], "size": [8, depth, 4]},
				{"t": "box", "pos": [0, -depth - 1, 0], "size": [20, 1, 20]},
				# 東の壁と、壁から gap 離した高さ 1 m の箱
				{"t": "box", "pos": [10.5, 0, 0], "size": [1, 4, 20]},
				{"t": "box", "pos": [10 - gap - 1, 0, 6], "size": [2, 1, 2]},
			],
			"props": [{"type": "exit", "id": "x", "to": "a", "pos": [0, 0, -9], "size": [4, 3, 1]}]}
		var g := GameSim.new()
		var vp := SubViewport.new()
		vp.own_world_3d = true
		vp.render_target_update_mode = SubViewport.UPDATE_DISABLED
		vp.size = Vector2i(2, 2)
		h.tree.root.add_child(vp)
		vp.add_child(g)
		g.setup({"world": World.from_dict({"areas": [{"id": "t", "rooms": {"a": room}}]}), "tuning": TestHelpers.default_tuning(), "seed": 1})
		await h.settle()
		var res := ReachScan.new(g).run()
		h.expect(res.stuck.is_empty() != c[2], "深さ %.1f m の穴：詰み %s（%d）" % [depth, "あり" if c[2] else "なし", res.stuck.size()])
		var hang := false
		for hg in res.hangs:
			if hg.pos.x > 8.0 and hg.pos.z > 4.5 and hg.pos.z < 7.5:
				hang = true
		h.expect(hang == c[3], "壁と箱の間 %.1f m：宙づりの候補 %s" % [gap, "あり" if c[3] else "なし"])
		h.free_game(g)
		await h.tree.physics_frame


## 実際に歩く：start（台の上）から dir の向きへゆっくり歩き、足が離れたら倒すのをやめる。止まったら接地していて、
## そこから back の所へ歩いて（跳んで）戻れる（back が null なら戻らない：縦坑の下りなど）
## jumps：戻るときに跳ぶボタンも押す（住人・端末のそばでは跳ぶボタンが「話す・調べる」になるので、そこでは押さない）
func _walk_off(g: GameSim, start: Vector3, dir: Vector2, back, what: String, jumps := true) -> void:
	var d := dir.normalized()
	var yaw := atan2(d.x, d.y)
	g.player.teleport(start, yaw)
	g.cam.yaw = yaw
	await h.run(g, 4, {})
	h.expect(g.player.grounded, "%s：台の上に立てる（%.2f, %.2f, %.2f）" % [what, g.player.pos.x, g.player.pos.y, g.player.pos.z])
	var left := false
	for i in TestHelpers.seconds(1.5):
		g.cam.yaw = yaw
		await h.run(g, 1, {"move_y": 0.0 if left else 0.25})
		if not g.player.grounded:
			left = true
	await h.run(g, TestHelpers.seconds(0.6), {})
	var p: Vector3 = g.player.pos
	h.expect(g.player.grounded, "%s：下りたところで接地している（宙に止まらない。%.2f, %.2f, %.2f）" % [what, p.x, p.y, p.z])
	if back == null:
		return
	var ok := await h.run_until(g, TestHelpers.seconds(4), func(i):
		var q: Vector3 = g.player.pos
		g.cam.yaw = atan2(back.x - q.x, back.z - q.z)
		return {"move_y": 1.0, "jump": jumps and i % 30 < 8}
	, func(): return g.player.grounded and Vector2(g.player.pos.x - back.x, g.player.pos.z - back.z).length() < 1.0)
	h.expect(ok, "%s：そこから部屋の中へ戻れる（%.2f, %.2f, %.2f）" % [what, g.player.pos.x, g.player.pos.y, g.player.pos.z])


## ハルの家：ベッドから西の壁・北の壁の方へ下りても、ベッドと壁の間に引っかからない（前は 0.6 m・0.5 m のすき間で宙づりのまま出られなかった）
func test_home_bed_no_hang() -> void:
	var g := _game("ch1.home", ["ch1.chores_started"])
	await h.settle()
	var mid := Vector3(0, 0, 0)
	await _walk_off(g, Vector3(-5.0, 0.62, 2.0), Vector2(-1, 0), mid, "ベッドから西の壁の方へ")
	await _walk_off(g, Vector3(-5.0, 0.62, 4.6), Vector2(-1, 0), mid, "ベッドの奥から西の壁の方へ")
	await _walk_off(g, Vector3(-5.5, 0.62, 5.0), Vector2(-1, 1), mid, "ベッドから北西の角の方へ")
	await _walk_off(g, Vector3(-4.6, 0.62, 5.0), Vector2(0, 1), mid, "ベッドから北の壁の方へ")
	h.free_game(g)


## 回収屋ギルド：バートンの頭から受付台の方へ、掲示板の端末から板の方へ、2 つの受付台の間へ下りても引っかからない
func test_guild_counters_no_hang() -> void:
	var g := _game("ch1.guild", ["ch1.chores_started"])
	await h.settle()
	var mid := Vector3(0, 0, -2)
	# バートンのそばでは跳ぶボタンが「話す」になる。受付台の上を歩いて端から下りる
	var past_counter := Vector3(4.0, 0, 6.5)
	await _walk_off(g, Vector3(0.0, 1.62, 5.0), Vector2(0, 1), past_counter, "バートンの頭から受付台の方へ", false)
	await _walk_off(g, Vector3(0.2, 1.62, 5.0), Vector2(0, 1), past_counter, "バートンの頭から受付台の方へ（右寄り）", false)
	await _walk_off(g, Vector3(7.0, 1.22, 6.5), Vector2(0, 1), mid, "掲示板の端末から板の方へ", false)
	await _walk_off(g, Vector3(-3.7, 1.12, 6.8), Vector2(1, 0), mid, "リタの受付台から隣の台の方へ", false)
	h.free_game(g)


## 縦坑（r11）：上の足場から壁ぎわの角の方へ、下から 2 つ目の足場から南の壁の方へ歩いても、壁と足場の間に引っかからない
## （前は上の足場の壁ぎわに 0.5 m 四方のすき間が 2 つ、下から 2 つ目の足場と南の壁の間に 0.5 m のすき間があった）
func test_r11_top_landing_no_hang() -> void:
	var g := _game("ch1.r11", ["ch1.frame_fitted", "ch1.blade_online"])
	await h.settle()
	# 足場の端から縦坑へ落ちるのは下りの道（下の足場か床に立つ）
	await _walk_off(g, Vector3(-5.6, 21.02, -3.3), Vector2(0, 1), null, "上の足場の西の壁ぎわを北へ")
	await _walk_off(g, Vector3(-3.3, 21.02, -5.6), Vector2(1, 0), null, "上の足場の南の壁ぎわを東へ")
	# 下から 2 つ目の足場（上面 4.2 m）から南の壁の方へ（前は壁との間が 0.5 m 空いていた）
	await _walk_off(g, Vector3(0.5, 4.22, -4.5), Vector2(0, -1), null, "下から 2 つ目の足場から南の壁の方へ")
	await _walk_off(g, Vector3(-0.6, 4.22, -5.0), Vector2(-0.3, -1), null, "下から 2 つ目の足場から南西の角の方へ")
	h.free_game(g)


## 伝導路（r15）：宝箱の上から東の壁の方へ下りても、宝箱と壁の間に引っかからない（前は 0.6 m のすき間で宙づりのまま出られなかった）
func test_r15_chest_no_hang() -> void:
	var g := _game("ch1.r15", ["ch1.drive_powered"])
	await h.settle()
	var mid := Vector3(5, 0, 8)
	await _walk_off(g, Vector3(9.0, 0.82, 9.6), Vector2(1, 0), mid, "宝箱から東の壁の方へ")
	await _walk_off(g, Vector3(9.0, 0.82, 10.4), Vector2(1, 0.3), mid, "宝箱から北東の方へ")
	h.free_game(g)


## 歯車の間（r13）：低いリフト lift1（底 0.1〜3.6 m）の下に立っていても、下りてくるリフトはハルの頭の上で止まり、どくとまた下りる
## （前はリフトがハルの体を床の中へ押し込み、床の板に挟まって動けなくなった。GameSim._mover_overlaps_player）
func test_r13_lift_does_not_crush() -> void:
	var g := _game("ch1.r13", ["ch1.drive_powered", "ch1.r13.cleared"])
	await h.settle()
	var mv: Props.Mover = g.movers.filter(func(m): return m.id == "ch1.r13.lift1")[0]
	await h.run_until(g, TestHelpers.seconds(20), {}, func(): return mv.t > 0.95)
	for spot in [Vector3(-5.5, 0, 5.0), Vector3(-6.9, 0, 6.4)]:
		g.player.teleport(spot, PI)
		g.cam.yaw = PI
		await h.run(g, TestHelpers.seconds(6), {})
		var p: Vector3 = g.player.pos
		h.expect(p.y > -0.05 and g.player.grounded, "リフトの下に立っていても、床の上に立ったまま（%.2f, %.2f, %.2f）" % [p.x, p.y, p.z])
		h.expect(mv.pos.y >= p.y + Player.HEIGHT, "リフトはハルの頭の上で止まる（リフトの底 %.2f）" % mv.pos.y)
		# 南へどく
		var out := await h.run_until(g, TestHelpers.seconds(3), func(_i):
			g.cam.yaw = PI
			return {"move_y": 1.0}
		, func(): return g.player.pos.z < 2.5)
		h.expect(out and g.player.grounded, "リフトの下から歩いて出られる（%.2f, %.2f, %.2f）" % [g.player.pos.x, g.player.pos.y, g.player.pos.z])
		var down := await h.run_until(g, TestHelpers.seconds(10), {}, func(): return mv.t < 0.02)
		h.expect(down, "どいたら、リフトは下まで下りる（t %.2f）" % mv.t)
		await h.run_until(g, TestHelpers.seconds(20), {}, func(): return mv.t > 0.95)
	h.free_game(g)

