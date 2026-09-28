// 仮の地形用の材質。ワールド座標で 1m ごとの格子線（4m ごとに濃い線）を描き、大きさを読み取りやすくする
shader_type spatial;

uniform vec4 albedo : source_color = vec4(0.6, 0.58, 0.55, 1.0);
uniform float roughness_value = 0.92;

varying vec3 world_pos;
varying vec3 world_normal;

void vertex() {
	world_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	world_normal = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz);
}

float grid(vec2 uv) {
	vec2 g = abs(fract(uv - 0.5) - 0.5) / fwidth(uv);
	return 1.0 - min(min(g.x, g.y), 1.0);
}

void fragment() {
	vec3 n = abs(world_normal);
	vec2 uv = n.y > 0.5 ? world_pos.xz : (n.x > 0.5 ? world_pos.zy : world_pos.xy);
	float line = grid(uv);
	float line4 = grid(uv / 4.0);
	ALBEDO = albedo.rgb * (1.0 - line * 0.16 - line4 * 0.2);
	ROUGHNESS = roughness_value;
}
