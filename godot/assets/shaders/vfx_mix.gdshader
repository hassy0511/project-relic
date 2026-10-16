// エフェクトの物（普通の半透明）：煙・粉じん・陶器と金属の破片・明るい床の上でも色が残る敵弾の芯。中身は vfx_particle.gdshaderinc
shader_type spatial;
render_mode unshaded, blend_mix, depth_draw_never, cull_disabled, shadows_disabled, skip_vertex_transform;
#include "vfx_particle.gdshaderinc"
