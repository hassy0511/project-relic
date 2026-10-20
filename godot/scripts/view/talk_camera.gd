class_name TalkCamera
extends RefCounted
## 会話のカメラ：住人に話しかけた会話の間、話し相手の頭と上半身がよく見える構図（ハルの肩越しか、少し横から。ハルは画面の横）を選ぶ。
## カメラを寄せるのは CameraRig（会話が始まると TALK_EASE 秒で寄せ、終わると同じ時間でふだんのカメラへ戻す）。
## 見た目だけ：ゲームの中身のカメラの向き（CameraOrbit の yaw・pitch）は変えないので、会話のあとはプレイヤーが向けていたカメラに戻る。
## 自動の回り込み・ロックオン・左スティックの基準（20_ゲームシステム設計.md 3 章）にも関わらない。
##
## 使うとき（partner）：会話が出ていて、それが住人に話しかけて始まった会話（GameSim.talk_npc）で、その住人が今の会話の話し手の 1 人で、
## 台本のカメラ（camera の手順の注視・置き場所）が動いておらず、黒帯の場面（GameSim.cinematic()）でもないとき。
## 台本のカメラ・黒帯の場面を使うイベントで話しかけたときは talk_npc が空（GameSim._interact）。
## ナゴミ・ハル・地の文の行で構図は変えない（話し相手を映したまま）。ナゴミだけ・地の文だけの会話、トリガーや台本で始まった会話、
## 戦闘中のひと言（会話ではない）では使わない。
##
## 構図の選び方（find）：ハルの頭から見て後ろ（BACKS）・横（SIDES、左右）・上（RISES）の候補の中から、
## ・置き場所：ハルの頭からカメラまで、地形・壊せる物・体だけを止める物（細い柱・露店の屋根など）に当たらず、まわり CLEAR に何も無い
##   （壁・露店・台の中に入らない。ふだんのカメラの壁よけ CameraRig._room と同じ考え）
## ・話し相手の顔が見える：カメラから顔まで、地形・壊せる物に当たらない。ハルの頭・胴・ナゴミに隠れない。台・机の上の品（見た目だけで
##   当たり判定が無い）に隠れないよう、顔までの線の下 GOODS_H に台の面が無い（台の奥の住人には、カメラを上げた候補が選ばれる）
## ・画面の上の方：顔を画面の上から 28%、肩もその上（スマホでは会話の窓が下の 45% を覆う）
## を満たすものを、点数（ハルが画面の横に見える・肩まで見える・顔までの距離・低さ・今のカメラのいる側・ナゴミのいない側）の高い順に選ぶ。
## 満たすものが無ければ使わない（ふだんのカメラのまま）。構図は会話の始めに 1 度だけ選び、会話の途中では動かさない。

## 会話のカメラの視野角（縦、度。ふだんは tuning の camera.fov＝60）
const FOV := 50.0
## 顔を置く高さ（画面の中心から上へ。画面の高さの半分に対する割合。0.44 で上から 28%）
const FACE_Y := 0.44
## 話し相手を画面の中心から横へずらす量（ハルの反対の側へ。画面の幅の半分に対する割合）
const NPC_X := 0.12
## 候補：ハルの頭から後ろ・横・上へ（m。上は、ハルの頭と話し相手の顔の高いほうから）。後ろ 0.3 は、すぐ後ろが壁のときの横からの構図
const BACKS := [0.3, 0.8, 1.2, 1.7, 2.3]
const SIDES := [0.45, 0.75, 1.1, 1.5]
const RISES := [0.15, 0.45, 0.8, 1.15]
## ハルの体（隠れの判定）：胴の軸の下端・上端の高さ（足元から）と半径（肩・腕）、頭の中心の高さと半径（髪・ゴーグル）
const BODY := Vector3(0.55, 1.25, 0.27)
const HEAD := Vector2(1.42, 0.17)
## ナゴミ（直径 25cm）の半径と、カメラを近づけない距離
const NAGOMI_R := 0.15
const NAGOMI_NEAR := 0.5
## 隠れの判定のゆとり（m）
const MARGIN := 0.05
## 住人の顔の高さ：名札の高さ（PropsView.NPC_LABEL_Y・TOWNSFOLK_LABEL_Y。既定 2.1）からこれを引く。肩は顔から SHOULDER 下
const FACE_BELOW_LABEL := 0.52
const SHOULDER := 0.25
## 視線の確かめは、顔・肩の中心からカメラの方へこれだけ寄せた点（頭・体の表の面）へ引く
const FRONT := 0.15
## 台・机の上の品の高さの見込み（見た目だけの物）。顔までの線の下にこの高さまで、床より高い面（台・机・他の住人の頭）があれば隠れるとみなす
const GOODS_H := 0.45
## カメラのまわりに空ける距離（m）
const CLEAR := 0.25
## ハルの頭との距離の下限（これより近いとハルの頭が画面を覆う）
const NEAR_HARU := 0.75
## 置き場所・視線に当たる物
const PLACE_MASK := Phys.TERRAIN | Phys.BREAKABLE | Phys.PROP
const SIGHT_MASK := Phys.TERRAIN | Phys.BREAKABLE
## 配列を入れると、find が候補ごとの点数と落とした理由を足していく（確かめ用）
static var trace = null


## 今、会話のカメラで映す話し相手（Props.Npc）。使わないときは null
static func partner(game: GameSim):
	var d: Dictionary = game.story.dialogue
	# 黒帯の場面（台本がカメラを取った・"cutscene" のイベント）では使わない
	if d.is_empty() or game.talk_npc == "" or game.cam_focus != null or game.cam_eye != null or game.cinematic():
		return null
	for n in game.npcs:
		if n.id == game.talk_npc:
			return n if speaks(game, n, String(d.get("id", ""))) else null
	return null


## 住人 n が会話 id の話し手の 1 人か（行の who が名札の名前か、PropsView.NPC_SPEAKERS の呼び名）
static func speaks(game: GameSim, n, id: String) -> bool:
	var names: Array = [String(n.name)]
	names.append_array(PropsView.NPC_SPEAKERS.get(n.id, []))
	for ln in game.dialogues.get(id, {}).get("lines", []):
		if ln.has("who") and names.has(String(ln.who)):
			return true
	return false


## 住人の顔の高さ（足元から m）
static func face_height(id: String) -> float:
	return float(PropsView.NPC_LABEL_Y.get(id, PropsView.TOWNSFOLK_LABEL_Y.get(id, 2.1))) - FACE_BELOW_LABEL


## 住人 n と話すときの構図：{ id: 住人の id, pos: カメラの場所, look: 見る点, fov, side: ハルから見たカメラの側（右 1・左 -1） }。
## 満たす構図が無ければ {}。from：今のカメラの場所（同じ側を少し選びやすく）、aspect：画面の横÷縦
static func find(game: GameSim, n, from: Vector3, aspect: float) -> Dictionary:
	var p: Vector3 = game.player.pos
	var head := p + Vector3(0, HEAD.x, 0)
	var pivot := p + Vector3(0, float(game.tuning.camera.pivotHeight), 0)
	var face: Vector3 = n.pos + Vector3(0, face_height(n.id), 0)
	var shoulder := face - Vector3(0, SHOULDER, 0)
	var flat := Vector3(n.pos.x - p.x, 0.0, n.pos.z - p.z)
	var u := flat.normalized() if flat.length() > 0.05 else U.yaw_to_dir(game.player.yaw)
	var right := Vector3(-u.z, 0.0, u.x)
	var ex: Array[RID] = []
	if n.body != null and is_instance_valid(n.body):
		ex.append((n.body as CollisionObject3D).get_rid())
	var nagomi = null
	if game.nagomi_present():
		var py: float = game.player.yaw
		var pr := Vector3(-cos(py), 0.0, sin(py))
		nagomi = p + pr * NagomiView.OFFSET.x + Vector3(0, NagomiView.OFFSET.y, 0) + U.yaw_to_dir(py) * NagomiView.OFFSET.z
	var tf := tan(deg_to_rad(FOV) * 0.5)
	var cam_side := signf(right.dot(from - p))
	var floor_y := minf(p.y, n.pos.y)
	var top := maxf(head.y, face.y)
	var cands: Array = []
	for s: float in [1.0, -1.0]:
		for b: float in BACKS:
			for l: float in SIDES:
				for r: float in RISES:
					var c := Vector3(head.x, top + r, head.z) - u * b + right * (s * l)
					var e := _compose(c, face, shoulder, p, nagomi, tf, aspect)
					var tag := "s%+d b%.1f l%.2f r%.2f" % [int(s), b, l, r]
					if e.has("why"):
						if trace is Array:
							trace.append("%s：%s" % [tag, e.why])
						continue
					e.score -= 1.5 * (r - float(RISES[0]))
					if s == cam_side:
						e.score += 0.4
					if nagomi != null and s < 0.0:
						e.score += 0.3
					e["side"] = s
					e["tag"] = tag
					cands.append(e)
	cands.sort_custom(func(a, b): return a.score > b.score)
	var best := {}
	for e in cands:
		if not best.is_empty() and e.score <= best.score:
			break
		var c: Vector3 = e.pos
		var why := ""
		if not _placeable(game, pivot, c):
			why = "置けない（壁・物の中か、ハルの頭から通らない）"
		else:
			var hid := _blocked(game, c, _front(face, c), floor_y, ex, true)
			if hid != "":
				why = "顔が見えない（%s）" % hid
			elif e.upper and _blocked(game, c, _front(shoulder, c), floor_y, ex, false) != "":
				e.score -= 1.0
				why = "肩が物の陰（減点）"
		if trace is Array:
			trace.append("%s：%.2f %s" % [e.tag, e.score, why])
		if why != "" and not why.ends_with("（減点）"):
			continue
		if best.is_empty() or e.score > best.score:
			best = e
	if best.is_empty():
		return {}
	if trace is Array:
		trace.append("選んだ：%s（%.2f）ハルの頭の画面の位置 %s" % [best.tag, best.score, best.haru])
	return {"id": String(n.id), "pos": best.pos, "look": best.look, "fov": FOV, "side": best.side}


## 置き場所 c からの構図。向きは、顔を画面の上（FACE_Y）、ハルと反対の側へ NPC_X ずらす。当たり判定を使わない確かめ
## （画面の中の位置・ハルの体とナゴミに隠れないか）をして点数を付ける。満たさなければ { why: 理由 }
static func _compose(c: Vector3, face: Vector3, shoulder: Vector3, p: Vector3, nagomi, tf: float, aspect: float) -> Dictionary:
	var head := p + Vector3(0, HEAD.x, 0)
	if c.distance_to(head) < NEAR_HARU or Vector2(c.x - p.x, c.z - p.z).length() < Player.RADIUS + 0.1:
		return {"why": "ハルに近すぎる"}
	if nagomi != null and c.distance_to(nagomi) < NAGOMI_NEAR:
		return {"why": "ナゴミに近すぎる"}
	# 顔まで、ハルの胴・頭とナゴミに隠れない（肩は隠れても減点だけ）
	if _hidden(c, face, p, nagomi):
		return {"why": "顔がハルかナゴミの陰"}
	var upper := not _hidden(c, shoulder, p, nagomi)
	var to_face := face - c
	var dist := to_face.length()
	var yaw := atan2(to_face.x, to_face.z)
	var pitch := asin(clampf(to_face.y / dist, -1.0, 1.0))
	# ハルの反対の側へ話し相手をずらす（ハルが画面の左なら話し相手は右。yaw を増やすとカメラは左へ回る）
	var h0 := _screen(_view(c, yaw, pitch), head, tf, aspect)
	var away := -signf(h0.x) if absf(h0.x) > 0.001 else 1.0
	yaw += away * atan(NPC_X * tf * aspect)
	pitch -= atan(FACE_Y * tf)
	var t := _view(c, yaw, pitch)
	var fs := _screen(t, face, tf, aspect)
	var ss := _screen(t, shoulder, tf, aspect)
	var hs := _screen(t, head, tf, aspect)
	if fs.z <= 0.0 or absf(fs.x) > 0.5 or fs.y < 0.25 or fs.y > 0.62 or ss.y < 0.0:
		return {"why": "顔・肩が画面の上の方に入らない"}
	# ハルが画面の横（中心から 0.2〜0.85、スマホの会話の窓（中心から下 0.08 より下）より上）に見えるほど、顔までの距離が 3.2m に近いほど高い点
	var score := 0.0
	var hx := absf(hs.x)
	if hs.z > 0.0 and hx >= 0.2 and hx <= 0.85 and hs.y > 0.0 and hs.y < 0.8:
		score += 3.0
	elif hs.z > 0.0 and hx <= 1.0 and hs.y > -0.6:
		score += 1.5
	score -= absf(hx - 0.5) if hs.z > 0.0 else 1.0
	score -= 0.6 * absf(dist - 3.2)
	if not upper:
		score -= 1.0
	return {"pos": c, "look": c + t.basis * Vector3(0, 0, -dist), "score": score, "upper": upper, "haru": hs}


## 線 c→x が、ハルの胴・頭かナゴミに隠れるか
static func _hidden(c: Vector3, x: Vector3, p: Vector3, nagomi) -> bool:
	var cp := Geometry3D.get_closest_points_between_segments(c, x, p + Vector3(0, BODY.x, 0), p + Vector3(0, BODY.y, 0))
	if cp[0].distance_to(cp[1]) < BODY.z + MARGIN:
		return true
	var hc := p + Vector3(0, HEAD.x, 0)
	if Geometry3D.get_closest_point_to_segment(hc, c, x).distance_to(hc) < HEAD.y + MARGIN:
		return true
	if nagomi != null and Geometry3D.get_closest_point_to_segment(nagomi, c, x).distance_to(nagomi) < NAGOMI_R + MARGIN:
		return true
	return false


## カメラを c に置けるか：ハルの頭（注視点）から c まで、地形・体だけを止める物に当たらず（壁の向こう・箱の中に入らない）、
## まわり CLEAR に何も無い
static func _placeable(game: GameSim, pivot: Vector3, c: Vector3) -> bool:
	var v := c - pivot
	if not game.phys.raycast(pivot, v.normalized(), v.length() + CLEAR, PLACE_MASK).is_empty():
		return false
	return not game.phys.sphere_hits(c, CLEAR, PLACE_MASK)


## c から点 x が見えないわけ（見えれば ""）：地形・壊せる物に当たる。goods なら、線の下 GOODS_H に台・机の面がある
## （台の上の品は見た目だけの物なので、面の高さで見込む）。ex：話し相手の体（当たり判定の箱）
static func _blocked(game: GameSim, c: Vector3, x: Vector3, floor_y: float, ex: Array[RID], goods: bool) -> String:
	var v := x - c
	var hit: Dictionary = game.phys.raycast(c, v.normalized(), v.length(), SIGHT_MASK, ex)
	if not hit.is_empty():
		return "物 %s" % hit.point
	if not goods:
		return ""
	var flat := Vector2(v.x, v.z).length()
	var n := int(ceil(flat / 0.3))
	for i in range(1, n):
		var k := float(i) / n
		# カメラのすぐ前と、話し相手の体のすぐ近くは見ない
		if flat * k < 0.3 or flat * (1.0 - k) < 0.2:
			continue
		hit = game.phys.raycast(c + v * k, Vector3.DOWN, GOODS_H, SIGHT_MASK, ex)
		if not hit.is_empty() and hit.point.y > floor_y + 0.25:
			return "台の面 %s" % hit.point
	return ""


## 顔・肩の中心 x から、カメラ c の方へ FRONT 寄せた点（見えるのは頭・体の表の面。壁・棚の前に立つ住人は、中心が壁に接していることがある：
## 下段のマーサは家の角に立つ）
static func _front(x: Vector3, c: Vector3) -> Vector3:
	var v := c - x
	v.y = 0.0
	return x + v.normalized() * FRONT if v.length() > 0.01 else x


## yaw・pitch を向いたカメラ（場所 c）
static func _view(c: Vector3, yaw: float, pitch: float) -> Transform3D:
	var fwd := Vector3(sin(yaw) * cos(pitch), sin(pitch), cos(yaw) * cos(pitch))
	return Transform3D(Basis.looking_at(fwd, Vector3.UP), c)


## 点 x の画面の位置：x・y は中心 0、右・上が正、画面の端が ±1。z は奥行き（カメラの後ろなら負）
static func _screen(t: Transform3D, x: Vector3, tf: float, aspect: float) -> Vector3:
	var l := t.affine_inverse() * x
	var depth := -l.z
	if depth <= 0.01:
		return Vector3(0, 0, -1)
	return Vector3(l.x / depth / (tf * aspect), l.y / depth / tf, depth)
