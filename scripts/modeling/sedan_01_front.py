"""Study front surfaces calibrated against Taiwan Hybrid photographic references.

The hood edge is supplied by the main body builder. Lamp housings and painted
bumper panels share their borders, leaving actual openings instead of covering
an uncut painted sheet with floating light strips.
"""
import math
import bpy
from mathutils import Vector
from mathutils.geometry import tessellate_polygon


def build_front(context):
    surface = context['surface_grid']
    mesh = context['mesh']
    curve = context['curve']
    box = context['box']
    material = context['material']
    hood = context['hood_surface']
    body_x = context['body_x']
    belt = context['belt']
    root = context['root']
    paint = context['paint']
    black = context['black']
    chrome = context['chrome']
    head = context['head']
    projector = material('HeadlampProjector',(.20,.27,.35),.25,.12,(.73,.87,1.0))
    seal = context['seal']
    lens = material('FrontLampClearLens', (.19, .23, .27), .25, .15, alpha=.14)
    reflector = material('FrontLampReflector', (.32, .36, .40), .82, .24)
    optical_black = material('FrontOpticalCavity', (.010,.013,.016), .10, .22)
    interpolate = context['interpolate']

    def clamp(value):
        return max(0, min(1, value))

    def smooth(value):
        t = clamp(value)
        return t*t*(3-2*t)

    # Sample the existing hood, including its swept-back outer corners.
    edge = [hood(.5+.5*i/100, 1) for i in range(101)]

    def hood_edge(x):
        x = abs(x)
        for a, b in zip(edge, edge[1:]):
            if a[0] <= x <= b[0]:
                t = (x-a[0])/max(.000001, b[0]-a[0])
                return tuple(a[k]*(1-t)+b[k]*t for k in range(3))
        return edge[-1]

    inner_x = .472
    outer_x = edge[-1][0]-.001

    def lamp_point(s, v, side=1, offset=0):
        x = inner_x+(outer_x-inner_x)*s
        top = hood_edge(x)
        height = (.115*(1-s)**.70+.055*math.sin(math.pi*s)**1.4)
        lower_x = x-.070*(1-s)**2
        lower_y = top[1]-height
        lower = (lower_x, lower_y, front_depth(lower_x+.003, lower_y+.001))
        return (side*(x*(1-v)+lower[0]*v+.003), top[1]*(1-v)+lower[1]*v+.001,
                top[2]*(1-v)+lower[2]*v+.004+offset)

    def cap_edge(x):
        magnitude = abs(x)
        side = 1 if x >= 0 else -1
        if magnitude >= inner_x-.070:
            low, high = 0, 1
            for _ in range(20):
                mid = (low+high)/2
                if abs(lamp_point(mid, 1)[0]) < magnitude:
                    low = mid
                else:
                    high = mid
            return lamp_point((low+high)/2, 1, side)
        upper = hood_edge(magnitude)
        return (x, upper[1], upper[2])

    def front_depth(x, y):
        # The opening height changes at the angled inner lamp corner, but the
        # underlying bumper depth field must stay continuous across that edge.
        cap = hood_edge(x)
        base = 2.302-.175*(abs(x)/.836)**3-.035*(1-smooth((y-.245)/.16))
        blend = smooth((y-.47)/max(.16, cap[1]-.47))
        return base*(1-blend)+cap[2]*blend

    def face(x, y, offset=0):
        return (x, y, front_depth(x, y)+offset)

    def face_patch(name, outline, mat, offset):
        vertices, faces, lookup = [], [], {}

        def index(point):
            coordinate = face(point.x, point.y, offset)
            key = tuple(round(value, 8) for value in coordinate)
            if key not in lookup:
                lookup[key] = len(vertices)
                vertices.append(coordinate)
            return lookup[key]

        # A single nonplanar n-gon would cut through the curved bumper between
        # its boundary vertices. Tessellate and reproject every interior sample.
        polygon = [Vector((x, y, 0)) for x, y in outline]
        triangles = tessellate_polygon([polygon])
        steps = 12
        for triangle in triangles:
            a, b, c = (polygon[vertex] for vertex in triangle)
            grid = {}
            for i in range(steps+1):
                for j in range(steps+1-i):
                    grid[i, j] = index(a+(b-a)*(i/steps)+(c-a)*(j/steps))
            for i in range(steps):
                for j in range(steps-i):
                    faces.append((grid[i, j], grid[i+1, j], grid[i, j+1]))
                    if i+j < steps-1:
                        faces.append((grid[i+1, j], grid[i+1, j+1], grid[i, j+1]))
        return mesh(name, vertices, faces, mat, root)

    def face_line(outline, offset):
        points = []
        for a, b in zip(outline, outline[1:]):
            for step in range(12):
                t = step/12
                points.append(face(a[0]*(1-t)+b[0]*t, a[1]*(1-t)+b[1]*t, offset))
        points.append(face(*outline[-1], offset))
        return points

    def outside(y):
        return abs(body_x(y, 2.20, 1))

    grille_bottom = .303
    grille_top = .638

    def grille_half(v):
        return .712-.185*smooth(v)+.012*math.sin(math.pi*v)

    def grille_point(u, v, offset=0):
        y = grille_bottom+(grille_top-grille_bottom)*v
        return face((u*2-1)*grille_half(v), y, offset)

    def corner_bounds(v):
        inner=interpolate([(0,.715),(.12,.743),(.40,.765),(.73,.755),(.91,.700),(1,.655)],v)
        outer=interpolate([(0,.778),(.12,.810),(.55,.824),(.80,.813),(.94,.780),(1,.723)],v)
        outer=min(outer,outside(.309+.370*v)-.006)
        return inner,outer

    def corner(u,v,side=1,depth=0):
        inner,outer=corner_bounds(v)
        return face(side*(inner+(outer-inner)*u),.309+.370*v,depth)

    def top_panel(u, v):
        across = u*2-1
        cap = cap_edge(across*outer_x)
        y = .679*(1-v)+cap[1]*v
        x = across*(outside(y)*(1-v)+outer_x*v)
        return face(x, y)

    surface('FrontUpperBumper', top_panel, 96, 20, paint, root, .014, normal=(0, 0, 1))
    surface('FrontNoseBridge',lambda u,v:face((u*2-1)*corner_bounds((.638+.041*v-.309)/.370)[0],.638+.041*v),
            64,6,paint,root,.014,normal=(0,0,1))
    surface('FrontLowerBumper', lambda u, v: face((u*2-1)*outside(.244+.059*v), .244+.059*v),
            64, 6, paint, root, .014, normal=(0, 0, 1))
    for side in [-1, 1]:
        def cheek(u, v, side=side):
            y = .309+(.638-.309)*v
            inside=grille_half((y-grille_bottom)/(grille_top-grille_bottom))
            cut=corner_bounds((y-.309)/.370)[0]
            x = side*(inside*(1-u)+cut*u)
            return face(x, y)
        surface('FrontBumperCheek', cheek, 18, 32, paint, root, .014, normal=(side*.2, 0, 1))
        def outside_cheek(u,v,side=side):
            y=.309+.370*v
            x=corner_bounds(v)[1]*(1-u)+outside(y)*u
            return face(side*x,y)
        surface('FrontCornerOuterSkin',outside_cheek,8,36,paint,root,.014,normal=(side*.2,0,1))
        surface('FrontCheekLowerJoin',lambda u,v,side=side:face(side*(grille_half((.303+.006*v-.303)/.335)*(1-u)+outside(.303+.006*v)*u),.303+.006*v),
                18,2,paint,root,.014,normal=(side*.2,0,1))

    # The fender must meet this actual bumper boundary. A rectangular fender
    # extending to z=2.20 at every height would protrude through the swept lamp.
    front_top = top_panel(1, 1)

    def side_boundary(t):
        y = .245+(front_top[1]-.245)*t
        if y > .679:
            return top_panel(1, (y-.679)/(front_top[1]-.679))
        return face(outside(y), y)

    for side, suffix in [(1, 'L'), (-1, 'R')]:
        previous = bpy.data.objects.get('FrontFender'+suffix)
        if previous:
            bpy.data.objects.remove(previous, do_unlink=True)

        def fender(u, v, side=side):
            front = side_boundary(v)
            z = .814+(front[2]-.814)*u
            natural_y = .245+(belt(z)-.245)*v
            y = natural_y+(front[1]-(.245+(belt(front[2])-.245)*v))*u**4
            natural_x = body_x(y, z, 1)
            x = natural_x+(front[0]-body_x(front[1], front[2], 1))*u**4
            return (side*x, y, z)

        panel = surface('FrontFender'+suffix, fender, 48, 28, paint, root, .017, normal=(side, 0, .1))
        context['cut_wheel_arches'](panel)

    # The dark recess replaces the center of the bumper, with a modeled inner lip.
    surface('GrilleRecess', lambda u, v: grille_point(u, v, -.025), 48, 28, black, root)
    for side in [-1, 1]:
        surface('GrilleSideReturn', lambda u, v, side=side:
                tuple(value+(0, 0, -.026*u)[k] for k, value in enumerate(grille_point(1 if side > 0 else 0, v))),
                2, 28, black, root)
    for end in [0, 1]:
        surface('GrilleHorizontalReturn', lambda u, v, end=end:
                tuple(value+(0, 0, -.026*v)[k] for k, value in enumerate(grille_point(u, end))),
                48, 2, black, root)
    boundary = [grille_point(i/32, 0, .001) for i in range(33)]
    boundary += [grille_point(1, i/20, .001) for i in range(1, 21)]
    boundary += [grille_point(1-i/32, 1, .001) for i in range(1, 33)]
    boundary += [grille_point(0, 1-i/20, .001) for i in range(1, 20)]
    curve('GrillePerimeter', boundary, .004, black, root, True)
    for row in range(9):
        y = .322+row*.039
        half = grille_half((y-grille_bottom)/(grille_top-grille_bottom))
        for column in range(-13, 14):
            x = column*.050+(row % 2)*.025
            if abs(x) > half-.032 or (abs(x) < .218 and .395 < y < .59):
                continue
            polygon = [face(x+.027*math.cos(i*math.tau/6),
                            y+.015*math.sin(i*math.tau/6), -.012) for i in range(6)]
            curve('GrilleCell', polygon, .0023, black, root, True, 1)

    for side in [-1, 1]:
        housing = lambda u, v, side=side: lamp_point(u, v, side)
        def cavity(u,v,side=side):
            depth=.036*max(0,math.sin(math.pi*u))**.25*max(0,math.sin(math.pi*v))**.30
            return lamp_point(u,v,side,-depth)
        surface('HeadlampHousing', cavity, 38, 18, optical_black, root, .006, normal=(side*.2, .3, 1))

        def inner_brow(u, v, side=side):
            inner = lamp_point(0, v, side)
            upper = hood_edge(inner[0])
            return (inner[0], inner[1]*(1-u)+upper[1]*u,
                    inner[2]*(1-u)+upper[2]*u)

        surface('HeadlampInnerBrow', inner_brow, 12, 20, paint, root, .009, normal=(side*.1, .3, 1))
        rim = [housing(i/32, 0) for i in range(33)]
        rim += [housing(1, i/12) for i in range(1, 13)]
        rim += [housing(1-i/32, 1) for i in range(1, 33)]
        rim += [housing(0, 1-i/12) for i in range(1, 12)]
        curve('HeadlampPanelGap', rim, .0022, seal, root, True)

        # Separate concave reflector cups leave visible dark space between optics.
        for start,width in [(.075,.17),(.27,.18)]:
            def optics(u,v,start=start,width=width,side=side):
                depth=-.025+.011*(abs(2*u-1)**2+abs(2*v-1)**2)*.5
                return lamp_point(start+width*u,.42+.20*v,side,depth)
            surface('HeadlampReflectorCup',optics,10,8,reflector,root)
            for row in [.44,.52,.60]:
                curve('ReflectorFineLayer',[lamp_point(start+width*i/16,row,side,-.013) for i in range(17)],.0009,reflector,root)
        center = Vector(lamp_point(.62, .43, side, -.012))
        axis_u = Vector(lamp_point(.605, .43, side))-Vector(lamp_point(.595, .43, side))
        axis_v = Vector(lamp_point(.60, .44, side))-Vector(lamp_point(.60, .42, side))
        normal = axis_u.cross(axis_v).normalized()
        if normal.z < 0:
            normal = -normal
        horizontal = Vector((side, 0, 0))
        horizontal = (horizontal-normal*horizontal.dot(normal)).normalized()
        vertical = normal.cross(horizontal).normalized()

        def ring(radius, depth):
            return [tuple(center+normal*depth+horizontal*(radius*math.cos(i*math.tau/40))+
                          vertical*(radius*math.sin(i*math.tau/40))) for i in range(40)]
        def projector_cup(u,v):
            radius=.019+.017*v
            return tuple(center+normal*(-.014+.017*v)+horizontal*(radius*math.cos(u*math.tau))+vertical*(radius*math.sin(u*math.tau)))
        surface('ProjectorBowl',projector_cup,40,8,reflector,root)
        curve('ProjectorOuterRing', ring(.036, .003), .0023, optical_black, root, True)
        def projector_lens(u,v):
            radius=.024*v
            return tuple(center+normal*(.004+.006*(1-v*v))+horizontal*(radius*math.cos(u*math.tau))+vertical*(radius*math.sin(u*math.tau)))
        surface('ProjectorOptic',projector_lens,40,8,projector,root)
        curve('ProjectorLensRim', ring(.024, .004), .0015, chrome, root, True)
        drl = [lamp_point(.025+.84*i/32, .88, side, .008) for i in range(33)]
        drl += [lamp_point(.865, .88-.57*i/12, side, .008) for i in range(1, 13)]
        curve('LEDLightGuide', drl, .0048, head, root)
        surface('HeadlampCover', lambda u, v, side=side: lamp_point(.01+.975*u, .015+.970*v, side, .016),
                32, 12, lens, root)
        signal = context['left_signal'] if side > 0 else context['right_signal']
        curve('FrontIndicator', [lamp_point(.035+.23*i/12, .97, side, .008) for i in range(13)], .003, signal, root)

        # The narrow upper grille and chrome blades meet the emblem cradle.
        wing = [(side*x, y) for x, y in [(.048, .716), (.130, .805), (.442, .815),
                                        (.474, .790), (.156, .780), (.104, .708)]]
        face_patch('UpperGrilleWing', wing, black, .003)
        strip = [(side*x, y) for x, y in [(.088, .729), (.137, .798), (.300, .804), (.465, .804)]]
        curve('UpperGrilleBlade', face_line(strip, .008), .0032, chrome, root)

        surface('CornerIntakeBack',lambda u,v,side=side:corner(u,v,side,-.035),20,30,optical_black,root)
        for end in [0,1]:
            surface('CornerIntakeWall',lambda u,v,end=end,side=side:corner(end,v,side,-.035*u),4,30,black,root)
            surface('CornerIntakeWall',lambda u,v,end=end,side=side:corner(u,end,side,-.035*v),20,4,black,root)
        # A rounded C-shaped strip follows the outer lip of the actual recess.
        trim=[corner(1-i/12,1,side,.002) for i in range(13)]
        trim=list(reversed(trim))+[corner(1,1-i/36,side,.002) for i in range(1,37)]
        trim += [corner(1-i/12,0,side,.002) for i in range(1,13)]
        curve('CornerBumperBrightTrim',trim,.0032,chrome,root)
        fog_y=.362
        fog_inner,fog_outer=corner_bounds((fog_y-.309)/.370)
        fog_x=(fog_inner+fog_outer)*.5
        fog_radius=min(.032,(fog_outer-fog_inner)*.44)
        # Check the entire circular rim, since the C opening narrows vertically.
        for _ in range(24):
            fits=True
            for index in range(72):
                angle=index*math.tau/72
                x=fog_x+fog_radius*math.cos(angle)
                y=fog_y+fog_radius*math.sin(angle)
                inner,outer=corner_bounds((y-.309)/.370)
                if not inner+.0035 <= x <= outer-.0035:
                    fits=False
                    break
            if fits:
                break
            fog_radius*=.97
        fog_scale=fog_radius/.032
        fog_center=Vector(face(side*fog_x,fog_y,-.022))
        def fog_bowl(u,v):
            radius=(.017+.015*v)*fog_scale
            return tuple(fog_center+Vector((radius*math.cos(u*math.tau),radius*math.sin(u*math.tau),-.010+.018*v)))
        surface('FogLampCup',fog_bowl,36,8,reflector,root)
        fog_ring=[tuple(fog_center+Vector((fog_radius*math.cos(i*math.tau/36),fog_radius*math.sin(i*math.tau/36),.008))) for i in range(36)]
        curve('FogLampRing',fog_ring,.0023*fog_scale,optical_black,root,True)
        surface('FogLampLens',lambda u,v:tuple(fog_center+Vector((.019*fog_scale*v*math.cos(u*math.tau),.019*fog_scale*v*math.sin(u*math.tau),.005*(1-v*v)))),36,7,projector,root)

    curve('FrontLowerValance', [face(x, .258, .002) for x in [-.77, -.60, -.30, 0, .30, .60, .77]], .009, black, root)
    cradle = [(math.cos(i*math.tau/48)*.087, .761+math.sin(i*math.tau/48)*.059) for i in range(48)]
    face_patch('FrontEmblemCradle', cradle, black, .004)
    plate_z = front_depth(0, .491)+.006
    box('FrontPlate', (0, .491, plate_z), (.415, .187, .008), context['plate'], radius=.005)
    boundary_x=inner_x-.070
    depth_steps=[abs(front_depth(boundary_x+.00001,y)-front_depth(boundary_x-.00001,y))
                 for y in [.60,.68,.74,.80,.86]]
    return {'plate_text': (0, .493, plate_z+.0048),
            'depthBoundaryMaxStep':max(depth_steps),'fogCenterX':fog_x,'fogRadius':fog_radius}
