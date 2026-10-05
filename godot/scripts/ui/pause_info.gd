class_name PauseInfo
extends RefCounted
## ポーズ画面と店・工房・ギルドの画面に出す文章を作る（ゲームの状態 → 文字列。画面の部品とは分けてテストできる形）

const KIND_ORDER := [["weapon", "武器"], ["frame", "フレーム"], ["chip", "チップ"], ["consumable", "消耗品"], ["key", "大事なもの"]]


static func play_time_text(seconds: float) -> String:
	var m := int(seconds / 60.0)
	return "%d 時間 %d 分" % [m / 60, m % 60] if m >= 60 else "%d 分" % m


static func place_text(g) -> String:
	var r: Dictionary = g.room
	var floor_name := String(r.get("map", {}).get("floor", ""))
	var nm := String(r.get("name", g.room_id))
	return nm if floor_name == "" or floor_name == nm else "%s（%s）" % [nm, floor_name]


static func status_text(g) -> String:
	var p = g.player
	var lines := [
		"HP　%d ／ %d" % [ceili(p.hp), int(p.max_hp)],
		"補修パック　×%d" % p.heals,
		"セル　%d" % g.cells,
		"回収屋の印　%s" % g.mark,
		"ギルドポイント　%d" % g.guild_points,
		"いる場所　%s" % place_text(g),
		"プレイ時間　%s" % play_time_text(g.play_time),
		"",
		"目的",
		"　%s" % (g.objective if g.objective != "" else "（なし）"),
	]
	if g.has_item("special.drill"):
		lines.insert(3, "武器エネルギー　%d ／ 100" % int(p.weapon_energy))
	return "\n".join(lines)


static func items_text(g) -> String:
	var lines := []
	for pair in KIND_ORDER:
		var names := []
		for id in g.items:
			if String(g.world.items.get(id, {}).get("kind", "")) == pair[0]:
				var nm: String = g.world.item_name(id)
				if id == "chip.charge":
					nm += "（装着中）" if g.charge_type() else "（外している）"
				names.append(nm)
		if not names.is_empty():
			lines.append("■ %s" % pair[1])
			for n in names:
				lines.append("　%s" % n)
	var mats := []
	for m in g.materials:
		if int(g.materials[m]) > 0:
			mats.append("　%s ×%d" % [g.world.item_name(m), int(g.materials[m])])
	if not mats.is_empty():
		lines.append("■ 素材")
		lines.append_array(mats)
	if not g.relics.is_empty():
		lines.append("■ 遺物（売ると…）")
		for r in g.relics:
			lines.append("　%s　%d セル" % [g.world.item_name(r), int(g.world.items.get(r, {}).get("sell", 20))])
	return "\n".join(lines) if not lines.is_empty() else "（まだ何も持っていない）"


## 入った部屋の一覧：階層（map.floor）ごとに並べ、今いる部屋に ◆ を付ける
static func map_text(g) -> String:
	var floors := {}
	var order := []
	for id in g.visited_rooms():
		var r: Dictionary = g.world.rooms[id]
		var fl := String(r.get("map", {}).get("floor", ""))
		if fl == "":
			fl = "そのほか"
		if not floors.has(fl):
			floors[fl] = []
			order.append(fl)
		floors[fl].append("%s%s" % ["◆ " if id == g.room_id else "　", r.get("name", id)])
	var lines := ["入った部屋 %d ／ 全部で %d　（◆ ＝ いまの場所）" % [g.visited_rooms().size(), g.world.rooms.size()], ""]
	for fl in order:
		lines.append("■ %s" % fl)
		lines.append_array(floors[fl])
	return "\n".join(lines)


static func requests_text(g) -> String:
	var lines := []
	for r in g.world.economy.get("guild", {}).get("requests", []):
		var st: String = g.requests.get(r.id, "")
		if st == "":
			continue
		var done := Cond.eval(r.get("done"), g)
		lines.append("■ %s（%s）" % [r.name, "達成済み" if st == "done" else ("報告できる" if done else "受けている")])
		lines.append("　%s" % r.get("text", ""))
	return "\n".join(lines) if not lines.is_empty() else "（受けている依頼はない。ギルドの依頼板で受けられる）"


## 操作の説明（キーボード・パッド・タッチ）
static func help_text(touch: bool) -> String:
	var lines := []
	for h in (Menu.HELP_TOUCH if touch else Menu.HELP):
		lines.append("%s：%s" % [h[0], h[1]])
	return "\n".join(lines)


static func save_info(d) -> String:
	if d == null:
		return "（空き）"
	var rid := String(d.get("room", ""))
	return "場所　%s\nプレイ時間　%s\nセル　%d\n保存した時刻　%s" % [rid, play_time_text(float(d.get("playTime", 0))), int(d.get("cells", 0)), String(d.get("savedAt", "")).replace("T", " ")]


## 店の品の説明（持っている数・値段・足りる／足りない）
static func shop_detail(g, shop_id: String, s: Dictionary) -> String:
	var item: String = s.item
	var price := int(s.price)
	var lines := [g.world.item_name(item), ""]
	match String(g.world.items.get(item, {}).get("kind", "")):
		"consumable":
			lines.append("持っている数　%d" % g.player.heals)
		"material":
			lines.append("持っている数　%d" % g.material_count(item))
	if int(s.get("count", 1)) > 1:
		lines.append("まとめ買い　×%d" % int(s.count))
	lines.append("値段　%d セル（いま　%d セル）　%s" % [price, g.cells, "買える" if g.cells >= price else "セルが足りない"])
	return "\n".join(lines)


## 工房のレシピの説明：必要な素材と持っている数、費用、条件
static func recipe_detail(g, r: Dictionary) -> String:
	var lines := [String(r.name), ""]
	if g.flag("crafted." + r.id) and r.id == "drill":
		lines.append("開発済み")
		return "\n".join(lines)
	lines.append("必要な素材")
	var needs: Dictionary = r.get("needs", {})
	for m in needs:
		var have: int = g.material_count(m)
		lines.append("　%s ×%d　（持っている %d）%s" % [g.world.item_name(m), int(needs[m]), have, "　○" if have >= int(needs[m]) else "　×"])
	if needs.is_empty():
		lines.append("　なし")
	var cost := int(r.get("cost", 0))
	lines.append("費用　%d セル（いま %d セル）%s" % [cost, g.cells, "　○" if g.cells >= cost else "　×"])
	if not Cond.eval(r.get("cond"), g):
		lines.append("")
		lines.append("まだ作れない（物語を進めると作れる）")
	return "\n".join(lines)


static func reward_text(r: Dictionary) -> String:
	var parts := []
	var rw: Dictionary = r.get("reward", {})
	if rw.has("cells"):
		parts.append("%d セル" % int(rw.cells))
	if rw.has("gp"):
		parts.append("ギルドポイント %d" % int(rw.gp))
	return "　".join(parts) if not parts.is_empty() else "（なし）"


static func request_detail(g, r: Dictionary) -> String:
	var st: String = g.requests.get(r.id, "")
	var state := "まだ受けていない"
	if st == "accepted":
		state = "報告できる" if Cond.eval(r.get("done"), g) else "受けている（まだ達成していない）"
	elif st == "done":
		state = "達成済み"
	return "%s\n\n%s\n\n報酬　%s\n状態　%s" % [r.name, r.get("text", ""), reward_text(r), state]
