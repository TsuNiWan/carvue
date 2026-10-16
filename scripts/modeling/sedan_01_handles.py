"""Exterior door grips placed from the actual door skin and trailing boundary."""
import math
import bpy
import bmesh


def build_handles(context):
    body_x = context['body_x']
    belt = context['belt']
    rear_boundary = context['rear_boundary']
    mesh = context['mesh']
    paint = context['paint']
    seal = context['seal']

    for obj in list(bpy.data.objects):
        if obj.name.startswith(('HandleRecess', 'BodyHandle')):
            bpy.data.objects.remove(obj, do_unlink=True)

    placements = []
    for side, suffix in [(1, 'L'), (-1, 'R')]:
        for front in [True, False]:
            part = ('front' if front else 'rear')+('Left' if side > 0 else 'Right')
            parent = context['joints'][part]
            z = -.082 if front else -1.18
            for _ in range(5):
                y = belt(z)-.130
                fraction = (y-.245)/(belt(z)-.245)
                trailing = -.242 if front else rear_boundary(fraction)
                z = trailing+(.160 if front else .180)
            y = belt(z)-.130
            x = body_x(y, z, side)
            panel = bpy.data.objects[('FrontDoor' if front else 'RearDoor')+suffix]

            # Deform a locally refined, closed shell instead of cutting long
            # boolean n-gons whose interpolated normals produce star artifacts.
            # Both shell surfaces move together, preserving the door thickness.
            bpy.context.view_layer.update()
            to_world = panel.matrix_world.copy()
            to_local = to_world.inverted()
            topology = bmesh.new()
            topology.from_mesh(panel.data)

            def bowl_radius(vertex):
                point = to_world @ vertex.co
                return ((-point.y-z)/.056)**2+((point.z-y-.003)/.048)**2

            edges = [edge for edge in topology.edges if any(bowl_radius(vertex) < 2.0 for vertex in edge.verts)]
            bmesh.ops.subdivide_edges(topology, edges=edges, cuts=2, use_grid_fill=True)
            for vertex in topology.verts:
                radius_squared = bowl_radius(vertex)
                if radius_squared < 1:
                    point = to_world @ vertex.co
                    point.x -= side*.014*(1-radius_squared)**2
                    vertex.co = to_local @ point
            bmesh.ops.recalc_face_normals(topology, faces=list(topology.faces))
            for face in topology.faces:
                face.smooth = True
            topology.to_mesh(panel.data)
            topology.free()

            def grip_point(u, angle):
                position_z = z+.095*(2*u-1)
                arch = .011+.016*math.sin(math.pi*u)**.70
                radius_y = .0105*(.72+.28*math.sin(math.pi*u))
                position_y = y+radius_y*math.sin(angle)
                outer_x = body_x(position_y, position_z, side)
                return (outer_x+side*(arch+.008*math.cos(angle)), position_y, position_z)

            sections, ring = 32, 20
            vertices = [grip_point(i/sections, j*math.tau/ring)
                        for i in range(sections+1) for j in range(ring)]
            faces = [(i*ring+j, i*ring+(j+1)%ring, (i+1)*ring+(j+1)%ring, (i+1)*ring+j)
                     for i in range(sections) for j in range(ring)]
            faces += [tuple(reversed(range(ring))), tuple(sections*ring+j for j in range(ring))]
            mesh('ExteriorGrip'+part, vertices, faces, paint, parent)

            # The fixed end cap and the moving grip meet at a narrow, inset seam.
            context['curve']('HandleEndCapSeam', [grip_point(.14, j*math.tau/28) for j in range(28)],
                             .00065, seal, parent, True)
            if front and side > 0:
                lock = grip_point(.095, 0)
                ring_points = [(lock[0]+side*.0008, lock[1]+.0035*math.sin(j*math.tau/24),
                                lock[2]+.0035*math.cos(j*math.tau/24)) for j in range(24)]
                mesh('DriverDoorKeyCylinder', ring_points, [tuple(range(24))], context['chrome'], parent, False)
                context['curve']('DriverDoorKeySlot', [(lock[0]+side*.0012, lock[1]+dy, lock[2]) for dy in [-.002, .002]],
                                 .0006, seal, parent)
            placements.append({'part': part, 'center': [x, y, z], 'doorTrailingZ': trailing,
                               'offsetFromTrailingEdge': z-trailing, 'gripLength': .190,
                               'bowlDepth': .014, 'sourceStatus': 'Photo calibrated; not factory measurements'})
    return placements
