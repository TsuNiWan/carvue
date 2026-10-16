"""Inspect the closed and moving rear door corner without changing the asset."""
import bpy
import math
import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from mathutils import Vector

root=Path(__file__).resolve().parents[2]
source=root/'assets/source/sedan-01'
bpy.ops.wm.open_mainfile(filepath=str(source/'vehicle.blend'))
scene=bpy.context.scene
camera=scene.camera
camera.data.clip_end=1000
scene.render.resolution_x=1000
scene.render.resolution_y=800
scene.cycles.samples=16
files=[]
for view,position,target,scale in [('door-lower',(3.15,1.35,.98),(.82,1.05,.46),.92),('c-pillar',(3.25,1.77,1.65),(.74,1.22,1.19),1.17)]:
    camera.data.ortho_scale=scale
    camera.location=Vector(position)
    camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler()
    for state,angle in [('closed',0),('half',33.5),('open',67)]:
        bpy.data.objects['door_rearLeft'].rotation_euler.z=-math.radians(angle)
        name=view+'-'+state+'.png'
        scene.render.filepath=str(source/'qa'/name)
        bpy.ops.render.render(write_still=True)
        files.append(name)
bpy.data.objects['door_rearLeft'].rotation_euler.z=0
bpy.data.objects['trunk'].rotation_euler.x=math.radians(70)
camera.location=Vector((3.0,4.0,1.6))
camera.rotation_euler=(Vector((0,1.95,1.05))-camera.location).to_track_quat('-Z','Y').to_euler()
camera.data.ortho_scale=2.30
scene.render.filepath=str(source/'qa/trunk-liner-detail.png')
bpy.ops.render.render(write_still=True)
files.append('trunk-liner-detail.png')
(source/'qa/door-lower-batch.json').write_text(json.dumps({
    'glbSha256':hashlib.sha256((root/'public/models/sedan-01/1.1.0/vehicle.glb').read_bytes()).hexdigest(),
    'completedAt':datetime.now(timezone.utc).isoformat(),
    'files':files,
},indent=2),encoding='utf-8')
