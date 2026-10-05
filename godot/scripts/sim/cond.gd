class_name Cond
extends RefCounted
## 条件の評価。扉・トリガー・イベントの分岐・敵の出現条件などで共通に使う。
## 書き方：
##   "ch1.drive_powered"                       文字列＝そのフラグが立っている
##   { "flag": "x" } / { "item": "key.b2" } / { "cells": 200 }（所持セル以上）
##   { "mark": "降下許可" }（印がその段以上）/ { "material": "scrap", "n": 3 } / { "cleared": "グループ名" }
##   { "not": 条件 } / { "all": [条件...] } / { "any": [条件...] } / 配列＝all
## 空（null・{}）は常に真。

const MARKS := ["見習い", "降下許可", "銅の印", "銀の印", "金の印", "一人前の印", "白磁の印"]


static func eval(c, g) -> bool:
	if c == null:
		return true
	if c is bool:
		return c
	if c is String:
		return g.flag(c)
	if c is Array:
		for x in c:
			if not eval(x, g):
				return false
		return true
	if c is Dictionary:
		for k in c:
			var ok := true
			match k:
				"flag":
					ok = g.flag(String(c.flag))
				"item":
					ok = g.has_item(String(c.item))
				"cells":
					ok = g.cells >= int(c.cells)
				"mark":
					ok = mark_rank(g.mark) >= mark_rank(String(c.mark))
				"material":
					ok = g.material_count(String(c.material)) >= int(c.get("n", 1))
				"cleared":
					ok = g.group_cleared(String(c.cleared))
				"not":
					ok = not eval(c["not"], g)
				"all":
					ok = eval(c.all, g)
				"any":
					ok = false
					for x in c.any:
						if eval(x, g):
							ok = true
							break
				"n":
					pass
				_:
					push_error("知らない条件: %s" % k)
			if not ok:
				return false
		return true
	return true


static func mark_rank(m: String) -> int:
	return maxi(0, MARKS.find(m))
