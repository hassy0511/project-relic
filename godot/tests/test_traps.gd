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



## ヤーナの工房：作業台の端末の上から作業台の方へ下りても、端末と作業台の間（前は 0.4 m）に引っかからない
func test_workshop_bench_no_hang() -> void:
	var g := _game("ch1.workshop", ["ch1.chores_started"])
	await h.settle()
	# ヤーナ・端末のそばでは跳ぶボタンが「話す・調べる」になるので、戻るときは跳ばない
	await _walk_off(g, Vector3(-5.25, 1.22, 4.5), Vector2(0, 1), Vector3(-5.0, 0, 0), "作業台の端末から作業台の方へ", false)
	await _walk_off(g, Vector3(-4.75, 1.22, 4.5), Vector2(0, 1), Vector3(-5.0, 0, 0), "作業台の端末から作業台の方へ（右寄り）", false)
	h.free_game(g)


## ジャンク溜まり（r02）：折れた柱の上から南西（がらくたの山の角）へ下りても、山の角と柱の間に引っかからない
func test_r02_pile_corner_no_hang() -> void:
	var g := _game("ch1.r02", ["ch1.got_spark"])
	await h.settle()
	await _walk_off(g, Vector3(-5.5, 3.22, -1.5), Vector2(-1, -1), Vector3(-2.0, 0, -4.0), "折れた柱の上から南西へ")
	await _walk_off(g, Vector3(-5.3, 3.22, -1.3), Vector2(-1, -1), Vector3(-2.0, 0, -4.0), "折れた柱の上から南西へ（奥から）")
	h.free_game(g)


## 隠し部屋 r14（ライフコア）は、近道のレバー（r17）をいつ引いても、引かなくても取り逃さない（N14、2026-11-05）。
## 崩落（r05）は一度きりの一方通行なので、ドリルを手にして町から遺構へ戻るとき、駆動層へ下りる道は近道のエレベーター（r02 ↔ r17）だけ。
## 前はレバーを引かずにボスまで進むと、エレベーターが開かないまま章が終わり、r14 へ行けなくなった。
## 今はオルドの再始動（ch1.ordo_restarted）で遺構に動力が戻り、エレベーターが開く。
## レバーは、それより前に外殻層・町へ戻る道を開ける褒美のまま（再始動の前は、引かないと開かない）。
## 部屋のつながりは出口（lock・when・unless）だけでたどり（台本で移る崩落はたどらない）、通る部屋の中
## （r02 の入口からエレベーター、r17 の中、r12 のエレベーターからひびの壁、r14 の入口からライフコア）は、形の調べ（ReachScan）で見る
func test_r14_reachable_in_every_order() -> void:
	var g := _game("ch1.mid", [], true)
	await h.settle()
	var main: Array = GameSim.CH1_ORDER.filter(func(f): return f != "ch1.shortcut_open")
	var drill := main.find("ch1.drill_developed")
	var restart := main.find("ch1.ordo_restarted")
	var spark := main.find("ch1.got_spark")
	# レバーを引く時：駆動回廊 r12（r17 の隣）に着いてから章の終わりまでのどこか。-1 は引かない
	var lever_at: Array = [-1]
	for i in range(main.find("ch1.first_beacon"), main.size()):
		lever_at.append(i)
	var cases := 0
	for at in lever_at:
		for s in main.size():
			g.story.flags.clear()
			for k in s + 1:
				g.set_flag(main[k])
			if at >= 0 and at <= s:
				g.set_flag("ch1.shortcut_open")
			g.drain_events()
			var lever := g.flag("ch1.shortcut_open")
			var what := "レバー：%s・%s まで" % ["引かない" if at < 0 else "%s の後に引く" % main[at], main[s]]
			var open := _exit_usable(g, "ch1.r02", "ch1.r02.to_r17") and _exit_usable(g, "ch1.r17", "ch1.r17.to_r02")
			if s >= restart:
				h.expect(open, "%s：オルドの再始動の後は、近道のエレベーターが両側から動く" % what)
			elif s >= spark:
				h.expect(open == lever, "%s：再始動の前は、レバーを引いたときだけ近道が開く（開いている %s）" % [what, open])
			if s >= drill:
				var seen := _rooms_by_exits(g, "ch1.mid")
				h.expect(seen.has("ch1.r14"), "%s：町から隠し部屋 r14 へ行ける（行ける部屋 %d）" % [what, seen.size()])
			if s >= restart:
				# 帰り道：再始動の後に町から行けるどの部屋からも、出口をたどって町へ戻れる。
				# 前は縦坑 r16 のリフトで B4（r18〜r20）へ下りると上へ戻る出口が無く、出られなかった。
				# 再始動までに必ず通った B2 の部屋の中の進み（封印・訓練・制圧・弁）も済んだことにする
				for f in ["ch1.r07.seal_open", "ch1.r08.trained", "ch1.r09.cleared", "switch.ch1.r10.valve", "cleared.r10_w1"]:
					g.set_flag(f)
				var stuck: Array = []
				for rid in _rooms_by_exits(g, "ch1.mid"):
					if not _rooms_by_exits(g, rid).has("ch1.mid"):
						stuck.append(rid)
				h.expect(stuck.is_empty(), "%s：町から行けるどの部屋からも町へ戻れる（戻れない部屋 %s）" % [what, stuck])
			cases += 1
	h.free_game(g)
	h.expect(cases > 100, "順番の組み合わせを調べた（%d）" % cases)
	# 部屋の中：レバーを引かないまま、ドリルを手にした後（章の終わりまで）。ひびの壁は壊した後
	var late: Array = main.slice(0, drill + 1)
	var path := [["ch1.r01", "ch1.r02", "ch1.r17"], ["ch1.r02", "ch1.r17", "ch1.r12"], ["ch1.r17", "ch1.r12", "ch1.r14"]]
	for p in path:
		var fl: Array = late + (["broken.ch1.r12.crack"] if p[1] == "ch1.r12" else [])
		h.expect(await _walks_through(fl, p[0], p[1], p[2]), "%s に %s から入って、%s への出口へ歩いて行ける" % [p[1], p[0], p[2]])
	h.expect(await _walks_through(late, "ch1.r17", "ch1.r12", "", Vector3(-8.5, 0, -14)), "r12 のひびの壁（壊す前）の前まで行ける")
	h.expect(await _walks_through(late, "ch1.r12", "ch1.r14", "", Vector3(0, 0.8, 0)), "r14 の入口からライフコアの所へ行ける")


## 実際のゲームで、近道のエレベーター（r02 の東の扉）へ歩いて入る：レバーを引かないまま、オルドの再始動の前（ボスを倒した所まで）は
## 乗れずに「閉まっている」と出て、再始動の後（ドリルを手にした後）は乗って r17 へ下りられる。下りた先の r17 のレバーは「もう開いている」と出る（N14）
func test_shortcut_opens_after_restart() -> void:
	var main: Array = GameSim.CH1_ORDER.filter(func(f): return f != "ch1.shortcut_open")
	for late in [false, true]:
		var flags: Array = main.slice(0, main.find("ch1.drill_developed" if late else "ch1.boss_defeated") + 1)
		var g := _game("ch1.r02", flags, true)
		await h.settle()
		g.player.teleport(Vector3(8.5, 0, 0), PI / 2)
		g.cam.yaw = PI / 2
		g.drain_events()
		var msgs: Array = []
		await h.run_until(g, TestHelpers.seconds(2.0), {"move_y": 1.0}, func():
			for e in g.drain_events():
				if e.type == "message":
					msgs.append(e.text)
			return g.room_id != "ch1.r02")
		if not late:
			h.expect(g.room_id == "ch1.r02", "再始動の前は、レバーを引かないとエレベーターに乗れない（%s）" % g.room_id)
			h.expect(msgs.any(func(t): return String(t).contains("閉まっている")), "閉まっていると出る（%s）" % [msgs])
			h.free_game(g)
			continue
		h.expect(g.room_id == "ch1.r17", "再始動の後は、レバーを引いていなくてもエレベーターで r17 へ下りられる（%s）" % g.room_id)
		await h.run(g, 10, {})
		# r17 のレバー（端末）の前に立って調べる
		g.player.teleport(Vector3(0, 0, -3.0), PI)
		g.cam.yaw = PI
		g.drain_events()
		await h.run(g, 6, {})
		await h.run(g, 1, {"jump": true})
		msgs = []
		await h.run(g, 30, func(_i):
			for e in g.drain_events():
				if e.type == "message":
					msgs.append(e.text)
			return {})
		h.expect(msgs.has("近道のエレベーターは、もう開いている"), "r17 のレバーは「もう開いている」と出る（%s）" % [msgs])
		h.free_game(g)


## 再始動の後に心臓部前室 r18 へ下りても戻れる：入ってきた扉（南）へ歩くと縦坑 r16 の底に出て、上り下りするリフトで上（町の側）へ上がれる。
## 再始動の前は、その扉はただの壁（出口が無い）。前は再始動の後に B4 へ下りると、上へ戻る出口が無かった
func test_b4_way_back_after_restart() -> void:
	var main: Array = GameSim.CH1_ORDER.filter(func(f): return f != "ch1.shortcut_open")
	for after in [false, true]:
		# 縦坑 r16 の底の待ち伏せ（突撃型）は倒した後とする
		var flags: Array = main.slice(0, main.find("ch1.ordo_restarted" if after else "ch1.boss_defeated") + 1) + ["ch1.r16.cleared"]
		var g := _game("ch1.r18", flags, true)
		await h.settle()
		var at: Vector3 = g.marker("from_r16").pos
		g.player.teleport(at, PI)
		g.cam.yaw = PI
		await h.run_until(g, TestHelpers.seconds(2.0), {"move_y": 1.0}, func(): return g.room_id != "ch1.r18")
		if after:
			h.expect(g.room_id == "ch1.r16" and g.player.pos.y < 0.5, "再始動の後は、r18 の南の扉から縦坑 r16 の底へ出る（%s、y=%.2f）" % [g.room_id, g.player.pos.y])
			# リフトが底に下りてくるのを待って乗り、上まで運ばれる
			var lift: Props.Mover = g.movers.filter(func(m): return m.id == "ch1.r16.lift_powered")[0]
			h.expect(await h.run_until(g, TestHelpers.seconds(12.0), {}, func(): return lift.t >= 1.0), "リフトが底まで下りてくる（t=%.2f）" % lift.t)
			g.player.yaw = PI
			g.cam.yaw = PI
			await h.run_until(g, TestHelpers.seconds(2.0), {"move_y": 1.0}, func(): return lift.carries(g.player.pos) and g.player.pos.z < 1.6)
			var top := await h.run_until(g, TestHelpers.seconds(14.0), {}, func(): return g.player.pos.y > 19.5 and g.player.grounded)
			h.expect(top, "リフトに乗って縦坑の上へ上がれる（y=%.2f）" % g.player.pos.y)
			# 上で歩いて降り、伝導路 r15 への出口まで行ける（落ちない）。前は上の足場とリフトの間に 0.8 m の隙間があり、
			# 歩いて降りると角に載ってから 20 m 下へ落ち、跳ばないと上の足場に乗れなかった
			var low := [100.0]
			var out := await h.run_until(g, TestHelpers.seconds(4.0), {"move_y": 1.0}, func():
				if g.room_id == "ch1.r16":
					low[0] = minf(low[0], g.player.pos.y)
				return g.room_id != "ch1.r16")
			h.expect(out and g.room_id == "ch1.r15" and low[0] > 19.5, "リフトから歩いて降りて r15 へ出る（%s、いちばん低い y=%.2f）" % [g.room_id, low[0]])
		else:
			h.expect(g.room_id == "ch1.r18", "再始動の前は、r18 の南の扉は出口ではない（%s）" % g.room_id)
		h.free_game(g)


## 縦坑 r16 の上で、上の足場とリフトの間を歩いて渡れる（隙間に落ちない）。再始動の前（乗ると下りる ride）は上の足場からリフトへ、
## 再始動の後（上り下りする pingpong。部屋に入った時は上で 3 秒止まっている）はリフトから上の足場へ。ゆっくり倒しても、リフトの中ほど・端からでも。
## 前は上の足場の縁（z=-2.4）とリフトの北の端（z=-1.6）の間が 0.8 m 空いていて、どちら向きでも角に載ってから 20 m 下へ落ちた
func test_r16_lift_top_no_gap() -> void:
	var main: Array = GameSim.CH1_ORDER.filter(func(f): return f != "ch1.shortcut_open")
	for after in [false, true]:
		var flags: Array = main.slice(0, main.find("ch1.ordo_restarted" if after else "ch1.drive_powered") + 1) + ["ch1.r16.cleared"]
		for x in [0.0, -2.0, 2.0]:
			for stick in [1.0, 0.4, 0.25]:
				var g := _game("ch1.r16", flags)
				await h.settle()
				var lift: Props.Mover = g.movers[0]
				var low := [100.0]
				if after:
					g.player.teleport(Vector3(x, 20.05, -1.0), PI)
					g.cam.yaw = PI
					await h.run_until(g, TestHelpers.seconds(4.0), {"move_y": stick}, func():
						low[0] = minf(low[0], g.player.pos.y)
						return g.player.pos.z < -4.0)
					h.expect(g.player.pos.z < -4.0 and low[0] > 19.9, "再始動の後：リフトから上の足場へ歩いて渡れる（x=%.1f・倒し %.2f：z=%.2f、いちばん低い y=%.2f）" % [x, stick, g.player.pos.z, low[0]])
				else:
					g.player.teleport(Vector3(x, 20.05, -3.5), 0.0)
					g.cam.yaw = 0.0
					# 体がすっかりリフトの上に乗ったら手を離す。ハルはリフトと一緒に下り、リフトより先に底へ落ちない
					var fell := [false]
					var north_edge: float = lift.pos.z - lift.size.z * 0.5
					await h.run_until(g, TestHelpers.seconds(4.0), {"move_y": stick}, func():
						fell[0] = fell[0] or g.player.pos.y < lift.pos.y + lift.size.y - 0.5
						return g.player.pos.z > north_edge + Player.RADIUS and g.player.grounded)
					await h.run_until(g, TestHelpers.seconds(8.0), {}, func():
						fell[0] = fell[0] or g.player.pos.y < lift.pos.y + lift.size.y - 0.5
						return lift.t >= 1.0)
					h.expect(lift.t >= 1.0 and not fell[0] and g.player.pos.y < 0.5, "再始動の前：上の足場からリフトへ歩いて乗り、底まで運ばれる（x=%.1f・倒し %.2f：落ちた=%s、t=%.2f、y=%.2f）" % [x, stick, fell[0], lift.t, g.player.pos.y])
				h.free_game(g)


## 崩落床 r05 の崩落の自動保存：最後に書く保存は、B2 に落ちたフラグ（ch1.fell_to_b2）と新しい目的を持つ。
## 前は r06 に着いたときだけ保存し、フラグと目的はその約 3 秒後に付いたので、その間にアプリが終わると古い目的のまま再開した
func test_collapse_autosave_has_flag() -> void:
	var g := _game("ch1.r05", ["ch1.chores_started", "ch1.nico_rescued", "ch1.scolded", "ch1.debt_scene", "ch1.ordo_stopped", "ch1.got_spark"], true)
	for t in g.triggers:
		t.fired = false
	await h.settle()
	g.player.teleport(Vector3(0, 0, 3), 0.0)
	var saves: Array = []
	await h.run_until(g, 3000, func(i): return {"jump": (i % 6) < 3} if g.story.blocking() else {}, func():
		for e in g.drain_events():
			if e.type == "autosave":
				saves.append(g.to_save())
		return g.room_id == "ch1.r06" and g.flag("ch1.fell_to_b2") and not g.story.running_event())
	h.expect(g.room_id == "ch1.r06" and g.flag("ch1.fell_to_b2"), "床が崩れて r06 へ落ちる（%s）" % g.room_id)
	var last: Dictionary = saves.back() if not saves.is_empty() else {}
	h.expect(not last.is_empty() and last.room == "ch1.r06" and last.flags.has("ch1.fell_to_b2") and String(last.objective).contains("上には戻れない"),
			"最後の自動保存は r06・落ちたフラグ・新しい目的を持つ（%s）" % [{} if last.is_empty() else {"room": last.room, "objective": last.objective}])
	h.free_game(g)


## 部屋 rid の出口 exit_id が、今のフラグで通れるか（when・unless・lock）。ひびの壁（壊せる壁。フラグ broken.<id>）で閉じた出口は、
## ドリルを手にした後（ch1.drill_developed）なら、その部屋の壁を壊して通れるとみなす
func _exit_usable(g: GameSim, rid: String, exit_id: String) -> bool:
	for p in g.world.room(rid).get("props", []):
		if p.type == "exit" and p.id == exit_id:
			return _exit_ok(g, rid, p)
	h.expect(false, "出口 %s が %s に無い" % [exit_id, rid])
	return false


func _exit_ok(g: GameSim, rid: String, p: Dictionary) -> bool:
	if p.has("when") and not Cond.eval(p.when, g):
		return false
	if p.has("unless") and Cond.eval(p.unless, g):
		return false
	var lock = p.get("lock")
	if lock == null or Cond.eval(lock, g):
		return true
	if lock is String and String(lock).begins_with("broken.") and g.flag("ch1.drill_developed"):
		var bid := String(lock).substr(7)
		for b in g.world.room(rid).get("props", []):
			if b.type == "breakable" and b.id == bid:
				return true
	return false


## 出口だけをたどって、部屋 from から行ける部屋（今のフラグで通れる出口だけ）
func _rooms_by_exits(g: GameSim, from: String) -> Dictionary:
	var seen := {from: true}
	var q: Array = [from]
	while not q.is_empty():
		var rid: String = q.pop_front()
		for p in g.world.room(rid).get("props", []):
			if p.type != "exit" or not _exit_ok(g, rid, p):
				continue
			var to: String = g.world.resolve(p.to, rid)
			if not seen.has(to):
				seen[to] = true
				q.append(to)
	return seen


## 部屋 rid に、部屋 prev からの出口で入って（その出口の spawn の目印から）、部屋 next への出口（next が空なら位置 goal の近く）へ
## 歩いて・跳んで行けるか（形の調べ）
func _walks_through(flags: Array, prev: String, rid: String, next: String, goal = null) -> bool:
	var g := _game(rid, flags, true)
	await h.settle()
	var spawn := ""
	for p in g.world.room(prev).get("props", []):
		if p.type == "exit" and g.world.resolve(p.to, prev) == rid:
			spawn = String(p.get("spawn", "start"))
	var start: Vector3 = g.marker(spawn).pos
	var scan := ReachScan.new(g, {"dash": g.has_ability("dash"), "from": [start]})
	scan.run()
	var ok := false
	if next == "":
		ok = scan.reaches_near(goal, 1.0)
	else:
		for x in g.exits:
			if x.to == next and scan.reaches_exit(x):
				ok = true
	h.free_game(g)
	await h.tree.physics_frame
	return ok
