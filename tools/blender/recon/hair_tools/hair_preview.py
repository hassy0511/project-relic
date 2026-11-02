"""Quick hair preview: cap-only head field (hair.build_head with LOCKS_AS_PARTS) + Haru's lock parts, Cycles renders
of the head from side/back/3-4/top/front with the drawings' outlines on top.
  RECON_CHAR=haru .venv-blender/bin/python tools/blender/recon/hair_tools/hair_preview.py --out build/prev/NAME [--recap] [--cap build/prev/cap.npz]
The cap field is cached (--recap recomputes it with the CAP params from chars/haru.json)."""
import argparse, json, math, os, sys, time
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'blender'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'blender', 'recon'))
os.chdir(REPO)
import numpy as np
from recon import hair as HR
from recon import views as V
ap = argparse.ArgumentParser()
ap.add_argument('--out', required=True)
ap.add_argument('--cap', default=os.path.join(REPO, 'build/prev/cap.npz'))
ap.add_argument('--recap', action='store_true')
ap.add_argument('--size', type=int, default=640)
ap.add_argument('--samples', type=int, default=12)
ap.add_argument('--views', default='side_right,back,front_right45,top,front,back_left45')
ap.add_argument('--nolocks', action='store_true')
ap.add_argument('--inset', default='')
args = ap.parse_args()
os.makedirs(args.out, exist_ok=True)
T0 = time.time()
HR.LOCKS_AS_PARTS = True
if args.inset:
    m, y0, y1, top, z0, z1 = map(float, args.inset.split(','))
    HR.CAP = dict(HR.CAP, inset_back={'m': m, 'y': (y0, y1), 'top': top, 'z_top': (z0, z1)})
    print('CAP inset', HR.CAP['inset_back'])
if args.recap or not os.path.exists(args.cap):
    d = np.load(os.path.join(V.WORK, 'hull.npz'))
    lo, vox, shape = d['lo'], float(d['vox']), tuple(int(s) for s in d['shape'])
    cams = V.load_calib()
    masks = {n: V.load_mask(n) for n in V.VIEWS}
    k0, phi, info = HR.build_head(cams, masks, lo, vox, shape, fit_sweeps=0)
    lo_s = lo + np.array([0, 0, k0 * vox])
    os.makedirs(os.path.dirname(args.cap), exist_ok=True)
    np.savez_compressed(args.cap, phi=phi, lo=lo_s, vox=vox)
    print('cap computed', round(time.time() - T0, 1), 's')
c = np.load(args.cap)
phi, lo, vox = c['phi'], c['lo'], float(c['vox'])
from recon import fair
xs = lo[0] + (np.arange(phi.shape[1]) + 0.5) * vox
sel = np.nonzero(np.abs(xs) < 0.30)[0]
sub = phi[:, sel[0]:sel[-1] + 1].copy()
sub[:int(0.06 / vox)] = np.minimum(sub[:int(0.06 / vox)], -0.01)
P, faces = fair.mesh_of(sub, lo + np.array([sel[0] * vox, 0, 0]), vox)
# colour: skin where the point is in the face window / below the hairline / ears / neck, else hair
f = HR.part_fields_at(P) if False else None
zh = HR.hairline_z(np.abs(P[:, 0]))
skin = ((P[:, 1] < HR.HAIRLINE['y_face']) & (P[:, 2] < zh)) | (P[:, 2] < 1.215)
for sx in (1, -1):
    cc = np.array([sx * HR.EAR['c'][0], HR.EAR['c'][1], HR.EAR['c'][2]])
    skin |= (np.sum(((P - cc) / (np.array(HR.EAR['r']) * 1.25 + 0.004)) ** 2, 1) < 1.0)
gog = (P[:, 1] < -0.03) & (P[:, 2] > 1.392) & (P[:, 2] < 1.49) & (np.abs(P[:, 0]) < 0.125)
locks = []
if not args.nolocks:
    import importlib
    import costume as CO      # loads chars/haru_parts.py into costume
    fn = getattr(CO.PARTS, 'hair_locks', None)
    locks = fn(phi=phi, lo=lo, vox=vox) if fn else []
print('locks', len(locks), 'tris', sum(len(l['mesh'][1]) for l in locks))
import bpy
strap = None
if not args.nolocks and getattr(CO, 'GOGGLE_STRAP', None):
    from mathutils.bvhtree import BVHTree
    bvh = BVHTree.FromPolygons([tuple(map(float, v)) for v in P], [tuple(map(int, t)) for t in faces])
    sV, sF, sinfo = CO.build_goggle_strap(dict(name='goggle_strap', **CO.GOGGLE_STRAP), bvh)
    strap = (sV, sF)
    npush = 0
    for L in locks:
        if L.get('strap_push'):
            V2, k = CO.strap_push(L['mesh'][0])
            L['mesh'] = (V2, L['mesh'][1])
            npush += k
    print('strap', sinfo, 'pushed', npush)
from lib import common as C
C.reset_scene()
def mk(name, V_, F_, rgb):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(map(float, v)) for v in V_], [], [tuple(map(int, t)) for t in F_])
    me.update()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    m = bpy.data.materials.new(name + '_m'); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']; b.inputs['Base Color'].default_value = rgb + (1,)
    b.inputs['Roughness'].default_value = 0.85
    me.materials.append(m)
    return ob
def srgb(h):
    h = h.lstrip('#'); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c)
HAIR, SKIN, GRAPH = srgb('#594333'), srgb('#E7B58D'), srgb('#444641')
fs = faces
lab = np.where(skin, 0, np.where(gog, 2, 1))
flab = lab[fs].max(1)
for k, col, nm in ((0, SKIN, 'skin'), (1, HAIR, 'cap'), (2, GRAPH, 'gog')):
    ff = fs[flab == k]
    if len(ff):
        ob = mk(nm, P, ff, col)
for i, L in enumerate(locks):
    col = {'umber': HAIR, 'graphite': GRAPH}.get(L.get('color', 'umber'), HAIR)
    ob = mk(L['name'], L['mesh'][0], L['mesh'][1], col)
    ob.data.polygons.foreach_set('use_smooth', [False] * len(ob.data.polygons))
if strap is not None:
    mk('strap', strap[0], strap[1], GRAPH)
sc = bpy.context.scene
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = args.samples
sc.render.threads_mode = 'FIXED'; sc.render.threads = 2
sc.cycles.use_denoising = True; sc.render.film_transparent = True; sc.view_settings.view_transform = 'Standard'
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
w.node_tree.nodes['Background'].inputs['Color'].default_value = (1, 1, 1, 1)
w.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.75
cd = bpy.data.cameras.new('cam'); cd.type = 'ORTHO'; cd.clip_end = 30
cam = bpy.data.objects.new('cam', cd); sc.collection.objects.link(cam); sc.camera = cam
ld = bpy.data.lights.new('sun', 'SUN'); ld.energy = 1.6; ld.angle = math.radians(15)
sun = bpy.data.objects.new('sun', ld); sc.collection.objects.link(sun)
from mathutils import Matrix, Vector
from recon import review as RV
CEN = (0.0, 0.035, 1.37); W = 0.56
VIEWS = {'side_right': (90, 0), 'back': (180, 0), 'front_right45': (45, 0), 'top': (0, 90), 'front': (0, 0),
         'back_left45': (-135, 0), 'side_left': (-90, 0), 'back_right45': (135, 0), 'top_back': (180, 50),
         'back_high': (180, 14), 'back_r30': (150, 10), 'side_left_hi': (-110, 20)}
for vn in args.views.split(','):
    az, el = VIEWS[vn]
    if el == 90:
        d = np.array([0, 0, -1.0]); r = np.array([1.0, 0, 0])
    else:
        d, r = RV.az_dirs(az, el)
    d = Vector(d).normalized(); r = Vector(r).normalized(); up = r.cross(d).normalized()
    cam.matrix_world = Matrix.Translation(Vector(CEN) - d * 10.0) @ Matrix((r, up, -d)).transposed().to_4x4()
    cd.ortho_scale = W
    ldir = (-d + (-r) * 0.5 + Vector((0, 0, 1)) * 0.8).normalized()
    sun.matrix_world = ldir.to_track_quat('Z', 'Y').to_matrix().to_4x4()
    sc.render.resolution_x = sc.render.resolution_y = args.size
    sc.render.filepath = os.path.join(args.out, vn + '.png')
    bpy.ops.render.render(write_still=True)
print('done', round(time.time() - T0, 1), 's')
