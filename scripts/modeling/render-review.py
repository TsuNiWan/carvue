"""Render repeatable exterior review views from the editable source asset."""
import bpy
import math
import sys
import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from mathutils import Quaternion, Vector

ROOT = Path(__file__).resolve().parents[2]
args = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
vehicle_id = args[0] if args else 'sedan-01'
source = ROOT / 'assets/source' / vehicle_id
bpy.ops.wm.open_mainfile(filepath=str(source/'vehicle.blend'))
scene = bpy.context.scene
camera = scene.camera
camera.data.clip_end=1000
scene.render.resolution_x = 1400
scene.render.resolution_y = 900
scene.cycles.samples = 24
scene.render.image_settings.file_format = 'PNG'
rendered=[]
asset_path=ROOT/'public/models'/vehicle_id/'1.1.0/vehicle.glb'
asset_hash=hashlib.sha256(asset_path.read_bytes()).hexdigest()
manifest=json.loads((asset_path.parent/'manifest.json').read_text(encoding='utf-8'))

def point(value): return (value[0],-value[2],value[1])

joint_nodes={key:bpy.data.objects[definition['node']] for key,definition in manifest['joints'].items()}
closed_poses={key:node.matrix_basis.to_quaternion() for key,node in joint_nodes.items()}
for node in joint_nodes.values(): node.rotation_mode='QUATERNION'

def pose(key, fraction):
    definition=manifest['joints'][key]
    joint_nodes[key].rotation_quaternion=closed_poses[key] @ Quaternion(Vector(point(definition['axis'])),definition['openAngle']*fraction)

def render(name, angle, height=2.25):
    camera.location=point((24*math.sin(angle),.72+(height-.72)*3,24*math.cos(angle)))
    camera.rotation_euler=(Vector(point((0,.72,0)))-camera.location).to_track_quat('-Z','Y').to_euler()
    camera.data.ortho_scale=6.0
    scene.render.filepath=str(source/'qa'/(name+'.png'))
    bpy.ops.render.render(write_still=True)
    rendered.append({'file':name+'.png','angleRadians':angle,'cameraHeight':.72+(height-.72)*3,'target':[0,.72,0],'cameraRadius':24,'projection':'orthographic','orthoScale':6})

def record_batch(name):
    record={'vehicleId':vehicle_id,'glbSha256':asset_hash,'blendSha256':hashlib.sha256((source/'vehicle.blend').read_bytes()).hexdigest(),'completedAt':datetime.now(timezone.utc).isoformat(),'images':rendered,'visualApproval':'pending review'}
    (source/'qa'/(name+'.json')).write_text(json.dumps(record,indent=2),encoding='utf-8')

if '--realism-study' in args:
    scene.render.resolution_x=1200
    scene.render.resolution_y=800
    scene.cycles.samples=10
    for name,angle,height in [('study-front-quarter',math.pi/4,1.75),('study-side',math.pi/2,.72),('study-rear-quarter',math.pi*.75,1.75),('study-rear',math.pi,1.2)]:
        bpy.data.objects['StudioGround'].hide_render=name=='study-side'
        render(name,angle,height)
    record_batch('realism-study-batch')
    print('REALISM_STUDY_READY',vehicle_id)
    sys.exit(0)

if '--handle-close' in args:
    detail_position=(3.8,1.45,-.48)
    detail_target=(.81,.90,-.66)
    camera.location=point(detail_position)
    camera.rotation_euler=(Vector(point(detail_target))-camera.location).to_track_quat('-Z','Y').to_euler()
    camera.data.ortho_scale=1.85
    scene.render.filepath=str(source/'qa/handles-close.png')
    bpy.ops.render.render(write_still=True)
    rendered.append({'file':'handles-close.png','cameraPosition':detail_position,'target':detail_target,'projection':'orthographic','orthoScale':1.85})

if '--rear-only' in args:
    scene.cycles.samples=16
    render('material-rear-quarter',math.pi*1.25,2.1)
    render('material-rear',math.pi,1.2)
    record_batch('rear-batch')
    print('REAR_REVIEW_READY',vehicle_id)
    sys.exit(0)

if '--shape-only' in args:
    scene.render.resolution_x=1100
    scene.render.resolution_y=700
    scene.cycles.samples=12
    for material_name in ['BodyPaint','InnerPaint']:
        shader=bpy.data.materials[material_name].node_tree.nodes['Principled BSDF']
        shader.inputs['Base Color'].default_value=(.24,.24,.24,1)
        shader.inputs['Metallic'].default_value=0
        shader.inputs['Roughness'].default_value=.72
        shader.inputs['Coat Weight'].default_value=0
    for name,angle,height in [('shape-front',0,1.2),('shape-front-quarter',math.pi/4,1.75),('shape-side',math.pi/2,.72),('shape-rear-quarter',math.pi*1.25,1.75),('shape-rear',math.pi,1.2)]:
        bpy.data.objects['StudioGround'].hide_render=name=='shape-side'
        render(name,angle,height)
    bpy.data.objects['StudioGround'].hide_render=False
    print('SHAPE_REVIEW_READY',vehicle_id)
    record_batch('shape-batch')
    sys.exit(0)

if '--steering-only' in args:
    wheels={name:bpy.data.objects[name] for name in manifest['frontWheels']}
    closed={name:node.matrix_basis.to_quaternion() for name,node in wheels.items()}
    centres={name:node.matrix_world.translation.copy() for name,node in wheels.items()}
    for node in wheels.values(): node.rotation_mode='QUATERNION'
    camera.data.type='ORTHO'
    camera.data.ortho_scale=1.6
    scene.render.resolution_x=1400
    scene.render.resolution_y=1000
    for degrees in [-30,30]:
        for name,node in wheels.items():
            node.rotation_quaternion=closed[name] @ Quaternion(Vector(point((0,1,0))),math.radians(degrees))
        for name,centre in centres.items():
            side=1 if centre.x>0 else -1
            target=(centre.x,centre.z+.05,-centre.y)
            position=(side*3.4,1.0,target[2]+2.3)
            camera.location=point(position)
            camera.rotation_euler=(Vector(point(target))-camera.location).to_track_quat('-Z','Y').to_euler()
            filename=f'steering-{name}-{degrees:+03}.png'
            scene.render.filepath=str(source/'qa'/filename)
            bpy.ops.render.render(write_still=True)
            rendered.append({'file':filename,'steeringDegrees':degrees,'wheelNode':name,
                             'cameraPosition':position,'target':target,'projection':'orthographic','orthoScale':1.6})
    assert hashlib.sha256(asset_path.read_bytes()).hexdigest()==asset_hash,'Model changed during steering review'
    record_batch('steering-batch')
    print('STEERING_REVIEW_READY',vehicle_id)
    sys.exit(0)

if '--poster-only' not in args:
    if '--open-only' not in args:
        for i in range(8): render(f'angle-{i*45:03}',i*math.pi/4)
    for name,angle in [('frontLeft',math.pi/4),('rearLeft',math.pi*.75),('frontRight',math.pi*1.75),('rearRight',math.pi*1.25)]:
        pose(name,1)
        render('open-'+name,angle,3.2)
        pose(name,0)
    for name in ['frontLeft','frontRight','rearLeft','rearRight']:
        pose(name,1)
    render('open-doors',math.pi/4,4.5)
    for name in ['frontLeft','frontRight','rearLeft','rearRight']:
        pose(name,0)
    pose('trunk',1)
    render('open-trunk',math.pi*1.25,4.5)
    for name in ['frontLeft','frontRight','rearLeft','rearRight']:
        pose(name,.5)
    pose('trunk',.5)
    render('half-front',math.pi/4,3.2)
    render('half-rear',math.pi*1.25,3.2)
    for name in ['frontLeft','frontRight','rearLeft','rearRight']:
        pose(name,0)
    pose('trunk',0)

scene.render.resolution_x=960
scene.render.resolution_y=640
scene.cycles.samples=32
scene.render.film_transparent=True
bpy.data.objects['StudioGround'].is_shadow_catcher=True
render('poster-source',math.pi/4)
scene.render.image_settings.file_format='WEBP'
scene.render.image_settings.quality=92
bpy.data.images['Render Result'].save_render(str(ROOT/'public/previews'/(vehicle_id+'.webp')),scene=scene)
record_batch('review-batch')
print('REVIEW_AND_POSTER_READY',vehicle_id)
