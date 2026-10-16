"""Render version-bound Vehicle detail evidence without changing the source asset."""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import bpy
from mathutils import Vector


workspace = Path(__file__).resolve().parents[2]
source = workspace / 'assets/source/sedan-02'
asset = workspace / 'public/models/sedan-02/1.1.0/vehicle.glb'
bpy.ops.wm.open_mainfile(filepath=str(source / 'vehicle.blend'))
scene = bpy.context.scene
camera = scene.camera
camera.data.type = 'ORTHO'
camera.data.clip_end = 1000
scene.render.resolution_x = 1200
scene.render.resolution_y = 800
scene.render.resolution_percentage = 100
scene.cycles.samples = 20
scene.render.image_settings.file_format = 'PNG'


def point(value):
    return value[0], -value[2], value[1]


views = [
    ('detail-front-lamp', (2.8, 1.65, 4.0), (.55, .79, 2.02), 1.65),
    ('detail-tail-rings', (2.6, 1.55, -4.1), (.60, .90, -2.19), 1.23),
    ('detail-rear-wheel', (4.0, .65, -1.70), (.86, .42, -1.3625), 1.1),
    ('detail-window-roof', (4.0, 2.35, .10), (.60, 1.14, -.20), 2.8),
]
images = []
for name, position, target, scale in views:
    camera.location = point(position)
    camera.rotation_euler = (Vector(point(target)) - camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera.data.ortho_scale = scale
    scene.render.filepath = str(source / 'qa' / (name + '.png'))
    bpy.ops.render.render(write_still=True)
    images.append({'file': name + '.png', 'cameraPosition': position, 'target': target, 'orthoScale': scale})
record = {
    'vehicleId': 'sedan-02',
    'glbSha256': hashlib.sha256(asset.read_bytes()).hexdigest(),
    'blendSha256': hashlib.sha256((source / 'vehicle.blend').read_bytes()).hexdigest(),
    'completedAt': datetime.now(timezone.utc).isoformat(),
    'images': images,
    'visualApproval': 'pending independent review',
    'renderBackend': {
        'engine': scene.render.engine, 'blenderVersion': bpy.app.version_string,
        'deviceOverride': sys.argv[sys.argv.index('--cycles-device') + 1] if '--cycles-device' in sys.argv else None,
        'resolution': [scene.render.resolution_x, scene.render.resolution_y],
        'samples': scene.cycles.samples, 'viewTransform': scene.view_settings.view_transform,
    },
}
(source / 'qa/detail-batch.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
print('Study3_DETAILS_READY')
