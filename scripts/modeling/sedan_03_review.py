"""Render Study structural, optical and glazing review details."""
import hashlib
import json
import sys
from datetime import datetime,timezone
from pathlib import Path

import bpy
from mathutils import Vector


ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'assets/source/sedan-03'
ASSET=ROOT/'public/models/sedan-03/1.1.0/vehicle.glb'
RAW=SOURCE/'vehicle.raw.glb'
BLEND=SOURCE/'vehicle.blend'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def point(value):
    return value[0],-value[2],value[1]


hashes={'glbSha256':digest(ASSET),'rawSha256':digest(RAW),'blendSha256':digest(BLEND)}
bpy.ops.wm.open_mainfile(filepath=str(BLEND))
scene=bpy.context.scene
camera=scene.camera
camera.data.type='ORTHO'
camera.data.clip_end=1000
scene.render.resolution_x=1400
scene.render.resolution_y=1000
scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
scene.cycles.samples=24
views=[
    ('detail-front-lamp-intake',(3.6,1.45,5.2),(.60,.62,2.01),1.65),
    ('detail-front-arch-door',(4.5,1.18,1.40),(.79,.65,.80),2.25),
    ('detail-rear-arch-join',(4.1,1.46,-4.4),(.79,.72,-1.75),1.95),
    ('detail-window-roof',(4.6,2.50,.25),(.63,1.15,-.32),3.0),
]
images=[]
for name,position,target,scale in views:
    camera.location=point(position)
    camera.rotation_euler=(Vector(point(target))-camera.location).to_track_quat('-Z','Y').to_euler()
    camera.data.ortho_scale=scale
    scene.render.filepath=str(SOURCE/'qa'/(name+'.png'))
    bpy.ops.render.render(write_still=True)
    images.append({'file':name+'.png','cameraPosition':position,'target':target,
                   'projection':'orthographic','orthoScale':scale})
assert hashes=={'glbSha256':digest(ASSET),'rawSha256':digest(RAW),'blendSha256':digest(BLEND)},'Asset changed during review'
record={'vehicleId':'sedan-03',**hashes,'completedAt':datetime.now(timezone.utc).isoformat(),
        'images':images,'visualApproval':'pending independent review',
        'renderBackend':{'engine':scene.render.engine,'blenderVersion':bpy.app.version_string,
                         'deviceOverride':sys.argv[sys.argv.index('--cycles-device')+1] if '--cycles-device' in sys.argv else None,
                         'resolution':[scene.render.resolution_x,scene.render.resolution_y],
                         'samples':scene.cycles.samples,'viewTransform':scene.view_settings.view_transform}}
(SOURCE/'qa/detail-batch.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
print('sedan_03_DETAILS_READY')
