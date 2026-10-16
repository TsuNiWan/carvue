"""Reproducible vehicle study based on real-vehicle reference observation.

Brand identifiers are omitted; exterior design rights remain unverified.
Coordinates: X left, Y up, Z forward, in meters.
"""
import math
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parent))
from vehicle_authoring import VehicleAuthoring
from sedan_03_surfaces import (AXLES,FRONT_RADIUS,REAR_RADIUS,BOTTOM,mix,profile,smooth,
                             belt,side_x,glass_x,cab_edge,cab_surface,cab_panel_surface,window_top,
                             front_z,rear_z,end_point,hood_y,hood_surface,
                             door_front,door_middle,door_back,arch_distance,clipped_grid,
                             front_wheelhouse_inner_x,wheelhouse_liner_outer_x)

a=VehicleAuthoring('sedan-03', 'Reconstructed vehicle study; exterior design rights unverified')
root=a.root
paint=a.material('BodyPaint',(.41,.445,.475),.63,.27,coat=.55)
inner_paint=a.material('InnerPaint',(.25,.282,.306),.39,.38)
black=a.material('GlossBlack',(.018,.022,.026),.16,.29)
seal=a.material('WindowSeals',(.013,.016,.019),rough=.60)
chrome=a.material('Chrome',(.79,.825,.86),.94,.20)
alloy=a.material('StudySilver',(.65,.685,.72),.86,.25)
dark_metal=a.material('DarkMetal',(.14,.158,.176),.52,.39)
rubber=a.material('TyreRubber',(.025,.028,.032),rough=.81)
glass=a.material('WindowGlass',(.060,.079,.090),rough=.15,alpha=.61)
lens=a.material('ClearLampCover',(.28,.34,.38),rough=.10,alpha=.13)
red_lens=a.material('RedLampCover',(.42,.012,.025),.08,.18,alpha=.40)
head=a.material('Headlamp',(.82,.9,.95),.07,.18,emission=(.85,.94,1))
tail=a.material('Taillamp',(.66,.02,.033),.07,.20,emission=(1,.012,.02))
signal_left=a.material('SignalLeft',(.64,.25,.016),rough=.23,emission=(1,.31,.01))
signal_right=a.material('SignalRight',(.64,.25,.016),rough=.23,emission=(1,.31,.01))
reflector=a.material('PassiveReflector',(.40,.016,.025),.08,.31)
leather=a.material('BlackStudy',(.049,.055,.060),rough=.56)
carpet=a.material('Carpet',(.039,.043,.047),rough=.95)
headliner=a.material('LightHeadliner',(.45,.46,.455),rough=.86)
wood=a.material('OpenPoreBlackWood',(.063,.059,.057),rough=.54)
stitch=a.material('SeatStitch',(.17,.178,.18),rough=.81)
display=a.material('DisplayGlass',(.016,.029,.041),.12,.19)
plate=a.material('PlateWhite',(.77,.78,.785),rough=.45)
mirror_material=a.material('MirrorSilver',(.66,.72,.76),.98,.095)


def ring_x(name,centre,radius,tube,mat,parent=None,count=80):
    return a.curve(name,[(centre[0],centre[1]+radius*math.cos(t),centre[2]+radius*math.sin(t))
                         for t in [math.tau*i/count for i in range(count)]],tube,mat,parent,cyclic=True)


def ring_z(name,centre,radius,tube,mat,parent=None,count=64):
    return a.curve(name,[(centre[0]+radius*math.cos(t),centre[1]+radius*math.sin(t),centre[2])
                         for t in [math.tau*i/count for i in range(count)]],tube,mat,parent,cyclic=True)


def ellipsoid(name,centre,radii,mat,parent=None,nu=32,nv=20):
    def surface(u,v):
        theta,phi=math.tau*u,math.pi*v
        return (centre[0]+radii[0]*math.sin(phi)*math.cos(theta),
                centre[1]+radii[1]*math.cos(phi),centre[2]+radii[2]*math.sin(phi)*math.sin(theta))
    return a.surface(name,surface,nu,nv,mat,parent)


def disc(name,centre,radius,depth,mat,parent=None,axis='Z'):
    def surface(u,v):
        first,second=radius*v*math.cos(math.tau*u),radius*v*math.sin(math.tau*u)
        if axis=='X':
            return centre[0],centre[1]+first,centre[2]+second
        return centre[0]+first,centre[1]+second,centre[2]
    return a.surface(name,surface,48,5,mat,parent,solid=depth,normal=(1,0,0) if axis=='X' else (0,0,-1))


doors={}
door_meshes={}
trunk=a.group('trunk',(0,1.063,-1.903),root)


def panel(name,side,parent,forward,back,is_door=False):
    gap=.0024 if is_door else .0017
    forward_gap=0 if name.startswith('FrontWing') else gap
    back_gap=0 if name.startswith('RearQuarter') else gap
    conditions=[lambda z,y:forward(y)-z-forward_gap,lambda z,y:z-back(y)-back_gap,
                lambda z,y:belt(z)-y,lambda z,y:arch_distance(y,z)]
    handle_z=-.265 if name.startswith('front') else -1.210
    handle_y=belt(handle_z)-.116
    def surface(z,y):
        bowl=0
        if is_door:
            radial=((z-handle_z)/.111)**2+((y-handle_y)/.035)**2
            bowl=.017*max(0,1-radial)**2
        return side*(side_x(y,z)-bowl),y,z
    obj,vertices,faces=clipped_grid(a,name,surface,(-2.55,2.24,BOTTOM,1.10),.022,
                                  conditions,paint,parent,(side,0,0),solid=.004)
    if is_door:
        door_meshes[name]=(vertices,faces)
    return obj


for side,suffix in [(1,'Left'),(-1,'Right')]:
    panel('FrontWing'+suffix,side,root,lambda y:end_point(True,y)[2],door_front)
    panel('RearQuarter'+suffix,side,root,door_back,lambda y:end_point(False,y)[2])
    for front in [True,False]:
        name=('front' if front else 'rear')+suffix
        forward,back=(door_front,door_middle) if front else (door_middle,door_back)
        hinge_z=.708 if front else -.442
        parent=a.group('door_'+name,(side*.839,.998,hinge_z),root)
        doors[name]=parent
        panel(name,side,parent,forward,back,True)
        # The complete glazed door arch, including the rear quarterlight, moves with the door.
        z_front=.683 if front else -.463
        z_back=-.413 if front else -1.450
        def window(u,v):
            z=mix(z_front,z_back,u)
            low=belt(z)+.007
            high=max(low+.004,window_top(z)-.010)
            y=mix(low,high,v)
            return side*glass_x(y,z),y,z
        a.surface('SideGlass'+name,window,52,23,glass,parent,solid=.0035,normal=(side,.1,0))
        outline=([window(i/64,0) for i in range(65)]+[window(1,i/24) for i in range(1,25)]
                 +[window(1-i/64,1) for i in range(1,65)]+[window(0,1-i/24) for i in range(1,24)])
        a.curve('DoorGlassRubber'+name,outline,.0052,seal,parent,cyclic=True)
        a.curve('ChromeUpperArch'+name,[window(i/72,1) for i in range(73)],.0034,chrome,parent)
        a.curve('ChromeBeltRail'+name,[window(i/72,0) for i in range(73)],.0035,chrome,parent)
        # A gently bowed black face covers each B-pillar door edge.
        b_u=1 if front else 0
        a.surface('BColumnCover'+name,lambda u,v:(lambda p:(p[0]+side*.0015*math.sin(math.pi*u),p[1],p[2]+mix(-.014,.014,u)))(window(b_u,v)),
                  7,26,seal,parent,solid=.010,normal=(side,0,0))
        if not front:
            divider=(z_front-(-1.133))/(z_front-z_back)
            a.curve('RearQuarterlightDivider'+name,[window(divider,i/30) for i in range(31)],.0055,seal,parent)
        z=-.265 if front else -1.210
        y=belt(z)-.116
        a.curve('ChromeDoorHandle'+name,[(side*(side_x(y,z-.087+.174*t)+.007+.015*math.sin(math.pi*t)),
                  y+.001*math.sin(math.pi*t),z-.087+.174*t) for t in [i/32 for i in range(33)]],.0073,chrome,parent)
        # Door cards and jambs use these same physical boundaries in sedan_03_cabin.
    # Native wheel-opening return lips are segmented by door ownership.
    for axle,r in zip(AXLES,(FRONT_RADIUS,REAR_RADIUS)):
        segments={root:[]}
        for i in range(161):
            angle=mix(-.42,math.pi+.42,i/160)
            y=r+.373*math.sin(angle);z=axle+.373*math.cos(angle)
            if y<BOTTOM:
                continue
            owner=doors['rear'+suffix] if axle<0 and door_back(y)<z<door_middle(y) else root
            segments.setdefault(owner,[]).append((side*side_x(y,z),y,z))
        for owner,points in segments.items():
            if len(points)<2:
                continue
            # Avoid connecting separate fixed arc pieces across an open door.
            strips=[];current=[]
            for p in points:
                if current and math.dist(current[-1],p)>.045:
                    strips.append(current);current=[]
                current.append(p)
            if current:
                strips.append(current)
            for strip in strips:
                vertices=strip+[(x-side*.028,y,z) for x,y,z in strip]
                n=len(strip)
                a.mesh('ArchReturn',vertices,[(i,i+1,i+1+n,i+n) for i in range(n-1)],inner_paint,owner,normal=(side,-.2,0))
        # The dark well stays inside the arch; its radial band cannot protrude into the opening.
        a.surface('WheelhouseLiner',lambda u,v,side=side,axle=axle,r=r:(
                  side*mix(.672,wheelhouse_liner_outer_x(r+.382*math.sin(mix(-.40,math.pi+.40,u)),
                      axle+.382*math.cos(mix(-.40,math.pi+.40,u))),v),r+.382*math.sin(mix(-.40,math.pi+.40,u)),
                  axle+.382*math.cos(mix(-.40,math.pi+.40,u))),76,10,seal,normal=(-side,0,0))
        wall_x=front_wheelhouse_inner_x() if axle>0 else .630
        clipped_grid(a,'WheelhouseInnerWall',lambda z,y,side=side,wall_x=wall_x:(side*wall_x,y,z),
                     (axle-.383,axle+.383,BOTTOM,r+.383),.026,
                     [lambda z,y,axle=axle,r=r:.383-math.hypot(y-r,z-axle)],seal,normal=(side,0,0))
    a.surface('Rocker'+suffix,lambda u,v,side=side:(
        side*(side_x(mix(.167,.201,v),mix(-1.018,1.015,u))-.005),mix(.167,.201,v),mix(-1.018,1.015,u)),
        84,6,paint,solid=.022,normal=(side,0,0))
    a.curve('RockerSilver'+suffix,[(side*(side_x(.193,z)+.001),.193,z) for z in [mix(-.989,.985,i/86) for i in range(87)]],.0030,chrome)
    # Fixed B-pillar core remains behind the moving black covers.
    a.surface('StructuralBPillar'+suffix,lambda u,v,side=side:(
        side*(glass_x(mix(.895,1.386,v),-.440)-.038),mix(.895,1.386,v),mix(-.472,-.416,u)),
        8,36,inner_paint,solid=.047,normal=(side,0,0))
    # The painted A/C rail is a surface strip, not a circular pipe.
    def side_rail(u,v,side=side):
        z=mix(-1.90,.730,u)
        lower=max(belt(z),window_top(z)+.002) if -1.47<=z<=.692 else belt(z)
        upper=cab_edge(z)
        y=mix(min(lower,upper),upper,v)
        return side*glass_x(y,z),y,z
    rail_mesh=a.surface('PillarAndRoofRail'+suffix,side_rail,122,17,paint,solid=.006,normal=(side,.5,0))
    rail_mesh.data.set_sharp_from_angle(angle=math.radians(35))
    # Round-ended, open-backed mirror shell and its own curved glass share an ellipse.
    parent=doors['front'+suffix]
    a.curve('MirrorMount'+suffix,[(side*.835,1.039,.561),(side*.911,1.057,.525)],.018,black,parent)
    def mirror_shell(u,v,side=side):
        t=math.tau*u;phi=math.pi*.5*v
        return side*.963+.119*math.sin(phi)*math.cos(t),1.093+.052*math.sin(phi)*math.sin(t),.493+.077*math.cos(phi)
    a.surface('MirrorHousing'+suffix,mirror_shell,56,20,paint,parent,solid=.005)
    a.surface('MirrorGlass'+suffix,lambda u,v,side=side:(side*.963+.112*v*math.cos(math.tau*u),
              1.093+.046*v*math.sin(math.tau*u),.490-.008*(1-v*v)),52,15,mirror_material,parent,normal=(0,0,-1))
    a.curve('MirrorGasket'+suffix,[(side*.963+.118*math.cos(t),1.093+.051*math.sin(t),.491)
              for t in [math.tau*i/72 for i in range(72)]],.003,seal,parent,cyclic=True)
    signal=signal_left if side==1 else signal_right
    a.curve('MirrorIndicator'+suffix,[(side*.963+.106*math.cos(t),1.072,.536+.015*math.sin(t))
              for t in [mix(.18,math.pi-.18,i/40) for i in range(41)]],.0024,signal,parent)

a.surface('Hood',lambda u,v:hood_surface(2*u-1,v),76,64,paint,solid=.006,normal=(0,1,.1))
for side in [-1,1]:
    a.curve('HoodShutLine',[(lambda p:(p[0]-side*.002,p[1]-.004,p[2]))(hood_surface(side,i/100)) for i in range(101)],.0016,seal)
# The windshield, roof and rear glass share one C1 longitudinal profile.
for name,mat in [('FrontWindscreen',glass),('RoofSkin',paint),('RearWindscreen',glass)]:
    limit=.958 if mat==glass else 1
    skin=a.surface(name,lambda u,v,name=name,limit=limit:cab_panel_surface(name,(2*u-1)*limit,v),
                   52,48,mat,solid=.004 if mat==glass else .006,normal=(0,1,0))
    skin.data.set_sharp_from_angle(angle=math.radians(35))
    if mat==glass:
        for side in [-1,1]:
            border=a.surface(name+'PaintBorder',lambda u,v,name=name,side=side:cab_panel_surface(name,side*mix(.958,1,u),v),
                             6,48,paint,solid=.006,normal=(side,.4,0))
            border.data.set_sharp_from_angle(angle=math.radians(35))
        for end in [0,1]:
            a.curve(name+'Seal',[(lambda p:(p[0],p[1]-.0015,p[2]))(cab_panel_surface(name,mix(-.958,.958,t),end)) for t in [i/66 for i in range(67)]],.002,seal)
a.box('Underbody',(0,.174,-.085),(1.48,.025,3.981),seal,radius=.025)

from sedan_03_front import build_front
from sedan_03_rear import build_rear
from sedan_03_cabin import build_cabin
from sedan_03_wheels import build_wheels

build_front(globals())
trunk_hotspot=build_rear(globals())
build_cabin(globals())
build_wheels(globals())

manifest={
    'schemaVersion':1,'vehicleId':'sedan-03','assetVersion':'1.1.0','units':'meter','forward':'+Z',
    'framing':{'target':[0,.670,-.153],'direction':[1.2,.46,1.65],'distance':7.669},
    'joints':{key:{'node':joint.name,'axis':[0,1,0],'openAngle':math.radians(-67 if 'Left' in key else 67)} for key,joint in doors.items()},
    'frontWheels':['wheel_frontLeft','wheel_frontRight'],
    'lights':{'head':['Headlamp'],'tail':['Taillamp'],'left':['SignalLeft'],'right':['SignalRight']},
    'headlights':[{'position':[x,.818,2.135],'target':[x,.06,8.2]} for x in [-.712,.712]],
    'hotspots':[],
}
manifest['joints']['trunk']={'node':'trunk','axis':[1,0,0],'openAngle':math.radians(72)}
labels={'frontLeft':'左前門','frontRight':'右前門','rearLeft':'左後門','rearRight':'右後門'}
for key,joint in doors.items():
    side=1 if 'Left' in key else -1
    z=-.265 if key.startswith('front') else -1.210
    y=belt(z)-.116
    world=(side*(side_x(y,z)+.029),y,z)
    origin=joint['origin_carvue']
    manifest['hotspots'].append({'id':key,'node':joint.name,'position':[world[i]-origin[i] for i in range(3)],'label':labels[key]})
manifest['hotspots'] += [
    {'id':'trunk','node':'trunk','position':trunk_hotspot,'label':'行李廂'},
    {'id':'headlights','node':'VehicleRoot','position':[.724,.849,2.120],'label':'車輛照明'},
]
a.export(manifest,{
    'dimensionsMeters':[4.751,1.820,1.440],'wheelbaseMeters':2.865,
    'frontTyre':'225/45 R18','rearTyre':'245/40 R18','wheelDesign':'Study silver paired multi-spoke',
    'construction':'Independent Study longitudinal and transverse fields; native physical-grid apertures and shared lamp/deck boundaries',
    'closedTransforms':'GLB local transforms are the closed pose; manifest motion is relative to each articulated node.',
    'qualityStatus':'Initial independent reconstruction; not visually approved. Requires external shape, articulation and WebGL review.',
})
