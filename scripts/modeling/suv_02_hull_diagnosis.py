"""Reproduce the small tail-lamp convex volume without loading or rendering a car."""
import json
import sys
from pathlib import Path

import bmesh
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from suv_02_surfaces import corner_path, tail_position

ROOT = Path(__file__).resolve().parents[2]
outline = [(.443, 1.094), (.816, 1.113), (.859, 1.109),
           (.858, 1.008), (.459, 1.026), (.418, 1.055)]
failures = json.loads((ROOT / 'assets/source/suv-02/qa/eighth-visibility-triangles.json').read_text())['opticalSamples']


def point(p):
    return (p[0], -p[2], p[1])


records = []
for sign in (-1, 1):
    perimeter = [(sign * x, y) for x, y in corner_path(outline, .055)]
    points = [point(tail_position(x, y, depth)) for depth in (.012, -.070) for x, y in perimeter]
    hull = bmesh.new()
    vertices = [hull.verts.new(p) for p in points]
    result = bmesh.ops.convex_hull(hull, input=vertices, use_existing_faces=False)
    result_faces = {item for item in result['geom'] if isinstance(item, bmesh.types.BMFace)}
    hull.normal_update()
    center = sum((v.co for v in vertices), Vector()) / len(vertices)
    planes = []
    for face in hull.faces:
        normal = face.normal.copy()
        d = -normal.dot(face.verts[0].co)
        if normal.dot(center) + d > 0:
            normal, d = -normal, -d
        distances = [normal.dot(Vector(p)) + d for p in points]
        planes.append({'normal': list(normal), 'd': d, 'area': face.calc_area(),
                       'inResultGeometry': face in result_faces,
                       'maxInputSignedDistance': max(distances),
                       'vertices': [list(v.co) for v in face.verts]})
    sample_rows = []
    for sample in failures:
        blocked = sample['blockingPaint']
        if not blocked or sample['lamp'] != 'tail' or sample['logicalXY'][0] * sign <= 0 or abs(sample['logicalXY'][0]) > .85:
            continue
        p = Vector(point(blocked['point']))
        distances = [Vector(plane['normal']).dot(p) + plane['d'] for plane in planes]
        sample_rows.append({'pointOrbit': blocked['point'], 'pointBlender': list(p),
                            'triangleOrbit': blocked['triangle'], 'maxSignedDistance': max(distances),
                            'positivePlaneIndices': [i for i, distance in enumerate(distances) if distance > 1e-5]})
    records.append({'sign': sign, 'perimeter': perimeter, 'hullInputBlender': points,
                    'centerBlender': list(center), 'planes': planes, 'samples': sample_rows,
                    'resultGeometryCount': len(result['geom']),
                    'resultFaceCount': len(result_faces),
                    'invalidSupportPlaneCount': sum(plane['maxInputSignedDistance'] > 1e-5 for plane in planes)})
    hull.free()

target = ROOT / 'assets/source/suv-02/qa/eighth-hull-diagnosis.json'
target.write_text(json.dumps(records, indent=2), encoding='utf-8')
print(json.dumps([{'sign': record['sign'], 'planes': len(record['planes']),
                   'invalidSupportPlaneCount': record['invalidSupportPlaneCount'],
                   'maxInputSignedDistance': max(p['maxInputSignedDistance'] for p in record['planes']),
                   'samples': record['samples']} for record in records], indent=2))
