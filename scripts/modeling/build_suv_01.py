"""Reproducible vehicle study based on real-vehicle reference observation.

Brand identifiers are omitted; exterior design rights remain unverified.
Coordinates: X left, Y up, Z forward, in meters.
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from vehicle_authoring import VehicleAuthoring, point, smoothstep


def profile(samples, value):
    """Nonuniform cubic Hermite interpolation with shared physical tangents."""
    if value <= samples[0][0]:
        return samples[0][1]
    if value >= samples[-1][0]:
        return samples[-1][1]
    slopes = [(samples[i + 1][1] - samples[i][1]) / (samples[i + 1][0] - samples[i][0])
              for i in range(len(samples) - 1)]
    tangents = [slopes[0]]
    for i in range(1, len(samples) - 1):
        if slopes[i - 1] * slopes[i] <= 0:
            tangents.append(0.)
        else:
            a, b = samples[i][0] - samples[i - 1][0], samples[i + 1][0] - samples[i][0]
            tangents.append((a + b) / (a / slopes[i - 1] + b / slopes[i]))
    tangents.append(slopes[-1])
    for i, ((a, va), (b, vb)) in enumerate(zip(samples, samples[1:])):
        if value <= b:
            t, h = (value - a) / (b - a), b - a
            return ((2 * t**3 - 3 * t*t + 1) * va + (t**3 - 2*t*t + t) * h * tangents[i]
                    + (-2*t**3 + 3*t*t) * vb + (t**3 - t*t) * h * tangents[i + 1])


def mix(a, b, t):
    return a + (b - a) * t


def blend(a, b, t):
    return tuple(mix(a[i], b[i], t) for i in range(3))


def samples(fn, count=80):
    return [fn(i / count) for i in range(count + 1)]


author = VehicleAuthoring('suv-01', 'Reconstructed vehicle study; exterior design rights unverified')
root = author.root
paint = author.material('BodyPaint', (.90, .915, .91), .56, .245, coat=.38)
innerpaint = author.material('InnerPaint', (.70, .73, .73), .35, .35)
black = author.material('BlackTrim', (.027, .035, .041), .05, .38)
black.node_tree.nodes['Principled BSDF'].inputs['Specular IOR Level'].default_value = .22
seal = author.material('WindowSeals', (.021, .026, .031), .015, .59)
glass = author.material('Glazing', (.11, .17, .20), .10, .145, alpha=.84, coat=.28)
glass.node_tree.nodes['Principled BSDF'].inputs['Specular IOR Level'].default_value = .35
chrome = author.material('SatinMetal', (.62, .68, .71), .94, .19)
wheelmetal = author.material('BlackAlloy', (.065, .077, .084), .86, .22, coat=.3)
rubber = author.material('TyreRubber', (.032, .037, .042), .01, .79)
leather = author.material('BlackLeather', (.070, .078, .087), .015, .66)
cloth = author.material('SeatInserts', (.095, .105, .119), .015, .78)
lining = author.material('CargoCarpet', (.068, .078, .09), 0, .95)
headliner = author.material('RoofLining', (.33, .35, .37), 0, .88)
head = author.material('Headlamp', (.80, .91, 1), .15, .18, emission=(.82, .94, 1))
tail = author.material('Taillamp', (.65, .006, .018), .14, .21, emission=(1, .003, .010))
signal_left = author.material('SignalLeft', (.74, .28, .011), .10, .23, emission=(1, .33, .015))
signal_right = author.material('SignalRight', (.74, .28, .011), .10, .23, emission=(1, .33, .015))
reflector = author.material('RedReflector', (.40, .006, .016), .18, .28)
lens = author.material('ClearLampCover', (.08, .095, .11), 0, .12, alpha=.065, coat=.06)
lens.node_tree.nodes['Principled BSDF'].inputs['Specular IOR Level'].default_value = .18
redlens = author.material('RedLampCavity', (.16, .003, .010), .2, .26)


# Five independent transverse regimes are interpolated along the body length.
WIDTH = [(-2.36, .76), (-2.18, .89), (-1.80, .909), (-1.35, .9185),
         (-.90, .903), (-.30, .900), (.30, .899), (.82, .908), (1.35, .9185),
         (1.82, .918), (2.15, .857), (2.33, .73)]
BELT = [(-2.36, 1.13), (-1.80, 1.185), (-1.10, 1.177), (-.30, 1.166),
        (.72, 1.154), (1.20, 1.159), (1.80, 1.135), (2.33, 1.102)]
ROOF = [(-1.87, 1.562), (-1.63, 1.603), (-1.02, 1.628), (-.38, 1.633),
        (-.10, 1.627), (.06, 1.610), (.164, 1.580), (.26, 1.52)]


def belt(z):
    return profile(BELT, z)


def side_x(z, y):
    """Broad shoulder, rising lower cove and integrated painted arch flare."""
    top = belt(z)
    height = max(0, min(1, (y - .25) / (top - .25)))
    cove = .052 * math.exp(-((z + .02) / 1.04)**4)
    mid = .44 + .075 * smoothstep((-z + .20) / 1.55)
    cove_t = (mid - .25) / (top - .25)
    section = [(0, -.050), (.075, -.012), (cove_t, -.010-cove),
               (cove_t+.17, -.024), (.58, -.020), (.82, .0), (.94, -.012), (1, -.047)]
    base = profile(WIDTH, z) + profile(section, height)
    base -= .008 * math.exp(-((y - mid) / .11)**2) * math.exp(-((z + .08) / 1.0)**4)
    for axle in [1.35, -1.35]:
        radius = math.hypot(z - axle, y - .3696)
        base += profile([(0,.029),(.411,.029),(.431,.047),(.470,.031),(.517,.007),(.561,0),(.85,0)],radius)
    # A smooth asymptote preserves curvature at the official maximum half-width.
    return .9325 - .010 * math.log1p(math.exp((.9325-base)/.010))


def roof_y(z):
    return profile(ROOF, z)


def upper_x(z):
    return profile([(-1.90, .729), (-1.60, .733), (-.75, .738), (.18, .735), (.26, .735)], z)


def window_top(z):
    if z > .15:
        return mix(roof_y(.15)-.063, belt(.805) + .027, smoothstep((z - .15) / .66))
    return roof_y(z) - .063


def glass_x(z, y):
    lo, hi = belt(z), roof_y(min(z, .15)) - .020
    t = max(0, min(1, (y - lo) / (hi - lo)))
    return mix(side_x(z, lo) - .008, upper_x(z), t) + .008 * math.sin(math.pi * t)


def outer_x(z, y):
    return side_x(z, y) if y <= belt(z) else glass_x(z, y)


def quarter_glass_point(side,u,v):
    z = mix(mix(-1.855, -1.708, v), mix(-1.409, -1.195, v), u)
    bottom = belt(z) + .024 + .054 * (1-u)**3
    y = mix(bottom, window_top(z) - .024, v)
    return side * glass_x(z, y), y, z


def rack_height(z):
    t=(z+1.66)/1.68
    crown=.014*(1-(.622/upper_x(z))**2)
    return roof_y(z)+crown+.035-.020*abs(2*t-1)**6


def strip(name, boundary_a, boundary_b, mat, parent=None, nu=64, nv=8, solid=.013, normal=None):
    return author.surface(name, lambda u, v: blend(boundary_a(u), boundary_b(u), v),
                          nu, nv, mat, parent, solid, normal)


def ring(name, center, radius, tube, mat, parent=None, axis='X', count=72):
    def shape(u, v):
        a, b = u * math.tau, v * math.tau
        r = radius + tube * math.cos(b)
        coords = (tube * math.sin(b), r * math.cos(a), r * math.sin(a))
        if axis == 'Z':
            coords = (coords[1], coords[2], coords[0])
        return tuple(center[i] + coords[i] for i in range(3))
    return author.surface(name, shape, count, 10, mat, parent)


def ellipsoid(name, center, scale, mat, parent=None, nu=48, nv=22):
    def fn(u, v):
        a, b = u * math.tau, (v - .5) * math.pi
        return (center[0] + scale[0] * math.cos(b) * math.cos(a),
                center[1] + scale[1] * math.sin(b),
                center[2] + scale[2] * math.cos(b) * math.sin(a))
    return author.surface(name, fn, nu, nv, mat, parent)


def remove_arches(obj):
    for axle in [1.35, -1.35]:
        author.cut_arch(obj, axle, .3696, .411)


def clipped_side_panel(name, bounds, resolution, constraints, x_at, side, material=paint):
    """Clip small physical Y/Z cells to analytic boundaries, sharing all vertices."""
    z0,z1,y0,y1=bounds
    nz,ny=resolution
    vertices,faces,lookup=[],[],{}
    def clip(polygon,condition):
        result=[]
        for start,end in zip(polygon,polygon[1:]+polygon[:1]):
            fs,fe=condition(*start),condition(*end)
            inside_s,inside_e=fs>=-1e-10,fe>=-1e-10
            if inside_s:result.append(start)
            if inside_s!=inside_e:
                low,high=0.,1.
                for _ in range(28):
                    t=(low+high)/2
                    candidate=(mix(start[0],end[0],t),mix(start[1],end[1],t))
                    if (condition(*candidate)>=0)==inside_s:low=t
                    else:high=t
                t=(low+high)/2
                result.append((mix(start[0],end[0],t),mix(start[1],end[1],t)))
        return result
    for j in range(ny):
        for i in range(nz):
            za,zb=mix(z0,z1,i/nz),mix(z0,z1,(i+1)/nz)
            ya,yb=mix(y0,y1,j/ny),mix(y0,y1,(j+1)/ny)
            polygon=[(za,ya),(zb,ya),(zb,yb),(za,yb)]
            for condition in constraints:
                polygon=clip(polygon,condition)
                if len(polygon)<3:break
            if len(polygon)<3:continue
            indices=[]
            for z,y in polygon:
                key=(round(z,7),round(y,7))
                if key not in lookup:
                    lookup[key]=len(vertices)
                    vertices.append((side*x_at(z,y),y,z))
                index=lookup[key]
                if not indices or indices[-1]!=index:indices.append(index)
            if len(indices)>2 and indices[0]==indices[-1]:indices.pop()
            if len(indices)>2:faces.append(tuple(indices))
    obj=author.mesh(name,vertices,faces,material,normal=(side,0,0))
    author.thickness(obj,.022)
    return obj


def door_front(zheight):
    return .790 - .035 * zheight


def door_cutline(v):
    return profile([(0, -.965), (.19, -1.010), (.48, -1.255), (.74, -1.395), (1, -1.412)], v)


def door_rear(v):
    boundary = door_cutline(v)
    y = mix(.322, 1.178, v)
    if abs(y - .3696) < .414:
        opening = -1.35 + math.sqrt(.414**2 - (y - .3696)**2)
        boundary = max(boundary, opening)
    return boundary


def rear_side_end(y):
    # The upper fixed lamp wraps forward into the quarter; the bumper stays deeper.
    return profile([(.256,-2.108),(1.045,-2.108),(1.080,-1.990),(1.176,-1.900)],y)


doors = {}
door_shapes = {}
for side, suffix in [(1, 'Left'), (-1, 'Right')]:
    for row in ['front', 'rear']:
        name = row + suffix
        forward = (lambda v: door_front(v)) if row == 'front' else (lambda v: -.310)
        back = (lambda v: -.302) if row == 'front' else door_rear
        origin_z = .765 if row == 'front' else -.310
        joint = author.group('door_' + name, (side * side_x(origin_z, .93), .93, origin_z), root)
        doors[name] = joint
        door_shapes[name] = (side, row, forward, back)

        def door_point(u, v, side=side, forward=forward, back=back):
            z = mix(back(v) + .002, forward(v) - .002, u)
            y = mix(.322, belt(z), v)
            return side * side_x(z, y), y, z
        panel = author.surface('DoorSkin_' + name, door_point, 66, 42, paint, joint, .018, (side, 0, 0))
        # Rear doors have a native wheel-clearance boundary, avoiding fragile Boolean sheets.

    # The fixed side shell shares every door boundary; wheel openings are real cuts.
    clipped_side_panel('RearQuarter'+suffix,(-2.108,-.850,.256,1.190),(94,64),[
        lambda z,y:belt(z)-y,
        lambda z,y:z-rear_side_end(y),
        lambda z,y:door_cutline(max(0,min(1,(y-.322)/(belt(z)-.322))))-.002-z,
        lambda z,y:(z+1.35)**2+(y-.3696)**2-.414**2,
    ],side_x,side)

    # Structural rocker is a curved closed section, not a floating straight strip.
    def rocker(u, v, side=side):
        z = mix(-.926, .895, u)
        x_top=side_x(z,.322)
        xx=profile([(0,x_top),(.15,x_top+.010),(.52,x_top+.012),(.63,x_top-.045),(.85,x_top-.052),(1,x_top)],v)
        yy=profile([(0,.320),(.15,.308),(.52,.258),(.63,.250),(.85,.305),(1,.320)],v)
        return side*xx,yy,z
    author.surface('Rocker' + suffix, rocker, 76, 22, paint)

    # Split wheel lips at the moving rear-door boundary, with separate capped segments.
    for axle in [1.35, -1.35]:
        groups = []
        current, current_parent = [], None
        for i in range(151):
            angle = mix(-.28, math.pi + .28, i / 150)
            z, y = axle + .415 * math.cos(angle), .3696 + .415 * math.sin(angle)
            v = max(0, min(1, (y - .322) / (belt(z) - .322)))
            parent = doors['rear' + suffix] if axle < 0 and z > door_cutline(v) + .004 and z < -.315 else root
            if current and parent != current_parent:
                groups.append((current_parent, current))
                current = []
            current_parent = parent
            current.append((side * (side_x(z, y) + .001), y, z))
        groups.append((current_parent, current))
        for index, (parent, coords) in enumerate(groups):
            if axle < 0 and parent == doors['rear' + suffix]:
                # Keep the capped moving lip inside the native door-skin bottom.
                # The circular arch continues below that skin only on fixed parts.
                bottom = .322 + .0027
                if coords[0][1] < bottom:
                    z = axle + math.sqrt(.415**2 - (bottom - .3696)**2)
                    endpoint = (side * (side_x(z, bottom) + .001), bottom, z)
                    coords = [endpoint] + [p for p in coords if p[1] > bottom]
            if len(coords) > 1:
                author.curve('ArchLip' + suffix + str(axle) + str(index), coords, .0027, paint, parent)


# Shared roof/glass endpoints eliminate the slab-edge wings of a boxed cabin.
def roof_surface(u, v):
    t = 2*u - 1
    z = mix(-1.815 + .030*(1-t*t), .164 - .027*(1-t*t), v)
    return (t * upper_x(z), roof_y(z) + .014 * (1-t*t), z)


author.surface('RoofPanel', roof_surface, 64, 70, paint, solid=.024, normal=(0, 1, 0))


def windshield(u, v):
    t = 2*u - 1
    top = roof_surface(u, 1)
    bottom = (t * .833, 1.169 + .018*(1-t*t), .803 + .070*(1-t*t))
    p = blend(bottom, top, v)
    return p[0], p[1] + .008 * math.sin(math.pi*v) * (1-t*t), p[2]


author.surface('Windscreen', windshield, 64, 34, glass, solid=.004, normal=(0, .8, .6))
for side, suffix in [(1, 'Left'), (-1, 'Right')]:
    screen_edge = lambda t, side=side: windshield(1 if side == 1 else 0, t)
    outer_edge = lambda t, side=side: (side * glass_x(mix(.820, .15, t), mix(belt(.82), window_top(.15), t)),
                                      mix(belt(.82), window_top(.15), t), mix(.820, .15, t))
    strip('APillar' + suffix, screen_edge, outer_edge, paint, nu=44, nv=8, normal=(side, .4, .25))
    # Rails use the roof's exact outer edge and descend to the side-window frame.
    strip('RoofRail' + suffix,
          lambda t, side=side: roof_surface(1 if side == 1 else 0, t),
          lambda t, side=side: (side * glass_x(mix(-1.815, .15, t), window_top(mix(-1.815, .15, t))),
                                window_top(mix(-1.815, .15, t)), mix(-1.815, .15, t)),
          paint, nu=76, nv=8, normal=(side, .7, 0))
    for row in ['front', 'rear']:
        parent = doors[row + suffix]
        front_z = (lambda v: mix(.754, .132, v)) if row == 'front' else (lambda v: -.336)
        back_z = (lambda v: -.276) if row == 'front' else (lambda v: mix(-1.374, -1.140, v))
        def pane(u, v, side=side, front_z=front_z, back_z=back_z):
            z = mix(back_z(v), front_z(v), u)
            roof_z = mix(back_z(1), front_z(1), u)
            y = mix(belt(z) + .016, window_top(roof_z) - .014, v)
            return side * glass_x(z, y), y, z
        author.surface('DoorGlass' + row + suffix, pane, 44, 23, glass, parent, .004, (side, .15, 0))
        edges = [samples(lambda t: pane(t, 0), 60), samples(lambda t: pane(1, t), 40),
                 samples(lambda t: pane(1-t, 1), 60), samples(lambda t: pane(0, 1-t), 40)]
        outline = [p for edge in edges for p in edge[:-1]]
        author.curve('MovingGlassFrame' + row + suffix, outline, .009, black, parent, cyclic=True)
        author.curve('GlassGasket' + row + suffix,
                     [(p[0] - side*.005, p[1], p[2]) for p in outline], .004, seal, parent, cyclic=True)
        # Distinct black B/C pillar faces are slightly bowed, with low specular response.
        strip('PillarCover' + row + suffix,
              lambda v: pane(0, v),
              lambda v, side=side: (pane(0, v)[0] + side*.002, pane(0, v)[1], pane(0, v)[2] - .027),
              black, parent, nu=34, nv=5, solid=.011, normal=(side, 0, 0))

    def quarter_glass(u, v, side=side):
        return quarter_glass_point(side,u,v)
    author.surface('QuarterGlass' + suffix, quarter_glass, 34, 26, glass, solid=.004, normal=(side, .15, 0))
    strip('QuarterUpperFrame'+suffix,
          lambda t:quarter_glass(t,1),
          lambda t,side=side:(lambda z:(side*glass_x(z,window_top(z)),window_top(z),z))
              (quarter_glass(t,1)[2]),paint,nu=44,nv=7,solid=.017,normal=(side,.25,0))
    outline = (samples(lambda t: quarter_glass(t, 0), 40)[:-1]
               + samples(lambda t: quarter_glass(1, t), 30)[:-1]
               + samples(lambda t: quarter_glass(1-t, 1), 40)[:-1]
               + samples(lambda t: quarter_glass(0, 1-t), 30)[:-1])
    author.curve('QuarterGasket' + suffix, outline, .009, black, cyclic=True)
    # Fixed shoulder beneath the last side glass meets the lower quarter at the belt.
    strip('QuarterShoulder' + suffix,
          lambda u: quarter_glass(u, 0),
          lambda u, side=side: (side*side_x(mix(-1.855, -1.409, u), belt(mix(-1.855, -1.409, u))),
                                belt(mix(-1.855, -1.409, u)), mix(-1.855, -1.409, u)),
          paint, nu=36, nv=6, normal=(side, .5, 0))
    # Roof-rack height is included in the published overall height.
    rail = samples(lambda t, side=side: (side*.622, rack_height(mix(-1.66,.02,t)), mix(-1.66, .02, t)), 70)
    author.curve('RoofRack' + suffix, rail, .007, black)
    for z in [-1.52, -.08]:
        rail_y=rack_height(z)
        base_y=roof_y(z)+.014*(1-(.622/upper_x(z))**2)
        author.box('RoofRackFoot' + suffix, (side*.622, (base_y+rail_y)/2, z),
                   (.030,max(.009,rail_y-base_y),.086), black, radius=.006)


# Hood has its own tall SUV crown and two broad shoulder ridges.
def hood_surface(u, v):
    t = 2*u - 1
    z = mix(.823, 2.190 - .225*abs(t)**3, v)
    x = t * mix(.833, .858, v)
    y = mix(1.184, 1.106, v) + .014*(1-t*t) + .020*math.exp(-((abs(t)-.78)/.14)**2)*math.sin(math.pi*v)
    return x, y, z


author.surface('Hood', hood_surface, 70, 70, paint, solid=.019, normal=(0, 1, .15))
for side, suffix in [(1, 'Left'), (-1, 'Right')]:
    strip('HoodShoulder' + suffix,
          lambda t, side=side: hood_surface(1 if side == 1 else 0, t),
          lambda t, side=side: (side*side_x(mix(.823, 1.965,t),belt(mix(.823,1.965,t))),
                                belt(mix(.823,1.965,t)),mix(.823,1.965,t)),
          paint, nu=65, nv=12, normal=(side,.65,0))
    author.curve('HoodSeal' + suffix,
                 samples(lambda t, side=side: tuple(hood_surface(1 if side==1 else 0,t)[i] + (0,.001,0)[i] for i in range(3)),65),
                 .0015, seal)


from suv_01_cabin import build_cabin
from suv_01_front import build_front
from suv_01_rear import build_rear
from suv_01_wheels import build_wheels

build_cabin(globals())
build_front(globals())
trunk, hatch_hotspot = build_rear(globals())
build_wheels(globals())

# One shared displacement lowers the hood/nose and their lamp/fascia boundaries.
# Wheels retain their measured axle and tyre dimensions; all adjoining skin points
# receive the same continuous field, so the change cannot create a new panel gap.
def nose_displacement(y, z):
    return .095 * smoothstep((z-.823)/1.135) * smoothstep((y-.55)/.55)


for obj in list(root.children_recursive):
    if obj.type != 'MESH' or obj.parent.name.startswith('wheel_'):
        continue
    origin = obj.parent['origin_carvue']
    for vertex in obj.data.vertices:
        y, z = vertex.co.z + origin[1], -vertex.co.y + origin[2]
        vertex.co.z -= nose_displacement(y,z)
    obj.data.update()
    # Sheet returns are real sharp edges; their normals must not bend the outer paint.
    if any(material in (paint,innerpaint) for material in obj.data.materials):
        obj.data.set_sharp_from_angle(angle=math.radians(35))

manifest = {
    'schemaVersion': 1, 'vehicleId': 'suv-01', 'assetVersion': '1.1.0', 'units': 'meter', 'forward': '+Z',
    'framing': {'target': [0, .7392, 0], 'direction': [1.2, .46, 1.65], 'distance': 7.5978},
    'joints': {key: {'node': joint.name, 'axis': [0,1,0],
                     'openAngle': math.radians(-67 if 'Left' in key else 67)} for key,joint in doors.items()},
    'frontWheels': ['wheel_frontLeft', 'wheel_frontRight'],
    'lights': {'head': ['Headlamp'], 'tail': ['Taillamp'], 'left': ['SignalLeft'], 'right': ['SignalRight']},
    'headlights': [{'position':[x,1.079-nose_displacement(1.079,2.16),2.16], 'target':[x,.10,8.1]} for x in [-.63,.63]],
    'hotspots': [],
}
manifest['joints']['trunk'] = {'node': 'trunk', 'axis': [1,0,0], 'openAngle': math.radians(86)}
labels = {'frontLeft':'左前門','frontRight':'右前門','rearLeft':'左後門','rearRight':'右後門'}
for key,joint in doors.items():
    side = 1 if 'Left' in key else -1
    z = -.10 if key.startswith('front') else -1.24
    world = (side*(side_x(z,1.05)+.028),1.07,z)
    origin=joint['origin_carvue']
    manifest['hotspots'].append({'id':key,'node':joint.name,'position':[world[i]-origin[i] for i in range(3)],'label':labels[key]})
manifest['hotspots'] += [
    {'id':'trunk','node':'trunk','position':hatch_hotspot,'label':'電動尾門'},
    {'id':'headlights','node':'VehicleRoot','position':[.64,1.08-nose_displacement(1.08,2.18),2.18],'label':'車頭燈'},
]
author.export(manifest, {
    'dimensionsMeters':[4.690,1.865,1.680], 'wheelbaseMeters':2.700,
    'tyres':'235/60 R18', 'construction':'Independent Vehicle nonuniform Hermite body sections and shared aperture boundaries',
    'closedTransforms':'The original GLB node transform is the closed pose; manifest rotations are relative local-axis rotations.',
    'qualityStatus':'Initial independent reconstruction; requires shape, open-state and WebGL review before verification.',
})
