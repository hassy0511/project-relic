// キットの面の材質の、汚れ・傷みの層があり、カメラのすぐ近くを網目に消す版（"detail" と "near_fade" のある材質。RoomKit.make_material）
shader_type spatial;

#define NEAR_FADE
#define DETAIL
#include "res://assets/shaders/kit_surface.gdshaderinc"
