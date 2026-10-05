class_name Economy
extends RefCounted
## 経済の入口：店・工房・ギルドの依頼。内容は content/economy.json（World.economy）。UI は薄い画面（段階 D で作り込む）。
## どれも { ok: bool, msg: String } を返し、成否は出来事（message）でも知らせる。
##
## economy.json の形：
##   shops:     { id: { name, stock: [ { item, price, cond? } ], buys_relics: true } }
##   workshops: { id: { name, recipes: [ { id, name, cost, needs: { 素材 id: 個数 }, gives: { grant の形 }, cond? } ] } }
##   guild:     { requests: [ { id, name, text, reward: { grant の形 }, done: 条件（満たすと完了できる）, cond?（受けられる条件） } ] }

static func _data(g, kind: String, id: String) -> Dictionary:
	return g.world.economy.get(kind, {}).get(id, {})


static func _result(g, ok: bool, msg: String) -> Dictionary:
	g.emit_event({"type": "message", "text": msg})
	g.emit_event({"type": "sfx", "id": "ui_ok" if ok else "locked"})
	return {"ok": ok, "msg": msg}


## 店で買う
static func buy(g, shop_id: String, item: String) -> Dictionary:
	var shop := _data(g, "shops", shop_id)
	for s in shop.get("stock", []):
		if s.item != item:
			continue
		if not Cond.eval(s.get("cond"), g):
			return _result(g, false, "まだ売れない")
		if not g.spend_cells(int(s.price)):
			return _result(g, false, "セルが足りない")
		if item == "consumable.repair":
			g.player.heals += 1
			g.emit_event({"type": "message", "text": "補修パックを買った"})
		elif item.begins_with("material."):
			g.add_material(item, int(s.get("count", 1)))
		else:
			g.give_item(item)
		return {"ok": true, "msg": ""}
	return _result(g, false, "その品はない")


## 遺物をジャンク屋・雑貨屋に売る（価格は items の sell）
static func sell_relic(g, shop_id: String, relic: String) -> Dictionary:
	if not _data(g, "shops", shop_id).get("buys_relics", false):
		return _result(g, false, "ここでは買い取らない")
	if not g.relics.has(relic):
		return _result(g, false, "持っていない")
	g.relics.erase(relic)
	var price := int(g.world.items.get(relic, {}).get("sell", 20))
	g.give_cells(price)
	return _result(g, true, "遺物を売った（セル +%d）" % price)


## 工房で作る・強化する
static func craft(g, workshop_id: String, recipe_id: String) -> Dictionary:
	for r in _data(g, "workshops", workshop_id).get("recipes", []):
		if r.id != recipe_id:
			continue
		if not Cond.eval(r.get("cond"), g):
			return _result(g, false, "まだ作れない")
		var needs: Dictionary = r.get("needs", {})
		for m in needs:
			if g.material_count(m) < int(needs[m]):
				return _result(g, false, "素材が足りない：%s" % g.world.item_name(m))
		if g.cells < int(r.get("cost", 0)):
			return _result(g, false, "セルが足りない")
		g.spend_cells(int(r.get("cost", 0)))
		for m in needs:
			g.add_material(m, -int(needs[m]))
		g.grant(r.get("gives", {}))
		g.set_flag("crafted." + recipe_id)
		return {"ok": true, "msg": ""}
	return _result(g, false, "その設計図はない")


static func _request(g, id: String) -> Dictionary:
	for r in g.world.economy.get("guild", {}).get("requests", []):
		if r.id == id:
			return r
	return {}


## 依頼を受ける
static func accept_request(g, id: String) -> Dictionary:
	var r := _request(g, id)
	if r.is_empty():
		return _result(g, false, "その依頼はない")
	if g.requests.has(id):
		return _result(g, false, "すでに受けている")
	if not Cond.eval(r.get("cond"), g):
		return _result(g, false, "まだ受けられない")
	g.requests[id] = "accepted"
	g.emit_event({"type": "message", "text": "依頼を受けた：%s" % r.name})
	return {"ok": true, "msg": ""}


## 依頼を完了する（done の条件を満たしていれば報酬）
static func complete_request(g, id: String) -> Dictionary:
	var r := _request(g, id)
	if r.is_empty() or g.requests.get(id, "") != "accepted":
		return _result(g, false, "その依頼は受けていない")
	if not Cond.eval(r.get("done"), g):
		return _result(g, false, "まだ達成していない")
	g.requests[id] = "done"
	g.grant(r.get("reward", {}))
	g.set_flag("request." + id)
	g.emit_event({"type": "message", "text": "依頼を達成した：%s" % r.name})
	return {"ok": true, "msg": ""}
