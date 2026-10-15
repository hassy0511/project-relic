class_name EnvironmentSetup
## 空・光・空気感。赤い砂の世界の、夕方に近い暖かい光（MVP の試験場用の仮の設定）

## スマホ・ブラウザ版の描き方（gl_compatibility）で、影を落とす太陽に掛ける強さ。
## この描き方は、影を落とす光を別の回で描き、トーンマップと sRGB に直した色を画面に足す（Godot 4.5 の
## drivers/gles3/shaders/scene.glsl の USE_ADDITIVE_LIGHTING）。明るい側を詰める曲線を通した色どうしを足すので、
## 光の当たる所が Forward+ より明るく白っぽく、平らに出た（町の床で +16〜36、遺構の床で +21。汚れの層も薄く見えた）。
## 太陽を弱めて、光の当たる所の明るさを Forward+ に合わせる（0.35 で昼の床が合い、壁は少し暗くなる。間を取って 0.4）。
## 部品の影つきの光（遺構の割れ目のスポット）は、この描き方では影を付けない（RoomKit._light。影なしなら同じ明るさになる）
const COMPAT_SHADOW_LIGHT := 0.4


## 影を落とす光の強さに掛ける割合（gl_compatibility だけ COMPAT_SHADOW_LIGHT、ほかは 1）
static func shadow_light_scale() -> float:
	return COMPAT_SHADOW_LIGHT if is_compat() else 1.0


## スマホ・ブラウザ版の軽い描き方か
static func is_compat() -> bool:
	return RenderingServer.get_current_rendering_method() == "gl_compatibility"


## 太陽の強さ（影を落とすので、gl_compatibility では shadow_light_scale を掛ける。元の値は "energy" のメタに）
static func set_sun_energy(sun: DirectionalLight3D, energy: float) -> void:
	sun.set_meta("energy", energy)
	sun.light_energy = energy * (shadow_light_scale() if sun.shadow_enabled else 1.0)
	_sync_sky_sun(sun)


## gl_compatibility の空の太陽（空の円盤だけを描く光。build で作る）を、太陽と同じ色・前の強さにそろえる。向きは子なので同じ
static func _sync_sky_sun(sun: DirectionalLight3D) -> void:
	var sky_sun: DirectionalLight3D = sun.get_meta("sky_sun", null)
	if sky_sun != null:
		sky_sun.light_color = sun.light_color
		sky_sun.light_energy = float(sun.get_meta("energy", sun.light_energy))

static func build(parent: Node) -> DirectionalLight3D:
	var we := WorldEnvironment.new()
	var env := Environment.new()
	var sky := Sky.new()
	var sky_mat := ProceduralSkyMaterial.new()
	sky_mat.sky_top_color = Color("#8fa6c4")
	sky_mat.sky_horizon_color = Color("#e7c29a")
	sky_mat.ground_bottom_color = Color("#5a4636")
	sky_mat.ground_horizon_color = Color("#c9a27e")
	sky_mat.sun_angle_max = 20.0
	sky.sky_material = sky_mat
	env.background_mode = Environment.BG_SKY
	env.sky = sky
	env.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	env.ambient_light_energy = 0.9
	env.reflected_light_source = Environment.REFLECTION_SOURCE_SKY
	env.tonemap_mode = Environment.TONE_MAPPER_AGX
	env.tonemap_exposure = 1.05
	# 画面の質：環境光の遮り、光のにじみ、遠くの霞み（ブラウザ版の軽い描画方式では一部が効かない）
	env.ssao_enabled = true
	env.ssao_radius = 1.2
	env.ssao_intensity = 1.6
	env.glow_enabled = true
	env.glow_intensity = 0.6
	env.glow_bloom = 0.05
	env.glow_hdr_threshold = 1.1
	env.fog_enabled = true
	env.fog_light_color = Color("#d9b58f")
	env.fog_density = 0.004
	env.fog_aerial_perspective = 0.4
	env.adjustment_enabled = true
	env.adjustment_saturation = 1.05
	we.environment = env
	parent.add_child(we)

	var sun := DirectionalLight3D.new()
	sun.light_color = Color("#fff1d6")
	sun.rotation_degrees = Vector3(-52, -150, 0)
	sun.shadow_enabled = true
	if is_compat():
		# 影を落とす太陽は弱める（COMPAT_SHADOW_LIGHT）ので、空に描く太陽の円盤（ProceduralSkyMaterial）は、
		# 空だけを照らす別の光で前の強さのまま描く（太陽は物だけを照らす。空の明るさ・環境光も前と同じ）
		sun.sky_mode = DirectionalLight3D.SKY_MODE_LIGHT_ONLY
		var sky_sun := DirectionalLight3D.new()
		sky_sun.name = "SkySun"
		sky_sun.sky_mode = DirectionalLight3D.SKY_MODE_SKY_ONLY
		sun.add_child(sky_sun)
		sun.set_meta("sky_sun", sky_sun)
	set_sun_energy(sun, 1.6)
	sun.shadow_bias = 0.03
	sun.shadow_normal_bias = 1.0
	sun.directional_shadow_max_distance = 60.0
	parent.add_child(sun)
	sun.set_meta("env", env)
	sun.set_meta("proc_sky", sky_mat)
	return sun


## 時間帯・場所の雰囲気：day（既定）| dawn（夜明け）| night（停電の夜）| interior（屋内）
static func apply_mood(sun: DirectionalLight3D, mood: String) -> void:
	var env: Environment = sun.get_meta("env")
	var sky: ProceduralSkyMaterial = sun.get_meta("proc_sky")
	env.sky.sky_material = sky
	env.adjustment_saturation = 1.05
	env.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	env.fog_sky_affect = 1.0
	match mood:
		"title":
			# タイトルの後ろの夜明けの空（霞を空にかけない）
			sky.sky_top_color = Color("#3e4a74")
			sky.sky_horizon_color = Color("#f2a272")
			sky.ground_horizon_color = Color("#c98a62")
			sky.ground_bottom_color = Color("#3a2a24")
			sun.light_color = Color("#ffc08a")
			set_sun_energy(sun, 1.4)
			sun.rotation_degrees = Vector3(-9, -150, 0)
			env.ambient_light_energy = 0.7
			env.fog_light_color = Color("#e5a782")
			env.fog_sky_affect = 0.15
		"dawn":
			sky.ground_bottom_color = Color("#5a4636")
			sky.sky_top_color = Color("#4f5f86")
			sky.sky_horizon_color = Color("#f0a679")
			sky.ground_horizon_color = Color("#b98a6a")
			sun.light_color = Color("#ffc08a")
			set_sun_energy(sun, 1.1)
			sun.rotation_degrees = Vector3(-14, -150, 0)
			env.ambient_light_energy = 0.7
			env.fog_light_color = Color("#e5a782")
		"night":
			sky.sky_top_color = Color("#070b1c")
			sky.sky_horizon_color = Color("#1e2748")
			sky.ground_bottom_color = Color("#0a0a12")
			sky.ground_horizon_color = Color("#1e2238")
			sun.light_color = Color("#8fa6ff")
			set_sun_energy(sun, 0.7)
			sun.rotation_degrees = Vector3(-60, -150, 0)
			# 空が暗いと環境光も暗くなりすぎるので、夜は青みの色で与える
			env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
			env.ambient_light_color = Color("#5a6a9a")
			env.ambient_light_energy = 0.9
			env.fog_light_color = Color("#1c2340")
		"ruin_b1", "ruin_b2", "ruin_b3", "ruin_b4":
			# 遺構の階層ごとの色（B1 外殻層＝割れ目の暖かい光、B2 配管層＝暗い青灰、B3 駆動層＝青銅とオレンジ、B4 心臓部＝紫と青緑）
			var pal: Array = {
				"ruin_b1": ["#a8987c", "#c8b290", "#ffe2b8", 0.9, 1.0, "#8a7660", "#c8b698"],
				"ruin_b2": ["#4c5f80", "#6a7fa6", "#9ab8e8", 0.7, 0.9, "#34425a", "#7f94bc"],
				"ruin_b3": ["#8a6a44", "#b08a54", "#ffc080", 0.8, 1.0, "#5a4228", "#c09866"],
				"ruin_b4": ["#6a5fa0", "#8a7cc0", "#a0f0e4", 0.8, 1.0, "#3a3460", "#9a90cc"],
			}[mood]
			sky.sky_top_color = Color(pal[0])
			sky.sky_horizon_color = Color(pal[1])
			sun.light_color = Color(pal[2])
			set_sun_energy(sun, pal[3])
			sun.rotation_degrees = Vector3(-60, -150, 0)
			# 屋内は空の色に頼らず、階層ごとの色の環境光で与える
			env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
			env.ambient_light_color = Color(pal[6])
			env.ambient_light_energy = pal[4]
			env.fog_light_color = Color(pal[5])
		"interior":
			sky.sky_top_color = Color("#6d6358")
			sky.sky_horizon_color = Color("#a08a6c")
			sun.light_color = Color("#ffe2b8")
			set_sun_energy(sun, 0.8)
			sun.rotation_degrees = Vector3(-60, -150, 0)
			env.ambient_light_energy = 0.8
			env.fog_light_color = Color("#8a7660")
		_:
			sky.sky_top_color = Color("#8fa6c4")
			sky.sky_horizon_color = Color("#e7c29a")
			sky.ground_bottom_color = Color("#5a4636")
			sky.ground_horizon_color = Color("#c9a27e")
			sun.light_color = Color("#fff1d6")
			set_sun_energy(sun, 1.6)
			sun.rotation_degrees = Vector3(-52, -150, 0)
			env.ambient_light_energy = 0.9
			env.fog_light_color = Color("#d9b58f")
	_sync_sky_sun(sun)


## 遠景の空の絵と、その空に合わせた光（キットの "sky"：{ "day": 絵, "night": 絵, "dawn": 絵 } と "light"：{ "night": { … } }）。
## apply_mood のあとに呼ぶ。path が "" なら作った空のまま。絵は正距円筒（tools/blender/kit/town_backdrop.py が bg_desert_* から作る）。
## 霞は空にかけない（絵の地平線の霞をそのまま見せる）。light の項目（どれも省略可）：
##   sky_energy（空の絵の明るさ）, sun_energy, sun_color, ambient_color（指定すると環境光をこの色に）, ambient_energy, fog_color,
##   saturation（色の鮮やかさ）。どれも apply_mood が毎回戻す項目だけ
## 空の絵が無い（path が ""）ときも、light の上書きは当てる（屋内の遺構のキットは "light" だけを書く）。
static func apply_sky(sun: DirectionalLight3D, path: String, light: Dictionary = {}) -> void:
	var env: Environment = sun.get_meta("env")
	if path != "" and ResourceLoader.exists(path):
		var cache: Dictionary = sun.get_meta("sky_cache", {})
		if not cache.has(path):
			var pano := PanoramaSkyMaterial.new()
			pano.panorama = load(path)
			cache[path] = pano
			sun.set_meta("sky_cache", cache)
		var mat: PanoramaSkyMaterial = cache[path]
		mat.energy_multiplier = float(light.get("sky_energy", 1.0))
		env.sky.sky_material = mat
		env.fog_sky_affect = 0.0
	if light.has("sun_energy"):
		set_sun_energy(sun, float(light.sun_energy))
	if light.has("sun_color"):
		sun.light_color = Color(light.sun_color)
		_sync_sky_sun(sun)
	if light.has("ambient_color"):
		env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
		env.ambient_light_color = Color(light.ambient_color)
	if light.has("ambient_energy"):
		env.ambient_light_energy = float(light.ambient_energy)
	if light.has("fog_color"):
		env.fog_light_color = Color(light.fog_color)
	if light.has("saturation"):
		env.adjustment_saturation = float(light.saturation)
