"""CPU checks for Vehicle boundary agreement and surface orientation."""
import ast
import hashlib
import json
import math
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.modules['bpy'] = types.ModuleType('bpy')
import suv_02_cabin
from suv_02_surfaces import belt, blend, end_skin, front_face, hood_surface

report = {'sources': {}, 'fenders': [], 'quarterWindowCells': [], 'doorBeltClearance': []}
for name in ('build_suv_02.py', 'suv_02_surfaces.py', 'suv_02_cabin.py'):
    path = ROOT / 'scripts/modeling' / name
    ast.parse(path.read_text(encoding='utf-8'))
    report['sources'][name] = hashlib.sha256(path.read_bytes()).hexdigest()
report['hoodMaximumSharedEdgeError'] = max(math.dist(hood_surface(i / 100, 1), front_face(i / 100, 1))
                                           for i in range(101))
assert report['hoodMaximumSharedEdgeError'] < 1e-12

def projected_area(a, b, c):
    return (b[1] - a[1]) * (c[2] - a[2]) - (b[2] - a[2]) * (c[1] - a[1])

for front, rear in ((2.30, .86), (-1.360, -2.395)):
    grid = [[end_skin(1, front, rear, i / 100, j / 36) for i in range(101)] for j in range(37)]
    areas = []
    for j in range(36):
        for i in range(100):
            q = [grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]]
            areas.extend((projected_area(q[0], q[1], q[2]), projected_area(q[0], q[2], q[3])))
    row = {'front': front, 'rear': rear, 'triangles': len(areas),
           'minimumProjectedDoubleArea': min(areas), 'flipped': sum(a <= 0 for a in areas)}
    report['fenders'].append(row)
    assert row['flipped'] == 0

class GeometryProbe:
    root = None

    def mesh(self, *args, **kwargs):
        return types.SimpleNamespace(data=types.SimpleNamespace(set_sharp_from_angle=lambda **kwargs: None))

    def thickness(self, *args):
        pass

    def curve(self, *args, **kwargs):
        pass

    def surface(self, name, fn, nu, nv, *args, **kwargs):
        if name not in ('DPillarShoulder', 'QuarterDivider'):
            return
        areas = []
        for j in range(nv):
            for i in range(nu):
                q = [fn(i / nu, j / nv), fn((i + 1) / nu, j / nv),
                     fn((i + 1) / nu, (j + 1) / nv), fn(i / nu, (j + 1) / nv)]
                areas.extend((projected_area(q[0], q[1], q[2]), projected_area(q[0], q[2], q[3])))
        report['quarterWindowCells'].append({'surface': name, 'triangles': len(areas),
                                             'minimumAbsoluteArea': min(abs(a) for a in areas),
                                             'positive': sum(a > 0 for a in areas),
                                             'negative': sum(a < 0 for a in areas)})

suv_02_cabin.create_door = lambda *args: None
suv_02_cabin.cabin_shell(GeometryProbe(), {name: None for name in
    ('paint', 'headliner', 'frontGlass', 'rubber', 'black', 'innerPaint', 'glass', 'silver')})
for kind, definition in suv_02_cabin.DOORS.items():
    front, rear, lower_front, _, _, lower_rear = definition
    gaps = []
    for i in range(65):
        z = blend(front, rear, i / 64)
        amount = (z - lower_front[0]) / (lower_rear[0] - lower_front[0])
        gaps.append(blend(lower_front[1], lower_rear[1], amount) - belt(z))
    report['doorBeltClearance'].append({'door': kind, 'minimum': min(gaps), 'maximum': max(gaps)})
    assert min(gaps) > 0, 'The door belt connector must not reverse orientation'

path = ROOT / (sys.argv[1] if len(sys.argv) > 1 else 'assets/source/suv-02/qa/tenth-geometry-check.json')
path.write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))
assert all(row['positive'] == 0 or row['negative'] == 0 for row in report['quarterWindowCells']), \
    'A quarter-window strip must not contain reversed triangles'
