extends SceneTree
## 自動テストの実行（画面なし）。tools/godot.sh test
## test_*.gd の中の test_ で始まる関数を順に実行し、失敗があれば終了コード 1 で終わる。
## 引数に名前の一部を渡すと、その名前を含むテストだけを実行する。

const SUITES := ["res://tests/test_feel.gd", "res://tests/test_combat.gd", "res://tests/test_touch.gd"]


func _initialize() -> void:
	_run.call_deferred()


func _run() -> void:
	var filter := ""
	var args := OS.get_cmdline_user_args()
	if args.size() > 0:
		filter = args[0]
	var h := TestHelpers.new(self)
	var count := 0
	var started := Time.get_ticks_msec()
	for path in SUITES:
		var suite = load(path).new(h)
		for m in suite.get_method_list():
			var n: String = m.name
			if not n.begins_with("test_") or (filter != "" and not n.contains(filter)):
				continue
			h.current = "%s:%s" % [path.get_file().get_basename(), n]
			var before := h.failures.size()
			var t0 := Time.get_ticks_msec()
			await suite.call(n)
			count += 1
			print("%s  %s（%d ms）" % ["✓" if h.failures.size() == before else "✗", h.current, Time.get_ticks_msec() - t0])
			await physics_frame
	print("")
	print("テスト %d 本、確認 %d 件、失敗 %d 件（%.1f 秒）" % [count, h.checks, h.failures.size(), (Time.get_ticks_msec() - started) / 1000.0])
	for f in h.failures:
		print("  ✗ ", f)
	quit(1 if h.failures.size() > 0 else 0)
