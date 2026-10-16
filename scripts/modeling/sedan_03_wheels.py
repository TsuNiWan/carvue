"""Study 18-inch paired multi-spoke wheels with the specified staggered tyres."""
import math
from sedan_03_surfaces import (AXLES,FRONT_RADIUS,REAR_RADIUS,FRONT_WHEEL_CENTRE_X,
                             FRONT_TYRE_WIDTH,mix,profile)


def tyre_radius_at(v,radius):
    section=((0,.229),(.05,.230),(.12,.245),(.21,radius-.024),(.34,radius-.003),
             (.44,radius),(.56,radius),(.66,radius-.003),(.79,radius-.024),(.88,.245),(.95,.230),(1,.229))
    return profile(section,v)


def tyre_mesh_radius(v,angle,radius):
    """Return the radial intersection with the actual 104 by 32 tyre mesh."""
    scaled=max(0,min(32,v*32))
    cell=min(31,int(scaled))
    radial=mix(tyre_radius_at(cell/32,radius),tyre_radius_at((cell+1)/32,radius),scaled-cell)
    step=math.tau/104
    return radial*math.cos(step/2)/math.cos(angle%step-step/2)


def build_wheels(c):
    a,root=c['a'],c['root']
    brake=a.material('BrakeDisc',(.31,.33,.35),.78,.40)
    for side,suffix in [(1,'Left'),(-1,'Right')]:
        for row,axle,radius,tyre_width in [('front',AXLES[0],FRONT_RADIUS,FRONT_TYRE_WIDTH),('rear',AXLES[1],REAR_RADIUS,.245)]:
            centre_x=side*(FRONT_WHEEL_CENTRE_X if row=='front' else .777)
            wheel=a.group('wheel_'+row+suffix,(centre_x,radius,axle),root)
            outer=abs(centre_x)+tyre_width*.47
            a.surface('Tyre'+row+suffix,lambda u,v:(centre_x+mix(-tyre_width*.5,tyre_width*.5,v),
                      radius+tyre_radius_at(v,radius)*math.cos(math.tau*u),axle+tyre_radius_at(v,radius)*math.sin(math.tau*u)),
                      104,32,c['rubber'],wheel)
            def tread_point(fraction,angle):
                radial=tyre_mesh_radius(fraction,angle,radius)+.00006
                return (centre_x+tyre_width*(fraction-.5),radius+radial*math.cos(angle),axle+radial*math.sin(angle))
            for offset in [-.19,-.07,.07,.19]:
                a.surface('TreadChannel',lambda u,v,offset=offset:tread_point(.5+offset+(v-.5)*.0012/tyre_width,math.tau*u),
                          104,1,c['seal'],wheel)
            for i in range(64):
                angle=math.tau*i/64
                a.surface('TreadSipe',lambda u,v,angle=angle:tread_point(.25+.5*u,
                          angle+.025*math.sin(math.pi*u)+(v-.5)*.0009/radius),16,1,c['seal'],wheel)
            a.surface('WheelBarrel',lambda u,v:(side*mix(abs(centre_x)-tyre_width*.41,outer,v),
                      radius+.222*math.cos(math.tau*u),axle+.222*math.sin(math.tau*u)),
                      80,7,c['alloy'],wheel)
            for r,tube in [(.2255,.004),(.218,.0023),(.059,.003)]:
                c['ring_x']('StudyRim',(side*outer,radius,axle),r,tube,c['alloy'],wheel)
            a.surface('BrakeRotor',lambda u,v:(side*(outer-.046),radius+mix(.045,.170,v)*math.cos(math.tau*u),
                      axle+mix(.045,.170,v)*math.sin(math.tau*u)),72,9,brake,wheel,solid=.010,normal=(side,0,0))
            a.box('BrakeCaliper',(side*(outer-.040),radius+.013,axle+.132),(.036,.107,.047),c['dark_metal'],wheel,radius=.014)
            for pair in range(10):
                angle=math.tau*pair/10+.025
                for branch in [-1,1]:
                    def spoke(u,v,angle=angle,branch=branch):
                        r=mix(.051,.221,u)
                        direction=angle+branch*mix(.031,.065,smooth_spread(u))
                        half=profile(((0,.008),(.15,.007),(.72,.0045),(1,.0055)),u)
                        tangent=(2*v-1)*half
                        x=outer-.025*(1-u)**2+.0025*(1-abs(2*v-1))*math.sin(math.pi*u)
                        return side*x,radius+r*math.cos(direction)-tangent*math.sin(direction),axle+r*math.sin(direction)+tangent*math.cos(direction)
                    a.surface('StudyPairedSpoke',spoke,19,5,c['alloy'],wheel,solid=.009,normal=(side,0,0))
            c['ellipsoid']('StudyHub',(side*(outer-.015),radius,axle),(.009,.054,.054),c['alloy'],wheel,32,16)
            for i in range(5):
                angle=math.tau*i/5
                yy=radius+.043*math.cos(angle);zz=axle+.043*math.sin(angle)
                c['ring_x']('BoltWell',(side*(outer-.004),yy,zz),.0077,.0019,c['black'],wheel,24)
                c['ellipsoid']('WheelBolt',(side*(outer-.003),yy,zz),(.0035,.0056,.0056),c['chrome'],wheel,14,8)



def smooth_spread(t):
    return t*t*(3-2*t)
