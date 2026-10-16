"""Measure Study source clearances and shared end tangents without Blender."""
import json
import math
from pathlib import Path

from sedan_03_surfaces import (side_x,end_point,front_z,rear_z,interior_outer_limit,hood_surface,
                             cab_surface,cab_edge,cab_panel_surface,roof_boundary,glass_x,deck_surface,polygon_distance,
                             FRONT_RADIUS,FRONT_WHEEL_CENTRE_X,FRONT_TYRE_WIDTH,front_wheelhouse_inner_x,
                             wheelhouse_liner_outer_x)
from sedan_03_front import lamp_loop,projector_layout,rounded_point,drl_outline


def unit(v):
    length=math.sqrt(sum(n*n for n in v))
    return tuple(n/length for n in v)


def cross(a,b):
    return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])


def derivative(fn,value,h):
    a,b=fn(value-h),fn(value+h)
    return tuple((b[i]-a[i])/(2*h) for i in range(3))


tangents=[]
for front in [True,False]:
    depth=front_z if front else rear_z
    for y in [.25,.40,.55,.70,.85]:
        edge=end_point(front,y)
        z=edge[2]+(-1 if front else 1)*.00010
        dz=(side_x(y,z+.000001)-side_x(y,z-.000001))/.000002
        dy=(side_x(y+.000001,z)-side_x(y-.000001,z))/.000002
        side_normal=unit((1,-dy,-dz))
        angle=math.pi/2-.00010
        def cap(a,h):
            x=end_point(front,h)[0]*math.sin(a)
            return x,h,depth(x,h)
        cap_normal=unit(cross(derivative(lambda a:cap(a,y),angle,.000001),
                              derivative(lambda h:cap(angle,h),y,.000001)))
        if cap_normal[0]<0:
            cap_normal=tuple(-n for n in cap_normal)
        difference=math.degrees(math.acos(max(-1,min(1,sum(a*b for a,b in zip(side_normal,cap_normal))))))
        assert difference<.2,(front,y,difference)
        tangents.append({'end':'front' if front else 'rear','height':y,'normalAngleDegrees':difference})

clearances=[]
for front in [True,False]:
    z=.007 if front else -.951
    for name,y,height,length,width,old_x in [
        ('pocket',.354,.105,.427 if front else .281,.069,.753),
        ('armrest',.633,.064,.520 if front else .399,.141,.724)]:
        outer=interior_outer_limit(y,height,z,length)
        skin=min(side_x(y+height*(j/60-.5),z+length*(i/128-.5)) for j in range(61) for i in range(129))
        clearance=skin-outer
        assert clearance>.0699,(front,name,clearance)
        clearances.append({'door':'front' if front else 'rear','component':name,
                           'oldClearanceMm':(skin-old_x-width/2)*1000,'newClearanceMm':clearance*1000})

lamp_margin=min(end_point(True,y)[0]-abs(x) for x,y in lamp_loop(1))
assert lamp_margin>.009,lamp_margin
lamp=lamp_loop(1)
cup_margin=min(-polygon_distance(*rounded_point(*module,math.tau*i/180),lamp)-.0028
               for module in projector_layout() for i in range(180))
drl_margin=min(-polygon_distance(x,y,lamp)-.006 for x,y in drl_outline(1))
assert cup_margin>.003 and drl_margin>.0004,(cup_margin,drl_margin)
front_base_gap=max(math.dist(hood_surface(i/40,0),cab_surface(i/40,.73)) for i in range(-40,41))
rear_base_gap=max(abs(deck_surface(i/40,0)[1]-cab_surface(deck_surface(i/40,0)[0]/glass_x(cab_edge(-1.90),-1.90),-1.90)[1])
                  for i in range(-40,41))
assert front_base_gap<1e-8 and rear_base_gap<1e-8,(front_base_gap,rear_base_gap)
roof_junctions=[]
for first,second,front in [('FrontWindscreen','RoofSkin',True),('RoofSkin','RearWindscreen',False)]:
    gaps=[];angles=[];crowns=[]
    for i in range(-50,51):
        t=i/50
        gaps.append(math.dist(cab_panel_surface(first,t,1),cab_panel_surface(second,t,0)))
        normals=[]
        for panel,v in [(first,1),(second,0)]:
            du=derivative(lambda u:cab_panel_surface(panel,u,v),t,.000001)
            dv=derivative(lambda w:cab_panel_surface(panel,t,w),v,.000001)
            normals.append(unit(cross(du,dv)))
        angles.append(math.degrees(math.acos(max(-1,min(1,sum(a*b for a,b in zip(*normals)))))))
        z=roof_boundary(front,t)
        crowns.append(cab_surface(0,z)[1]-cab_surface(1,z)[1])
    assert max(gaps)<1e-8 and max(angles)<.02 and max(crowns)<.010,(gaps,angles,crowns)
    roof_junctions.append({'panels':[first,second],'maximumBoundaryGapMm':max(gaps)*1000,
                           'maximumNormalAngleDegrees':max(angles),'maximumEndCrownMm':max(crowns)*1000,
                           'sharedCentreBowMm':45})
roof_height=max(cab_surface(0,-1.90+2.63*i/10000)[1] for i in range(10001))
assert abs(roof_height-1.44)<1e-6,roof_height
wall_x=front_wheelhouse_inner_x()
steering_samples=[]
for degrees in range(-30,31):
    angle=math.radians(degrees)
    # Every rotated tyre point lies inside this conservative bounding cylinder.
    inner=FRONT_WHEEL_CENTRE_X-(FRONT_RADIUS+.0006)*abs(math.sin(angle))-FRONT_TYRE_WIDTH*.5*abs(math.cos(angle))
    clearance=inner-wall_x
    assert clearance>=.020-1e-12,(degrees,clearance)
    steering_samples.append({'degrees':degrees,'innerEnvelopeX':inner,'wallClearanceMm':clearance*1000})
steering={'coordinateConvention':'Absolute X; reflected symmetrically for the right front wheel.',
          'frontWheelCentreX':FRONT_WHEEL_CENTRE_X,'nominalTyreRadius':FRONT_RADIUS,
          'outerEnvelopeRadiusIncludingTread':FRONT_RADIUS+.0006,'tyreHalfWidth':FRONT_TYRE_WIDTH*.5,
          'limitDegrees':30,'minimumInnerEnvelopeX':min(p['innerEnvelopeX'] for p in steering_samples),
          'fixedWallX':wall_x,'minimumClearanceMm':min(p['wallClearanceMm'] for p in steering_samples),
          'rearFixedWallXUnchanged':.630,'samples':steering_samples}
liner_checks=[]
for name,axle,radius,half_width in [('front',1.4325,FRONT_RADIUS,FRONT_TYRE_WIDTH/2),('rear',-1.4325,.3266,.245/2)]:
    def edge(u):
        angle=-.4+(math.pi+.8)*u
        y=radius+.382*math.sin(angle);z=axle+.382*math.cos(angle)
        return wheelhouse_liner_outer_x(y,z),y,z
    liner_clearances=[];minimum_radial=1
    for i in range(76):
        start,end=edge(i/76),edge((i+1)/76)
        for j in range(41):
            fraction=j/40
            x,y,z=tuple(start[k]+(end[k]-start[k])*fraction for k in range(3))
            liner_clearances.append(side_x(y,z)-.004-x)
            minimum_radial=min(minimum_radial,math.hypot(y-radius,z-axle))
    # A rigid rotation cannot exceed this tyre bounding sphere; the YZ projection
    # is smaller, so the complete tub remains clear for every steering angle.
    tyre_sphere=math.hypot(radius+.0006,half_width)
    assert min(liner_clearances)>.003-1e-9,(name,min(liner_clearances))
    assert minimum_radial-tyre_sphere>.030,(name,minimum_radial,tyre_sphere)
    widths=[edge(i/1000)[0]-.672 for i in range(1001)]
    assert min(widths)>.10,(name,min(widths))
    liner_checks.append({'axle':name,'samplesOnActualAngularMeshEdges':len(liner_clearances),
                         'bodyInwardThicknessMm':4,'minimumInnerBodySurfaceClearanceMm':min(liner_clearances)*1000,
                         'minimumTubWidthMm':min(widths)*1000,'minimumRenderedTubRadius':minimum_radial,
                         'tyreBoundingSphereRadius':tyre_sphere,
                         'minimumTyreRadialClearanceMm':(minimum_radial-tyre_sphere)*1000,
                         'frontInnerWallUnchanged':name=='front','method':'Outer edge uses a C1 smooth minimum with an 8 mm transition. Positive radial width and monotone angular sampling preclude folded tub faces; actual straight mesh edges are sampled against the inward body surface.'})
report={'scope':'Current Python surface definitions only; new Blender mesh and visual result remain unverified.',
        'status':'passed','endTangentSamples':tangents,'interiorClearances':clearances,
        'headlampMinimumOuterEdgeClearanceMm':lamp_margin*1000,'frontSteeringEnvelope':steering,
        'projectorRimMinimumHousingClearanceMm':cup_margin*1000,'drlTrimMinimumHousingClearanceMm':drl_margin*1000,
        'frontGlassHoodSharedBoundaryGapMm':front_base_gap*1000,'rearGlassDeckSharedBoundaryGapMm':rear_base_gap*1000,
        'roofSharedJunctions':roof_junctions,'roofMaximumHeightMm':roof_height*1000,
        'fixedWheelhouseLinerClearances':liner_checks}
output=Path(__file__).resolve().parents[2]/'assets/source/sedan-03/surface-checks.json'
output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'status':report['status'],'maximumNormalAngleDegrees':max(p['normalAngleDegrees'] for p in tangents),
                  'minimumInteriorClearanceMm':min(p['newClearanceMm'] for p in clearances),
                  'headlampMinimumEdgeClearanceMm':lamp_margin*1000,
                  'frontSteeringMinimumClearanceMm':steering['minimumClearanceMm'],
                  'frontInnerWallX':wall_x},indent=2))
