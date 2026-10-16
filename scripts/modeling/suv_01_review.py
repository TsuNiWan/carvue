"""Focused Vehicle material/structure review; never modifies the source model."""
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import bpy
from mathutils import Quaternion, Vector


workspace=Path(__file__).resolve().parents[2]
source=workspace/'assets/source/suv-01'
asset=workspace/'public/models/suv-01/1.1.0/vehicle.glb'
bpy.ops.wm.open_mainfile(filepath=str(source/'vehicle.blend'))
scene=bpy.context.scene
camera=scene.camera
camera.data.type='ORTHO'
camera.data.clip_end=1000
scene.render.resolution_x=1000
scene.render.resolution_y=750
scene.render.resolution_percentage=100
scene.cycles.samples=14
scene.render.image_settings.file_format='PNG'


def point(value):
    return value[0],-value[2],value[1]


views=[
    ('detail-front-lamp',(2.7,1.50,4.4),(.62,.985,2.04),.91),
    ('detail-front-corner',(2.4,.84,4.0),(.60,.47,2.10),1.21),
    ('detail-rear-lamp',(3.4,1.65,-4.2),(.78,1.295,-2.05),1.28),
    ('detail-wheel',(4.0,.69,1.75),(.90,.410,1.35),1.02),
    ('detail-rear-signal',(3.4,1.65,-4.2),(.78,1.295,-2.05),1.28),
]
candidate_only='--candidate-only' in sys.argv
steering_only='--steering-only' in sys.argv
motion_candidate='--motion-candidate' in sys.argv
if candidate_only:
    views=[view for view in views if view[0] in ('detail-front-corner','detail-wheel','detail-rear-signal')]
if steering_only:
    views=[('detail-steering-left',(4.0,.69,1.75),(.90,.410,1.35),1.20),
           ('detail-steering-right',(4.0,.69,1.75),(.90,.410,1.35),1.20)]
if motion_candidate:
    diagonal=24/math.sqrt(2)
    views=[('candidate-open-doors',(diagonal,12.06,diagonal),(0,.72,0),6),
           ('candidate-half-front',(diagonal,8.16,diagonal),(0,.72,0),6),
           ('candidate-open-rearLeft',(diagonal,8.16,-diagonal),(0,.72,0),6),
           ('detail-steering-left',(4.0,.69,1.75),(.90,.410,1.35),1.20),
           ('detail-steering-right',(4.0,.69,1.75),(.90,.410,1.35),1.20),
           ('candidate-rear-quarter',(diagonal,5.31,-diagonal),(0,.72,0),6)]
    scene.render.resolution_x,scene.render.resolution_y=1400,900
    scene.cycles.samples=24
manifest=json.loads((asset.parent/'manifest.json').read_text(encoding='utf-8'))
joint_poses={key:bpy.data.objects[definition['node']].matrix_basis.to_quaternion()
             for key,definition in manifest['joints'].items()}
wheel_poses={name:bpy.data.objects[name].matrix_basis.to_quaternion()
             for name in ('wheel_frontLeft','wheel_frontRight')}
images=[]
for name,position,target,scale in views:
    signal_on=name=='detail-rear-signal'
    steering_degrees=30 if name=='detail-steering-left' else -30 if name=='detail-steering-right' else 0
    parts={key:(1 if name=='candidate-open-doors' and key!='trunk' else
                .5 if name=='candidate-half-front' else
                1 if name=='candidate-open-rearLeft' and key=='rearLeft' else 0)
           for key in joint_poses}
    for key,closed_pose in joint_poses.items():
        definition=manifest['joints'][key]
        joint=bpy.data.objects[definition['node']]
        joint.rotation_mode='QUATERNION'
        joint.rotation_quaternion=closed_pose @ Quaternion(Vector(point(definition['axis'])),definition['openAngle']*parts[key])
    for wheel_name,closed_pose in wheel_poses.items():
        wheel=bpy.data.objects[wheel_name]
        wheel.rotation_mode='QUATERNION'
        wheel.rotation_quaternion=closed_pose @ Quaternion(Vector(point((0,1,0))),math.radians(steering_degrees))
    for material_name in ('SignalLeft','SignalRight'):
        bpy.data.materials[material_name].node_tree.nodes['Principled BSDF'].inputs['Emission Strength'].default_value=3 if signal_on else 0
    camera.location=point(position)
    camera.rotation_euler=(Vector(point(target))-camera.location).to_track_quat('-Z','Y').to_euler()
    camera.data.ortho_scale=scale
    scene.render.filepath=str(source/'qa'/(name+'.png'))
    bpy.ops.render.render(write_still=True)
    images.append({'file':name+'.png','cameraPosition':position,'target':target,'orthoScale':scale,
                   'rearSignalsOn':signal_on,'steeringDegrees':steering_degrees,'parts':parts})
record={
    'vehicleId':'suv-01','glbSha256':hashlib.sha256(asset.read_bytes()).hexdigest(),
    'blendSha256':hashlib.sha256((source/'vehicle.blend').read_bytes()).hexdigest(),
    'completedAt':datetime.now(timezone.utc).isoformat(),'images':images,'visualApproval':'pending review',
    'renderBackend':{'engine':scene.render.engine,'blenderVersion':bpy.app.version_string,
                     'deviceOverride':sys.argv[sys.argv.index('--cycles-device')+1] if '--cycles-device' in sys.argv else None,
                     'overrideSource':'Cycles command-line device override',
                     'resolution':[scene.render.resolution_x,scene.render.resolution_y],
                     'samples':scene.cycles.samples,'viewTransform':scene.view_settings.view_transform},
}
batch_name=('motion-candidate-batch.json' if motion_candidate else 'steering-batch.json' if steering_only
            else 'candidate-batch.json' if candidate_only else 'optics-batch.json')
(source/'qa'/batch_name).write_text(json.dumps(record,indent=2),encoding='utf-8')
print('CRV_OPTICS_READY')
