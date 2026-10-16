"""Visible cabin, shared door openings and moving door cards for the Vehicle."""
import math
import bmesh


def build_cabin(c):
    a, root = c['author'], c['root']
    paint, black, seal = c['paint'], c['black'], c['seal']
    leather, cloth, chrome = c['leather'], c['cloth'], c['chrome']
    side_x, belt, glass_x = c['side_x'], c['belt'], c['glass_x']
    mix, samples, strip = c['mix'], c['samples'], c['strip']
    ellipsoid, ring = c['ellipsoid'], c['ring']
    smoothstep = c['smoothstep']

    # The floor ends behind the firewall and steps inward around the rear wheel houses.
    def floor_surface(u,v):
        z=mix(-1.885,.805,v)
        width=c['profile']([(-1.885,.810),(-1.812,.810),(-1.790,.580),
                            (-.910,.580),(-.887,.810),(.805,.810)],z)
        return (2*u-1)*width,.3145,z
    a.surface('CabinFloor',floor_surface,24,130,c['lining'],solid=.055,normal=(0,1,0))
    a.box('Firewall', (0,.71,.855), (1.55,.71,.090), c['lining'], radius=.06)
    a.box('CentreTunnel', (0,.35,-.21), (.21,.12,1.94), black, radius=.05)
    # Molded dashboard is a broad rounded surface, with the horizontal honeycomb vent strip.
    a.box('DashboardCore', (0,1.005,.697), (1.54,.228,.375), black, radius=.087)
    a.box('DashboardLower', (0,.79,.66), (1.45,.23,.23), leather, radius=.07)
    a.box('VentRail', (0,.984,.483), (1.32,.06,.018), seal, radius=.010)
    for i in range(68):
        x = -.651 + i*.0194
        if -.19 < x < .21:
            continue
        a.curve('VentHex', [(x-.005,.969,.471),(x-.011,.984,.471),(x-.005,.999,.471),
                            (x+.005,.999,.471),(x+.011,.984,.471),(x+.005,.969,.471)],
                .0013, chrome, cyclic=True)
    a.box('CentreDisplayCase', (0,1.132,.606), (.252,.155,.023), black, radius=.011)
    a.box('CentreDisplayGlass', (0,1.136,.590), (.232,.130,.007), c['glass'], radius=.005)
    a.box('InstrumentHood', (.434,1.055,.632), (.357,.144,.240), black, radius=.046)
    a.box('InstrumentDisplay', (.434,1.040,.495), (.274,.080,.012), c['glass'], radius=.011)
    a.box('ConsoleBody', (0,.515,-.006), (.25,.382,.790), black, radius=.049)
    a.box('Armrest', (0,.710,-.199), (.238,.082,.282), leather, radius=.04)
    a.box('ShifterBase', (0,.707,.224), (.150,.034,.207), black, radius=.018)
    a.box('Shifter', (0,.77,.251), (.057,.084,.060), leather, radius=.016)
    for z in [-.001,.119]:
        a.curve('CupholderRim',samples(lambda t,z=z:(.047*math.cos(t*math.tau),.711,z+.047*math.sin(t*math.tau)),48),
                .004,chrome,cyclic=True)
        a.box('Cupholder', (0,.690,z), (.094,.019,.097),seal,radius=.033)
    # Steering plane is tilted toward the driver; the circular rim is native geometry.
    steering_center=(.431,.983,.393)
    points=[]
    for i in range(97):
        angle=i*math.tau/96
        points.append((steering_center[0]+.160*math.cos(angle),
                       steering_center[1]+.154*math.sin(angle),
                       steering_center[2]+.048*math.sin(angle)))
    a.curve('SteeringRim',points,.016,leather,cyclic=True)
    a.box('SteeringHub',steering_center,(.120,.105,.055),leather,radius=.027)
    for sign in [-1,1]:
        a.curve('SteeringSpoke',[(.431+sign*.05,.983,.384),(.431+sign*.14,.977,.385)],.014,black)
    a.curve('SteeringLowerSpoke',[(.431,.943,.393),(.431,.845,.351)],.013,chrome)

    for side,suffix in [(1,'Left'),(-1,'Right')]:
        x=side*.430
        for row,z in [('Front',.012),('Rear',-1.026)]:
            if row=='Front':
                a.box('SeatBase'+suffix,(x,.399,z),(.459,.19,.482),black,radius=.05)
                a.box('Cushion'+suffix,(x,.492,z+.018),(.443,.136,.468),leather,radius=.062)
                a.box('CushionInsert'+suffix,(x,.555,z+.033),(.285,.027,.362),cloth,radius=.022)
                a.box('SeatBack'+suffix,(x,.849,z-.232),(.426,.641,.153),leather,radius=.06)
                a.box('SeatBackInsert'+suffix,(x,.874,z-.144),(.279,.474,.023),cloth,radius=.023)
                for sign in [-1,1]:
                    ellipsoid('BackBolster'+suffix,(x+sign*.164,.846,z-.146),(.055,.27,.050),leather)
                    ellipsoid('CushionBolster'+suffix,(x+sign*.178,.534,z+.015),(.043,.040,.18),leather)
                a.box('Headrest'+suffix,(x,1.253,z-.230),(.26,.239,.137),leather,radius=.052)
                for dx in [-.07,.07]:
                    a.curve('HeadrestPost',[(x+dx,1.090,z-.230),(x+dx,1.153,z-.230)],.008,chrome)
                for i in range(5):
                    y=.675+i*.083
                    a.curve('BackInsertSeam',[(x-.133,y,z-.126),(x+.133,y,z-.126)],.0016,seal)
                    zz=z-.125+i*.072
                    a.curve('SeatInsertSeam',[(x-.129,.572,zz),(x+.129,.572,zz)],.0016,seal)
                a.box('SeatbeltBuckle',(x-side*.237,.53,z-.150),(.038,.067,.050),black,radius=.009)
                a.box('BuckleButton',(x-side*.237,.566,z-.145),(.029,.008,.028),c['reflector'],radius=.003)
            else:
                a.box('RearSeatBase'+suffix,(x,.432,z),(.510,.196,.452),black,radius=.05)
                a.box('RearCushion'+suffix,(x,.534,z),(.504,.148,.46),leather,radius=.056)
                a.box('RearCushionInsert'+suffix,(x,.602,z+.008),(.343,.025,.355),cloth,radius=.025)
                a.box('RearBack'+suffix,(x,.895,z-.227),(.506,.646,.147),leather,radius=.045)
                a.box('RearBackInsert'+suffix,(x,.892,z-.144),(.354,.481,.020),cloth,radius=.02)
                a.box('RearHeadrest'+suffix,(x,1.273,z-.218),(.263,.210,.121),leather,radius=.04)
                for i in range(5):
                    y=.694+i*.083
                    a.curve('RearSeatSeam',[(x-.172,y,z-.13),(x+.172,y,z-.13)],.0015,seal)
        a.curve('Seatbelt'+suffix,[(side*.78,1.385,-.343),(side*.596,.880,-.286),
                                   (side*.648,.476,-.307)],.012,seal)
    a.box('RearMiddleCushion',(0,.531,-1.026),(.347,.143,.449),leather,radius=.036)
    a.box('RearMiddleBack',(0,.889,-1.253),(.347,.622,.142),leather,radius=.036)
    a.box('RearMiddleHeadrest',(0,1.217,-1.255),(.226,.154,.116),leather,radius=.032)
    # The underside of the roof and the pillar trim remain visible with doors open.
    a.surface('Headliner',lambda u,v: (lambda p:(p[0]*.972,p[1]-.050,p[2]))(c['roof_surface'](u,v)),
              45,46,c['headliner'],solid=.010,normal=(0,-1,0))
    a.box('OverheadConsole',(0,1.548,-.035),(.20,.031,.21),black,radius=.024)

    for name,joint in c['doors'].items():
        side,row,forward,back=c['door_shapes'][name]
        # Follow the actual outer opening, with dense reprojection into the curved skin.
        contour=[]
        for i in range(41):
            v=i/40
            z=forward(v) if row=='front' else -.310
            contour.append((z,mix(.322,belt(z),v)))
        if row=='front':
            contour += [(mix(.755,.15,t),mix(belt(.755),c['window_top'](.15),t)) for t in [i/40 for i in range(1,41)]]
            contour += [(mix(.15,-.302,t),c['window_top'](mix(.15,-.302,t))) for t in [i/30 for i in range(1,31)]]
            contour += [(-.302,mix(c['window_top'](-.302),.322,t)) for t in [i/65 for i in range(1,66)]]
        else:
            contour += [(-.310,mix(belt(-.310),c['window_top'](-.310),t)) for t in [i/25 for i in range(1,26)]]
            contour += [(mix(-.310,-1.140,t),c['window_top'](mix(-.310,-1.140,t))) for t in [i/40 for i in range(1,41)]]
            contour += [(mix(-1.140,-1.412,t),mix(c['window_top'](-1.140),belt(-1.412),t)) for t in [i/28 for i in range(1,29)]]
            contour += [(back(1-t),mix(belt(back(1-t)),.322,t)) for t in [i/42 for i in range(1,43)]]
        z0,z1=back(0),forward(0)
        contour += [(mix(z0,z1,t),.322) for t in [i/40 for i in range(1,41)]]
        verts=[]
        for depth in [0,.070]:
            for z,y in contour:
                xx=c['outer_x'](z,y)-.030-depth
                verts.append((side*xx,y,z))
        n=len(contour)
        jamb=a.mesh('ApertureDepth'+name,verts,[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)],c['innerpaint'],normal=(side,0,0))
        a.thickness(jamb,.014)
        # The fixed jamb return stays behind the painted 414 mm wheel opening.
        for axle in [1.35,-1.35]:
            a.cut_arch(jamb,axle,.3696,.425)
        weather=[]
        for z,y in contour:
            if math.hypot(z+1.35,y-.3696)<.427:
                continue
            weather.append((side*(c['outer_x'](z,y)-.050),y,z))
        a.curve('ApertureSeal'+name,weather,.007,seal,cyclic=True)
        # Molded door card follows the same rising rear edge and wheel relief.
        def card(u,v):
            z=mix(back(v)+.050,forward(v)-.050,u)
            y=mix(.353,belt(z)-.034,v)
            xx=side_x(z,y)-.067-.016*math.sin(math.pi*v)
            return side*xx,y,z
        card_obj=a.surface('DoorCard'+name,card,44,32,leather,joint,.024,(side,0,0))
        c['remove_arches'](card_obj)
        center_z=(back(.62)+forward(.62))/2
        width=forward(.62)-back(.62)-.15
        a.box('DoorArmrest'+name,(side*(side_x(center_z,.78)-.108),.780,center_z),(.097,.064,width*.79),leather,joint,radius=.025)
        a.box('DoorSwitch'+name,(side*(side_x(center_z,.812)-.101),.818,center_z+.10),(.057,.015,.126),black,joint,radius=.006)
        a.curve('InnerDoorTrim'+name, samples(lambda t:(side*(side_x(mix(back(.90)+.10,forward(.90)-.10,t),1.043)-.098),1.043,
                                                                    mix(back(.90)+.10,forward(.90)-.10,t)),40),.004,chrome,joint)
        a.curve('InnerDoorHandle'+name,[(side*(side_x(center_z,.973)-.112),.961,center_z+.23),
                                       (side*(side_x(center_z,.973)-.141),.944,center_z+.14),
                                       (side*(side_x(center_z,.973)-.121),.954,center_z+.06)],.009,chrome,joint,bezier=True)
        pocket_z,pocket_length=center_z,width*.68
        if row=='rear':
            lower_boundaries=[]
            for i in range(25):
                y=mix(.3975,.5585,i/24)
                v=.2
                for _ in range(12):
                    v=(y-.322)/(belt(back(v))-.322)
                lower_boundaries.append(back(v))
            pocket_back=max(lower_boundaries)+.055
            pocket_front=forward(.2)-.065
            pocket_z=(pocket_back+pocket_front)/2
            pocket_length=pocket_front-pocket_back
        a.box('DoorPocket'+name,(side*(side_x(pocket_z,.477)-.102),.478,pocket_z),
              (.083,.161,pocket_length),black,joint,radius=.035)
        # The bowl is an analytic deformation of both panel layers, retaining shell thickness.
        handle_z=back(.88)+.161
        handle_y=belt(handle_z)-.121
        skin=next(obj for obj in joint.children if obj.name.startswith('DoorSkin'))
        origin=joint['origin_carvue']
        topology=bmesh.new(); topology.from_mesh(skin.data)
        selected=[]
        for edge in topology.edges:
            if all(abs((-v.co.y+origin[2])-handle_z)<.175 and abs((v.co.z+origin[1])-handle_y)<.085 for v in edge.verts):
                selected.append(edge)
        if selected:
            bmesh.ops.subdivide_edges(topology,edges=selected,cuts=2,use_grid_fill=True)
        for vertex in topology.verts:
            z=-vertex.co.y+origin[2]; y=vertex.co.z+origin[1]
            q=((z-handle_z)/.109)**2+((y-handle_y)/.040)**2
            if q<1:
                vertex.co.x-=side*.012*(1-q)**2
        bmesh.ops.recalc_face_normals(topology,faces=list(topology.faces))
        topology.to_mesh(skin.data);topology.free()
        for p in skin.data.polygons:p.use_smooth=True
        points=samples(lambda t:(side*(side_x(handle_z+mix(-.091,.091,t),handle_y)+.016+.014*math.sin(math.pi*t)),
                                  handle_y+.003*math.sin(math.pi*t),handle_z+mix(-.091,.091,t)),45)
        a.curve('ExteriorHandle'+name,points,.011,paint,joint)
        for z in [handle_z-.082,handle_z+.082]:
            ellipsoid('HandleFoot'+name,(side*(side_x(z,handle_y)+.012),handle_y,z),(.016,.013,.014),paint,joint,nu=20,nv=10)
        if row=='front':
            a.curve('MirrorStalk'+name,[(side*.850,1.16,.656),(side*.970,1.207,.608)],.028,black,joint)
            ellipsoid('MirrorShell'+name,(side*1.012,1.229,.594),(.132,.063,.093),black,joint)
            def mirror_glass(u,v,side=side):
                angle=u*math.tau
                xx=.118*v*math.cos(angle)
                yy=.049*v*math.sin(angle)
                zz=.594-.093*math.sqrt(max(.02,1-(xx/.132)**2-(yy/.063)**2))-.001
                return side*(1.012+xx),1.229+yy,zz
            a.surface('MirrorGlass'+name,mirror_glass,48,14,chrome,joint,normal=(0,0,-1))
            signal=c['signal_left'] if side==1 else c['signal_right']
            a.curve('MirrorIndicator'+name,samples(lambda t:(side*(.948+.174*t),1.213,.642+.026*math.sin(math.pi*t)),30),.003,signal,joint)
    # Fixed B posts are projected inside the body, and narrow toward the roof.
    for side in [-1,1]:
        a.surface('BPost',lambda u,v:(side*(c['outer_x'](-.305+mix(-.033,.033,u),mix(.32,1.56,v))-.075),
                                      mix(.32,1.56,v),-.305+mix(-.033,.033,u)),
                  6,56,c['headliner'],solid=.036,normal=(side,0,0))
