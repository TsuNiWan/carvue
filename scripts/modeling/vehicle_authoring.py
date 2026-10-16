"""Blender primitives and export plumbing for independently authored vehicles.

All input points use CARVUE meters: X left, Y up, Z forward. This module has
no body profiles, lamps, wheel designs, or other vehicle-specific geometry.
"""
import json
import math
from pathlib import Path

import bpy
import bmesh
from mathutils import Vector
from public_source import save_source

WORKSPACE = Path(__file__).resolve().parents[2]


def point(value):
    return (value[0], -value[2], value[1])


def smoothstep(value):
    value = max(0, min(1, value))
    return value * value * (3 - 2 * value)


def interpolate(samples, value):
    if value <= samples[0][0]:
        return samples[0][1]
    for (a, av), (b, bv) in zip(samples, samples[1:]):
        if value <= b:
            return av + (bv - av) * (value - a) / (b - a)
    return samples[-1][1]


class VehicleAuthoring:
    def __init__(self, vehicle_id, reference):
        self.vehicle_id = vehicle_id
        self.source = WORKSPACE / 'assets/source' / vehicle_id
        self.output = WORKSPACE / 'public/models' / vehicle_id / '1.1.0'
        for directory in [self.source, self.source / 'qa', self.output, WORKSPACE / 'public/previews']:
            directory.mkdir(parents=True, exist_ok=True)
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete(use_global=False)
        for collection in [bpy.data.meshes, bpy.data.curves, bpy.data.materials]:
            for block in list(collection):
                if block.users == 0:
                    collection.remove(block)
        self.root = self.group('VehicleRoot')
        self.root['vehicleId'] = vehicle_id
        self.root['assetVersion'] = '1.1.0'
        self.root['provenance'] = 'Reconstructed vehicle study; exterior design rights unverified'

    def group(self, name, origin=(0, 0, 0), parent=None):
        obj = bpy.data.objects.new(name, None)
        bpy.context.collection.objects.link(obj)
        obj['origin_carvue'] = list(origin)
        obj.parent = parent
        base = parent['origin_carvue'] if parent else (0, 0, 0)
        obj.location = point(tuple(origin[i] - base[i] for i in range(3)))
        return obj

    def material(self, name, color, metal=0, rough=.4, alpha=1, emission=None, coat=0):
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        linear = tuple(c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4 for c in color)
        mat.diffuse_color = (*linear, alpha)
        shader = mat.node_tree.nodes.get('Principled BSDF')
        for key, value in [('Base Color', (*linear, alpha)), ('Metallic', metal),
                           ('Roughness', rough), ('Alpha', alpha), ('Coat Weight', coat)]:
            shader.inputs[key].default_value = value
        if emission:
            shader.inputs['Emission Color'].default_value = (*emission, 1)
            shader.inputs['Emission Strength'].default_value = 1
        if alpha < 1:
            mat.surface_render_method = 'DITHERED'
        return mat

    def mesh(self, name, vertices, faces, mat, parent=None, smooth=True, normal=None):
        parent = parent if parent is not None else self.root
        origin = parent['origin_carvue']
        data = bpy.data.meshes.new(name + 'Mesh')
        data.from_pydata([point(tuple(p[i] - origin[i] for i in range(3))) for p in vertices], [], faces)
        data.update()
        obj = bpy.data.objects.new(name, data)
        bpy.context.collection.objects.link(obj)
        obj.parent = parent
        data.materials.append(mat)
        topology = bmesh.new()
        topology.from_mesh(data)
        bmesh.ops.recalc_face_normals(topology, faces=list(topology.faces))
        if normal:
            average = sum((face.normal for face in topology.faces), Vector((0, 0, 0)))
            if average.dot(Vector(point(normal))) < 0:
                bmesh.ops.reverse_faces(topology, faces=list(topology.faces))
        topology.to_mesh(data)
        topology.free()
        for polygon in data.polygons:
            polygon.use_smooth = smooth
        return obj

    @staticmethod
    def apply(obj, modifier):
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=modifier.name)

    def bevel(self, obj, width=.008, segments=3):
        modifier = obj.modifiers.new('Edge finishing', 'BEVEL')
        modifier.width, modifier.segments = width, segments
        self.apply(obj, modifier)
        return obj

    def thickness(self, obj, amount=.016):
        modifier = obj.modifiers.new('Panel thickness', 'SOLIDIFY')
        modifier.thickness, modifier.offset = amount, -1
        self.apply(obj, modifier)
        return obj

    def surface(self, name, fn, nu, nv, mat, parent=None, solid=0, normal=None):
        vertices = [fn(i / nu, j / nv) for j in range(nv + 1) for i in range(nu + 1)]
        faces = []
        for j in range(nv):
            for i in range(nu):
                a = j * (nu + 1) + i
                faces.append((a, a + 1, a + nu + 2, a + nu + 1))
        obj = self.mesh(name, vertices, faces, mat, parent, normal=normal)
        if solid:
            self.thickness(obj, solid)
        return obj

    def box(self, name, center, size, mat, parent=None, radius=.012):
        corners = [(-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1),
                   (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)]
        vertices = [tuple(center[i] + c[i] * size[i] / 2 for i in range(3)) for c in corners]
        obj = self.mesh(name, vertices, [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
                                         (3, 7, 6, 2), (0, 4, 7, 3), (1, 2, 6, 5)], mat, parent)
        if radius:
            self.bevel(obj, min(radius, min(size) / 2.1))
        return obj

    def curve(self, name, points, radius, mat, parent=None, cyclic=False, bezier=False):
        parent = parent if parent is not None else self.root
        origin = parent['origin_carvue']
        data = bpy.data.curves.new(name + 'Curve', 'CURVE')
        data.dimensions, data.resolution_u = '3D', 3
        data.bevel_depth, data.bevel_resolution, data.use_fill_caps = radius, 2, True
        spline = data.splines.new('BEZIER' if bezier else 'POLY')
        coordinates = [point(tuple(p[i] - origin[i] for i in range(3))) for p in points]
        if not bezier:
            spline.points.add(len(points) - 1)
            for target, coordinate in zip(spline.points, coordinates):
                target.co = (*coordinate, 1)
        else:
            spline.bezier_points.add(len(points) - 1)
            for target, coordinate in zip(spline.bezier_points, coordinates):
                target.co = coordinate
                target.handle_left_type = target.handle_right_type = 'AUTO'
        spline.use_cyclic_u = cyclic
        obj = bpy.data.objects.new(name, data)
        bpy.context.collection.objects.link(obj)
        obj.parent = parent
        data.materials.append(mat)
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.convert(target='MESH')
        for polygon in obj.data.polygons:
            polygon.use_smooth = True
        return obj

    def cut_arch(self, obj, axle, height, radius):
        bpy.ops.mesh.primitive_cylinder_add(vertices=80, radius=radius, depth=3,
                                            location=point((0, height, axle)), rotation=(0, math.pi / 2, 0))
        cutter = bpy.context.object
        modifier = obj.modifiers.new('Wheel opening', 'BOOLEAN')
        modifier.operation, modifier.solver, modifier.object = 'DIFFERENCE', 'EXACT', cutter
        self.apply(obj, modifier)
        bpy.data.objects.remove(cutter, do_unlink=True)

    def export(self, manifest, report):
        # Merge only material siblings, never across a moving joint.
        for parent in [self.root] + [obj for obj in self.root.children_recursive if obj.type == 'EMPTY']:
            batches = {}
            for obj in list(parent.children):
                if obj.type == 'MESH' and len(obj.data.materials) == 1:
                    batches.setdefault(obj.data.materials[0].name, []).append(obj)
            for name, objects in batches.items():
                if len(objects) < 2:
                    continue
                bpy.ops.object.select_all(action='DESELECT')
                for obj in objects:
                    obj.select_set(True)
                bpy.context.view_layer.objects.active = objects[0]
                bpy.ops.object.join()
                objects[0].name = parent.name + '_' + name
        (self.output / 'manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')
        bpy.ops.object.select_all(action='DESELECT')
        for obj in [self.root] + list(self.root.children_recursive):
            obj.select_set(True)
        bpy.context.view_layer.objects.active = self.root
        bpy.ops.export_scene.gltf(filepath=str(self.output / 'vehicle.glb'), export_format='GLB',
                                  use_selection=True, export_apply=True, export_yup=True,
                                  export_animations=False, export_extras=True, export_cameras=False,
                                  export_lights=False, export_texcoords=False)
        report.update(vehicleId=self.vehicle_id, blenderVersion=bpy.app.version_string,
                      glbBytes=(self.output / 'vehicle.glb').stat().st_size,
                      meshCount=sum(obj.type == 'MESH' for obj in self.root.children_recursive))
        (self.source / 'build-report.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
        for names in manifest['lights'].values():
            for name in names:
                bpy.data.materials[name].node_tree.nodes['Principled BSDF'].inputs['Emission Strength'].default_value = 0
        self.studio()
        save_source(self.source / 'vehicle.blend')

    def studio(self):
        scene = bpy.context.scene
        scene.render.engine = 'CYCLES'
        scene.cycles.samples, scene.cycles.use_denoising = 24, True
        scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = 1400, 900, 100
        scene.render.image_settings.file_format = 'PNG'
        scene.view_settings.view_transform = 'AgX'
        scene.world.use_nodes = True
        scene.world.node_tree.nodes['Background'].inputs[0].default_value = (.13, .16, .19, 1)
        scene.world.node_tree.nodes['Background'].inputs[1].default_value = .6
        floor = self.material('StudioFloor', (.043, .052, .063), .12, .36)
        self.surface('StudioGround', lambda u, v: ((u - .5) * 200, -.011, (v - .5) * 200),
                     1, 1, floor, self.group('Studio'), normal=(0, 1, 0))
        for name, position, power, size, color in [
                ('KeySoftbox', (3.7, 5.8, 4), 1500, 5, (.82, .89, 1)),
                ('RoofSoftbox', (-3, 5.5, -1.8), 1800, 5.5, (1, .95, .87)),
                ('RimSoftbox', (1.4, 3.3, -5), 1300, 4, (.64, .77, 1)),
                ('FrontFill', (-3.5, 2.2, 5.8), 650, 3, (1, 1, 1))]:
            data = bpy.data.lights.new(name, 'AREA')
            data.energy, data.shape, data.size, data.size_y, data.color = power, 'RECTANGLE', size, size * .45, color
            obj = bpy.data.objects.new(name, data)
            bpy.context.collection.objects.link(obj)
            obj.location = point(position)
            obj.rotation_euler = (Vector(point((0, .72, 0))) - obj.location).to_track_quat('-Z', 'Y').to_euler()
        camera = bpy.data.objects.new('ReviewCamera', bpy.data.cameras.new('ReviewCamera'))
        bpy.context.collection.objects.link(camera)
        camera.data.type, camera.data.ortho_scale = 'ORTHO', 6.4
        camera.location = point((8, 3.5, 8))
        camera.rotation_euler = (Vector(point((0, .72, 0))) - camera.location).to_track_quat('-Z', 'Y').to_euler()
        scene.camera = camera
