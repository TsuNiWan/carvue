"""Small CPU reproduction of sharp-edge edits after custom corner normals."""
import json
import math
from pathlib import Path
import bpy

records = []
for name, normals in [('custom_crease', [(0, 0, 1)] * 3 + [(0, .6, .8)] * 3),
                      ('smooth', [(0, .3, .9539392014)] * 6)]:
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)], [], [(0, 1, 2), (0, 2, 3)])
    for polygon in mesh.polygons:
        polygon.use_smooth = True
    mesh.normals_split_custom_set(normals)
    before = [tuple(n.vector) for n in mesh.corner_normals]
    before_sharp = [bool(e.use_edge_sharp) for e in mesh.edges]
    mesh.set_sharp_from_angle(angle=math.radians(35))
    after = [tuple(n.vector) for n in mesh.corner_normals]
    records.append({'name': name, 'before': before, 'after': after, 'beforeSharp': before_sharp,
                    'afterSharp': [bool(e.use_edge_sharp) for e in mesh.edges],
                    'maxDifference': max(math.dist(a, b) for a, b in zip(before, after))})
    mesh.normals_split_custom_set(normals)
    fixed_before = [tuple(n.vector) for n in mesh.corner_normals]
    fixed_sharp = [bool(e.use_edge_sharp) for e in mesh.edges]
    if not mesh.has_custom_normals:
        mesh.set_sharp_from_angle(angle=math.radians(35))
    fixed_after = [tuple(n.vector) for n in mesh.corner_normals]
    fixed_difference = max(math.dist(a, b) for a, b in zip(fixed_before, fixed_after))
    assert fixed_difference == 0
    assert fixed_sharp == [bool(e.use_edge_sharp) for e in mesh.edges]
    records[-1]['fixedBranch'] = {'maxDifference': fixed_difference,
                                'sharpEdgesPreserved': True, 'cornerNormalsPreserved': True}
path = Path(__file__).resolve().parents[2] / 'assets/source/suv-02/qa/custom-normal-sharp-probe.json'
path.write_text(json.dumps(records, indent=2), encoding='utf-8')
print(json.dumps(records, indent=2))
