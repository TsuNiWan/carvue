"""Bounded triangle clipping for untextured vehicle aperture carriers."""
import bpy
import math
from mathutils import Vector
from vehicle_authoring import point
from convex_support import convex_support


def cut_convex_aperture(name, front, back, target_prefixes, parent=None):
    """Subtract a bounded convex aperture by deterministic triangle clipping.

    This avoids manifold-dependent Boolean behaviour on thin, curved shells.
    Existing triangle winding is retained; optical well returns close the cut.
    """
    reports = []
    support = convex_support([point(p) for p in front + back])
    planes = [(plane['normal'], plane['offset']) for plane in support['planes']]
    low, high = support['min'], support['max']
    max_hull_error = support['maxHullErrorMeters']
    assert len(planes) >= 4, 'The aperture hull must enclose a finite volume'

    def dot(a, b):
        return sum(x * y for x, y in zip(a, b))

    def area_normal(poly):
        a = tuple(poly[1][i] - poly[0][i] for i in range(3))
        b = tuple(poly[2][i] - poly[0][i] for i in range(3))
        return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2],
                a[0] * b[1] - a[1] * b[0])

    def split_polygon(poly, normal, d):
        inside, outside = [], []
        for a, b in zip(poly, poly[1:] + poly[:1]):
            da, db = dot(normal, a) + d, dot(normal, b) + d
            a_inside, b_inside = da <= 0, db <= 0
            (inside if a_inside else outside).append(a)
            if a_inside != b_inside:
                fraction = max(0, min(1, da / (da - db)))
                crossing = tuple(a[i] + fraction * (b[i] - a[i]) for i in range(3))
                inside.append(crossing)
                outside.append(crossing)
        return inside, outside

    bpy.context.view_layer.update()
    for obj in list(bpy.data.objects):
        if obj.type != 'MESH' or not any(obj.name.startswith(prefix) for prefix in target_prefixes):
            continue
        if parent is not None and obj.parent != parent:
            continue
        assert len(obj.data.materials) == 1 and not obj.data.uv_layers, 'This cutter only supports untextured, single-material shells'
        # Preserve sharp edges that encode normals from an earlier aperture cut.
        if not obj.data.has_custom_normals:
            obj.data.set_sharp_from_angle(angle=math.radians(35))
        obj.data.calc_loop_triangles()
        world = obj.matrix_world
        inverse = world.inverted()
        coordinates = [tuple(world @ v.co) for v in obj.data.vertices]
        source_normals = [tuple(item.vector) for item in obj.data.corner_normals]
        vertices, faces, vertex_ids, vertex_keys = [], [], {}, []
        output_normals = []
        preserved, candidates, degenerate = [], 0, 0

        def add_polygon(poly, corner_normals=None):
            if len(poly) < 3:
                return
            ids = []
            for p in poly:
                key = tuple(round(c, 9) for c in p)
                if key not in vertex_ids:
                    vertex_ids[key] = len(vertices)
                    vertices.append(inverse @ Vector(p))
                    vertex_keys.append(key)
                ids.append(vertex_ids[key])
            for i in range(1, len(ids) - 1):
                face = (ids[0], ids[i], ids[i + 1])
                if len(set(face)) == 3:
                    winding = area_normal([poly[0], poly[i], poly[i + 1]])
                    assert dot(winding, triangle_normal) >= -1e-20, 'Clipping must preserve triangle winding'
                    faces.append(face)
                    for index in (0, i, i + 1):
                        if corner_normals is not None:
                            output_normals.append(corner_normals[index])
                            continue
                        p = poly[index]
                        weights = [dot(area_normal([p, triangle_points[1], triangle_points[2]]), triangle_normal) / normal_squared,
                                   dot(area_normal([triangle_points[0], p, triangle_points[2]]), triangle_normal) / normal_squared]
                        weights.append(1 - weights[0] - weights[1])
                        interpolated = tuple(sum(weights[j] * triangle_normals[j][k] for j in range(3)) for k in range(3))
                        magnitude = math.sqrt(dot(interpolated, interpolated))
                        assert magnitude > 1e-12, 'A clipped corner must retain a valid interpolated normal'
                        output_normals.append(tuple(value / magnitude for value in interpolated))

        for triangle in obj.data.loop_triangles:
            poly = [coordinates[i] for i in triangle.vertices]
            triangle_points = poly
            triangle_normals = [source_normals[i] for i in triangle.loops]
            triangle_normal = area_normal(poly)
            normal_squared = dot(triangle_normal, triangle_normal)
            keys = tuple(sorted(tuple(round(c, 9) for c in p) for p in poly))
            if len(set(keys)) < 3 or dot(triangle_normal, triangle_normal) == 0:
                degenerate += 1
                continue
            if any(max(p[i] for p in poly) < low[i] or min(p[i] for p in poly) > high[i] for i in range(3)):
                preserved.append(keys)
                add_polygon(poly, triangle_normals)
                continue
            candidates += 1
            for normal, d in planes:
                poly, outside = split_polygon(poly, normal, d)
                add_polygon(outside)
                if len(poly) < 3:
                    break
        resulting_keys = {tuple(sorted(vertex_keys[i] for i in face)) for face in faces}
        assert all(key in resulting_keys for key in preserved), 'Every triangle outside the aperture bounds must remain'
        reports.append({'aperture': name, 'carrier': obj.name,
                                 'inputTriangles': len(obj.data.loop_triangles), 'candidateTriangles': candidates,
                                 'degenerateInputTriangles': degenerate,
                                 'untouchedTrianglesVerified': len(preserved), 'outputTriangles': len(faces),
                                 'windingVerified': True, 'interpolatedCornerNormals': len(output_normals)})
        mesh = bpy.data.meshes.new(obj.name + 'ApertureMesh')
        mesh.from_pydata(vertices, [], faces)
        for material in obj.data.materials:
            mesh.materials.append(material)
        old_mesh = obj.data
        obj.data = mesh
        for polygon in mesh.polygons:
            polygon.use_smooth = True
        mesh.update()
        assert len(output_normals) == len(mesh.loops), 'Every clipped mesh corner must retain its source normal'
        mesh.normals_split_custom_set(output_normals)
        if old_mesh.users == 0:
            bpy.data.meshes.remove(old_mesh)
    if reports:
        reports[0]['cutterPlanes'] = [{'normal': normal, 'offset': d} for normal, d in planes]
        reports[0]['maximumHullErrorMeters'] = max_hull_error
        reports[0]['hullMethod'] = support['method']
        reports[0]['hullVolumeCubicMeters'] = support['volumeCubicMeters']
    return reports
