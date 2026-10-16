"""Study split waterdrop lamps, movable plated deck and rounded Study valance."""
import math
from sedan_03_surfaces import (mix,smooth,belt,side_x,glass_x,cab_edge,cab_surface,rear_z,rear_top,rear_edge_top,end_point,deck_surface,
                             trunk_width,polygon_distance,clipped_grid,clipped_cap)


def tail_bounds(t):
    x=.294+.579*t
    top=.990+.021*math.sin(math.pi*t*.70)
    low=.979-.145*math.sin(math.pi*t*.84)**.65
    return x,top,low


def tail_loop(side):
    upper=[];lower=[]
    for i in range(73):
        t=i/72
        x,top,low=tail_bounds(t)
        upper.append((side*x,top))
        lower.append((side*(x-.010*t**4),low))
    return upper+list(reversed(lower))


def build_rear(c):
    a,root,trunk=c['a'],c['root'],c['trunk']
    paint,seal,chrome,black=c['paint'],c['seal'],c['chrome'],c['black']
    loops=[tail_loop(side) for side in [-1,1]]
    def moving(x,y,gap=0):
        return min(y-.582-gap,trunk_width(y)-abs(x)-gap)
    holes=[lambda x,y,loop=loop:polygon_distance(x,y,loop) for loop in loops]
    conditions=[lambda x,y:end_point(False,y)[0]-abs(x),lambda x,y:rear_top(x)-y]
    clipped_cap(a,'RearBumperAndFixedQuarter',False,(.177,1.066),
                conditions+holes+[lambda x,y:-moving(x,y,-.0015)],paint)
    clipped_cap(a,'MovingTrunkFascia',False,(.582,1.065),
                conditions+holes+[lambda x,y:moving(x,y,.0025)],paint,trunk)
    a.surface('TrunkDeck',lambda u,v:deck_surface(2*u-1,v),66,36,paint,trunk,solid=.006,normal=(0,1,-.10))
    for side in [-1,1]:
        def shoulder(u,v,side=side):
            inner=deck_surface(side,v)
            edge=rear_edge_top()
            outer_z=mix(-1.90,edge[2],v)
            outer_y=belt(outer_z)
            outer=(side*side_x(outer_y,outer_z),outer_y,outer_z)
            base=tuple(mix(inner[i],outer[i],u) for i in range(3))
            inner_end=deck_surface(side,1)
            end=tuple(mix(inner_end[i],(side*edge[0],edge[1],edge[2])[i],u) for i in range(3))
            target=(end[0],rear_top(end[0]),rear_z(end[0],rear_top(end[0])))
            cabin_width=glass_x(cab_edge(-1.90),-1.90)
            start_inner=deck_surface(side,0)
            start_x=mix(start_inner[0],side*cabin_width,u)
            start_y=mix(start_inner[1],belt(-1.90),u)
            start_correction=cab_surface(start_x/cabin_width,-1.90)[1]-start_y
            return tuple(base[i]+(target[i]-end[i])*smooth(v)**4+(start_correction*(1-v)**2 if i==1 else 0) for i in range(3))
        a.surface('RearDeckShoulder',shoulder,18,44,paint,solid=.006,normal=(side,.7,-.1))
        line=[deck_surface(side,i/60) for i in range(61)]
        a.curve('DeckSideSeal',[(x-side*.004,y-.010,z) for x,y,z in line],.0035,seal)
        # Outer fixed lamps and inner moving lamps use exactly the same depth field.
        loop=tail_loop(side)
        for moving_lamp,parent in [(False,root),(True,trunk)]:
            seam=(lambda x,y:moving(x,y,.0025)) if moving_lamp else (lambda x,y:-moving(x,y,-.0015))
            bounds=(min(x for x,y in loop),max(x for x,y in loop),min(y for x,y in loop),max(y for x,y in loop))
            clipped_grid(a,'TailBlackCarrier',lambda x,y:(x,y,rear_z(x,y)+.030),bounds,.009,
                         [lambda x,y:-polygon_distance(x,y,loop),seam],black,parent,(0,0,-1),solid=.006)
            # Thick clear-red housing, with red optics separately layered ahead of it.
            clipped_grid(a,'TailRedLens',lambda x,y:(x,y,rear_z(x,y)+.005),bounds,.011,
                         [lambda x,y:-polygon_distance(x,y,loop),seam],c['red_lens'],parent,(0,0,-1))
            outline=[]
            for x,y in loop:
                if seam(x,y)>=0:
                    outline.append((x,y,rear_z(x,y)+.002))
                elif len(outline)>1:
                    a.curve('TailLampSeal',outline,.0028,seal,parent)
                    outline=[]
            if len(outline)>1:
                a.curve('TailLampSeal',outline,.0028,seal,parent)
            def optic(u,v):
                xx,top,low=tail_bounds(.045+.91*u)
                return side*xx,mix(low,top,.14+.72*v)
            # Repeated diagonal crystalline cells live within the continuous taper.
            for i in range(20):
                t0=(i+.3)/20;t1=(i+.9)/20
                cell=[]
                for u,v in [(t0,.68),(t1,.68),(t1+.011,.37),(t0+.011,.35)]:
                    x,y=optic(u,v)
                    if seam(x,y)<.001 or polygon_distance(x,y,loop)>-.006:
                        break
                    cell.append((x,y,rear_z(x,y)-.001))
                if len(cell)==4:
                    a.mesh('TailOpticalCell',cell,[(0,1,2,3)],c['tail'],parent,normal=(0,0,-1))
            for lower in [False,True]:
                coords=[]
                for i in range(100):
                    t=.04+.92*i/99
                    xx,top,low=tail_bounds(t)
                    x=side*xx
                    y=mix(low,top,.14 if lower else .86)
                    if seam(x,y)>.003:
                        coords.append((x,y,rear_z(x,y)-.001))
                    elif len(coords)>1:
                        a.curve('TailGuide',coords,.0029,c['tail'],parent);coords=[]
                if len(coords)>1:
                    a.curve('TailGuide',coords,.0029,c['tail'],parent)
            signal=c['signal_left'] if side==1 else c['signal_right']
            coords=[]
            for i in range(80):
                t=.07+.86*i/79
                xx,top,low=tail_bounds(t)
                x=side*xx;y=mix(low,top,.60)
                if seam(x,y)>.006:
                    coords.append((x,y,rear_z(x,y)-.0015))
            if len(coords)>1:
                a.curve('RearIndicator',coords,.0024,signal,parent)
        # Thin passive reflector is part of the fixed bumper, not the lamp circuit.
        a.surface('RearReflector',lambda u,v,side=side:(side*mix(.500,.790,u),
                  .440+(v-.5)*(.012+.010*math.sin(math.pi*u)),rear_z(side*mix(.500,.790,u),.44)-.003),
                  40,5,c['reflector'],normal=(0,0,-1))
        a.curve('RearReflectorChrome',[(side*mix(.49,.80,t),.426,rear_z(side*mix(.49,.80,t),.426)-.004) for t in [i/48 for i in range(49)]],.0025,chrome)

    # Lower valance has a broad rolled silver edge and two rounded decorative outlets.
    a.surface('LowerRearValance',lambda u,v:(
        (2*u-1)*end_point(False,mix(.19,.304,v))[0]*.984,mix(.19,.304,v),
        rear_z((2*u-1)*end_point(False,mix(.19,.304,v))[0]*.984,mix(.19,.304,v))-.002),
        90,15,c['dark_metal'],normal=(0,0,-1),solid=.011)
    a.curve('ValanceSilverRibbon',[(x,.248+.006*(1-(x/.77)**2),rear_z(x,.248)-.005)
                                  for x in [mix(-.775,.775,i/100) for i in range(101)]],.010,chrome)
    for side in [-1,1]:
        outlet=[]
        for i in range(96):
            t=math.tau*i/96
            x=side*.629+.125*math.cos(t)
            y=.230+.033*math.sin(t)+.011*side*math.cos(t)
            outlet.append((x,y))
        clipped_grid(a,'DecorativeOutletDark',lambda x,y:(x,y,rear_z(x,y)-.014),
                     (side*.629-.128,side*.629+.128,.18,.279),.008,
                     [lambda x,y,loop=outlet:-polygon_distance(x,y,loop)],black,normal=(0,0,-1))
        a.curve('RoundedExhaustFinisher',[(x,y,rear_z(x,y)-.018) for x,y in outlet],.006,chrome,cyclic=True)
    plate_y=.739
    a.box('RearPlate',(0,plate_y,rear_z(0,plate_y)-.010),(.465,.108,.014),c['plate'],trunk,radius=.006)
    for side in [-1,1]:
        for x in [side*.277,side*.746]:
            c['ring_z']('RearParkSensor',(x,.467,rear_z(x,.467)-.001),.008,.0011,seal)

    # Liner, weatherstrip and cargo walls all follow the current deck/rear field.
    a.surface('TrunkDeckLiner',lambda u,v:(lambda p:(p[0]*.956,p[1]-.032,p[2]+.004))(
              deck_surface(2*u-1,.045+.90*v)),54,30,c['carpet'],trunk,solid=.009,normal=(0,-1,0))
    clipped_grid(a,'TrunkRearLiner',lambda x,y:(x,y,rear_z(x,y)+.038),
                 (-.655,.655,.614,1.044),.020,[lambda x,y:moving(x,y,.029)],c['carpet'],trunk,(0,0,1),solid=.011)
    a.box('TrunkPullHandle',(0,.674,rear_z(0,.674)+.055),(.117,.028,.025),black,trunk,radius=.012)
    a.box('CargoFloor',(0,.386,-1.948),(1.26,.029,.904),c['carpet'],radius=.027)
    a.box('CargoFrontWall',(0,.682,-1.492),(1.28,.589,.040),c['carpet'],radius=.035)
    for side in [-1,1]:
        a.surface('CargoSideWall',lambda u,v,side=side:(
            side*(.650-.060*math.sin(math.pi*u)),mix(.390,1.034,v),
            mix(-1.505,rear_z(side*(.650-.060*math.sin(math.pi*u)),mix(.390,1.034,v))+.053,u)),
            38,26,c['carpet'],solid=.014,normal=(-side,0,0))
        a.curve('GooseneckHinge',[(side*.567,1.049,-1.886),(side*.570,.907,-1.975),
                                 (side*.563,.821,-1.979),(side*.558,.799,-1.860)],.013,c['inner_paint'],trunk,bezier=True)
        line=[]
        for i in range(61):
            y=mix(.599,1.040,i/60);x=side*(trunk_width(y)-.008)
            line.append((x,y,rear_z(x,y)+.020))
        a.curve('TrunkSideWeatherstrip',line,.007,seal)
    a.curve('TrunkBottomWeatherstrip',[(x,.590,rear_z(x,.59)+.018) for x in [mix(-.527,.527,i/64) for i in range(65)]],.008,seal)
    a.surface('CargoSill',lambda u,v:(
        mix(-.532,.532,u),mix(.416,.583,v),rear_z(mix(-.532,.532,u),.59)+.040),
        44,12,c['carpet'],solid=.018,normal=(0,0,1))
    return [0,-.257,-.596]
