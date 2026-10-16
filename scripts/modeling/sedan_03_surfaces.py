"""Independent Study Study surface fields in CARVUE coordinates."""
import math
from functools import lru_cache

AXLES = (1.4325, -1.4325)
FRONT_RADIUS = .32985
REAR_RADIUS = .3266
FRONT_WHEEL_CENTRE_X = .785
FRONT_TYRE_WIDTH = .225
BOTTOM = .175
FRONT_END = 2.2225
REAR_END = -2.5285


def front_wheelhouse_inner_x():
    # Preserve a conservative 0.6 mm allowance for tyre-surface details.
    envelope_radius=FRONT_RADIUS+.0006
    angle=math.radians(30)
    return FRONT_WHEEL_CENTRE_X-envelope_radius*math.sin(angle)-FRONT_TYRE_WIDTH*.5*math.cos(angle)-.020


def mix(a, b, t):
    return a + (b - a) * t


def smooth(t):
    t = max(0, min(1, t))
    return t * t * (3 - 2 * t)


@lru_cache(maxsize=64)
def slopes(points):
    h = [b[0] - a[0] for a, b in zip(points, points[1:])]
    d = [(b[1] - a[1]) / w for a, b, w in zip(points, points[1:], h)]
    result = [d[0]]
    for i in range(1, len(points) - 1):
        w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
        result.append(0 if d[i - 1] * d[i] <= 0 else (w1 + w2) / (w1 / d[i - 1] + w2 / d[i]))
    result.append(d[-1])
    return h, result


def profile(points, value):
    if value <= points[0][0]:
        return points[0][1]
    if value >= points[-1][0]:
        return points[-1][1]
    intervals, deriv = slopes(tuple(points))
    for i, ((a, av), (b, bv)) in enumerate(zip(points, points[1:])):
        if value <= b:
            t, h = (value - a) / (b - a), intervals[i]
            return ((2*t**3-3*t*t+1)*av + (t**3-2*t*t+t)*h*deriv[i]
                    + (-2*t**3+3*t*t)*bv + (t**3-t*t)*h*deriv[i+1])


WIDTH = ((-2.53,.740),(-2.23,.883),(-1.94,.883),(-1.55,.886),(-1.30,.881),
         (-.85,.851),(-.32,.836),(.35,.842),(.88,.865),(1.42,.882),(1.70,.882),(1.95,.882),(2.23,.770))
BELT = ((-2.53,1.012),(-2.34,1.023),(-1.88,1.075),(-1.47,1.079),(-.86,1.063),
        (-.32,1.049),(.30,1.043),(.73,1.030),(1.23,.984),(1.75,.941),(2.02,.886),(2.23,.821))
CAB = ((-1.90,1.090),(-1.65,1.186),(-1.36,1.303),(-1.08,1.389),
       (-.76,1.429),(-.51,1.440),(-.20,1.428),(.10,1.390),(.37,1.285),(.73,1.055))
WINDOW = ((-1.470,1.085),(-1.430,1.166),(-1.30,1.263),(-1.08,1.343),
          (-.78,1.389),(-.50,1.401),(-.20,1.389),(.08,1.352),(.35,1.253),(.692,1.039))


def belt(z):
    return profile(BELT, z)


def side_x(y, z):
    # Ease the last 140 mm into each rounded end with a zero longitudinal slope.
    # A wheel flare must not reverse the required tangent at the cap boundary.
    for join,direction in [(front_join_z(y),1),(rear_join_z(y),-1)]:
        distance=direction*(join-z)
        if 0<=distance<.140:
            t=distance/.140
            z=join-direction*.140*(2*t*t-t*t*t)
            break
    t = max(0, min(1, (y - BOTTOM) / (belt(z) - BOTTOM)))
    # A broad convex shoulder rolls into a soft lower-door return, not a crease.
    cove=.30+.11*smooth((-z-.20)/1.15)
    shoulder=.782+.103*math.exp(-((z+1.35)/.69)**2)+.045*math.exp(-((z-1.40)/.55)**2)
    middle=.048+.011*math.exp(-((z+.14)/.77)**2)
    offset = profile(((0,-.070),(.13,-.064),(cove,-middle),(.61,-.016),
                      (shoulder,.014),(.967,-.007),(1,-.029)), t)
    flare = sum(.020 * math.exp(-((math.hypot(y-r, z-a)-.379)/.093)**2)
                for a, r in zip(AXLES, (FRONT_RADIUS, REAR_RADIUS)))
    return profile(WIDTH, z) + offset + flare


def glass_x(y, z):
    return side_x(belt(z), z) - .385 * max(0, y-belt(z))


def interior_outer_limit(y,height,z,length,clearance=.070):
    """Bound a box against the entire curved skin span, including the door cove."""
    return min(side_x(y+height*(j/24-.5),z+length*(i/48-.5))
               for j in range(25) for i in range(49))-clearance


def cab_edge(z):
    crown = profile(((-1.90,1.090-belt(-1.90)),(-1.65,.029),(-1.26,.022),
                     (-1.074,.007),(-.96,.014),(-.76,.029),(-.20,.029),
                     (-.04,.014),(.105,.007),(.22,.016),(.51,.029),(.73,.025)),z)
    return profile(CAB, z) - crown


def cab_surface(t, z):
    top, edge = profile(CAB,z), cab_edge(z)
    return (t*glass_x(edge,z), top-(top-edge)*t*t, z)


def roof_boundary(front,t):
    # A shared bowed header spreads the opaque panel transition across the crown.
    bow=.045*(1-t*t)
    return .105-bow if front else -1.074+bow


def cab_panel_surface(panel,t,v):
    if panel=='FrontWindscreen':
        start,end=.73,roof_boundary(True,t)
    elif panel=='RoofSkin':
        start,end=roof_boundary(True,t),roof_boundary(False,t)
    else:
        start,end=roof_boundary(False,t),-1.90
    return cab_surface(t,mix(start,end,v))


def window_top(z):
    return profile(WINDOW,z)


def front_join_z(y):
    return 1.739+.082*y


def rear_join_z(y):
    return -2.081+.048*y


def front_z(x, y):
    join=front_join_z(y)
    width=side_x(y,join)
    centre=profile(((.16,2.110),(.25,2.190),(.48,FRONT_END),(.63,2.211),(.76,2.181),(.86,2.137),(1.05,1.920)),y)
    t=min(1,abs(x)/width)
    cheek=(-.068*math.exp(-((abs(x)-.650)/.185)**2-((y-.383)/.115)**2)
           +.031*math.exp(-((abs(x)-.630)/.200)**2-((y-.536)/.080)**2))
    return join+(centre-join)*math.sqrt(max(0,1-t**4))+cheek*(1-t**4)**2


def rear_z(x, y):
    join=rear_join_z(y)
    width=side_x(y,join)
    centre=profile(((.16,-2.340),(.26,-2.430),(.43,-2.509),(.59,REAR_END),
                    (.76,-2.491),(.91,-2.479),(1.07,-2.430)),y)
    recess=.061*(1-smooth((abs(x)-.26)/.17))*math.exp(-((y-.779)/.170)**4)
    t=min(1,abs(x)/width)
    return join+(centre-join)*math.sqrt(max(0,1-t**4))+recess


@lru_cache(maxsize=16384)
def end_point(front, y):
    z=front_join_z(y) if front else rear_join_z(y)
    return side_x(y,z),y,z


@lru_cache(maxsize=8192)
def front_top(x):
    edge=front_edge_top()
    t=min(1,abs(x)/edge[0])
    return .835+(edge[1]-.835)*t**6


@lru_cache(maxsize=1)
def front_edge_top():
    y=.93
    for _ in range(24):
        y=belt(front_join_z(y))
    return end_point(True,y)


@lru_cache(maxsize=8192)
def rear_top(x):
    edge=rear_edge_top()
    t=min(1,abs(x)/edge[0])
    return 1.048+(edge[1]-1.048)*t**6


@lru_cache(maxsize=1)
def rear_edge_top():
    y=1.06
    for _ in range(24):
        y=belt(rear_join_z(y))
    return end_point(False,y)


def hood_y(x,z):
    width=side_x(belt(z),z)
    t=x/max(.01,width)
    crown=.025*max(0,1-t*t)
    # The paired power domes fade before the leading edge and cowl.
    longitudinal=smooth((z-.74)/.24)*smooth((2.19-z)/.27)
    dome=.025*math.exp(-((abs(t)-.51)/.10)**2)*longitudinal
    return belt(z)+crown+dome


def hood_surface(t,v):
    edge=front_edge_top()
    width=side_x(belt(.73),.73)
    x=t*edge[0]
    leading=(x,front_top(x),front_z(x,front_top(x)))
    trailing=(t*width,hood_y(t*width,.73),.73)
    z=mix(.73,edge[2],v)
    side=(t*side_x(belt(z),z),belt(z),z)
    corners=(t*mix(width,edge[0],v),mix(belt(.73),edge[1],v),z)
    base=tuple(mix(trailing[i],leading[i],v)+side[i]-corners[i] for i in range(3))
    sculpt=(.019*max(0,1-t*t)+.025*math.exp(-((abs(t)-.52)/.115)**2))*math.sin(math.pi*v)**1.3
    return base[0],base[1]+sculpt,base[2]


def deck_width(v):
    return mix(.720,.661,smooth(v))


def deck_surface(t,v):
    x=t*deck_width(v)
    end=rear_z(x,rear_top(x))
    z=mix(-1.90,end,v)
    # Shared rear edge and a shallow integral lip, without a separate spoiler.
    cabin_width=glass_x(cab_edge(-1.90),-1.90)
    start_y=cab_surface(x/cabin_width,-1.90)[1]
    y=mix(start_y,rear_top(x),smooth(v))+.009*math.sin(math.pi*v)
    return x,y,z


def trunk_width(y):
    return profile(((.570,.495),(.620,.560),(.710,.605),(.87,.640),(1.06,.661)),y)


def door_front(y):
    return .725-.026*smooth((y-.23)/.81)


def door_middle(y):
    return -.467+.035*smooth((y-.23)/.84)


def door_back(y):
    return -1.040-.425*smooth((y-.28)/.81)


def arch_distance(y,z):
    return min(math.hypot(y-r,z-a)-.373 for a,r in zip(AXLES,(FRONT_RADIUS,REAR_RADIUS)))


def clip_polygon(polygon, fn):
    if not polygon:
        return []
    result=[]
    for a,b in zip(polygon,polygon[1:]+polygon[:1]):
        av,bv=fn(*a),fn(*b)
        if av>=-1e-10:
            result.append(a)
        if (av<0)!=(bv<0):
            lo,hi=0.,1.
            for _ in range(24):
                mid=(lo+hi)*.5
                p=(mix(a[0],b[0],mid),mix(a[1],b[1],mid))
                if (fn(*p)<0)==(av<0):
                    lo=mid
                else:
                    hi=mid
            t=(lo+hi)*.5
            result.append((mix(a[0],b[0],t),mix(a[1],b[1],t)))
    return result


_polygon_bounds={}


def polygon_distance(x,y,loop):
    key=id(loop)
    if key not in _polygon_bounds:
        _polygon_bounds[key]=(loop,min(p[0] for p in loop),max(p[0] for p in loop),
                              min(p[1] for p in loop),max(p[1] for p in loop))
    _,xmin,xmax,ymin,ymax=_polygon_bounds[key]
    outside=math.hypot(max(xmin-x,0,x-xmax),max(ymin-y,0,y-ymax))
    if outside>0:
        return outside
    inside=False
    distance=1e3
    for a,b in zip(loop,loop[1:]+loop[:1]):
        dx,dy=b[0]-a[0],b[1]-a[1]
        t=max(0,min(1,((x-a[0])*dx+(y-a[1])*dy)/max(1e-12,dx*dx+dy*dy)))
        distance=min(distance,math.hypot(x-a[0]-t*dx,y-a[1]-t*dy))
        if (a[1]>y)!=(b[1]>y) and x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:
            inside=not inside
    return -distance if inside else distance


def clipped_grid(author,name,mapper,limits,step,constraints,mat,parent=None,normal=None,solid=0):
    """Clip a fixed physical grid; never reparameterize columns at wheel arches."""
    a0,a1,b0,b1=limits
    step_a,step_b=step if isinstance(step,tuple) else (step,step)
    na,nb=math.ceil((a1-a0)/step_a),math.ceil((b1-b0)/step_b)
    vertices,faces,index=[],[],{}
    def vertex(p):
        key=(round(p[0],6),round(p[1],6))
        if key not in index:
            index[key]=len(vertices)
            vertices.append(mapper(*p))
        return index[key]
    for j in range(nb):
        for i in range(na):
            lo,hi=mix(a0,a1,i/na),mix(a0,a1,(i+1)/na)
            bottom,top=mix(b0,b1,j/nb),mix(b0,b1,(j+1)/nb)
            polygon=[(lo,bottom),(hi,bottom),(hi,top),(lo,top)]
            for fn in constraints:
                polygon=clip_polygon(polygon,fn)
                if len(polygon)<3:
                    break
            if len(polygon)>=3:
                face=[]
                for p in polygon:
                    ix=vertex(p)
                    if not face or face[-1]!=ix:
                        face.append(ix)
                if len(face)>2 and face[0]==face[-1]:
                    face.pop()
                if len(set(face))>=3:
                    faces.append(tuple(face))
    obj=author.mesh(name,vertices,faces,mat,parent,normal=normal)
    if solid:
        author.thickness(obj,solid)
        # A folded rim cannot contribute its normal to the smooth exterior skin.
        obj.data.set_sharp_from_angle(angle=math.radians(35))
    return obj,vertices,faces


def clipped_cap(author,name,front,y_range,constraints,mat,parent=None,solid=.006):
    """Sample a rounded end in angle so its side tangent is resolved evenly."""
    depth=front_z if front else rear_z
    def x_at(angle,y):
        return end_point(front,y)[0]*math.sin(angle)
    return clipped_grid(author,name,lambda angle,y:(x_at(angle,y),y,depth(x_at(angle,y),y)),
                        (-math.pi/2,math.pi/2,*y_range),(.020,.012),
                        [lambda angle,y,fn=fn:fn(x_at(angle,y),y) for fn in constraints],
                        mat,parent,(0,0,1 if front else -1),solid)


def boundary_edges(faces):
    counts={}
    oriented={}
    for face in faces:
        for a,b in zip(face,face[1:]+face[:1]):
            key=tuple(sorted((a,b)))
            counts[key]=counts.get(key,0)+1
            oriented[key]=(a,b)
    return [oriented[key] for key,count in counts.items() if count==1]


def wheelhouse_liner_outer_x(y,z):
    """Keep the fixed tub inside the four-millimetre inward body shell."""
    # Reserve half a millimetre for the straight render-mesh edge interpolation.
    limit=side_x(y,z)-.004-.0035
    blend=max(0,1-abs(.851-limit)/.008)
    return min(.851,limit)-.008*blend*blend/4
