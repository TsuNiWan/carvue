"""Render the three agreed Study detail checks from one frozen source asset."""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'assets/source/suv-02'
ASSET = ROOT / 'public/models/suv-02/1.1.0/vehicle.glb'
BLEND = SOURCE / 'vehicle.blend'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def point(value):
    return (value[0], -value[2], value[1])


asset_hash, blend_hash = digest(ASSET), digest(BLEND)
bpy.ops.wm.open_mainfile(filepath=str(BLEND))
scene = bpy.context.scene
camera = scene.camera
scene.render.resolution_x = 1400
scene.render.resolution_y = 900
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.cycles.samples = 24
camera.data.type = 'ORTHO'
camera.data.clip_end = 1000
views = [
    ('detail-window-pillars', (4.8, 2.7, -.65), (.72, 1.40, -.62), 2.70),
    ('detail-wheel-941', (4.3, .85, 1.90), (.87, .365, 1.4325), 1.04),
    ('detail-tail-arrows', (4.3, 1.80, -5.6), (.70, 1.05, -2.16), 1.45),
]
if '--eighth-check' in sys.argv or '--ninth-check' in sys.argv:
    base_views = views
    views = [
        ('detail-headlamp-upper', (4.3, 2.3, 5.6), (.70, 1.04, 2.04), 1.55),
        ('detail-cowl-roof', (3.0, 2.7, 2.7), (.0, 1.36, .56), 2.65),
        base_views[1] if '--eighth-check' in sys.argv else base_views[2],
        base_views[0],
    ]
rendered = []
for name, position, target, scale in views:
    camera.location = point(position)
    camera.rotation_euler = (Vector(point(target)) - camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera.data.ortho_scale = scale
    scene.render.filepath = str(SOURCE / 'qa' / (name + '.png'))
    bpy.ops.render.render(write_still=True)
    rendered.append({'file': name + '.png', 'cameraPosition': position, 'target': target,
                     'projection': 'orthographic', 'orthoScale': scale})

assert digest(ASSET) == asset_hash, 'GLB changed during the detail review'
assert digest(BLEND) == blend_hash, 'Source blend changed during the detail review'
record = {'vehicleId': 'suv-02', 'glbSha256': asset_hash, 'blendSha256': blend_hash,
          'completedAt': datetime.now(timezone.utc).isoformat(), 'images': rendered,
          'visualApproval': 'pending independent review'}
(SOURCE / 'qa/details-batch.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
print('Vehicle_DETAIL_REVIEW_READY')
