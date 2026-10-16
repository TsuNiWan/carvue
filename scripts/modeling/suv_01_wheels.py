"""235/60 R18 tyres and the Study black five split-pair alloy design."""
import math


def build_wheels(c):
    a,root=c['author'],c['root']
    mix,profile=c['mix'],c['profile']
    black,metal,rubber=c['black'],c['wheelmetal'],c['rubber']
    brake=a.material('BrakeDisc',(.30,.32,.34),.78,.43)
    caliper=a.material('Caliper',(.31,.34,.35),.5,.40)
    for side,suffix in [(1,'Left'),(-1,'Right')]:
        for axle,row in [(1.35,'front'),(-1.35,'rear')]:
            centre=(side*.806,.3696,axle)
            wheel=a.group('wheel_'+row+suffix,centre,root)
            steering_limit=math.radians(30)
            inner_wall=(.806-.3696*math.sin(steering_limit)-.1175*math.cos(steering_limit)-.020
                        if row=='front' else .590)
            # A fixed molded wheel-house liner closes the view into the body cavity.
            def wheel_house(u,v,side=side,axle=axle,row=row,inner_wall=inner_wall):
                angle=mix(-.30,math.pi+.30,u)
                yy=.3696+(.428-.006*v)*math.sin(angle)
                zz=axle+(.428-.006*v)*math.cos(angle)
                # The rear door cove is narrower than a constant-width liner.
                outer=.906 if row=='front' else min(.906,c['side_x'](zz,yy)-.020)
                return side*mix(inner_wall,outer,v),yy,zz
            a.surface('WheelHouseLiner'+row+suffix,
                      wheel_house,
                      112,12,black,root,.006,normal=(0,-1,0))
            a.surface('WheelHouseInnerWall'+row+suffix,
                      lambda u,v,side=side,axle=axle,inner_wall=inner_wall:(
                          side*inner_wall,
                          .3696+.428*v*math.sin(mix(-.30,math.pi+.30,u)),
                          axle+.428*v*math.cos(mix(-.30,math.pi+.30,u))),
                      112,18,black,root,.007,normal=(side,0,0))
            # Cross-section includes rounded shoulders, sidewall and a flattened tread crown.
            tyre_section=[(0,-.105,.2286),(.06,-.116,.245),(.16,-.1175,.300),
                          (.25,-.110,.343),(.33,-.095,.366),(.41,-.070,.3696),(.50,0,.3696),
                          (.59,.070,.3696),(.67,.095,.366),(.75,.110,.343),
                          (.84,.1175,.300),(.94,.116,.245),(1,.105,.2286)]
            def tyre(u,v):
                angle=u*math.tau
                radius=profile([(t,r) for t,x,r in tyre_section],v)
                xx=profile([(t,x) for t,x,r in tyre_section],v)
                return centre[0]+xx,centre[1]+radius*math.cos(angle),centre[2]+radius*math.sin(angle)
            a.surface('Tyre'+row+suffix,tyre,112,44,rubber,wheel)
            # Circumferential grooves and subtle tread blocks retain a thick SUV tyre reading.
            def tread_radius(offset):
                return profile([(-.095,.366),(-.070,.3696),(.070,.3696),(.095,.366)],offset)
            for offset in [-.075,-.027,.027,.075]:
                c['ring']('TreadGroove',(centre[0]+offset,centre[1],centre[2]),tread_radius(offset)-.0004,.0010,black,wheel,count=108)
            for k in range(78):
                angle=k*math.tau/78
                coords=[]
                for i in range(5):
                    offset=mix(-.093,.093,i/4)
                    aa=angle+.033*math.sin(math.pi*i/4)
                    radius=tread_radius(offset)+.0001
                    coords.append((centre[0]+offset,centre[1]+radius*math.cos(aa),centre[2]+radius*math.sin(aa)))
                a.curve('TreadSipe',coords,.0009,black,wheel)
            face_x=side*.918
            for radius,tube in [(.225,.005),(.211,.003),(.068,.004)]:
                c['ring']('RimLip',(face_x,centre[1],axle),radius,tube,metal,wheel,count=88)
            # Barrel is a proper deep cylinder, open between the cast spokes.
            a.surface('RimBarrel',lambda u,v:(side*mix(.755,.916,v),centre[1]+.217*math.cos(u*math.tau),axle+.217*math.sin(u*math.tau)),
                      88,8,metal,wheel)
            a.surface('BrakeRotor',lambda u,v:(side*.859,centre[1]+mix(.050,.174,v)*math.cos(u*math.tau),
                                                axle+mix(.050,.174,v)*math.sin(u*math.tau)),
                      80,10,brake,wheel,solid=.011,normal=(side,0,0))
            a.box('BrakeCaliper',(side*.865,centre[1]+.012,axle+.142),(.048,.112,.055),caliper,wheel,radius=.018)
            # Each of five spokes branches into a closely spaced pair, not ten equal angles.
            for group in range(5):
                for branch in [-1,1]:
                    base=group*math.tau/5+math.pi/2
                    def spoke(u,v,base=base,branch=branch):
                        r=mix(.063,.219,u)
                        spread=mix(.072,.164,u)
                        angle=base+branch*spread
                        width=profile([(0,.011),(.2,.010),(.56,.013),(.88,.015),(1,.018)],u)
                        tangent=(2*v-1)*width
                        yy=centre[1]+r*math.cos(angle)-tangent*math.sin(angle)
                        zz=axle+r*math.sin(angle)+tangent*math.cos(angle)
                        face=.897+.021*math.sin(math.pi*u/2)+.004*(1-abs(2*v-1))*math.sin(math.pi*u)
                        return side*face,yy,zz
                    a.surface('SplitSpoke',spoke,25,8,metal,wheel,.013,(side,0,0))
            c['ellipsoid']('WheelHub',(side*.907,centre[1],axle),(.009,.061,.061),metal,wheel,nu=42,nv=20)
            for k in range(5):
                aa=k*math.tau/5+math.pi/2
                yy=centre[1]+.050*math.cos(aa);zz=axle+.050*math.sin(aa)
                c['ring']('BoltSeat',(side*.916,yy,zz),.009,.002,black,wheel,count=24)
                c['ellipsoid']('WheelBolt',(side*.916,yy,zz),(.004,.006,.006),c['chrome'],wheel,nu=16,nv=10)
            # Flat centre cap with the Study H and a restrained metallic edge.
            c['ring']('CentreCap',(side*.920,centre[1],axle),.023,.002,c['chrome'],wheel,count=36)
            for offset in [-.009,.009]:
                a.curve('HubH',[(side*.921,centre[1]-.014,axle+offset*1.15),(side*.921,centre[1]+.014,axle+offset)],.0024,c['chrome'],wheel)
            a.curve('HubHCross',[(side*.921,centre[1],axle-.009),(side*.921,centre[1],axle+.009)],.0024,c['chrome'],wheel)
