// キットの面の材質（RoomKit）。部屋の灰色の地形と、飾りの部品（GLB）の両方に使う。
// UV はメートル（部屋の面は RoomKit がワールド座標から、部品は Blender で付けた値）。1 枚の絵 = uv_m メートル。
// seam_every を 0 より大きくすると、その間隔（m）で板の継ぎ目の線を描く（壁の白磁の板など）。
shader_type spatial;

#include "res://assets/shaders/kit_surface.gdshaderinc"
