"""Vehicle roof-hinged hatch, cargo opening and independent high L-shaped lamps."""
import math


def build_rear(c):
    a,root=c['author'],c['root']
    mix,profile,samples,strip=c['mix'],c['profile'],c['samples'],c['strip']
    paint,black,chrome=c['paint'],c['black'],c['chrome']

    def gate_width(y):
        return profile([(.565,.760),(.625,.818),(.85,.839),(1.13,.843),(1.27,.807),(1.50,.741),(1.575,.690)],y)

    def rear_z(x,y):
        center=profile([(.205,-2.250),(.300,-2.346),(.46,-2.360),(.58,-2.311),(.70,-2.298),
                        (.87,-2.274),(1.00,-2.285),(1.18,-2.233),(1.31,-2.115),(1.575,-1.846)],y)
        return center + .058*(abs(x)/.91)**4

    def rounded_bridge(side,y,z_side,side_width,face_width):
        start=(side*side_width,y,z_side)
        end=(side*face_width,y,rear_z(face_width,y))
        controls=[start,(start[0],y,end[2]+.030),(end[0]+side*.037,y,end[2]),end]
        return lambda t:tuple((1-t)**3*controls[0][i]+3*(1-t)**2*t*controls[1][i]
                              +3*(1-t)*t*t*controls[2][i]+t**3*controls[3][i] for i in range(3))

    def mapped_band(label,outer,inner,mapper,material,parent,offset=.020):
        # Each short quad is reprojected onto the curved lens carrier.
        for i,p in enumerate(outer):
            q=outer[(i+1)%len(outer)]
            r,s=inner[i],inner[(i+1)%len(inner)]
            def fn(u,v,p=p,q=q,r=r,s=s):
                uv=(mix(mix(p[0],q[0],u),mix(r[0],s[0],u),v),
                    mix(mix(p[1],q[1],u),mix(r[1],s[1],u),v))
                point=mapper(*uv)
                return point[0],point[1],point[2]-offset
            a.surface(label,fn,18,4,material,parent,.005,(0,0,-1))

    def hatch_recess(x,y):
        return .054*math.exp(-(x/.37)**6)*math.exp(-((y-.986)/.116)**6)

    def gate(u,v):
        y=mix(.569,1.574,v)
        x=(2*u-1)*gate_width(y)
        # The licence depression occupies the painted hatch, not a surface-mounted plate.
        depression=hatch_recess(x,y)
        return x,y,rear_z(x,y)+depression

    pivot=(0,1.567,-1.849)
    hatch=a.group('trunk',pivot,root)
    def tail_lower(x):
        return profile([(0,1.209),(.400,1.209),(.526,1.088),(.839,1.078)],abs(x))
    # Shared boundaries divide the lower hatch, horizontal inner lamps and glazing.
    def hatch_patch(label,y0,y1,x0,x1,material,solid=.019):
        def fn(u,v):
            y=mix(y0,y1,v)
            x=mix(x0(y),x1(y),u)
            dep=hatch_recess(x,y)
            return x,y,rear_z(x,y)+dep
        return a.surface(label,fn,60,32,material,hatch,solid,(0,0,-1))
    def hatch_lower(u,v):
        top_x=(2*u-1)*gate_width(1.12)
        for _ in range(5):
            top_x=(2*u-1)*gate_width(tail_lower(top_x))
        y=mix(.569,tail_lower(top_x),v)
        x=(2*u-1)*gate_width(y)
        depression=hatch_recess(x,y)
        return x,y,rear_z(x,y)+depression
    a.surface('HatchLower',hatch_lower,100,48,paint,hatch,.019,(0,0,-1))
    hatch_patch('HatchLampBrow',1.209,1.239,lambda y:-gate_width(y),gate_width,paint)
    hatch_patch('RearGlass',1.239,1.554,lambda y:-gate_width(y)+.011,lambda y:gate_width(y)-.011,c['glass'],.005)
    hatch_patch('HatchTopFrame',1.554,1.574,lambda y:-gate_width(y),gate_width,black,.023)
    for side in [-1,1]:
        hatch_patch('RearGlassSide',1.239,1.554,
                    lambda y,side=side:side*(gate_width(y)-.011),lambda y,side=side:side*gate_width(y),black,.017)
        # Horizontal inner lamps travel with the complete hatch; their aperture is native.
        def inner_lamp(u,v,side=side):
            x=side*mix(.407,gate_width(1.12)-.005,u)
            y=mix(tail_lower(x)+.003,1.205,v)
            for _ in range(5):
                x=side*mix(.407,gate_width(y)-.005,u)
                y=mix(tail_lower(x)+.003,1.205,v)
            return x,y,rear_z(x,y)+.016
        a.surface('InnerTailCavity',inner_lamp,42,15,c['redlens'],hatch,.023,(0,0,-1))
        mapped_band('InnerTailPerimeter',[(.03,.06),(.98,.06),(.98,.94),(.03,.94)],
                    [(.10,.23),(.91,.23),(.91,.82),(.10,.82)],inner_lamp,c['tail'],hatch)
        mapped_band('InnerTailRedCell',[(.61,.23),(.90,.23),(.91,.80),(.64,.80)],
                    [(.68,.37),(.83,.37),(.84,.68),(.70,.68)],inner_lamp,c['tail'],hatch,.023)
        a.surface('InnerTailClearTrapezoid',lambda u,v:(lambda p:(p[0],p[1],p[2]-.013))
                  (inner_lamp(mix(mix(.14,.10,v),mix(.51,.55,v),u),mix(.42,.78,v))),
                  25,10,chrome,hatch,.005,(0,0,-1))
        for row in range(5):
            a.surface('InnerTailClearPrism',lambda u,v,row=row:(lambda p:(p[0],p[1],p[2]-.017))
                      (inner_lamp(mix(.15,.52,u),.44+.065*row+.012*v)),
                      24,2,c['lens'],hatch,.002,(0,0,-1))
        a.surface('InnerTailCover',lambda u,v:(lambda p:(p[0],p[1],p[2]-.022))(inner_lamp(u,v)),
                  42,15,c['lens'],hatch,.002,(0,0,-1))

    # Fixed D-pillar surfaces and the vertical light housing share a parametric boundary.
    for side,suffix in [(1,'Left'),(-1,'Right')]:
        def d_pillar(u,v,side=side):
            y=mix(1.176,1.575,v)
            z_side=profile([(0,c['rear_side_end'](1.176)),(.20,-1.990),(.55,-1.803),(1,-1.720)],v)
            width=c['glass_x'](z_side,y)
            lower_z=c['rear_side_end'](1.176)
            width+=((c['side_x'](lower_z,1.176)-c['glass_x'](lower_z,1.176))
                    *(1-c['smoothstep'](v/.15)))
            return rounded_bridge(side,y,z_side,width,gate_width(y)+.013)(u)
        def window_boundary(y,side=side):
            lower=c['quarter_glass_point'](side,0,0)
            upper=c['quarter_glass_point'](side,0,1)
            shoulder_y=c['belt'](lower[2])
            if y<shoulder_y:
                start=d_pillar(0,0)
                end=(side*c['side_x'](lower[2],shoulder_y),shoulder_y,lower[2])
                return c['blend'](start,end,(y-1.176)/(shoulder_y-1.176))
            if y<lower[1]:
                start=(side*c['side_x'](lower[2],shoulder_y),shoulder_y,lower[2])
                return c['blend'](start,lower,(y-shoulder_y)/(lower[1]-shoulder_y))
            if y>upper[1]:
                return c['blend'](upper,d_pillar(0,1),(y-upper[1])/(1.575-upper[1]))
            low,high=0.,1.
            for _ in range(30):
                t=(low+high)/2
                if c['quarter_glass_point'](side,0,t)[1]<y:low=t
                else:high=t
            return c['quarter_glass_point'](side,0,(low+high)/2)
        # The painted D-pillar spans the actual glazing edge to the lamp carrier.
        # Its two edges are sampled from their source surfaces, including the shoulder.
        a.surface('DPillarWindowReturn'+suffix,
                  lambda u,v:c['blend'](window_boundary(mix(1.176,1.575,v)),d_pillar(0,v),u),
                  12,86,paint,solid=.019,normal=(side,0,-.25))
        for label,u0,u1,v0,v1 in [('Outer',0,.26,0,1),('Inner',.82,1,0,1),
                                  ('Top',.26,.82,.93,1)]:
            a.surface('DPillar'+suffix+label,lambda u,v,u0=u0,u1=u1,v0=v0,v1=v1:d_pillar(mix(u0,u1,u),mix(v0,v1,v)),
                      18,40,paint,solid=.021,normal=(side,0,-.8))
        def vertical_lamp(u,v):
            p=d_pillar(mix(.262,.818,u),mix(0,.928,v))
            return p[0]-side*.008,p[1],p[2]+.008
        a.surface('VerticalTailHousing'+suffix,vertical_lamp,18,55,c['redlens'],solid=.020,normal=(side,0,-.8))
        a.surface('VerticalTailGuide'+suffix,lambda u,v:(lambda p:(p[0],p[1],p[2]-.004))
                  (d_pillar(mix(.335,.558,u),mix(0,.913,v))),12,60,c['tail'],solid=.005,normal=(side,0,-.8))
        a.surface('VerticalTailCover'+suffix,lambda u,v:(lambda p:(p[0]+side*.010,p[1],p[2]-.012))(vertical_lamp(u,v)),
                  20,55,c['lens'],solid=.002,normal=(side,0,-.8))
        # Broad quarter-to-tail corner is a round curve with a native lamp-sized upper gap.
        def corner(u,v):
            y=mix(.566,1.176,v)
            z_side=c['rear_side_end'](y)
            return rounded_bridge(side,y,z_side,c['side_x'](z_side,y),gate_width(y)+.013)(u)
        def optical_layer(u,v,distance):
            p=corner(u,v)
            lo,hi=max(0,u-.0001),min(1,u+.0001)
            pu,pv=corner(hi,v),corner(lo,v)
            du=tuple(pu[i]-pv[i] for i in range(3))
            lo,hi=max(0,v-.0001),min(1,v+.0001)
            pu,pv=corner(u,hi),corner(u,lo)
            dv=tuple(pu[i]-pv[i] for i in range(3))
            normal=(du[1]*dv[2]-du[2]*dv[1],du[2]*dv[0]-du[0]*dv[2],du[0]*dv[1]-du[1]*dv[0])
            length=math.sqrt(sum(value*value for value in normal))
            direction=1 if side*normal[0]-normal[2]>0 else -1
            return tuple(p[i]+distance*direction*normal[i]/length for i in range(3))
        a.surface('RearCorner'+suffix,lambda u,v:corner(u,mix(0,.835,v)),38,38,paint,solid=.021,normal=(side,0,-.7))
        a.surface('OuterTailHousing'+suffix,lambda u,v:(lambda p:(p[0]-side*.005,p[1],p[2]+.009))(corner(u,mix(.84,1,v))),
                  38,15,c['redlens'],solid=.022,normal=(side,0,-.7))
        # The lower red elbow turns around the quarter in one projected polygon band.
        mapped_band('OuterTailFold'+suffix,
                    [(.015,.858),(.48,.845),(.98,.858),(.98,1),(.43,1),(.015,.965)],
                    [(.10,.883),(.49,.871),(.90,.884),(.90,.957),(.43,.959),(.10,.941)],
                    corner,c['tail'],root,.004)
        a.surface('OuterTailClear'+suffix,lambda u,v:optical_layer(mix(.43,.955,u),mix(.888,.954,v),.006),
                  24,8,chrome,solid=.004,normal=(side,0,-.7))
        signal=c['signal_left'] if side==1 else c['signal_right']
        a.surface('RearTurnSignal'+suffix,lambda u,v:optical_layer(mix(.45,.94,u),mix(.897,.925,v),.008),
                  24,4,signal,solid=.003,normal=(side,0,-.7))
        a.surface('OuterTailCover'+suffix,lambda u,v:optical_layer(u,mix(.84,1,v),.014),
                  40,15,c['lens'],solid=.002,normal=(side,0,-.7))

    # Rear bumper has a broad crown, painted angular lower platform and inset outlets.
    def bumper_width(y):
        return profile([(.215,.834),(.32,.857),(.43,.859),(.566,gate_width(.566)+.013)],y)
    def bumper(u,v):
        y=mix(.215,.566,v)
        x=(2*u-1)*bumper_width(y)
        z=rear_z(x,y)+.020*math.exp(-((y-.298)/.057)**2)*math.exp(-((abs(x)-.52)/.24)**4)
        return x,y,z
    a.surface('RearBumper',bumper,100,42,paint,solid=.026,normal=(0,0,-1))
    for side,suffix in [(1,'Left'),(-1,'Right')]:
        a.surface('BumperSide'+suffix,
                  lambda u,v,side=side:(lambda y:rounded_bridge(side,y,-2.108,c['side_x'](-2.108,y),bumper_width(y))(u))
                  (mix(.215,.566,v)),40,32,paint,solid=.02,normal=(side,0,-.4))
        a.curve('RearReflector'+suffix,samples(lambda t,side=side:(side*mix(.579,.826,t),.465,rear_z(side*mix(.579,.826,t),.465)-.005),40),
                .009,c['reflector'])
        # Rounded trapezoidal outlet trim, with real depth into a black pocket.
        coords=[(.606,.253),(.625,.325),(.843,.325),(.825,.246)]
        outline=[]
        for i,p in enumerate(coords):
            q=coords[(i+1)%len(coords)]
            outline+=samples(lambda t,p=p,q=q,side=side:(side*mix(p[0],q[0],t),mix(p[1],q[1],t),
                                                        rear_z(side*mix(p[0],q[0],t),mix(p[1],q[1],t))-.006),14)[:-1]
        a.curve('OutletChrome'+suffix,outline,.010,chrome,cyclic=True)
        a.surface('OutletDark'+suffix,lambda u,v,side=side:(side*mix(.626,.825,u),mix(.262,.315,v),
                    rear_z(side*mix(.626,.825,u),mix(.262,.315,v))-.005),24,12,black,solid=.015,normal=(0,0,-1))
    for x in [-.36,-.18,0,.18,.36]:
        a.box('RearLowerFin',(x,.24,-2.286),(.012,.047,.054),paint,radius=.004)

    # Continuous deep cargo collar and molded wheel housings remain fixed when the hatch opens.
    perimeter=[]
    for i in range(65):
        y=mix(.588,1.563,i/64);perimeter.append((gate_width(y)-.032,y,rear_z(gate_width(y),y)+.034))
    for i in range(49):
        x=mix(gate_width(1.563)-.032,-gate_width(1.563)+.032,i/48);perimeter.append((x,1.563,rear_z(x,1.563)+.034))
    for i in range(65):
        y=mix(1.563,.588,i/64);perimeter.append((-gate_width(y)+.032,y,rear_z(gate_width(y),y)+.034))
    for i in range(49):
        x=mix(-gate_width(.588)+.032,gate_width(.588)-.032,i/48);perimeter.append((x,.588,rear_z(x,.588)+.034))
    n=len(perimeter)
    verts=perimeter+[(p[0]*.968,p[1]+(.018 if p[1]<.7 else -.018),p[2]+.098) for p in perimeter]
    collar=a.mesh('CargoOpeningCollar',verts,[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)],c['innerpaint'])
    a.thickness(collar,.018)
    a.curve('CargoWeatherSeal',[(p[0],p[1],p[2]+.023) for p in perimeter],.009,c['seal'],cyclic=True)
    a.box('CargoFloor',(0,.587,-1.795),(1.42,.057,.842),c['lining'],radius=.025)
    a.box('CargoSill',(0,.605,-2.210),(1.421,.04,.097),black,radius=.018)
    for side in [-1,1]:
        c['ellipsoid']('CargoWheelHouse',(side*.704,.719,-1.610),(.192,.228,.401),c['lining'])
        a.box('CargoSideWall',(side*.775,.852,-1.938),(.100,.48,.415),c['lining'],radius=.046)
        a.curve('CargoStrut',[(side*.759,1.05,-2.137),(side*.714,1.477,-1.92)],.014,black)
        a.curve('StrutPiston',[(side*.714,1.477,-1.92),(side*.687,1.538,-1.86)],.007,chrome)
        a.box('TailHinge',(side*.488,1.558,-1.837),(.102,.035,.078),c['innerpaint'],radius=.008)
    # Molded inner hatch skin follows its exterior instead of hanging as a flat black card.
    a.surface('HatchInnerLiner',lambda u,v:(lambda p:(p[0]*.946,p[1]+.015,p[2]+.057+.013*math.sin(math.pi*v)))
              (gate(.036+.928*u,.018+.591*v)),58,38,black,hatch,.019,normal=(0,0,1))
    liner_edge=samples(lambda t:(lambda p:(p[0]*.946,p[1]+.015,p[2]+.057))(gate(.036+.928*t,.018)),65)
    liner_edge+=samples(lambda t:(lambda p:(p[0]*.946,p[1]+.015,p[2]+.057))(gate(.964,.018+.591*t)),35)
    liner_edge+=samples(lambda t:(lambda p:(p[0]*.946,p[1]+.015,p[2]+.057))(gate(.964-.928*t,.609)),65)
    liner_edge+=samples(lambda t:(lambda p:(p[0]*.946,p[1]+.015,p[2]+.057))(gate(.036,.609-.591*t)),35)
    a.curve('HatchLinerRim',liner_edge,.012,black,hatch,cyclic=True)
    a.box('HatchPullPocket',(.45,.691,-2.211),(.125,.048,.028),c['seal'],hatch,radius=.013)
    # Spoiler, brake strip and wiper are attached to the moving upper hatch.
    a.surface('TailSpoiler',lambda u,v:((2*u-1)*.771,mix(1.600,1.568,v)+.017*(1-(2*u-1)**2),mix(-1.762,-1.995,v)),
              54,18,black,hatch,.025,normal=(0,1,-.25))
    a.curve('HighBrakeLamp',samples(lambda t:(mix(-.319,.319,t),1.579,-1.984),48),.007,c['tail'],hatch)
    a.curve('RearWiper',[(.03,1.254,-2.239),(.118,1.276,-2.211),(.458,1.276,-2.211)],.010,black,hatch)
    a.box('RearPlate',(0,.986,rear_z(0,.986)+hatch_recess(0,.986)-.014),
          (.435,.162,.018),black,hatch,radius=.008)
    return hatch,[0,.900-pivot[1],-2.286-pivot[2]]
