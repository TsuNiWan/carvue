"""Vehicle e:HEV hexagonal grille, narrow LED lamps and sculpted lower fascia."""
import math
import bpy


def build_front(c):
    a=c['author']; mix=c['mix']; profile=c['profile']; samples=c['samples']
    paint,black,chrome=c['paint'],c['black'],c['chrome']
    reflector_material=a.material('HeadlampReflectorMetal',(.25,.29,.32),.84,.24)

    def depth(x,y):
        centre=profile([(.205,2.215),(.31,2.324),(.45,2.330),(.64,2.303),(.91,2.270),(1.11,2.19),(1.16,2.155)],y)
        return centre-.225*(abs(x)/.858)**3

    def outer_width(y):
        return profile([(.205,.803),(.32,.843),(.60,.876),(.94,.873),(1.04,.866),(1.12,.858)],y)

    def grille_width(y):
        return profile([(.646,.448),(.690,.537),(.965,.712),(1.039,.641)],y)

    def lower_width(y):
        return profile([(.310,.697),(.350,.688),(.460,.580),(.515,.531)],y)

    def corner_inner(y):
        return mix(.731,.815,(y-.346)/.282)

    def corner_outer(y):
        return mix(.816,.858,(y-.346)/.282)

    def lamp_bounds(x):
        u=max(0,min(1,(abs(x)-.408)/.450))
        upper=1.106+.014*(1-(x/.858)**2)
        return upper-.107+.041*u,upper

    def top(x):
        y=1.106+.014*(1-(x/.858)**2)
        return y-(.079 if abs(x)>.405 else 0)

    def sheet(label,x0,x1,y0,y1,material,nu=44,nv=24,offset=0,solid=.022):
        return a.surface(label,lambda u,v:(lambda y:(lambda x:(x,y,depth(x,y)+offset))
                        (mix(x0(y),x1(y),u)))(mix(y0,y1,v)),nu,nv,material,solid=solid,normal=(0,0,1))

    # A native opening is preserved for the hexagonal main grille.
    sheet('FasciaLowerLip',lambda y:-outer_width(y),outer_width,.205,.310,paint,88,16)
    sheet('FasciaLowerBridge',lambda y:-corner_inner(y),corner_inner,.515,.628,paint,82,18)
    sheet('FasciaShoulderBridge',lambda y:-outer_width(y),outer_width,.628,.646,paint,82,4)
    sheet('UpperGrilleBridge',lambda y:-.405,lambda y:.405,1.039,1.113,paint,50,10)
    for side,suffix in [(1,'Left'),(-1,'Right')]:
        sheet('LowerIntakeFoot'+suffix,lambda y,side=side:side*lower_width(y),
              lambda y,side=side:side*outer_width(y),.310,.346,paint,32,5)
        sheet('LowerIntakeCheek'+suffix,lambda y,side=side:side*lower_width(y),
              lambda y,side=side:side*corner_inner(y),.346,.515,paint,36,24)
        sheet('CornerOuterFrame'+suffix,lambda y,side=side:side*corner_outer(y),
              lambda y,side=side:side*outer_width(y),.346,.628,paint,12,36)
        def grille_cheek(u,v,side=side):
            top_y=1.025
            for _ in range(8):
                top_y=lamp_bounds(mix(grille_width(top_y),outer_width(top_y),u))[0]
            y=mix(.646,top_y,v)
            x=side*mix(grille_width(y),outer_width(y),u)
            return x,y,depth(x,y)
        a.surface('GrilleCheek'+suffix,grille_cheek,44,42,paint,solid=.022,normal=(0,0,1))
        # The slim lamp occupies the actual hood/fascia gap, with no paint underneath it.
        def lamp(u,v,side=side):
            x=side*mix(.408,.858,u)
            lower,upper=lamp_bounds(x)
            y=mix(lower,upper,v)
            return x,y,depth(x,y)-.014
        # The rear wall sits behind the concave cells, not in front of them.
        a.surface('HeadlampCavity'+suffix,lambda u,v:(lambda p:(p[0],p[1],p[2]-.045))(lamp(u,v)),
                  52,16,black,solid=.012,normal=(0,0,1))
        for edge in [0,1]:
            a.surface('HeadlampHorizontalReturn'+suffix,
                      lambda u,v,edge=edge:(lambda p:(p[0],p[1],p[2]-.045*v))(lamp(u,edge)),
                      52,5,black,solid=.003,normal=(0,0,1))
            a.surface('HeadlampVerticalReturn'+suffix,
                      lambda u,v,edge=edge:(lambda p:(p[0],p[1],p[2]-.045*v))(lamp(edge,u)),
                      16,5,black,solid=.003,normal=(0,0,1))
        # The painted lower return starts outside the grille, never across its aperture.
        low,high=0.,1.
        for _ in range(30):
            middle=(low+high)/2
            p=lamp(middle,0)
            if abs(p[0])<grille_width(p[1]):low=middle
            else:high=middle
        painted_start=(low+high)/2
        a.surface('LampUnderEdge'+suffix,lambda u,v:(lambda p:(p[0],p[1]-.008*v,p[2]+.016))
                  (lamp(mix(painted_start,1,u),0)),
                  52,4,paint,solid=.014,normal=(0,.3,1))
        # Five individual dark reflector cells sit behind the upper continuous LED guide.
        for i in range(5):
            left=.027+i*.188
            def cup(u,v,left=left):
                p=lamp(left+.158*u,.14+.59*v)
                inset=.028*math.sin(math.pi*u)*math.sin(math.pi*v)
                return p[0],p[1],p[2]-.006-inset
            a.surface('LEDReflector'+suffix,cup,14,10,reflector_material,solid=.003,normal=(0,0,1))
            for offset in [.028,.116]:
                a.surface('ReflectorRib'+suffix,lambda u,v,left=left,offset=offset:(lambda p:(p[0],p[1],p[2]-.001))
                          (lamp(left+offset+.014*u+.025*v,.18+.49*v)),3,10,chrome,solid=.002,normal=(0,0,1))
            for level in [.20,.62]:
                a.surface('ReflectorEdge'+suffix,lambda u,v,left=left,level=level:(lambda p:(p[0],p[1],p[2]-.002))
                          (lamp(left+.020+.115*u,level+.044*v)),12,3,chrome,solid=.002,normal=(0,0,1))
            a.surface('LEDUnit'+suffix,lambda u,v,left=left:(lambda p:(p[0],p[1],p[2]-.016))
                      (lamp(left+.040+.077*u,.26+.21*v)),8,5,c['head'],solid=.004,normal=(0,0,1))
        a.surface('HeadlampDRL'+suffix,lambda u,v:(lambda p:(p[0],p[1],p[2]+.021))(lamp(u,mix(.81,.93,v))),
                  64,4,c['head'],solid=.004,normal=(0,0,1))
        signal=c['signal_left'] if side==1 else c['signal_right']
        a.surface('HeadTurnSignal'+suffix,lambda u,v:(lambda p:(p[0],p[1],p[2]+.020))(lamp(mix(.68,.98,u),mix(.60,.70,v))),
                  22,4,signal,solid=.004,normal=(0,0,1))
        a.surface('HeadlampCover'+suffix,lambda u,v:(lambda p:(p[0],p[1],p[2]+.027))(lamp(u,v)),
                  52,16,c['lens'],solid=.002,normal=(0,0,1))
        # Fascia and fender now use the same front boundary, at every height.
        old=bpy.data.objects.get('FrontWing'+suffix)
        if old:bpy.data.objects.remove(old,do_unlink=True)
        def front_edge(y):return depth(outer_width(y),y)
        def upper_y(z):
            return mix(c['belt'](c['door_front'](1)),1.106,
                       (z-c['door_front'](1))/(front_edge(1.106)-c['door_front'](1)))
        def wing_x(z,y):
            end=front_edge(y)
            start=end-.180
            if z<=start:return c['side_x'](z,y)
            t=max(0,min(1,(z-start)/(end-start)))
            x0=c['side_x'](start,y)
            x1=outer_width(y)
            m0=(c['side_x'](start+.0001,y)-c['side_x'](start-.0001,y))/.0002
            # This derivative is the inverse of the actual front-face depth derivative.
            m1=-(.858**3)/(.675*x1*x1)
            h=end-start
            return ((2*t**3-3*t*t+1)*x0+(t**3-2*t*t+t)*h*m0
                    +(-2*t**3+3*t*t)*x1+(t**3-t*t)*h*m1)
        c['clipped_side_panel']('FrontWing'+suffix,(.74,2.15,.256,1.168),(106,66),[
            lambda z,y:z-c['door_front'](max(0,min(1,(y-.256)/(1.154-.256)))),
            lambda z,y:front_edge(y)-z,
            lambda z,y:upper_y(z)-y,
            lambda z,y:(z-1.35)**2+(y-.3696)**2-.414**2,
        ],wing_x,side)
        # The visible lip follows this fender's blended width, not the old side section.
        for old in list(bpy.data.objects):
            if old.name.startswith('ArchLip'+suffix+'1.35'):
                bpy.data.objects.remove(old,do_unlink=True)
        arch=[]
        for i in range(181):
            angle=mix(-.275,math.pi+.275,i/180)
            z=1.35+.4145*math.cos(angle)
            y=.3696+.4145*math.sin(angle)
            arch.append((side*(wing_x(z,y)+.0006),y,z))
        a.curve('FrontArchLip'+suffix,arch,.0017,paint)
        old=bpy.data.objects.get('HoodShoulder'+suffix)
        if old:bpy.data.objects.remove(old,do_unlink=True)
        def wing_top(t,side=side):
            z=mix(c['door_front'](1),front_edge(1.106),t)
            y=upper_y(z)
            return side*wing_x(z,y),y,z
        c['strip']('HoodShoulder'+suffix,lambda t,side=side:c['hood_surface'](1 if side==1 else 0,t),
                   wing_top,paint,nu=70,nv=12,normal=(side,.65,0))
        # Wide sculpted e:HEV lower corner inlet, projected onto the fascia.
        def corner(u,v,side=side):
            y=mix(.346,.628,v)
            inner=corner_inner(y)
            outer=corner_outer(y)
            x=side*mix(inner,outer,u)
            return x,y,depth(x,y)-.022
        a.surface('CornerInlet'+suffix,corner,16,30,black,solid=.009,normal=(0,0,1))
        for edge in [0,1]:
            a.surface('CornerReturn'+suffix,lambda u,v,edge=edge:(lambda p:(p[0],p[1],p[2]+.022*v))(corner(edge,u)),
                      38,6,paint,solid=.010,normal=(0,0,1))
        for i in range(3):
            y=.410+i*.057
            a.curve('CornerVane'+suffix,samples(lambda t,side=side,y=y:
                     (side*mix(corner_inner(y)+.012,corner_outer(y)-.008,t),y,
                      depth(side*mix(corner_inner(y)+.012,corner_outer(y)-.008,t),y)-.013),15),.003,black)
        a.surface('CornerLowerLED'+suffix,lambda u,v,side=side:(lambda x,y:(x,y,depth(x,y)-.016))
                  (side*mix(.777,.808,u),mix(.353,.365,v)),12,4,c['head'],solid=.003,normal=(0,0,1))
        # A rounded bevel returns from the painted diagonal frame into the deep intake.
        a.surface('LowerIntakeReturn'+suffix,lambda u,v,side=side:(lambda y:(lambda x:
                  (x,y,depth(x,y)-.037*v+.011*math.sin(math.pi*v)))
                  (side*(lower_width(y)-.015*v)))(mix(.312,.513,u)),
                  42,10,paint,solid=.014,normal=(0,0,1))
    # Dark grille backing and a deep hex lattice; cells are clipped analytically to its outline.
    sheet('GrilleBack',lambda y:-grille_width(y)+.007,lambda y:grille_width(y)-.007,.650,1.035,black,60,34,offset=-.021,solid=.018)
    edge=[]
    for i in range(81):
        y=mix(.650,1.037,i/80);edge.append((grille_width(y),y,depth(grille_width(y),y)-.001))
    edge+=samples(lambda t:(mix(grille_width(1.037),-grille_width(1.037),t),1.037,depth(mix(grille_width(1.037),-grille_width(1.037),t),1.037)-.001),70)
    for i in range(81):
        y=mix(1.037,.650,i/80);edge.append((-grille_width(y),y,depth(-grille_width(y),y)-.001))
    edge+=samples(lambda t:(mix(-grille_width(.650),grille_width(.650),t),.650,depth(mix(-grille_width(.650),grille_width(.650),t),.650)-.001),55)
    a.curve('GrilleSurround',edge,.010,black,cyclic=True)
    r=.044
    for row in range(5):
        y=.685+row*.076
        for col in range(-9,10):
            x=col*.086+(row%2)*.043
            pts=[(x+r*math.cos(k*math.tau/6),y+r*math.sin(k*math.tau/6)) for k in range(6)]
            if all(.652<yy<1.034 and abs(xx)<grille_width(yy)-.01 for xx,yy in pts):
                a.curve('HexGrille',[(xx,yy,depth(xx,yy)-.006) for xx,yy in pts],.0026,black,cyclic=True)
    sheet('LowerMeshBack',lambda y:-lower_width(y)+.012,lambda y:lower_width(y)-.012,
          .312,.513,black,70,22,offset=-.041,solid=.010)
    for slant in [-1,1]:
        for i in range(37):
            x0=mix(-.82,.82,i/36)
            coords=[]
            for j in range(23):
                y=mix(.317,.508,j/22);x=x0+slant*(y-.412)*.74
                if abs(x)<lower_width(y)-.019:
                    coords.append((x,y,depth(x,y)-.027))
            if len(coords)>1:a.curve('LowerIntakeMesh',coords,.0024,black)
    a.box('FrontPlate',(0,.600,2.308),(.436,.140,.023),black,radius=.008)
