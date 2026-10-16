"""Audit editable sources and render neutral previews from the saved scene."""
import bpy
import hashlib
import json
import sys
from pathlib import Path
from mathutils import Vector

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from public_source import save_source

ids = ['sedan-01', 'suv-01', 'sedan-02', 'suv-02', 'sedan-03']
records = []
for vehicle_id in ids:
    source = root / 'assets/source' / vehicle_id / 'vehicle.blend'
    bpy.ops.wm.open_mainfile(filepath=str(source))
    vehicle = bpy.data.objects['VehicleRoot']
    assert vehicle['vehicleId'] == vehicle_id
    assert vehicle['assetVersion'] == '1.1.0'
    images = [{'name': image.name, 'source': image.source, 'packed': bool(image.packed_file), 'path': image.filepath}
              for image in bpy.data.images if image.type not in {'RENDER_RESULT', 'COMPOSITING'}]
    assert not images, 'Editable model must not contain photographic image references'
    assert not list(bpy.data.libraries), 'External linked libraries are not allowed'
    assert not list(bpy.data.texts), 'Embedded scripts are not allowed'
    assert all(not font.filepath or font.filepath == '<builtin>' for font in bpy.data.fonts), 'External font reference'
    output = source.parent / 'qa'
    output.mkdir(exist_ok=True)
    scene = bpy.context.scene
    camera = scene.camera
    camera.data.clip_end = 1000
    camera.location = (8, -8, 3.5)
    camera.rotation_euler = (Vector((0, 0, .72)) - camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera.data.ortho_scale = 6.4
    scene.render.resolution_x = 1200
    scene.render.resolution_y = 750
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.filepath = '//qa/preview.png'
    save_source(source)
    bpy.ops.render.render(write_still=True)
    records.append({'id': vehicle_id, 'blendSha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                    'imageReferences': images, 'linkedLibraries': 0, 'embeddedScripts': 0,
                    'nodes': len(vehicle.children_recursive), 'preview': f'public/previews/{vehicle_id}.webp'})
destination = root / 'docs/evidence/source-audit.json'
destination.write_text(json.dumps(records, indent=2), encoding='utf-8')
print('Editable source audit and preview renders complete')
