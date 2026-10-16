"""Inspect frozen mesh islands at CPU ray hits without rendering or saving."""
import json
import sys
from pathlib import Path
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / 'assets/source/suv-02/qa'
args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
blend_path = ROOT / args[0] if args else QA / '582ce8-ninth-review/vehicle.blend'
input_path = ROOT / args[1] if args else QA / 'ninth-surface-diagnosis.json'
output_path = ROOT / args[2] if args else QA / 'ninth-mesh-islands.json'
bpy.ops.wm.open_mainfile(filepath=str(blend_path))
record = json.loads(input_path.read_text())

def orbit(p):
    return [p.x, p.z, -p.y]

meshes = {}
for row in record['results']:
    hit = row['hits'][0]
    obj = bpy.data.objects[hit['mesh']]
    if obj.name not in meshes:
        obj.data.calc_loop_triangles()
        vertices = [obj.matrix_world @ v.co for v in obj.data.vertices]
        faces = [list(t.vertices) for t in obj.data.loop_triangles]
        tree = BVHTree.FromPolygons(vertices, faces, all_triangles=True)
        vertex_faces = [[] for v in vertices]
        for i, face in enumerate(faces):
            for v in face:
                vertex_faces[v].append(i)
        meshes[obj.name] = (obj, vertices, faces, tree, vertex_faces)
    obj, vertices, faces, tree, vertex_faces = meshes[obj.name]
    p = Vector((hit['point'][0], -hit['point'][2], hit['point'][1]))
    _, normal, face_id, distance = tree.find_nearest(p)
    pending, component = [face_id], set()
    while pending:
        f = pending.pop()
        if f in component:
            continue
        component.add(f)
        for v in faces[f]:
            pending.extend(n for n in vertex_faces[v] if n not in component)
    ids = set(v for f in component for v in faces[f])
    bounds = [[min(orbit(vertices[v])[i] for v in ids) for i in range(3)],
              [max(orbit(vertices[v])[i] for v in ids) for i in range(3)]]
    hit['sourceIsland'] = {'triangles': len(component), 'vertices': len(ids), 'bounds': bounds,
                           'nearestTriangle': face_id, 'distance': distance,
                           'faceNormal': orbit(normal)}
output_path.write_text(json.dumps(record, indent=2))
print(json.dumps([{'view': row['view'], 'pixel': row['pixel'],
                  'island': row['hits'][0]['sourceIsland']} for row in record['results']], indent=2))
