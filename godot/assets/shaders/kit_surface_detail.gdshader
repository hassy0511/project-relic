// キットの面の材質の、汚れ・傷みの層（材質の "detail"）のある版（RoomKit.make_material）。中身は kit_surface.gdshaderinc と kit_detail.gdshaderinc
shader_type spatial;

#define DETAIL
#include "res://assets/shaders/kit_surface.gdshaderinc"
