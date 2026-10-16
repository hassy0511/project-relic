// エフェクトの光（足し合わせ）：火花・光の粒・輪・斬撃の帯・光柱。霞を受けない。中身は vfx_particle.gdshaderinc
shader_type spatial;
render_mode unshaded, blend_add, depth_draw_never, cull_disabled, shadows_disabled, skip_vertex_transform, fog_disabled;
#include "vfx_particle.gdshaderinc"
