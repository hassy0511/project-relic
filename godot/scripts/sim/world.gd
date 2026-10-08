class_name World
extends RefCounted
## ゲーム世界のデータ：エリア（部屋の集まり）・会話・イベント・アイテム・経済。content/world.json（目次）から読む。
## 部屋の id は「エリア id.部屋名」（例：ch1.r02）。別の部屋を指すとき、ドットのない名前は同じエリアの部屋とみなす。

var areas := {}
var rooms := {}
var dialogues := {}
var events := {}
var items := {}
var economy := {}
var start := {"room": "", "spawn": "start"}
var _geo_cache := {}


## 目次ファイルから読む。content/world.json
static func load_manifest(path: String) -> World:
	var m = U.load_json(path)
	var base := path.get_base_dir()
	var w := World.new()
	w.start = m.get("start", w.start)
	for f in m.get("areas", []):
		w.add_area(U.load_json("%s/%s" % [base, f]))
	for f in m.get("dialogue", []):
		w.dialogues.merge(U.load_json("%s/%s" % [base, f]), true)
	for f in m.get("events", []):
		w.events.merge(U.load_json("%s/%s" % [base, f]), true)
	if m.has("items"):
		w.items = U.load_json("%s/%s" % [base, m.items])
	if m.has("economy"):
		w.economy = U.load_json("%s/%s" % [base, m.economy])
	return w


## 辞書から作る（テスト用）：{ start?, areas: [エリア...], dialogues?, events?, items?, economy? }
static func from_dict(d: Dictionary) -> World:
	var w := World.new()
	w.start = d.get("start", w.start)
	for a in d.get("areas", []):
		w.add_area(a)
	w.dialogues = d.get("dialogues", {})
	w.events = d.get("events", {})
	w.items = d.get("items", {})
	w.economy = d.get("economy", {})
	if w.start.room == "" and not w.rooms.is_empty():
		w.start.room = w.rooms.keys()[0]
	return w


## 1 部屋だけの世界（試しの部屋・テスト用）。geometry は作ってある { faces, markers }
static func adhoc(placement: Dictionary, geometry: Dictionary, dialogues: Dictionary, events: Dictionary) -> World:
	var w := World.new()
	var room := placement.duplicate()
	room["area"] = "adhoc"
	w.rooms["adhoc"] = room
	w.areas["adhoc"] = {"id": "adhoc", "name": placement.get("name", "adhoc"), "rooms": {"adhoc": room}}
	w._geo_cache["adhoc"] = geometry
	w.dialogues = dialogues
	w.events = events
	w.start = {"room": "adhoc", "spawn": String(placement.get("playerStart", "start"))}
	return w


func add_area(a: Dictionary) -> void:
	var aid: String = a.id
	areas[aid] = a
	for k in a.get("rooms", {}):
		var r: Dictionary = a.rooms[k]
		r["area"] = aid
		r["id"] = "%s.%s" % [aid, k]
		rooms[r.id] = r


func has_room(id: String) -> bool:
	return rooms.has(id)


func room(id: String) -> Dictionary:
	assert(rooms.has(id), "部屋が見つからない: %s" % id)
	return rooms[id]


## 部屋の id を完全な形にする（ドットがなければ from_room と同じエリア）
func resolve(id: String, from_room: String) -> String:
	if id.contains("."):
		return id
	var area: String = rooms[from_room].area if rooms.has(from_room) else ""
	return "%s.%s" % [area, id]


## 部屋の地形：{ faces, tints?, markers }。GLB の部屋（"model"）は目印も読み、データの "markers" で足せる
func geometry(room_id: String) -> Dictionary:
	if _geo_cache.has(room_id):
		return _geo_cache[room_id]
	var r := room(room_id)
	var geo: Dictionary
	if r.has("model"):
		var lv := LevelLoader.load_level("res://assets/%s" % r.model)
		lv.node.free()
		geo = lv.geometry
		var extra := RoomGeo.build(r)
		geo.faces.append_array(extra.faces)
		geo["prop"] = extra.prop
		geo.markers.merge(extra.markers, true)
	else:
		geo = RoomGeo.build(r)
	_geo_cache[room_id] = geo
	return geo


func item_name(id: String) -> String:
	return String(items.get(id, {}).get("name", GameSim.ITEM_NAMES.get(id, id)))
