"""P15 single-bar grille, non-AMG bumper openings and P35 optics."""
import math
from sedan_03_surfaces import (mix, profile, front_z, front_top, end_point,
                             polygon_distance, clipped_grid, clipped_cap)


def rounded_loop(cx,cy,rx,ry,power=2.8,count=96):
    points=[]
    for i in range(count):
        t=math.tau*i/count
        co,si=math.cos(t),math.sin(t)
        points.append((cx+rx*math.copysign(abs(co)**(2/power),co),
                       cy+ry*math.copysign(abs(si)**(2/power),si)))
    return points


def lamp_bounds(t):
    x=.515+.339*t
    top=front_top(x)-.012
    height=.080+.055*math.sin(math.pi*t*.86)**.60+.036*t*t
    return x,top,height


def lamp_loop(side):
    upper=[];lower=[]
    for i in range(49):
        t=i/48
        x,top,height=lamp_bounds(t)
        upper.append((side*x,top))
        lower.append((side*(x+.068*(1-t)**2+.006*t**4),top-height))
    # The inboard contour sweeps outward below its pointed upper corner.
    start,end=lower[0],upper[0]
    control=(side*(abs(end[0])+.012),end[1]-.048)
    inner=[tuple((1-t)**2*start[i]+2*t*(1-t)*control[i]+t*t*end[i] for i in range(2))
           for t in [j/24 for j in range(1,24)]]
    return upper+list(reversed(lower))+inner


def projector_layout():
    result=[]
    for t,rx,ry in [(.320,.036,.026),(.680,.049,.047)]:
        x,top,height=lamp_bounds(t)
        result.append((x,top-height*.53,rx,ry))
    return result


def rounded_point(x,y,rx,ry,angle):
    co,si=math.cos(angle),math.sin(angle)
    return (x+rx*math.copysign(abs(co)**(2/3.2),co),
            y+ry*math.copysign(abs(si)**(2/3.2),si))


def drl_outline(side):
    def upper(t,drop=.013):
        x,top,_=lamp_bounds(t)
        return side*x,top-drop
    start=upper(.195,.056)
    control=upper(.080,.039)
    end=upper(.090)
    points=[tuple((1-t)**2*start[i]+2*t*(1-t)*control[i]+t*t*end[i] for i in range(2))
            for t in [j/18 for j in range(19)]]
    points.extend(upper(mix(.090,.935,i/64)) for i in range(1,65))
    return points


def build_front(c):
    a,root=c['a'],c['root']
    paint,black,seal,chrome=c['paint'],c['black'],c['seal'],c['chrome']
    grille=rounded_loop(0,.669,.539,.148,3.05)
    # The lower opening is continuous behind the plate, with raised outer cheeks.
    upper=((0,.430),(.25,.429),(.45,.449),(.64,.479),(.77,.480),(.85,.441),(.867,.396))
    lower=((0,.263),(.30,.267),(.45,.283),(.58,.321),(.72,.285),(.82,.290),(.867,.365))
    intake=[(x,profile(upper,abs(x))) for x in [mix(-.867,.867,i/144) for i in range(145)]]
    intake.extend((x,profile(lower,abs(x))) for x in [mix(.867,-.867,i/144) for i in range(145)])
    intake=[(math.copysign(min(abs(x),end_point(True,y)[0]-.009),x),y) for x,y in intake]
    cheeks=[]
    for side in [-1,1]:
        loop=[]
        for i in range(112):
            t=math.tau*i/112
            x=.656+.191*math.copysign(abs(math.cos(t))**.80,math.cos(t))
            y=.382+.091*math.sin(t)+.008*math.cos(t)
            x=min(x,end_point(True,y)[0]-.015)
            loop.append((side*x,y))
        cheeks.append(loop)
    lamps=[lamp_loop(side) for side in [-1,1]]
    holes=[grille,intake]+lamps
    conditions=[lambda x,y: end_point(True,y)[0]-abs(x),lambda x,y: front_top(x)-y]
    conditions.extend(lambda x,y,loop=loop: polygon_distance(x,y,loop) for loop in holes)
    clipped_cap(a,'FrontBumperSkin',True,(.172,.99),conditions,paint)

    def recess(name,loop,depth,mat,edge_mat=paint):
        cx=sum(x for x,y in loop)/len(loop);cy=sum(y for x,y in loop)/len(loop)
        vertices=[(x,y,front_z(x,y)) for x,y in loop]+[(x,y,front_z(x,y)-depth) for x,y in loop]
        n=len(loop)
        a.mesh(name+'Return',vertices,[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)],edge_mat,normal=(0,0,1))
        clipped_grid(a,name+'DarkCavity',lambda x,y:(x,y,front_z(x,y)-depth),
                     (min(x for x,y in loop),max(x for x,y in loop),min(y for x,y in loop),max(y for x,y in loop)),
                     .012,[lambda x,y:-polygon_distance(x,y,loop)],mat,normal=(0,0,1),solid=.006)
        return cx,cy

    recess('MainGrille',grille,.048,black,black)
    a.curve('GrilleChromePerimeter',[(x,y,front_z(x,y)+.002) for x,y in grille],.0060,chrome,cyclic=True)
    # Fine dark blades remain secondary to the single horizontal bright wing.
    for i in range(47):
        x=-.510+i*.0222
        ys=[.528+j*.002 for j in range(142) if polygon_distance(x,.528+j*.002,grille)<-.008]
        if not ys:
            continue
        a.curve('GrilleBlade',[(x,y,front_z(x,y)-.022) for y in [mix(min(ys),max(ys),k/12) for k in range(13)]],.0028,c['dark_metal'])
    for side in [-1,1]:
        a.surface('SingleChromeWing',lambda u,v,side=side:(
            side*mix(.107,.514,u),.663+(v-.5)*mix(.037,.014,u)+.009*u,
            front_z(side*mix(.107,.514,u),.663)-.001+.010*math.sin(math.pi*v)),
            48,6,chrome,solid=.005,normal=(0,0,1))
    recess('LowerIntake',intake,.037,black,black)
    for y in [.298,.327,.353]:
        xs=[-.55+i*.011 for i in range(101) if polygon_distance(-.55+i*.011,y,intake)<-.006]
        a.curve('LowerAirBlade',[(x,y,front_z(x,y)-.023) for x in xs],.0028,black)
    for loop in cheeks:
        cx=sum(x for x,y in loop)/len(loop)
        for row in range(10):
            y=.325+row*.017
            for col in range(19):
                x=cx-.15+col*.017+(row%2)*.0085
                hexagon=[(x+.009*math.cos(math.tau*k/6),y+.007*math.sin(math.tau*k/6)) for k in range(6)]
                if all(polygon_distance(xx,yy,loop)<-.005 and polygon_distance(xx,yy,intake)<-.006 for xx,yy in hexagon):
                    a.curve('IntakeMesh',[(xx,yy,front_z(xx,yy)-.019) for xx,yy in hexagon],.0011,c['dark_metal'],cyclic=True)
        a.curve('SideIntakeCentreBlade',[(cx-.10+i*.20/36,.402,front_z(cx-.10+i*.20/36,.402)-.010) for i in range(37)],.004,black)
    # Curved lower valance and the narrow Study chrome trim follow the face.
    a.curve('FrontLowerChrome',[(x,.229+.016*(abs(x)/.8)**2,front_z(x,.229)+.002) for x in [mix(-.805,.805,i/96) for i in range(97)]],.0042,chrome)
    a.box('FrontPlate',(0,.400,front_z(0,.40)+.018),(.465,.107,.015),c['plate'],radius=.007)

    for side,loop in zip([-1,1],lamps):
        recess('HeadlampHousing',loop,.058,black,black)
        a.curve('HeadlampGasket',[(x,y,front_z(x,y)+.001) for x,y in loop],.0028,seal,cyclic=True)
        # Three-dimensional chrome cups surround recessed convex optical lenses.
        for cx,cy,rx,ry in projector_layout():
            cx*=side
            def cup(u,v,cx=cx,cy=cy,rx=rx,ry=ry):
                scale=mix(.57,1,v)
                x,y=rounded_point(cx,cy,rx*scale,ry*scale,math.tau*u)
                return x,y,front_z(x,y)-mix(.044,.010,v**.72)
            a.surface('P35ReflectorCup',cup,56,9,chrome,normal=(0,0,1))
            outer=[rounded_point(cx,cy,rx,ry,math.tau*i/72) for i in range(72)]
            a.curve('P35OpticalSurround',[(x,y,front_z(x,y)-.009) for x,y in outer],.0028,c['dark_metal'],cyclic=True)
            def optic(u,v,cx=cx,cy=cy,rx=rx,ry=ry):
                x,y=rounded_point(cx,cy,rx*.62*v,ry*.62*v,math.tau*u)
                return x,y,front_z(x,y)-.030+.008*(1-v*v)
            a.surface('P35ConvexLens',optic,48,8,c['head'],normal=(0,0,1))
        for t in [.54,.65,.76,.87]:
            cx,top,height=lamp_bounds(t)
            cy=top-height+.016
            points=[(side*(cx+dx),cy+dy) for dx,dy in [(-.011,-.006),(.011,-.006),(.009,.010),(-.009,.010)]]
            a.mesh('P35LowerReflectorFacet',[(x,y,front_z(x,y)-(.034 if i<2 else .018)) for i,(x,y) in enumerate(points)],
                   [(0,1,2,3)],chrome,normal=(0,0,1))
        eyebrow=[(x,y,front_z(x,y)-.007) for x,y in drl_outline(side)]
        a.curve('P35DrlChromeSurround',[(x,y,z-.001) for x,y,z in eyebrow],.0060,chrome)
        a.curve('P35UpperBrow',eyebrow,.0040,c['head'])
        marker_x=side*.675;marker_y=front_top(marker_x)-.082
        marker=rounded_loop(marker_x,marker_y,.009,.020,3,48)
        a.curve('P35CentreMarkerBezel',[(x,y,front_z(x,y)-.014) for x,y in marker],.0024,chrome,cyclic=True)
        a.surface('sedan_03SingleLightPoint',lambda u,v:(lambda p:(p[0],p[1],front_z(*p)-.019))(
                  rounded_point(marker_x,marker_y,.005*v,.015*v,math.tau*u)),32,5,c['head'],normal=(0,0,1))
        signal=c['signal_left'] if side==1 else c['signal_right']
        a.curve('FrontIndicator',[(p[0],p[1]-.009,p[2]-.002) for p in eyebrow[15:]],.0025,signal)
        clipped_grid(a,'HeadlampClearCover',lambda x,y:(x,y,front_z(x,y)+.001),
                     (min(x for x,y in loop),max(x for x,y in loop),min(y for x,y in loop),max(y for x,y in loop)),
                     .014,[lambda x,y,loop=loop:-polygon_distance(x,y,loop)],c['lens'],normal=(0,0,1))
