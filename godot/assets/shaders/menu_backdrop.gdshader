// メニューの後ろ：ゲームの画面をぼかして暗くする（見本の画面と同じく、後ろの景色が柔らかく透ける）
shader_type canvas_item;

uniform sampler2D screen_tex : hint_screen_texture, filter_linear_mipmap;
uniform float blur_lod = 2.6;
uniform vec4 tint : source_color = vec4(0.05, 0.045, 0.04, 0.6);

void fragment() {
	vec3 c = textureLod(screen_tex, SCREEN_UV, blur_lod).rgb;
	COLOR = vec4(mix(c, tint.rgb, tint.a), 1.0);
}
