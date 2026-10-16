"""Render authored optical and alloy surfaces at a repeatable inspection scale."""
import bpy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from mathutils import Vector

root=Path(__file__).resolve().parents[2]
source=root/'assets/source/sedan-01'
asset_hash=hashlib.sha256((root/'public/models/sedan-01/1.1.0/vehicle.glb').read_bytes()).hexdigest()
images=[]
bpy.ops.wm.open_mainfile(filepath=str(source/'vehicle.blend'))
scene=bpy.context.scene
scene.render.resolution_x=1000
scene.render.resolution_y=800
scene.cycles.samples=12
camera=scene.camera
camera.data.clip_end=1000
def point(p): return (p[0],-p[2],p[1])
for name,position,target,scale in [
    ('detail-rear-lamp',(2.7,1.48,-4.2),(.65,.93,-2.21),1.05),
    ('detail-front-lamp',(2.5,1.42,4.5),(.64,.78,2.05),1.08),
    ('detail-front-corner',(2.8,1.16,4.8),(.76,.49,2.19),.80),
    ('detail-wheel',(3.3,.83,2.1),(.82,.34,1.365),.83),
]:
    camera.location=point(position)
    camera.rotation_euler=(Vector(point(target))-camera.location).to_track_quat('-Z','Y').to_euler()
    camera.data.ortho_scale=scale
    scene.render.filepath=str(source/'qa'/(name+'.png'))
    bpy.ops.render.render(write_still=True)
    images.append({'file':name+'.png','cameraPosition':position,'target':target,'orthoScale':scale})
(source/'qa/optics-batch.json').write_text(json.dumps({'glbSha256':asset_hash,'blendSha256':hashlib.sha256((source/'vehicle.blend').read_bytes()).hexdigest(),'completedAt':datetime.now(timezone.utc).isoformat(),'images':images,'visualApproval':'pending review'},indent=2))
