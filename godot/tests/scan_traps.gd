extends SceneTree
## 第 1 章の部屋を ReachScan で調べて、詰み（入れるのに出られない所）と宙づりの候補を書き出す（実際のゲームで確かめる前の候補探し）。
##   tools/godot.sh run --script res://tests/scan_traps.gd -- [部屋 id の一部] [--json=<書き出す先>] [--verbose]
## 宙づりの候補は形だけの見積もり（多めに出る）。本当に止まるかは tests/test_traps.gd が実際のゲームで体を置いて確かめる
## 部屋ごとに、そこにいるときの本筋の段階（立っているフラグ・使える力）で調べる（ReachScan.CH1_STATES）。

func _initialize() -> void:
	_run.call_deferred()


static func make_game(tree: SceneTree) -> GameSim:
	var g := GameSim.new()
	var vp := SubViewport.new()
	vp.own_world_3d = true
	vp.render_target_update_mode = SubViewport.UPDATE_DISABLED
	vp.size = Vector2i(2, 2)
	tree.root.add_child(vp)
	vp.add_child(g)
	g.setup({"world": World.load_manifest("res://content/world.json"), "tuning": TestHelpers.default_tuning(), "seed": 1})
	return g


func _run() -> void:
	var filter := ""
	var json_path := ""
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--json="):
			json_path = a.trim_prefix("--json=")
		elif not a.begins_with("--"):
			filter = a
	var found: Array = []
	var total_stuck := 0
	var total_hard := 0
	var total_hang := 0
	var total_slide := 0
	for room in ReachScan.CH1_STATES:
		if filter != "" and not room.contains(filter):
			continue
		for st in ReachScan.CH1_STATES[room]:
			var g := make_game(self)
			await physics_frame
			for f in ReachScan.CH1_STATES[room][st]:
				g.set_flag(f)
			g.load_room(room)
			await physics_frame
			var scan := ReachScan.new(g, {"dash": g.has_ability("dash"), "verbose": OS.get_cmdline_user_args().has("--verbose")})
			var res := scan.run()
			print("%s [%s] dash=%s  node %d、まとまり %d（行ける %d）  %s" % [room, st, scan.dash, res.nodes, res.comps, res.reached, res.ms])
			for s in res.stuck:
				found.append({"room": room, "state": st, "flags": ReachScan.CH1_STATES[room][st], "kind": "stuck", "pos": [s.pos.x, s.pos.y, s.pos.z], "box": s.box, "y0": s.y0, "y1": s.y1, "nodes": s.nodes})
				total_stuck += 1
				print("  詰み：高さ %.2f〜%.2f  %d 点  範囲 x %.2f〜%.2f, z %.2f〜%.2f  例 (%.2f, %.2f, %.2f)%s" % [s.y0, s.y1, s.nodes,
					s.box[0], s.box[2], s.box[1], s.box[3], s.pos.x, s.pos.y, s.pos.z, "  動く足場" if s.mover >= 0 else ""])
			for s in res.hard:
				found.append({"room": room, "state": st, "flags": ReachScan.CH1_STATES[room][st], "kind": "hard", "pos": [s.pos.x, s.pos.y, s.pos.z], "box": s.box, "y0": s.y0, "y1": s.y1, "nodes": s.nodes})
				total_hard += 1
				print("  限界の跳びでだけ出られる：高さ %.2f〜%.2f  %d 点  範囲 x %.2f〜%.2f, z %.2f〜%.2f  例 (%.2f, %.2f, %.2f)%s" % [s.y0, s.y1, s.nodes,
					s.box[0], s.box[2], s.box[1], s.box[3], s.pos.x, s.pos.y, s.pos.z, "  動く足場" if s.mover >= 0 else ""])
			var seen := {}
			for hg in res.hangs:
				var k := Vector3i(roundi(hg.pos.x * 2), roundi(hg.pos.y * 2), roundi(hg.pos.z * 2))
				if seen.has(k):
					continue
				seen[k] = true
				found.append({"room": room, "state": st, "flags": ReachScan.CH1_STATES[room][st], "kind": "wedged" if hg.wedged else "slide",
					"pos": [hg.pos.x, hg.pos.y, hg.pos.z], "from": [hg.from.x, hg.from.y, hg.from.z]})
				if hg.wedged:
					total_hang += 1
				else:
					total_slide += 1
				print("  %s：(%.2f, %.2f, %.2f)  元 (%.2f, %.2f, %.2f)" % ["宙づり（抜けられない）" if hg.wedged else "宙づり（横へ抜けられる）",
					hg.pos.x, hg.pos.y, hg.pos.z, hg.from.x, hg.from.y, hg.from.z])
			g.get_parent().queue_free()
			await physics_frame
	print("詰みの候補 %d、限界の跳びでだけ出られる %d、抜けられない宙づり %d、横へ抜けられる宙づり %d" % [total_stuck, total_hard, total_hang, total_slide])
	if json_path != "":
		var f := FileAccess.open(json_path, FileAccess.WRITE)
		f.store_string(JSON.stringify(found, " "))
		f.close()
	quit()
