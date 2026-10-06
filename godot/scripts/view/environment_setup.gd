class_name EnvironmentSetup
## 空・光・空気感。赤い砂の世界の、夕方に近い暖かい光（MVP の試験場用の仮の設定）

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
	sun.light_energy = 1.6
	sun.rotation_degrees = Vector3(-52, -150, 0)
	sun.shadow_enabled = true
	sun.shadow_bias = 0.03
	sun.shadow_normal_bias = 1.0
	sun.directional_shadow_max_distance = 60.0
	parent.add_child(sun)
	sun.set_meta("env", env)
	return sun


## 時間帯・場所の雰囲気：day（既定）| dawn（夜明け）| night（停電の夜）| interior（屋内）
static func apply_mood(sun: DirectionalLight3D, mood: String) -> void:
	var env: Environment = sun.get_meta("env")
	var sky: ProceduralSkyMaterial = env.sky.sky_material
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
			sun.light_energy = 1.4
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
			sun.light_energy = 1.1
			sun.rotation_degrees = Vector3(-14, -150, 0)
			env.ambient_light_energy = 0.7
			env.fog_light_color = Color("#e5a782")
		"night":
			sky.sky_top_color = Color("#070b1c")
			sky.sky_horizon_color = Color("#1e2748")
			sky.ground_bottom_color = Color("#0a0a12")
			sky.ground_horizon_color = Color("#1e2238")
			sun.light_color = Color("#8fa6ff")
			sun.light_energy = 0.7
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
			sun.light_energy = pal[3]
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
			sun.light_energy = 0.8
			sun.rotation_degrees = Vector3(-60, -150, 0)
			env.ambient_light_energy = 0.8
			env.fog_light_color = Color("#8a7660")
		_:
			sky.sky_top_color = Color("#8fa6c4")
			sky.sky_horizon_color = Color("#e7c29a")
			sky.ground_bottom_color = Color("#5a4636")
			sky.ground_horizon_color = Color("#c9a27e")
			sun.light_color = Color("#fff1d6")
			sun.light_energy = 1.6
			sun.rotation_degrees = Vector3(-52, -150, 0)
			env.ambient_light_energy = 0.9
			env.fog_light_color = Color("#d9b58f")
