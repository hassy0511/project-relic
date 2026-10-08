// キットの面の材質の、カメラのすぐ近くを網目に消す版（材質の定義の "near_fade": [消える距離, 見える距離]。RoomKit.make_material）。
// 当たり判定の無い飾りの部品（日よけ・柱・灯など）に使う。中身は kit_surface.gdshaderinc
shader_type spatial;

#define NEAR_FADE
#include "res://assets/shaders/kit_surface.gdshaderinc"
