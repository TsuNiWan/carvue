"""Reproducible vehicle study based on real-vehicle reference observation.

Brand identifiers are omitted; exterior design rights remain unverified.
Coordinates: X left, Y up, Z forward, in meters.
"""
import bpy
import bmesh
import math
import json
import sys
from pathlib import Path
from mathutils import Vector
from mathutils.geometry import tessellate_polygon

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'assets/source/sedan-01'
OUTPUT = ROOT / 'public/models/sedan-01/1.1.0'
QA = SOURCE / 'qa'
for directory in [SOURCE, OUTPUT, QA, ROOT / 'public/previews']:
    directory.mkdir(parents=True, exist_ok=True)

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for datablocks in [bpy.data.meshes, bpy.data.curves, bpy.data.materials]:
    for block in list(datablocks):
        if block.users == 0:
            datablocks.remove(block)

def bp(point):
    return (point[0], -point[2], point[1])

def material(name, color, metal=0.0, rough=0.4, emission=None, alpha=1):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    color = tuple(c/12.92 if c<=.04045 else ((c+.055)/1.055)**2.4 for c in color)
    mat.diffuse_color = (*color, alpha)
    shader = mat.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (*color, alpha)
    shader.inputs['Metallic'].default_value = metal
    shader.inputs['Roughness'].default_value = rough
    shader.inputs['Alpha'].default_value = alpha
    if emission:
        shader.inputs['Emission Color'].default_value = (*emission, 1)
        shader.inputs['Emission Strength'].default_value = 1.0
    if name == 'BodyPaint':
        shader.inputs['Coat Weight'].default_value = 0.9
        shader.inputs['Coat Roughness'].default_value = 0.19
    if name == 'WindowGlass':
        shader.inputs['Specular IOR Level'].default_value = .35
    if alpha < 1:
        mat.surface_render_method = 'DITHERED'
    return mat

paint = material('BodyPaint', (0.33, 0.38, 0.46), .52, .29)
paint_inner = material('InnerPaint', (.13, .17, .22), .35, .36)
glass = material('WindowGlass', (.035, .055, .071), .0, .19, alpha=.82)
black = material('GrilleBlack', (.014, .018, .021), .18, .31)
rubber = material('TireRubber', (.019, .022, .026), .0, .71)
seal = material('WindowSeals', (.009, .012, .016), .02, .54)
pillar_finish = material('PillarSatinBlack', (.016, .019, .023), .0, .43)
pillar_finish.node_tree.nodes['Principled BSDF'].inputs['Specular IOR Level'].default_value=.16
chrome = material('PolishedAlloy', (.62, .66, .71), .91, .19)
alloy = material('SatinAlloy', (.38, .41, .46), .86, .29)
dark_alloy = material('WheelInner', (.064, .070, .08), .6, .39)
cabin = material('CabinBlack', (.028, .032, .038), .02, .64)
leather = material('SeatLeather', (.080, .086, .090), .03, .46)
carpet = material('Carpet', (.034, .037, .042), .0, .95)
ivory = material('Headliner', (.36, .38, .38), .0, .91)
head = material('Headlamp', (.68, .77, .88), .15, .13, (.73, .87, 1.0))
tail = material('Taillamp', (.42, .010, .021), .17, .21, (1, .01, .025))
tail_clear = material('TailClearLens', (.56, .59, .63), .45, .22)
rear_reflector_material = material('RearReflector', (.43, .012, .018), .25, .22)
left_signal = material('SignalLeft', (.47, .19, .012), .15, .24, (1, .32, .006))
right_signal = material('SignalRight', (.47, .19, .012), .15, .24, (1, .32, .006))
screen = material('DisplayGlass', (.008, .025, .039), .22, .15)
plate = material('PlateWhite', (.70, .73, .76), .1, .47)

def group(name, origin=(0, 0, 0), parent=None):
    obj = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(obj)
    obj['origin_carvue'] = list(origin)
    if parent:
        obj.parent = parent
        po = parent['origin_carvue']
        obj.location = bp(tuple(origin[i] - po[i] for i in range(3)))
    else:
        obj.location = bp(origin)
    return obj

root = group('VehicleRoot')
root['vehicleId'] = 'sedan-01'
root['assetVersion'] = '1.1.0'
root['provenance'] = 'Reconstructed vehicle study; exterior design rights unverified'

def mesh(name, vertices, faces, mat, parent=root, smooth=True):
    origin = parent['origin_carvue']
    data = bpy.data.meshes.new(name + 'Mesh')
    data.from_pydata([bp(tuple(p[i]-origin[i] for i in range(3))) for p in vertices], [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.parent = parent
    obj.data.materials.append(mat)
    bm = bmesh.new()
    bm.from_mesh(data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(data)
    bm.free()
    for polygon in data.polygons:
        polygon.use_smooth = smooth
    return obj

def modifier_apply(obj, modifier):
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=modifier.name)

def bevel(obj, width=.008, segments=3):
    mod = obj.modifiers.new('Edge finishing', 'BEVEL')
    mod.width = width
    mod.segments = segments
    modifier_apply(obj, mod)
    return obj

def thickness(obj, amount=.016):
    mod = obj.modifiers.new('Panel thickness', 'SOLIDIFY')
    mod.thickness = amount
    mod.offset = -1
    modifier_apply(obj, mod)
    return obj

def box(name, center, size, mat, parent=root, radius=.012):
    cx, cy, cz = center
    sx, sy, sz = [x/2 for x in size]
    points = [(cx+x*sx, cy+y*sy, cz+z*sz) for x,y,z in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]]
    obj = mesh(name, points, [(0,3,2,1),(4,5,6,7),(0,1,5,4),(3,7,6,2),(0,4,7,3),(1,2,6,5)], mat, parent)
    if radius:
        bevel(obj, min(radius, min(size)/2.1), 3)
    return obj

def curve(name, points, radius, mat, parent=root, cyclic=False, resolution=3):
    origin = parent['origin_carvue']
    data = bpy.data.curves.new(name + 'Curve', 'CURVE')
    data.dimensions = '3D'
    data.resolution_u = resolution
    data.bevel_depth = radius
    data.bevel_resolution = 2
    spline = data.splines.new('POLY' if cyclic else 'BEZIER')
    if cyclic:
        spline.points.add(len(points)-1)
        for point,coordinate in zip(spline.points,points):
            point.co=(*bp(tuple(coordinate[i]-origin[i] for i in range(3))),1)
    else:
        spline.bezier_points.add(len(points)-1)
        for point, coordinate in zip(spline.bezier_points, points):
            point.co = bp(tuple(coordinate[i] - origin[i] for i in range(3)))
            point.handle_left_type = 'AUTO'
            point.handle_right_type = 'AUTO'
    spline.use_cyclic_u = cyclic
    data.use_fill_caps = True
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.parent = parent
    obj.data.materials.append(mat)
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.convert(target='MESH')
    for poly in obj.data.polygons:
        poly.use_smooth = True
    return obj

def interpolate(points, x):
    if x <= points[0][0]: return points[0][1]
    if x >= points[-1][0]: return points[-1][1]
    h=[points[i+1][0]-points[i][0] for i in range(len(points)-1)]
    d=[(points[i+1][1]-points[i][1])/h[i] for i in range(len(h))]
    slopes=[d[0]]
    for i in range(1,len(points)-1):
        if d[i-1]*d[i] <= 0:
            slopes.append(0)
        else:
            w1=2*h[i]+h[i-1]; w2=h[i]+2*h[i-1]
            slopes.append((w1+w2)/(w1/d[i-1]+w2/d[i]))
    slopes.append(d[-1])
    for i in range(len(points)-1):
        if points[i][0] <= x <= points[i+1][0]:
            t = (x-points[i][0])/h[i]
            return (2*t**3-3*t*t+1)*points[i][1]+(t**3-2*t*t+t)*h[i]*slopes[i]+(-2*t**3+3*t*t)*points[i+1][1]+(t**3-t*t)*h[i]*slopes[i+1]

def belt(z):
    return interpolate([(-2.315,1.020),(-2.03,1.051),(-1.45,1.065),(-.3,1.045),(.80,1.015),(1.4,.98),(2.02,.88),(2.315,.805)],z)

def body_width(z):
    return interpolate([(-2.315,.785),(-2.12,.86),(-1.34,.89),(-.2,.873),(.72,.873),(1.39,.89),(2.08,.85),(2.315,.776)],z)

section_levels=[0,.075,.24,.44,.68,.84,.95,1]
door_section=[-.045,-.027,-.076,-.055,-.027,-.008,-.021,-.048]
arch_section=[-.052,-.032,-.024,-.018,-.008,-.012,-.022,-.030]
nose_section=[-.049,-.025,-.013,-.007,-.003,-.002,-.012,-.026]
tail_section=[-.080,-.047,-.025,-.009,-.025,-.009,-.021,-.055]
body_sections=[
    (-2.315,tail_section),(-2.12,tail_section),
    (-1.70,[-.052,-.027,-.015,-.004,0,-.010,-.023,-.034]),
    (-1.335,arch_section),(-.88,[d*.60+a*.40 for d,a in zip(door_section,arch_section)]),(-.30,door_section),(.58,door_section),
    (.90,[-.046,-.023,-.027,-.011,-.004,-.006,-.017,-.028]),
    (1.365,arch_section),(1.90,nose_section),(2.315,nose_section),
]

def body_x(y,z,side):
    t=max(0,min(1,(y-.23)/(belt(z)-.23)))
    offsets=[interpolate([(position,values[index]) for position,values in body_sections],z) for index in range(len(section_levels))]
    if z>=.814:
        offsets[-1]=-body_width(z)*.033
    lift_fraction=max(0,min(1,(-z+.05)/1.35))
    lift=.045*lift_fraction*lift_fraction*(3-2*lift_fraction)
    levels=[value+lift*weight for value,weight in zip(section_levels,[0,0,1,.55,.15,0,0,0])]
    x=body_width(z)+interpolate(list(zip(levels,offsets)),t)
    for axle in [1.365,-1.335]:
        radius=math.hypot(y-.317,z-axle)
        x+=.018*math.exp(-((radius-.389)/.055)**2)
    return side*x

def surface_grid(name, fn, nu, nv, mat, parent=root, solid=.0, normal=None):
    verts = [fn(i/nu,j/nv) for j in range(nv+1) for i in range(nu+1)]
    faces=[]
    for j in range(nv):
        for i in range(nu):
            a=j*(nu+1)+i
            faces.append((a,a+1,a+nu+2,a+nu+1))
    obj=mesh(name,verts,faces,mat,parent)
    if normal:
        direction=Vector(bp(normal))
        average=sum((face.normal for face in obj.data.polygons),Vector((0,0,0)))
        if average.dot(direction)<0:
            bm=bmesh.new()
            bm.from_mesh(obj.data)
            bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
            bm.to_mesh(obj.data)
            bm.free()
    if solid:
        thickness(obj,solid)
        obj.data.set_sharp_from_angle(angle=math.radians(35))
    return obj

def cut_wheel_arches(obj):
    for axle in [1.365,-1.335]:
        bpy.ops.mesh.primitive_cylinder_add(vertices=80, radius=.365, depth=3, location=bp((0,.317,axle)), rotation=(0,math.pi/2,0))
        cutter=bpy.context.object
        modifier=obj.modifiers.new('Wheel opening','BOOLEAN')
        modifier.operation='DIFFERENCE'
        modifier.solver='EXACT'
        modifier.object=cutter
        modifier_apply(obj,modifier)
        bpy.data.objects.remove(cutter,do_unlink=True)

def mapped_patch(name,outline,fn,mat,parent=root):
    polygon=[Vector((u,v,0)) for u,v in outline]
    vertices=[]; faces=[]
    for triangle in tessellate_polygon([polygon]):
        a,b,c=[polygon[index] for index in triangle]
        grid={}
        for i in range(9):
            for j in range(9-i):
                uv=a+(b-a)*(i/8)+(c-a)*(j/8)
                grid[i,j]=len(vertices)
                vertices.append(fn(uv.x,uv.y))
        for i in range(8):
            for j in range(8-i):
                faces.append((grid[i,j],grid[i+1,j],grid[i,j+1]))
                if i+j<7:
                    faces.append((grid[i+1,j],grid[i+1,j+1],grid[i,j+1]))
    obj=mesh(name,vertices,faces,mat,parent)
    topology=bmesh.new()
    topology.from_mesh(obj.data)
    bmesh.ops.remove_doubles(topology,verts=list(topology.verts),dist=.000001)
    bmesh.ops.recalc_face_normals(topology,faces=list(topology.faces))
    topology.to_mesh(obj.data)
    topology.free()
    return obj

front_left=group('door_frontLeft',(.842,1.00,.81),root)
front_right=group('door_frontRight',(-.842,1.00,.81),root)
rear_left=group('door_rearLeft',(.848,1.015,-.255),root)
rear_right=group('door_rearRight',(-.848,1.015,-.255),root)
trunk=group('trunk',(0,1.045,-1.515),root)
joints={'frontLeft':front_left,'frontRight':front_right,'rearLeft':rear_left,'rearRight':rear_right}

def rear_boundary(t): return -.97-.48*t

def door_corner_rise(u):
    return .080*(math.exp(-(u/.055)**2)+math.exp(-((1-u)/.055)**2))

def door_surface(front,u,v,side,lower_strip=False):
    fraction=v
    for _ in range(5):
        back=-.242 if front else rear_boundary(fraction)+.002
        leading=.810 if front else -.249
        z=back+(leading-back)*u
        low=.245+door_corner_rise(u)
        y=.242+door_corner_rise(u)*v if lower_strip else low+(belt(z)-low)*v
        fraction=max(0,min(1,(y-.245)/(belt(z)-.245)))
    return(body_x(y,z,side),y,z)

for side in [-1,1]:
    suffix='L' if side>0 else 'R'
    front_door=front_left if side>0 else front_right
    rear_door=rear_left if side>0 else rear_right
    sections=[
        ('FrontFender',lambda t:.814,lambda t:2.20,root),
        ('FrontDoor',lambda t:-.242,lambda t:.81,front_door),
        ('RearDoor',lambda t:rear_boundary(t)+.002,lambda t:-.249,rear_door),
        ('RearQuarter',lambda t:-2.20+.10*(1-t)**2,lambda t:rear_boundary(t)-.002,root),
    ]
    for name,start,end,parent in sections:
        def fn(u,v,start=start,end=end):
            z=start(v)+(end(v)-start(v))*u
            y=.245+(belt(z)-.245)*v
            return(body_x(y,z,side),y,z)
        if name in ['FrontDoor','RearDoor']:
            fn=lambda u,v,front=name=='FrontDoor':door_surface(front,u,v,side)
        nu,nv=(60,30) if name in ['FrontDoor','RearDoor'] else (36,18)
        obj=surface_grid(name+suffix,fn,nu,nv,paint,parent,.017,normal=(side,0,0))
        cut_wheel_arches(obj)
        obj.data.set_sharp_from_angle(angle=math.radians(35))
        if name in ['FrontDoor','RearDoor']:
            for corner in [0,.87]:
                lower_corner=surface_grid('FixedDoorLowerCorner',lambda u,v,corner=corner,front=name=='FrontDoor':door_surface(front,corner+.13*u,v,side,True),12,6,paint,root,.015,normal=(side,0,0))
                cut_wheel_arches(lower_corner)
    # The wheel-house liner is recessed; the external arch remains painted metal.
    for axle in [1.365,-1.335]:
        def arch_point(a):
            y=.317+.371*math.sin(a)
            z=axle+.371*math.cos(a)
            return(body_x(y,z,side)+side*.002,y,z)
        ranges=[(-.10,math.pi+.10,root)]
        if axle<0:
            low,high=0,math.pi/2
            for _ in range(22):
                angle=(low+high)/2
                _,y,z=arch_point(angle)
                fraction=(y-.245)/(belt(z)-.245)
                if z>rear_boundary(fraction): low=angle
                else: high=angle
            split=(low+high)/2
            ranges=[(-.10,split-.006,rear_door),(split+.006,math.pi+.10,root)]
        for first,last,parent in ranges:
            count=max(12,math.ceil((last-first)*32))
            outline=[arch_point(first+(last-first)*i/count) for i in range(count+1)]
            curve('ArchLip'+suffix,outline,.0025,paint,parent)
        surface_grid('WheelWell'+suffix,lambda u,v,axle=axle:(side*(.68+.18*v),.317+.359*math.sin(math.pi*u),axle+.359*math.cos(math.pi*u)),40,2,black)
    def sill_surface(u,v,side=side):
        z=-.965+1.77*u
        x=body_x(.245,z,side)-side*.040*(1-v)**1.5
        lower=.200+.010*math.sin(math.pi*u)
        return(x,lower+(.242-lower)*v,z)
    surface_grid('Rocker'+suffix,sill_surface,32,5,paint,root,.012,normal=(side,0,0))

# Hood and roof are dense continuous cross-section surfaces, not stacked primitives.
def hood_surface(u,v):
    t=u*2-1
    front_edge=2.27-.40*abs(t)**5
    z=.83+(front_edge-.83)*v
    x=t*(body_width(z)*.97)
    y=belt(z)+.028*(1-t*t)+.002*math.exp(-((abs(t)-.59)/.14)**2)
    return(x,y,z)
hood=surface_grid('SculptedHood',hood_surface,40,40,paint,root,.016,normal=(0,1,0))
for side in [-1,1]:
    edge=[hood_surface(1 if side>0 else 0,i/32) for i in range(33)]
    curve('HoodShutLine',[(x+side*.0003,y+.0008,z) for x,y,z in edge],.0015,seal)

roof_sections=[(-1.04,1.337,.61),(-.96,1.372,.625),(-.80,1.417,.65),(-.40,1.438,.673),(.05,1.427,.668),(.19,1.403,.654),(.27,1.372,.645)]
def roof_surface(u,v):
    station=-1.04+1.31*v
    y=interpolate([(a,b) for a,b,c in roof_sections],station)
    t=u*2-1
    rear_edge=-1.04+.035*(1-t*t)
    front_edge=.27-.040*(1-t*t)
    z=rear_edge+(front_edge-rear_edge)*v
    crown=.047-.028*(v**5+(1-v)**5)
    edge_y=y-crown
    width=.825-(edge_y-1.04)*.43-.004
    return(t*width,y-crown*t*t,z)
surface_grid('RoofSkin',roof_surface,32,36,paint,root,.014,normal=(0,1,0))
surface_grid('RoofLiner',lambda u,v:tuple(a+b for a,b in zip(roof_surface(u,v),(0,-.022,0))),18,18,ivory)

def windscreen(u,v):
    t=u*2-1
    top=roof_surface(u,1)
    bottom=(t*.797,1.022+.015*(1-t*t),.835)
    return(bottom[0]*(1-v)+top[0]*v,bottom[1]*(1-v)+top[1]*v,bottom[2]*(1-v)+top[2]*v-.025*(1-t*t)*math.sin(math.pi*v))
surface_grid('Windscreen',windscreen,32,24,glass,root,normal=(0,1,1))
curve('FrontScreenSeal',[windscreen(i/16,0) for i in range(17)]+[windscreen(1,i/12) for i in range(1,13)]+[windscreen(1-i/16,1) for i in range(1,17)]+[windscreen(0,1-i/12) for i in range(1,12)],.006,seal,cyclic=True)
def backscreen(u,v):
    t=u*2-1
    top=roof_surface(u,0)
    bottom=(t*.753,1.075+.009*(1-t*t),-1.606)
    return(top[0]*(1-v)+bottom[0]*v,top[1]*(1-v)+bottom[1]*v,top[2]*(1-v)+bottom[2]*v)
surface_grid('RearWindscreen',backscreen,32,24,glass,root,normal=(0,1,-1))
curve('RearScreenSeal',[backscreen(i/16,0) for i in range(17)]+[backscreen(1,i/12) for i in range(1,13)]+[backscreen(1-i/16,1) for i in range(1,17)]+[backscreen(0,1-i/12) for i in range(1,12)],.006,seal,cyclic=True)
for i in range(7):
    v=.2+i*.09
    curve('RearDefroster',[backscreen(.06,v),backscreen(.5,v),backscreen(.94,v)],.00065,dark_alloy)

# Windows follow the uninterrupted arched daylight opening.
window_roof=[(-1.43,1.085),(-1.04,1.290),(-.67,1.373),(-.22,1.390),(.23,1.331),(.77,1.047)]
def side_glass_x(y,z,side):
    return side*(.825-(y-1.04)*.43)

def window_roof_edge(z,side):
    y=interpolate(window_roof,z)+.004
    return(side_glass_x(y,z,side)+side*.004,y,z)
def window_panel(name,z0,z1,side,parent):
    def pane(u,v):
        z=z0+(z1-z0)*u
        if name.startswith('QuarterGlass'):
            # The tip is rounded in the shared pane boundary, not masked by trim.
            z+=.018*(1-u)**6*abs(2*v-1)**3
        lower=belt(z)+.008
        upper=interpolate(window_roof,z)-.010
        y=lower+(upper-lower)*v
        return(side_glass_x(y,z,side),y,z)
    surface_grid(name,pane,24,9,glass,parent,normal=(side,0,0))
    boundary=[pane(i/16,0) for i in range(17)]+[pane(1,i/6) for i in range(1,7)]+[pane(1-i/20,1) for i in range(1,21)]+[pane(0,1-i/6) for i in range(1,6)]
    curve(name+'Rubber',boundary,.0035,seal,parent,True)
    curve(name+'ChromeBelt',[pane(0,0),pane(.5,0),pane(1,0)],.0032,chrome,parent)
    def window_frame(u,v):
        x,y,z=pane(u,1)
        return(x+side*.003,y-.015*(1-v),z)
    surface_grid(name+'UpperFrame',window_frame,28,2,seal,parent,.007,normal=(side,0,0))
    def belt_shoulder(u,v):
        inner=pane(u,0)
        outer=(body_x(belt(inner[2]),inner[2],side),belt(inner[2]),inner[2])
        return tuple(inner[i]*(1-v)+outer[i]*v for i in range(3))
    surface_grid(name+'BeltShoulder',belt_shoulder,28,5,paint,parent,.009,normal=(0,1,0))

for side in [-1,1]:
    suffix='L' if side>0 else 'R'
    front_door=front_left if side>0 else front_right
    rear_door=rear_left if side>0 else rear_right
    window_panel('FrontGlass'+suffix,-.197,.745,side,front_door)
    window_panel('RearGlass'+suffix,-1.062,-.28,side,rear_door)
    window_panel('QuarterGlass'+suffix,-1.404,-1.085,side,rear_door)
    def a_pillar(u,v,side=side):
        inner=windscreen(1 if side>0 else 0,v)
        z=.77+(.27-.77)*v
        outer=window_roof_edge(z,side)
        return tuple(inner[i]*(1-u)+outer[i]*u for i in range(3))
    surface_grid('APillar',a_pillar,10,28,paint,root,.014)
    def roof_rail(u,v,side=side):
        top=roof_surface(1 if side>0 else 0,v)
        top_x,top_y,z=abs(top[0]),top[1],top[2]
        bottom=window_roof_edge(z,side)
        bottom_x,bottom_y=abs(bottom[0]),bottom[1]
        return(side*(top_x*(1-u)+bottom_x*u),top_y*(1-u)+bottom_y*u,z)
    surface_grid('RoofSideRail'+suffix,roof_rail,24,48,paint,root,.012)
    # Curved painted C pillar bridges the rear glass and backlight.
    def c_pillar(u,v,side=side):
        inner=backscreen(1 if side>0 else 0,v)
        z=-1.04-.397*v
        outer=window_roof_edge(z,side)
        return tuple(inner[i]*(1-u)+outer[i]*u+(0,.006*math.sin(math.pi*u)*math.sin(math.pi*v),0)[i] for i in range(3))
    def c_pillar_base(u,v,side=side):
        a=Vector(c_pillar(u,1))
        tangent=(a-Vector(c_pillar(u,.99)))/.01
        z=a.z-.026
        d=Vector((body_x(belt(z),z,side),belt(z),z))
        b=a+tangent*.030
        b.y=max(b.y,d.y+.003)
        c=d+Vector((-side*.020,.008,.012))
        point=a*(1-v)**3+b*(3*(1-v)**2*v)+c*(3*(1-v)*v*v)+d*v**3
        return tuple(point)
    surface_grid('CPillar'+suffix,lambda u,v:c_pillar(u,v/.84) if v<=.84 else c_pillar_base(u,(v-.84)/.16),24,50,paint,root,.015)
    def b_pillar_outer(u,v,side=side):
        z=-.272+.074*u
        lower=belt(z)+.006
        y=lower+(interpolate(window_roof,z)-.007-lower)*v
        return(side_glass_x(y,z,side)+side*(.004+.0015*math.sin(math.pi*u)),y,z)
    surface_grid('BPillar'+suffix,b_pillar_outer,8,24,pillar_finish,root,.008,normal=(side,0,0))
    # Door apertures, visible inner skins, handles, and armrests move with each door.
    for is_front,parent in [(True,front_door),(False,rear_door)]:
        zfront=.78 if is_front else -.28
        zback=-.21 if is_front else -1.00
        zcenter=(zfront+zback)/2
        def door_inner(u,v,side=side,is_front=is_front):
            _,y,z=door_surface(is_front,.025+.95*u,.015+.95*v,side)
            y+=.018*(1-v)
            return(body_x(y,z,side)-side*.056,y,z)
        inner_panel=surface_grid('DoorInnerPanel',door_inner,24,15,cabin,parent,.022)
        cut_wheel_arches(inner_panel)
        edge=[door_inner(i/16,0) for i in range(17)]+[door_inner(1,i/12) for i in range(1,13)]+[door_inner(1-i/16,1) for i in range(1,17)]+[door_inner(0,1-i/12) for i in range(1,12)]
        inner_edge=curve('InnerDoorEdge',edge,.009,paint_inner,parent,True)
        cut_wheel_arches(inner_edge)
        box('DoorPaddedInsert',(side*.780,.786,zcenter),(.030,.125,(zfront-zback)*.85),leather,parent,.022)
        box('Armrest',(side*.727,.64,zcenter),(.14,.075,(zfront-zback)*.60),cabin,parent,.026)
        box('InnerDoorHandle',(side*.717,.821,zcenter+.14),(.016,.025,.115),chrome,parent,.009)
        curve('DoorSillSeal',[(body_x(.276,z,side)-side*.019,.276,z) for z in [zfront,zcenter,zback]],.005,seal)
        handle_z=zback+.19
        y=belt(handle_z)-.074
        x=body_x(y,handle_z,side)
        box('HandleRecess',(x+side*.005,y,handle_z),(.024,.048,.17),dark_alloy,parent,.02)
        curve('BodyHandle',[(x+side*.018,y,handle_z-.069),(x+side*.037,y+.006,handle_z),(x+side*.025,y+.002,handle_z+.068)],.012,paint,parent)
    # The mirror belongs to the front door, including its amber repeater.
    curve('MirrorStem',[(side*.81,1.039,.664),(side*.911,1.024,.615)],.019,seal,front_door)
    box('MirrorLower',(side*.937,1.065,.607),(.201,.058,.175),black,front_door,.034)
    box('MirrorCap',(side*.937,1.098,.612),(.195,.075,.170),paint,front_door,.036)
    box('MirrorGlass',(side*.939,1.080,.526),(.162,.060,.007),chrome,front_door,.014)
    curve('MirrorRepeater',[(side*1.024,1.067,.619),(side*.963,1.071,.681),(side*.881,1.068,.682)],.005,left_signal if side>0 else right_signal,front_door)

sys.path.insert(0,str(Path(__file__).resolve().parent))
from sedan_01_front import build_front
front_features=build_front(globals())
from sedan_01_handles import build_handles
handle_placements=build_handles(globals())

# Separate trunk deck and fascia. The opening has a floor, walls, gutter and seals.
def trunk_deck(u,v):
    t=u*2-1
    crown=.009+.015*v*v*(3-2*v)
    roll=.040*(v**4-v**20)
    return(t*(.750-.070*v),1.073-.065*v+.026*v**4+roll+crown*(1-t*t),-1.609-.688*v+.027*t*t*v)
surface_grid('TrunkDeck',trunk_deck,36,24,paint,trunk,.017,normal=(0,1,0))
for side in [-1,1]:
    def quarter_crown(u,v,side=side):
        edge=trunk_deck(1 if side>0 else 0,v)
        z=edge[2]
        inner_x=abs(edge[0])+.0035
        outer_x=abs(body_x(belt(z),z,1))
        a=Vector((inner_x,edge[1],z))
        d=Vector((outer_x,belt(z),z))
        b=a+Vector(((outer_x-inner_x)*.38,-.0015,0))
        c=d+Vector((-.015,.018,0))
        point=a*(1-u)**3+b*(3*(1-u)**2*u)+c*(3*(1-u)*u*u)+d*u**3
        return(side*point.x,point.y,point.z)
    surface_grid('RearQuarterCrown',quarter_crown,10,32,paint,root,.016,normal=(0,1,0))
def trunk_width(v):
    return interpolate([(0,.585),(.065,.621),(.15,.641),(1,.680)],v)
def trunk_rear(u,v):
    t=u*2-1
    top=trunk_deck(u,1)
    bottom=(t*.585,.645,-2.265+.020*t*t)
    # The plate face retreats behind the lamp shoulder; the lower shut edge
    # turns outward again to meet the bumper crown.
    depth=.084*math.exp(-(abs(t)/.90)**6)
    recess=interpolate([(0,0),(.13,.31),(.34,.94),(.56,1),(.76,.70),(.84,.43),(1,0)],v)
    z=bottom[2]*(1-v)+top[2]*v+depth*recess
    if v>.84:
        span=.16
        s=(v-.84)/span
        start_z=bottom[2]*.16+top[2]*.84+depth*.43
        recess_slope=(interpolate([(0,0),(.13,.31),(.34,.94),(.56,1),(.76,.70),(.84,.43),(1,0)],.84)-interpolate([(0,0),(.13,.31),(.34,.94),(.56,1),(.76,.70),(.84,.43),(1,0)],.839))/.001
        start_slope=top[2]-bottom[2]+depth*recess_slope
        previous=trunk_deck(u,.999)
        top_slope=(top[1]-bottom[1])*(top[2]-previous[2])/(top[1]-previous[1])
        z=(2*s**3-3*s*s+1)*start_z+(s**3-2*s*s+s)*span*start_slope+(-2*s**3+3*s*s)*top[2]+(s**3-s*s)*span*top_slope
    return(t*trunk_width(v),bottom[1]*(1-v)+top[1]*v,z)
surface_grid('TrunkRearPanel',trunk_rear,40,24,paint,trunk,.018,normal=(0,0,-1))

def trunk_fascia(x,y,offset=0):
    v=max(0,min(1,(y-.645)/.383))
    for _ in range(3):
        t=max(-1,min(1,x/trunk_width(v)))
        top=trunk_deck((t+1)/2,1)
        v=max(0,min(1,(y-.645)/(top[1]-.645)))
    point=trunk_rear((t+1)/2,v)
    return(x,y,point[2]-offset)
def rear_side_boundary(y):
    t=max(0,min(1,(y-.245)/(belt(-2.20)-.245)))
    for _ in range(3):
        z=-2.20+.10*(1-t)**2
        t=max(0,min(1,(y-.245)/(belt(z)-.245)))
    return abs(body_x(y,z,1)),z

def rear_round_bridge(inner,outer,u,side,inner_slope):
    a=Vector(inner); d=Vector(outer)
    span=max(.01,d.x-a.x)
    side_slope=(abs(body_x(d.y,d.z+.008,1))-d.x)/.008
    turn=max(.020,min(.065,(d.z-a.z)*.85))
    b=a+Vector((span*.42,0,inner_slope*span*.42))
    c=d-Vector((side_slope*turn,0,turn))
    point=a*(1-u)**3+b*(3*(1-u)**2*u)+c*(3*(1-u)*u*u)+d*u**3
    return(side*point.x,point.y,point.z)

def rear_shoulder(u,v,side):
    inner=trunk_rear(1,v)
    y=inner[1]
    outer_x,outer_z=rear_side_boundary(y)
    outer=(outer_x,y,outer_z)
    adjacent=trunk_rear(.99,v)
    slope=(inner[2]-adjacent[2])/(inner[0]-adjacent[0])
    return rear_round_bridge((inner[0]+.004,y,inner[2]),outer,u,side,slope)

def rear_bumper_base_z(x,y):
    v=max(0,min(1,(y-.245)/.400))
    extent,rear_edge=rear_side_boundary(y)
    t=min(1,abs(x)/extent)
    # Broad bumper shoulder and lower return, not one extruded vertical panel.
    center=interpolate([(.245,-2.184),(.320,-2.253),(.440,-2.292),(.520,-2.301),(.600,-2.285),(.645,-2.265)],y)
    base=center+(rear_edge-center)*t*t
    top_extent,top_edge=rear_side_boundary(.645)
    top_x=t*top_extent
    if top_x<=.585:
        top_z=trunk_rear((top_x/.585+1)/2,0)[2]
    else:
        fraction=(top_x-.589)/(top_extent-.589)
        top_z=rear_shoulder(max(0,min(1,fraction)),0,1)[2]
    base_top=-2.265+(top_edge+2.265)*t*t
    return base+(top_z-base_top)*v**3

def bumper_platform(x,y):
    extent,_=rear_side_boundary(y)
    def ease(value):
        value=max(0,min(1,value))
        return value*value*(3-2*value)
    across=ease((abs(x)-.200)/.380)
    edge=ease((extent-abs(x))/.080)
    # A broad, asymmetric recessed platform blends inward and returns to the
    # painted lower lip; a Gaussian would instead form a small round dimple.
    bottom=.303+.045*(1-across)
    top=.642
    lower_return=ease((y-bottom)/.055)
    upper_return=ease((top-y)/.100)
    return .028*across*edge*lower_return*upper_return

def rear_bumper_z(x,y):
    return rear_bumper_base_z(x,y)+bumper_platform(x,y)

def rear_lower_corner(u,y,side):
    outer_x,outer_z=rear_side_boundary(y)
    inner=(.585,y,rear_bumper_base_z(.585,y))
    slope=(rear_bumper_base_z(.585,y)-rear_bumper_base_z(.579,y))/.006
    p=rear_round_bridge(inner,(outer_x,y,outer_z),u,side,slope)
    return(p[0],p[1],p[2]+bumper_platform(p[0],y))

def rear_lower_face(x,y,offset=0):
    if abs(x)<=.585: return(x,y,rear_bumper_z(x,y)-offset)
    side=1 if x>0 else -1
    low,high=0,1
    for _ in range(18):
        middle=(low+high)/2
        if abs(rear_lower_corner(middle,y,side)[0])<abs(x): low=middle
        else: high=middle
    p=rear_lower_corner((low+high)/2,y,side)
    return(x,y,p[2]-offset)

surface_grid('RearBumperCenter',lambda u,v:((u*2-1)*.585,.245+.397*v,rear_bumper_z((u*2-1)*.585,.245+.397*v)),40,30,paint,root,.02,normal=(0,0,-1))
for side in [-1,1]:
    def fixed_rear_corner(u,v,side=side):
        y=.245+.789*v
        if y>=.645:
            return rear_shoulder(u,min(1,(y-.645)/.389),side)
        return rear_lower_corner(u,y,side)
    rear_corner=surface_grid('RearCorner',fixed_rear_corner,20,50,paint,root,.018,normal=(0,0,-1))
    from sedan_01_lamps import build_rear_lamp
    build_rear_lamp(side,rear_corner,globals())
    def rear_reflector(u,v,side=side):
        x=side*(.558+.217*u)
        y=.290+.038*v+.010*(1-u)**2
        return rear_lower_face(x,y,.005)
    surface_grid('RearReflector',rear_reflector,20,5,rear_reflector_material,root,normal=(0,0,-1))
def lower_valance(u,v):
    t=u*2-1
    x=t*.77
    y=.255+.029*v+.026*abs(t)**6
    return rear_lower_face(x,y,.004)
surface_grid('RearLowerValance',lower_valance,50,6,black,root,normal=(0,0,-1))
chrome_points=[]
for i in range(61):
    x=-.645+1.29*i/60
    y=.958 if abs(x)<.335 else .959-.081*(abs(x)-.335)/.316
    chrome_points.append(trunk_fascia(x,y,.006))
curve('TrunkChrome',chrome_points,.0028,chrome,trunk)
rear_plate_z=trunk_fascia(0,.787,.006)[2]
box('TrunkPlateRecess',(0,.784,rear_plate_z),(.44,.21,.009),black,trunk,.012)
box('RearPlate',(0,.787,rear_plate_z-.008),(.405,.17,.008),plate,trunk,.006)
box('CargoFloor',(0,.470,-1.700),(1.24,.033,.83),carpet,radius=.025)
box('CargoBackWall',(0,.708,-1.276),(1.26,.47,.025),carpet,radius=.008)
box('CargoRearSill',(0,.56,-2.133),(1.16,.18,.028),carpet,radius=.008)
for side in [-1,1]:
    box('CargoSideWall',(side*.621,.692,-1.704),(.034,.44,.842),carpet,radius=.015)
    box('CargoWheelBulge',(side*.560,.562,-1.42),(.21,.23,.32),carpet,radius=.085)
    rear_seal=[trunk_rear(1 if side>0 else 0,i/16) for i in range(17)]
    deck_seal=[trunk_deck(1 if side>0 else 0,1-i/20) for i in range(1,21)]
    curve('TrunkSeal',[(x-side*.016,y-.016,z+.009) for x,y,z in rear_seal+deck_seal],.006,seal)
    box('TrunkHingeBearing',(side*.50,1.025,-1.515),(.044,.040,.079),paint_inner,radius=.005)
    curve('TrunkHinge',[(side*.50,1.045,-1.515),(side*.50,.990,-1.590),(side*.50,1.043,-1.750)],.010,chrome,trunk)
for name,fn,offset,normal in [('TrunkInnerLiner',trunk_deck,(0,-1,0),(0,-1,0)),('TrunkFasciaLiner',trunk_rear,(0,0,1),(0,0,1))]:
    def liner(u,v,fn=fn,offset=offset):
        corner=.040*abs(2*v-1)**14
        point=fn(.055+corner+(.890-2*corner)*u,.055+.89*v)
        depth=.026+.008*math.sin(math.pi*u)*math.sin(math.pi*v)
        return tuple(point[i]+offset[i]*depth for i in range(3))
    surface_grid(name,liner,32,24,carpet,trunk,.008,normal=normal)
    perimeter=[(i/24,0) for i in range(24)]+[(1,i/16) for i in range(16)]+[(1-i/24,1) for i in range(24)]+[(0,1-i/16) for i in range(16)]
    outer=[tuple(value+offset[i]*.016 for i,value in enumerate(fn(.018+.964*u,.018+.964*v))) for u,v in perimeter]
    inner=[liner(u,v) for u,v in perimeter]
    n=len(perimeter)
    frame=mesh(name+'PaintedFrame',outer+inner,[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)],paint_inner,trunk)
    thickness(frame,.006)

# Interior geometry is detailed for views through open doors, not a cockpit mode.
for side in [-1,1]:
    front_lower=[(point[1]+.015,point[2]) for point in [door_surface(True,i/32,0,side) for i in range(33)]]
    rear_lower=[(point[1]+.015,point[2]) for point in [door_surface(False,i/32,0,side) for i in range(33)]]
    profiles=[
        [(1.018,.812),(1.178,.541),(1.355,.248),(1.385,-.215),(1.043,-.242)]+front_lower+[(.784,.812)],
        [(1.388,-.259),(1.378,-.61),(1.295,-1.04),(1.064,-1.421),(.765,-1.242)]+rear_lower,
    ]
    for index,profile in enumerate(profiles):
        sampled=[]
        for p0,p1 in zip(profile,profile[1:]+profile[:1]):
            steps=max(2,math.ceil(math.hypot(p1[0]-p0[0],p1[1]-p0[1])/.024))
            sampled.extend([(p0[0]+(p1[0]-p0[0])*j/steps,p0[1]+(p1[1]-p0[1])*j/steps) for j in range(steps)])
        profile=sampled
        cy=sum(p[0] for p in profile)/len(profile)
        cz=sum(p[1] for p in profile)/len(profile)
        outer=[]; inner=[]; deep=[]
        for y,z in profile:
            xx=abs(side_glass_x(y,z,1))-.008 if y>belt(z) else abs(body_x(y,z,1))-.020
            yy=cy+(y-cy)*.957
            zz=cz+(z-cz)*.957
            inner_x=abs(side_glass_x(yy,zz,1))-.020 if yy>belt(zz) else abs(body_x(yy,zz,1))-.032
            outer.append((side*xx,y,z))
            inner.append((side*inner_x,yy,zz))
            deep.append((side*(inner_x-.060),yy,zz))
        n=len(profile)
        faces=[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
        for name,vertices in [('DoorApertureFlange',outer+inner),('DoorJambDepth',inner+deep)]:
            frame=mesh(name,vertices,faces,paint_inner)
            thickness(frame,.003)
            cut_wheel_arches(frame)
        weather_seal=curve('DoorWeatherSeal',[(x-side*.011,y,z) for x,y,z in inner],.0065,seal,cyclic=True)
        cut_wheel_arches(weather_seal)
    box('BodySillStructure',(side*.773,.294,-.085),(.115,.075,1.77),paint_inner,radius=.016)
    box('SillScuffPlate',(side*.76,.337,-.04),(.091,.014,1.48),dark_alloy,radius=.005)
    def b_post(u,v,side=side):
        y=.31+1.061*v
        z=-.296+.089*u
        x=body_x(y,z,side)-side*.04 if y<1.04 else side_glass_x(y,z,side)-side*.024
        return(x,y,z)
    surface_grid('BPostStructure',b_post,5,24,cabin,root,.045,normal=(side,0,0))
    box('DoorLatch',(side*.802,.737,-.249),(.042,.073,.017),chrome,radius=.003)
box('InteriorFloor',(0,.281,-.265),(1.56,.06,2.25),carpet,radius=.025)
box('CenterTunnel',(0,.354,-.15),(.29,.16,1.78),cabin,radius=.055)
box('RearParcelShelf',(0,1.024,-1.338),(1.41,.041,.36),cabin,radius=.035)
for side in [-1,1]:
    x=side*.385
    box('FrontSeatBase',(x,.493,.058),(.50,.20,.58),leather,radius=.087)
    box('SeatCenterCushion',(x,.608,.063),(.34,.035,.42),cabin,radius=.032)
    seat_back=box('FrontSeatBack',(x,.86,-.223),(.47,.64,.145),leather,radius=.065)
    # A gentle rearward rake is baked in mesh coordinates for predictable export.
    for vertex in seat_back.data.vertices:
        height=vertex.co.z
        vertex.co.y += max(0,height-.55)*.15
    box('SeatBackInsert',(x,.88,-.149),(.31,.45,.031),cabin,radius=.04)
    box('Headrest',(x,1.236,-.266),(.267,.202,.121),leather,radius=.041)
    for xx in [x-.084,x+.084]:
        curve('HeadrestPost',[(xx,1.12,-.257),(xx,1.168,-.257)],.006,chrome)
    curve('SeatStitch',[(x-side*.197,.64,.25),(x-side*.205,.64,-.16),(x-side*.18,1.08,-.244)],.0012,alloy)
    curve('SeatBelt',[(side_glass_x(1.304,-.263,side)-side*.055,1.304,-.263),(side*.682,.542,-.26),(side*.650,.357,-.28)],.010,seal)
box('RearBench',(0,.514,-.893),(1.35,.21,.51),leather,radius=.076)
box('RearSeatBack',(0,.839,-1.098),(1.36,.57,.145),leather,radius=.075)
for x in [-.45,0,.45]:
    box('RearHeadrest',(x,1.178,-1.129),(.24,.17,.10),leather,radius=.035)
for x in [-.225,.225]:
    curve('RearSeatStitch',[(x,.632,-.73),(x,.632,-.994),(x,1.033,-1.018)],.0015,alloy)
box('Dashboard',(0,.957,.663),(1.49,.223,.377),cabin,radius=.07)
box('DashboardLower',(0,.777,.62),(1.27,.22,.26),cabin,radius=.06)
curve('DashboardTrim',[(-.70,.931,.462),(-.38,.923,.437),(0,.912,.446),(.38,.923,.437),(.70,.931,.462)],.006,chrome)
for x in [-.59,.59]:
    box('AirVent',(x,.949,.451),(.18,.071,.018),black,radius=.012)
    for yy in [.929,.951,.972]:
        curve('VentSlat',[(x-.077,yy,.439),(x+.077,yy,.439)],.0018,alloy)
box('CenterDisplayFrame',(0,1.086,.468),(.30,.202,.026),black,radius=.014)
box('CenterDisplay',(0,1.089,.452),(.275,.173,.004),screen,radius=.003)
box('ClimatePanel',(0,.883,.418),(.30,.073,.032),black,radius=.01)
box('Console',(0,.576,.184),(.244,.249,.619),cabin,radius=.045)
box('ConsoleArmrest',(0,.623,-.196),(.23,.085,.22),leather,radius=.033)
curve('GearLever',[(0,.633,.16),(0,.726,.18)],.014,chrome)
box('GearKnob',(0,.741,.18),(.062,.051,.085),leather,radius=.022)
box('InstrumentHood',(.385,1.048,.474),(.334,.15,.18),cabin,radius=.05)
box('InstrumentScreen',(.385,1.057,.376),(.281,.098,.01),screen,radius=.013)
steering_center=(.385,.953,.260)
wheel_ring=[(steering_center[0]+.169*math.cos(i*math.tau/64),steering_center[1]+.169*math.sin(i*math.tau/64),steering_center[2]+.043*math.sin(i*math.tau/64)) for i in range(64)]
curve('SteeringRim',wheel_ring,.018,leather,cyclic=True)
box('SteeringHub',steering_center,(.135,.105,.061),cabin,radius=.025)
for x,y,z in [(.235,.957,.261),(.535,.957,.261),(.385,.802,.222)]:
    curve('SteeringSpoke',[steering_center,(x,y,z)],.016,chrome)
for x in [-.40,.40]:
    box('FrontFloorMat',(x,.320,.07),(.44,.011,.53),cabin,radius=.025)
    box('RearFloorMat',(x,.320,-.54),(.42,.011,.38),cabin,radius=.018)

# Wheels use a smooth revolved tire cross-section and ten individually sculpted spokes.
def lathe_x(name,center,profile,mat,parent,segments=64):
    cx,cy,cz=center
    verts=[]
    for axial,radius in profile:
        for i in range(segments):
            a=i*math.tau/segments
            verts.append((cx+axial,cy+radius*math.cos(a),cz+radius*math.sin(a)))
    faces=[]
    for j in range(len(profile)-1):
        for i in range(segments):
            a=j*segments+i; b=j*segments+(i+1)%segments
            faces.append((a,b,b+segments,a+segments))
    return mesh(name,verts,faces,mat,parent)

for side in [-1,1]:
    for front_axle,zz in [(True,1.365),(False,-1.335)]:
        pivot=group(('wheel_front' if front_axle else 'wheel_rear')+('Left' if side>0 else 'Right'),(side*.771,.317,zz),root)
        center=(side*.771,.317,zz)
        tire_profile=[(-.105,.218),(-.108,.251),(-.103,.286),(-.075,.312),(-.055,.317),(.055,.317),(.075,.312),(.103,.286),(.108,.251),(.105,.218)]
        lathe_x('Tire',center,tire_profile,rubber,pivot,72)
        lathe_x('AlloyBarrel',center,[(-.105,.211),(-.105,.221),(.111,.221),(.112,.199),(.105,.196)],alloy,pivot)
        lathe_x('BrakeDisc',center,[(side*.052,.026),(side*.052,.161),(side*.064,.161),(side*.064,.026)],dark_alloy,pivot)
        for radius in [.260,.283,.296]:
            ring=[(center[0]+side*.106,center[1]+radius*math.cos(i*math.tau/72),center[2]+radius*math.sin(i*math.tau/72)) for i in range(72)]
            curve('TireSidewallRib',ring,.0013,black,pivot,True)
        for j in range(48):
            a=j*math.tau/48
            points=[]
            for ax,angle in [(-.070,a),(-.040,a+.021),(.040,a+.045),(.070,a+.068)]:
                points.append((center[0]+ax,center[1]+.3178*math.cos(angle),center[2]+.3178*math.sin(angle)))
            curve('TreadGroove',points,.0017,black,pivot,resolution=1)
        from sedan_01_wheels import build_alloy
        build_alloy(center,side,pivot,globals())

# Fuel flap follows the quarter panel surface.
fuel_outline=[]
for corner_z,corner_y,start in [(-1.616,.993,0),(-1.820,.993,90),(-1.820,.873,180),(-1.616,.873,270)]:
    for i in range(7):
        angle=math.radians(start+90*i/6)
        z=corner_z+.014*math.cos(angle)
        y=corner_y+.014*math.sin(angle)
        fuel_outline.append((body_x(y,z,1)+.0012,y,z))
curve('FuelFlap',fuel_outline,.0014,seal,cyclic=True)
def add_text(name,text,location,size,mat,back=False,parent=root):
    data=bpy.data.curves.new(name,'FONT')
    data.body=text
    data.align_x='CENTER'
    data.align_y='CENTER'
    data.size=size
    data.extrude=.0003
    obj=bpy.data.objects.new(name,data)
    bpy.context.collection.objects.link(obj)
    origin=parent['origin_carvue']
    obj.location=bp(tuple(location[i]-origin[i] for i in range(3)))
    obj.rotation_euler=(math.pi/2,0,math.pi if back else 0)
    obj.parent=parent
    data.materials.append(mat)
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True); bpy.context.view_layer.objects.active=obj
    bpy.ops.object.convert(target='MESH')
add_text('FrontPlateText','CARVUE',front_features['plate_text'],.066,black)
add_text('RearPlateText','CARVUE',(0,.794,rear_plate_z-.014),.061,black,True,trunk)

# Consolidate only siblings with the same material. Joints remain explicit nodes.
for parent in [root,front_left,front_right,rear_left,rear_right,trunk]+[o for o in bpy.data.objects if o.type=='EMPTY' and o.name.startswith('wheel_')]:
    batches={}
    for obj in list(parent.children):
        if obj.type=='MESH' and len(obj.data.materials)==1:
            batches.setdefault(obj.data.materials[0].name,[]).append(obj)
    for mat_name,objects in batches.items():
        if len(objects)<2: continue
        bpy.ops.object.select_all(action='DESELECT')
        for obj in objects: obj.select_set(True)
        bpy.context.view_layer.objects.active=objects[0]
        bpy.ops.object.join()
        objects[0].name=parent.name+'_'+mat_name
        if parent==root and mat_name=='BodyPaint':
            topology=bmesh.new()
            topology.from_mesh(objects[0].data)
            bmesh.ops.remove_doubles(topology,verts=list(topology.verts),dist=.00001)
            bmesh.ops.recalc_face_normals(topology,faces=list(topology.faces))
            topology.to_mesh(objects[0].data)
            topology.free()

from sedan_01_lamps import restore_panel_normals
restore_panel_normals(globals())

manifest={
 'schemaVersion':1,'vehicleId':'sedan-01','assetVersion':'1.1.0','units':'meter','forward':'+Z',
 'framing':{'target':[0,.6314,0],'direction':[1.2,.46,1.65],'distance':7.5006},
 'joints':{k:{'node':v.name,'axis':[0,1,0],'openAngle':(-1 if k.endswith('Left') else 1)*math.radians(67)} for k,v in joints.items()},
 'frontWheels':['wheel_frontLeft','wheel_frontRight'],
 'lights':{'head':['Headlamp','HeadlampProjector'],'tail':['Taillamp'],'left':['SignalLeft'],'right':['SignalRight']},
 'headlights':[{'position':[x,.865,2.27],'target':[x*1.7,.05,8.27]} for x in [.67,-.67]],
 'hotspots':[
   *[{'id':key,'node':node.name,'position':[.04 if key.endswith('Left') else -.04,-.12,-.64 if key.startswith('front') else -.48],'label':{'frontLeft':'左前門','frontRight':'右前門','rearLeft':'左後門','rearRight':'右後門'}[key]} for key,node in joints.items()],
   {'id':'trunk','node':'trunk','position':[0,-.12,-.79],'label':'行李廂'},
   {'id':'headlights','node':'VehicleRoot','position':[.72,.86,2.30],'label':'車輛照明'}
 ]
}
manifest['joints']['trunk']={'node':'trunk','axis':[1,0,0],'openAngle':math.radians(70)}
(OUTPUT/'manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding='utf-8')

# Export only the vehicle; studio lights and ground are never part of the GLB.
bpy.ops.object.select_all(action='DESELECT')
root.select_set(True)
for obj in root.children_recursive: obj.select_set(True)
bpy.context.view_layer.objects.active=root
bpy.ops.export_scene.gltf(filepath=str(OUTPUT/'vehicle.glb'),export_format='GLB',use_selection=True,export_apply=True,export_yup=True,export_animations=False,export_extras=True,export_cameras=False,export_lights=False,export_texcoords=False)
for lamp_material in [head,bpy.data.materials['HeadlampProjector'],tail,left_signal,right_signal]:
    lamp_material.node_tree.nodes['Principled BSDF'].inputs['Emission Strength'].default_value=0
triangles=sum(len(obj.data.polygons) for obj in root.children_recursive if obj.type=='MESH')
(SOURCE/'build-report.json').write_text(json.dumps({'vehicleId':'sedan-01','blenderVersion':bpy.app.version_string,'polygonCount':triangles,'meshCount':sum(o.type=='MESH' for o in root.children_recursive),'glbBytes':(OUTPUT/'vehicle.glb').stat().st_size,'handlePlacements':handle_placements,'frontGeometry':front_features,'sectionLevels':section_levels,'bodySections':body_sections,'referenceStatus':'Official and Taiwan owner photographs inspected; product shape review pending'},indent=2),encoding='utf-8')

scene=bpy.context.scene
scene.render.engine='CYCLES'
scene.cycles.samples=24
scene.cycles.use_denoising=True
scene.render.resolution_x=1400
scene.render.resolution_y=900
scene.render.resolution_percentage=100
scene.world.color=(.22,.22,.22)
scene.view_settings.view_transform='AgX'
scene.render.image_settings.file_format='PNG'
scene.render.film_transparent=False
world=scene.world
world.use_nodes=True
world.node_tree.nodes['Background'].inputs[0].default_value=(.13,.16,.19,1)
world.node_tree.nodes['Background'].inputs[1].default_value=.6
floor_mat=material('StudioFloor',(.043,.052,.063),.12,.36)
surface_grid('StudioGround',lambda u,v:((u-.5)*200,-.011,(v-.5)*200),1,1,floor_mat,parent=group('Studio'),normal=(0,1,0))

def area(name,position,power,size,color):
    data=bpy.data.lights.new(name,'AREA'); data.energy=power; data.shape='RECTANGLE'; data.size=size; data.size_y=size*.45; data.color=color
    obj=bpy.data.objects.new(name,data); bpy.context.collection.objects.link(obj); obj.location=bp(position)
    direction=Vector(bp((0,.65,0)))-obj.location
    obj.rotation_euler=direction.to_track_quat('-Z','Y').to_euler()
area('KeySoftbox',(3.7,5.8,4.0),1500,5.0,(.82,.89,1.0))
area('RoofSoftbox',(-3.0,5.5,-1.8),1800,5.5,(1.0,.95,.87))
area('RimSoftbox',(1.4,3.3,-5.0),1300,4.0,(.64,.77,1.0))
area('FrontFill',(-3.5,2.2,5.8),650,3.0,(1.0,1.0,1.0))
camera_data=bpy.data.cameras.new('ReviewCamera')
camera=bpy.data.objects.new('ReviewCamera',camera_data)
bpy.context.collection.objects.link(camera)
scene.camera=camera
camera.data.type='ORTHO'; camera.data.ortho_scale=6.4

def view(name,angle,elevation=.35,opened=False):
    distance=8
    position=(distance*math.sin(angle),2.65 if elevation==.35 else 4.6,distance*math.cos(angle))
    camera.location=bp(position)
    direction=Vector(bp((0,.72,0)))-camera.location
    camera.rotation_euler=direction.to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(QA/(name+'.png'))
    bpy.ops.render.render(write_still=True)

from public_source import save_source
save_source(SOURCE/'vehicle.blend')
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
if '--all-views' in args:
    for i in range(8): view(f'angle-{i*45:03}',i*math.pi/4)
    for key,node in joints.items(): node.rotation_euler.z=(-1 if key.endswith('Left') else 1)*math.radians(67)
    trunk.rotation_euler.x=math.radians(70)
    view('open-doors',math.pi/4,.55,True)
    view('open-trunk',math.pi*1.25,.55,True)
elif '--export-only' not in args:
    view('review-front',math.pi/4)
    view('review-rear',math.pi*1.25)
print('Study_ASSET_READY',str(OUTPUT/'vehicle.glb'))
