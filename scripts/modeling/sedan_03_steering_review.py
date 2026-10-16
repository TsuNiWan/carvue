"""Render both Study front wheel envelopes at the product steering limits."""
import hashlib
import json
import math
import sys
from datetime import datetime,timezone
from pathlib import Path

import bpy
from mathutils import Quaternion,Vector


ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'assets/source/sedan-03'
ASSET=ROOT/'public/models/sedan-03/1.1.0/vehicle.glb'
BLEND=SOURCE/'vehicle.blend'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def point(value):
    return value[0],-value[2],value[1]


def hashes():
    return {'glbSha256':digest(ASSET),'rawSha256':digest(SOURCE/'vehicle.raw.glb'),
            'blendSha256':digest(BLEND)}


frozen=hashes()
manifest=json.loads((ASSET.parent/'manifest.json').read_text(encoding='utf-8'))
bpy.ops.wm.open_mainfile(filepath=str(BLEND))
scene=bpy.context.scene
camera=scene.camera
camera.data.type='ORTHO'
camera.data.clip_end=1000
camera.data.ortho_scale=1.35
scene.render.resolution_x=1400
scene.render.resolution_y=1000
scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
scene.cycles.samples=24
wheels={name:bpy.data.objects[name] for name in manifest['frontWheels']}
closed={name:node.matrix_basis.to_quaternion() for name,node in wheels.items()}
for node in wheels.values():
    node.rotation_mode='QUATERNION'
images=[]
for degrees in [-30,30]:
    for name,node in wheels.items():
        node.rotation_quaternion=closed[name] @ Quaternion(Vector(point((0,1,0))),math.radians(degrees))
    for side,label in [(1,'left'),(-1,'right')]:
        position=(side*3.4,.90,3.7)
        target=(side*.72,.40,1.4325)
        camera.location=point(position)
        camera.rotation_euler=(Vector(point(target))-camera.location).to_track_quat('-Z','Y').to_euler()
        name=f'steering-{label}-{degrees:+03}'
        scene.render.filepath=str(SOURCE/'qa'/(name+'.png'))
        bpy.ops.render.render(write_still=True)
        images.append({'file':name+'.png','steeringDegrees':degrees,'wheelNodes':list(wheels),
                       'cameraPosition':position,'target':target,'projection':'orthographic','orthoScale':1.35})
assert frozen==hashes(),'Frozen model files changed during steering review'
record={'vehicleId':'sedan-03',**frozen,'completedAt':datetime.now(timezone.utc).isoformat(),
        'images':images,'visualApproval':'pending independent review',
        'renderBackend':{'engine':scene.render.engine,'blenderVersion':bpy.app.version_string,
                         'deviceOverride':sys.argv[sys.argv.index('--cycles-device')+1] if '--cycles-device' in sys.argv else None,
                         'resolution':[1400,1000],'samples':24,'viewTransform':scene.view_settings.view_transform}}
(SOURCE/'qa/steering-batch.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
print('sedan_03_STEERING_READY')
