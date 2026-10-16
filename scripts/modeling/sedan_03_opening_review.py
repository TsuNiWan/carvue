"""Render only the two frozen Study rear-opening regression views."""
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


def hashes():
    return {key:hashlib.sha256(path.read_bytes()).hexdigest() for key,path in [
        ('glbSha256',ASSET),('rawSha256',SOURCE/'vehicle.raw.glb'),('blendSha256',BLEND)]}


def point(value):
    return value[0],-value[2],value[1]


frozen=hashes()
manifest=json.loads((ASSET.parent/'manifest.json').read_text(encoding='utf-8'))
bpy.ops.wm.open_mainfile(filepath=str(BLEND))
scene=bpy.context.scene
camera=scene.camera
camera.data.type='ORTHO'
camera.data.clip_end=1000
camera.data.ortho_scale=6
camera.location=point((-24/math.sqrt(2),8.16,-24/math.sqrt(2)))
camera.rotation_euler=(Vector(point((0,.72,0)))-camera.location).to_track_quat('-Z','Y').to_euler()
scene.render.resolution_x=1400
scene.render.resolution_y=900
scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
scene.cycles.samples=24
joints={key:bpy.data.objects[definition['node']] for key,definition in manifest['joints'].items()}
closed={key:node.matrix_basis.to_quaternion() for key,node in joints.items()}
for node in joints.values():
    node.rotation_mode='QUATERNION'
images=[]
for name,fractions in [('open-rearRight',{'rearRight':1}),('half-rear',{key:.5 for key in joints})]:
    for key,node in joints.items():
        definition=manifest['joints'][key]
        node.rotation_quaternion=closed[key] @ Quaternion(Vector(point(definition['axis'])),definition['openAngle']*fractions.get(key,0))
    scene.render.filepath=str(SOURCE/'qa'/(name+'.png'))
    bpy.ops.render.render(write_still=True)
    images.append({'file':name+'.png','parts':fractions,'cameraPosition':[-24/math.sqrt(2),8.16,-24/math.sqrt(2)],
                   'target':[0,.72,0],'projection':'orthographic','orthoScale':6})
assert frozen==hashes(),'Frozen model files changed during opening review'
record={'vehicleId':'sedan-03',**frozen,'completedAt':datetime.now(timezone.utc).isoformat(),
        'images':images,'visualApproval':'pending independent review',
        'renderBackend':{'engine':scene.render.engine,'blenderVersion':bpy.app.version_string,
                         'deviceOverride':sys.argv[sys.argv.index('--cycles-device')+1] if '--cycles-device' in sys.argv else None,
                         'resolution':[1400,900],'samples':24,'viewTransform':scene.view_settings.view_transform}}
(SOURCE/'qa/opening-batch.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
print('sedan_03_OPENING_READY')
