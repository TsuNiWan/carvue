"""P14 black Study cabin and the visible four-door aperture structures."""
import math
from sedan_03_surfaces import (mix,belt,side_x,glass_x,cab_surface,window_top,arch_distance,
                             clipped_grid,door_front,door_middle,door_back,boundary_edges,interior_outer_limit)


def build_cabin(c):
    a,root=c['a'],c['root']
    black,seal,chrome=c['black'],c['seal'],c['chrome']
    leather,carpet,wood=c['leather'],c['carpet'],c['wood']
    a.box('CabinFloor',(0,.242,-.430),(1.50,.046,2.590),carpet,radius=.026)
    a.box('Firewall',(0,.607,.624),(1.47,.702,.070),black,radius=.055)
    a.box('CentreTunnel',(0,.307,-.430),(.262,.12,2.27),black,radius=.034)
    a.box('DashboardTop',(0,.933,.511),(1.47,.150,.263),leather,radius=.055)
    a.surface('DashboardWoodSweep',lambda u,v:(mix(-.69,.69,u),mix(.716,.916,v),
               .356+.035*(1-(2*u-1)**2)+.020*math.sin(math.pi*v)),60,17,wood,solid=.022,normal=(0,0,-1))
    a.curve('DashboardChromeSweep',[(mix(-.69,.69,i/72),.718,.340+.035*(1-(2*i/72-1)**2)) for i in range(73)],.0033,chrome)
    a.box('Glovebox',(-.421,.669,.498),(.520,.241,.167),black,radius=.034)
    a.box('InstrumentDisplay',(.420,1.004,.343),(.307,.170,.023),c['display'],radius=.015)
    # Five circular turbine outlets, including the characteristic centre trio.
    for x,y,z in [(-.686,.939,.355),(-.159,.982,.364),(0,.982,.369),(.159,.982,.364),(.686,.939,.355)]:
        c['disc']('AirVentWell',(x,y,z),.049,.018,black,axis='Z')
        c['ring_z']('AirVentOuter',(x,y,z-.015),.047,.005,chrome)
        c['ring_z']('AirVentInner',(x,y,z-.019),.035,.0029,c['dark_metal'])
        for angle in [i*math.tau/8 for i in range(8)]:
            a.curve('VentTurbineBlade',[(x+.018*math.cos(angle),y+.018*math.sin(angle),z-.025),
                     (x+.037*math.cos(angle+.18),y+.037*math.sin(angle+.18),z-.014)],.0024,c['dark_metal'])
        a.box('VentTab',(x,y,z-.025),(.030,.009,.014),chrome,radius=.004)
    # The portrait display rises out of the curved centre console.
    a.surface('PortraitDisplay',lambda u,v:(mix(-.124,.124,u),mix(.565,.908,v),mix(.132,.326,v)),
              18,28,c['display'],solid=.016,normal=(0,.3,-1))
    display_outline=[(-.126,.563,.131),(.126,.563,.131),(.126,.910,.327),(-.126,.910,.327)]
    a.curve('DisplayBezel',display_outline,.006,black,cyclic=True)
    a.box('ConsoleBody',(0,.425,-.185),(.293,.272,.758),black,radius=.041)
    a.box('ConsoleLid',(0,.563,-.361),(.266,.065,.339),leather,radius=.032)
    a.surface('ConsoleGloss',lambda u,v:(mix(-.139,.139,u),.552+.060*v*v,mix(-.17,.143,v)),
              22,26,c['display'],solid=.013,normal=(0,1,0))
    for side in [-1,1]:
        a.curve('ConsoleSilverEdge',[(side*.145,.557+.060*t*t,mix(-.52,.15,t)) for t in [i/60 for i in range(61)]],.0035,chrome)
    a.box('ConsoleRearVentBody',(0,.530,-.591),(.258,.198,.058),black,radius=.028)
    for x in [-.060,.060]:
        c['ring_z']('RearCabinVent',(x,.552,-.627),.040,.004,chrome)
        c['disc']('RearCabinVentWell',(x,.552,-.621),.036,.012,seal,axis='Z')

    # L3E has one horizontal control wing on either side and a split lower spoke.
    steering=(.421,.918,.123)
    a.curve('SteeringRim',[(steering[0]+.158*math.cos(t),steering[1]+.153*math.sin(t),steering[2]+.046*math.sin(t))
              for t in [math.tau*i/96 for i in range(97)]],.015,leather,cyclic=True)
    a.box('SteeringHub',steering,(.125,.119,.065),leather,radius=.038)
    for side in [-1,1]:
        a.box('SteeringControlWing',(.421+side*.094,.931,.109),(.092,.041,.021),c['display'],radius=.013)
        a.curve('SteeringLowerFork',[(.421+side*.036,.882,.101),(.421+side*.023,.772,.078)],.007,chrome)

    for side,suffix in [(1,'Left'),(-1,'Right')]:
        x=side*.410
        # Separate side bolsters and a gently reclined back avoid a block seat silhouette.
        a.box('FrontSeatBase'+suffix,(x,.338,-.203),(.472,.135,.482),black,radius=.045)
        a.box('FrontCushion'+suffix,(x,.418,-.180),(.454,.133,.459),leather,radius=.056)
        a.surface('FrontSeatBack'+suffix,lambda u,v,x=x:(x+mix(-.218,.218,u),mix(.458,1.033,v),
                  -.423-.101*v+.043*(2*u-1)**2),34,34,leather,solid=.110,normal=(0,0,1))
        for edge in [-1,1]:
            c['ellipsoid']('FrontBackBolster'+suffix,(x+edge*.182,.737,-.400),(.042,.242,.045),leather)
            c['ellipsoid']('FrontCushionBolster'+suffix,(x+edge*.184,.473,-.169),(.045,.035,.185),leather)
        a.box('FrontHeadrest'+suffix,(x,1.118,-.515),(.245,.216,.128),leather,radius=.053)
        for dx in [-.070,.070]:
            a.curve('HeadrestStem',[(x+dx,1.013,-.515),(x+dx,1.057,-.515)],.006,chrome)
        for y in [.561,.685,.837,.977]:
            z=-.423-.101*(y-.458)/.575+.003
            a.curve('FrontSeatSeam',[(x-.134,y,z),(x+.134,y,z)],.0012,c['stitch'])
        a.box('RearCushion'+suffix,(x,.450,-1.068),(.505,.134,.471),leather,radius=.055)
        a.surface('RearSeatBack'+suffix,lambda u,v,x=x:(x+mix(-.249,.249,u),mix(.485,1.047,v),
                  -1.270-.110*v+.025*(2*u-1)**2),30,30,leather,solid=.095,normal=(0,0,1))
        a.box('RearHeadrest'+suffix,(x,1.125,-1.364),(.257,.196,.119),leather,radius=.045)
        for y in [.616,.743,.925]:
            z=-1.270-.110*(y-.485)/.562+.003
            a.curve('RearSeatSeam',[(x-.172,y,z),(x+.172,y,z)],.0013,c['stitch'])
        a.curve('FrontSeatBelt'+suffix,[(side*.745,1.235,-.475),(side*.565,.778,-.470),(side*.625,.446,-.350)],.010,seal)
        a.box('SeatBuckle'+suffix,(side*.155,.454,-.289),(.037,.059,.051),black,radius=.008)
        a.box('BuckleRelease'+suffix,(side*.155,.486,-.277),(.027,.009,.025),c['reflector'],radius=.003)
    a.box('RearCentreCushion',(0,.450,-1.068),(.331,.134,.465),leather,radius=.040)
    a.box('RearCentreBack',(0,.771,-1.330),(.330,.580,.110),leather,radius=.034)
    a.box('RearCentreHeadrest',(0,1.087,-1.367),(.224,.149,.105),leather,radius=.034)
    a.box('RearParcelShelf',(0,.954,-1.616),(1.29,.060,.418),c['carpet'],radius=.028)
    a.surface('Headliner',lambda u,v:(lambda p:(p[0]*.97,p[1]-.046,p[2]))(cab_surface(2*u-1,mix(-1.07,.10,v))),
              52,54,c['headliner'],solid=.012,normal=(0,-1,0))
    a.box('OverheadConsole',(0,1.351,-.018),(.167,.025,.196),c['headliner'],radius=.018)

    for name,parent in c['doors'].items():
        side=1 if 'Left' in name else -1
        front=name.startswith('front')
        forward,back=(door_front,door_middle) if front else (door_middle,door_back)
        xoffset=.067
        limits=(-1.50,.76,.185,1.093)
        constraints=[lambda z,y:forward(y)-z-.006,lambda z,y:z-back(y)-.006,
                     lambda z,y:belt(z)-y-.012,lambda z,y:arch_distance(y,z)-.004]
        clipped_grid(a,'MouldedDoorCard'+name,lambda z,y:(side*(side_x(y,z)-xoffset),y,z),
                     limits,.027,constraints,leather,parent,(-side,0,0),solid=.018)
        z0,z1=(.535,-.329) if front else (-.555,-1.320)
        a.surface('DoorUpperSoftRail'+name,lambda u,v:(
            side*(side_x(mix(.818,.952,v),mix(z0,z1,u))-.071),mix(.818,.952,v),mix(z0,z1,u)),
            38,8,leather,parent,solid=.015,normal=(-side,0,0))
        arm_z=.007 if front else -.951
        arm_length=.520 if front else .399
        arm_outer=interior_outer_limit(.633,.064,arm_z,arm_length)
        a.box('DoorArmrest'+name,(side*(arm_outer-.141/2),.633,arm_z),(.141,.064,arm_length),leather,parent,radius=.029)
        a.curve('DoorArmrestSilver'+name,[(side*.648,.650,arm_z-.211),(side*.648,.657,arm_z+.211)],.004,chrome,parent)
        control_z=.325 if front else -.695
        a.box('DoorControlRecess'+name,(side*.755,.840,control_z),(.024,.112,.319 if front else .224),c['display'],parent,radius=.029)
        a.curve('DoorRelease'+name,[(side*.738,.813,control_z-.103),(side*.733,.810,control_z+.070),(side*.741,.843,control_z+.091)],.006,chrome,parent,bezier=True)
        if front:
            a.curve('SeatControlOutline'+name,[(side*.737,.806,control_z+.107),(side*.737,.806,control_z+.143),
                     (side*.737,.826,control_z+.143),(side*.737,.826,control_z+.121),(side*.737,.872,control_z+.119)],.005,chrome,parent)
            a.box('WindowSwitchPack'+name,(side*.688,.674,.129),(.055,.017,.158),c['display'],parent,radius=.006)
        # Conservative pocket volume; lower-pocket photos are explicitly incomplete.
        pocket_length=.427 if front else .281
        pocket_outer=interior_outer_limit(.354,.105,arm_z,pocket_length)
        a.box('DoorLowerPocket'+name,(side*(pocket_outer-.069/2),.354,arm_z),(.069,.105,pocket_length),black,parent,radius=.034)
        c['ellipsoid']('DoorSpeaker'+name,(side*.714,.534,control_z),(.013,.086,.108),c['dark_metal'],parent,28,20)
        # Fixed jamb depth is built from the same clipped panel boundary.
        vertices,faces=c['door_meshes'][name]
        edges=boundary_edges(faces)
        jamb_vertices=[];jamb_faces=[]
        for ia,ib in edges:
            p,q=vertices[ia],vertices[ib]
            if min(p[1]-belt(p[2]),q[1]-belt(q[2]))>-.010:
                continue
            if max(abs(arch_distance(p[1],p[2])),abs(arch_distance(q[1],q[2])))<.001:
                # The wheel tub, rather than a painted fixed door jamb, closes this edge.
                continue
            inner=[(p[0]-side*.030,p[1],p[2]),(q[0]-side*.030,q[1],q[2]),
                   (q[0]-side*.098,q[1],q[2]),(p[0]-side*.098,p[1],p[2])]
            start=len(jamb_vertices)
            jamb_vertices.extend(inner)
            jamb_faces.append((start,start+1,start+2,start+3))
        a.mesh('ApertureDepth'+name,jamb_vertices,jamb_faces,c['inner_paint'],normal=(side,0,0))
        # The upper aperture follows the actual window arch, not a straight chord.
        frontz=.685 if front else -.464
        backz=-.444 if front else -1.454
        a.surface('UpperDoorJamb'+name,lambda u,v:(
            side*(glass_x(window_top(mix(frontz,backz,u)),mix(frontz,backz,u))-.026-.053*v),
            window_top(mix(frontz,backz,u))-.008,mix(frontz,backz,u)),
            64,5,c['inner_paint'],solid=.012,normal=(0,1,0))
        a.curve('UpperDoorWeatherstrip'+name,[(side*(glass_x(window_top(z),z)-.040),window_top(z)-.011,z)
                  for z in [mix(frontz,backz,i/64) for i in range(65)]],.004,seal)
        a.box('DoorLatch'+name,(side*(side_x(.825,back(.825))-.055),.825,back(.825)-.007),(.026,.038,.014),chrome,parent,radius=.004)
        for y in [.455,.817]:
            z=forward(y)
            a.box('DoorHinge'+name,(side*(side_x(y,z)-.064),y,z),(.054,.045,.052),c['inner_paint'],parent,radius=.009)
