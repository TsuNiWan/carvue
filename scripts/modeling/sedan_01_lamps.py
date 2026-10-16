"""Recessed, continuously wrapped Study rear lamps and optical layers."""
import math
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform

_surface_references=[]


def carve_surface(name, fn, panels, depth, direction, context, nu=24, nv=12):
    """Cut the painted shell and return the same boundary's recessed surface."""
    mesh = context['mesh']
    outside = .012
    vertices = []
    for offset in [outside,-depth]:
        for j in range(nv+1):
            for i in range(nu+1):
                u,v=i/nu,j/nv
                p=Vector(fn(u,v))
                n=Vector(direction(u,v)).normalized()
                vertices.append(tuple(p+n*offset))
    count=(nu+1)*(nv+1)
    faces=[]
    for j in range(nv):
        for i in range(nu):
            a=j*(nu+1)+i
            faces.extend([(a,a+1,a+nu+2,a+nu+1),
                          (a+count,a+nu+1+count,a+nu+2+count,a+1+count)])
    perimeter=list(range(nu+1))+[j*(nu+1)+nu for j in range(1,nv+1)]
    perimeter += [nv*(nu+1)+i for i in range(nu-1,-1,-1)]
    perimeter += [j*(nu+1) for j in range(nv-1,0,-1)]
    faces += [(a,b,b+count,a+count) for a,b in zip(perimeter,perimeter[1:]+perimeter[:1])]
    cutter=mesh(name+'Cutter',vertices,faces,context['black'])
    bounds=[(min(p[i] for p in vertices)-.025,max(p[i] for p in vertices)+.025) for i in range(3)]
    for panel in panels:
        if panel is None: continue
        bpy.context.view_layer.update()
        panel.data.calc_loop_triangles()
        positions=[panel.matrix_world@v.co for v in panel.data.vertices]
        normals=[(panel.matrix_world.to_3x3()@v.normal).normalized() for v in panel.data.vertices]
        triangles=[tuple(t.vertices) for t in panel.data.loop_triangles]
        tree=BVHTree.FromPolygons(positions,triangles,all_triangles=True)
        _surface_references.append((panel.parent.name,tree,positions,normals,triangles,bounds))
        mod=panel.modifiers.new(name+' opening','BOOLEAN')
        mod.operation='DIFFERENCE'
        mod.solver='EXACT'
        mod.object=cutter
        context['modifier_apply'](panel,mod)
    bpy.data.objects.remove(cutter,do_unlink=True)


def restore_panel_normals(context):
    """Preserve the original curved skin normals after topological cutouts.

    Boolean return walls keep their geometric normals. Only surviving exterior
    points on the source skin receive interpolated normals from that skin.
    """
    for obj in bpy.data.objects:
        if obj.type!='MESH' or not obj.data.materials or obj.data.materials[0].name!='BodyPaint':
            continue
        refs=[item for item in _surface_references if item[0]==obj.parent.name]
        if not refs: continue
        bpy.context.view_layer.update()
        normals=[tuple(n.vector) for n in obj.data.corner_normals]
        for polygon in obj.data.polygons:
            for loop_index in polygon.loop_indices:
                loop=obj.data.loops[loop_index]
                point=obj.matrix_world@obj.data.vertices[loop.vertex_index].co
                orbit=(point.x,point.z,-point.y)
                for _,tree,positions,source_normals,triangles,bounds in refs:
                    if any(orbit[i]<bounds[i][0] or orbit[i]>bounds[i][1] for i in range(3)):
                        continue
                    near,_,index,distance=tree.find_nearest(point)
                    if near is None or distance>.0025: continue
                    a,b,c=triangles[index]
                    normal=barycentric_transform(near,positions[a],positions[b],positions[c],source_normals[a],source_normals[b],source_normals[c]).normalized()
                    if normal.dot(polygon.normal)>.50:
                        normals[loop_index]=tuple(normal)
                        break
        obj.data.normals_split_custom_set(normals)


def build_rear_lamp(side, corner, context):
    surface=context['surface_grid']; curve=context['curve']
    mapped=context['mapped_patch']; material=context['material']
    root=context['root']; trunk=context['trunk']
    body_x=context['body_x']; interpolate=context['interpolate']
    rear_shoulder=context['rear_shoulder']; side_boundary=context['rear_side_boundary']
    fascia=context['trunk_fascia']
    tail=context['tail']; chrome=context['chrome']; black=context['black']
    clear=context['tail_clear']
    cavity=bpy.data.materials.get('TailLampCavity') or material('TailLampCavity',(.09,.009,.015),.22,.24)
    cover=bpy.data.materials.get('TailLampCover') or material('TailLampCover',(.24,.05,.058),.0,.15,alpha=.13)

    def lower_edge(u):
        return interpolate([(0,.886),(.56,.880),(.76,.913),(1,.957)],u)

    def upper_edge(u):
        return interpolate([(0,1.008),(.56,1.000),(.80,.985),(1,.966)],u)

    def boundary(u,v):
        low=lower_edge(u)
        high=upper_edge(u)
        y=low+(high-low)*v
        if u<=.56:
            p=rear_shoulder(u/.56,max(0,min(1,(y-.645)/.389)),side)
            return (p[0],y,p[2])
        fraction=(u-.56)/.44
        _,z0=side_boundary(y)
        z=z0+.265*fraction
        return(body_x(y,z,side),y,z)

    def normal(u,v):
        a=Vector(boundary(max(0,u-.001),v)); b=Vector(boundary(min(1,u+.001),v))
        c=Vector(boundary(u,max(0,v-.001))); d=Vector(boundary(u,min(1,v+.001)))
        n=(b-a).cross(d-c).normalized()
        if n.dot(Vector((side,0,-1)))<0: n=-n
        return n

    # Build the surrounding skin from the exact lamp boundary. Native grid
    # borders avoid the long nonplanar polygons left by a Boolean cut.
    paint=context['paint']; belt=context['belt']; rear_skin=context['fixed_rear_corner']
    bpy.data.objects.remove(corner,do_unlink=True)
    for upper in [False,True]:
        def rear_band(u,v,upper=upper):
            if upper:
                low=upper_edge(.56*u)
                y=low+(1.034-low)*v
            else:
                y=.245+(lower_edge(.56*u)-.245)*v
            return rear_skin(u,(y-.245)/.789,side)
        surface('RearLampSurround',rear_band,28,24 if not upper else 6,paint,root,.017,normal=(side*.2,0,-1))
    quarter=bpy.data.objects.get('RearQuarter'+('L' if side>0 else 'R'))
    if quarter: bpy.data.objects.remove(quarter,do_unlink=True)
    for zone in ['lower','tip','upper']:
        def quarter_front(u,v,zone=zone):
            lower=.245 if zone=='lower' else lower_edge(1) if zone=='tip' else upper_edge(1)
            upper=lower_edge(1) if zone=='lower' else upper_edge(1) if zone=='tip' else 1.06
            y=lower+(upper-lower)*v
            last=-1.43
            for _ in range(5):
                first=side_boundary(y)[1]+.265
                fraction=max(0,min(1,(y-.245)/(belt(last)-.245)))
                last=context['rear_boundary'](fraction)-.002
                z=first+(last-first)*u
                if zone=='upper': y=lower+(belt(z)-lower)*v
            return(body_x(y,z,side),y,z)
        panel=surface('RearQuarter'+('L' if side>0 else 'R')+zone,quarter_front,30,24 if zone=='lower' else 6 if zone=='upper' else 2,paint,root,.017,normal=(side,0,0))
        context['cut_wheel_arches'](panel)
    for upper in [False,True]:
        def side_band(u,v,upper=upper):
            lamp_u=.56+.44*u
            low=upper_edge(lamp_u) if upper else .245
            high=1.06 if upper else lower_edge(lamp_u)
            for _ in range(4):
                y=low+(high-low)*v
                z=side_boundary(y)[1]+.265*u
                if upper: high=belt(z)
            return(body_x(y,z,side),y,z)
        surface('RearLampSideSurround',side_band,24,6 if upper else 24,paint,root,.017,normal=(side,0,0))

    def layer(u,v,depth):
        return tuple(Vector(boundary(u,v))+normal(u,v)*depth)

    surface('TailCavityBack',lambda u,v:layer(u,v,-.031),36,14,cavity,root,normal=(side,0,-1))
    for edge in [0,1]:
        surface('TailHousingReturn',lambda u,v,edge=edge:layer(u,edge,-.031*v),36,3,black,root)
        surface('TailHousingReturn',lambda u,v,edge=edge:layer(edge,v,-.031*u),3,14,black,root)
    # One swept guide has a rounded bend and a closed cross-section. It cannot
    # overlap a second sheet at the rear-to-side transition.
    path=[(.015+.325*i/14,.75) for i in range(15)]
    a=Vector((.34,.75)); b=Vector((.48,.75)); c=Vector((.49,.41)); d=Vector((.575,.19))
    for i in range(1,29):
        t=i/28
        uv=a*(1-t)**3+b*3*(1-t)**2*t+c*3*(1-t)*t*t+d*t**3
        path.append(tuple(uv))
    centers=[Vector(layer(u,v,-.004)) for u,v in path]
    vertices=[]
    profile=[(-1,-.004),(-.86,.001),(.86,.001),(1,-.004),(.86,-.010),(-.86,-.010)]
    for i,((u,v),center) in enumerate(zip(path,centers)):
        tangent=(centers[min(len(centers)-1,i+1)]-centers[max(0,i-1)]).normalized()
        n=normal(u,v)
        across=tangent.cross(n).normalized()
        half_width=.013+.004*max(0,(i-14)/(len(path)-15))
        vertices.extend(tuple(center+across*(width*half_width)+n*depth) for width,depth in profile)
    faces=[]; count=len(profile)
    for i in range(len(path)-1):
        for j in range(count):
            faces.append((i*count+j,i*count+(j+1)%count,(i+1)*count+(j+1)%count,(i+1)*count+j))
    faces.extend([tuple(range(count-1,-1,-1)),tuple((len(path)-1)*count+j for j in range(count))])
    context['mesh']('TailFoldedGuide',vertices,faces,tail,root)
    clear_outline=[(.025,.085),(.405,.085),(.44,.25),(.40,.39),(.35,.36),(.025,.28)]
    lens=mapped('TailLowerOptic',clear_outline,lambda u,v:layer(u,v,-.009),clear)
    context['thickness'](lens,.006)
    for row in [.16,.24]:
        curve('TailReflectorFlute',[layer(.03+.34*i/14,row,-.007) for i in range(15)],.0012,chrome)
    curve('TailLowerChrome',[layer(.01+.52*i/24,.035,-.002) for i in range(25)],.0018,chrome)
    surface('TailTransparentCover',lambda u,v:layer(u,v,.001),36,14,cover)

    def inner(u,v):
        x=side*(.335+.316*u)
        low=.962-.081*u
        high=.978+.020*u
        return fascia(x,low+(high-low)*v,0)
    # The inner lamp belongs to the trunk and receives its own true opening.
    rear=bpy.data.objects.get('TrunkRearPanel')
    carve_surface('TrunkLamp',inner,[rear],.023,lambda u,v:(0,0,-1),context,26,10)
    surface('TrunkLampBack',lambda u,v:tuple(Vector(inner(u,v))+Vector((0,0,.021))),26,10,cavity,trunk)
    for edge in [0,1]:
        surface('TrunkLampReturn',lambda u,v,edge=edge:tuple(Vector(inner(u,edge))+Vector((0,0,.021*v))),26,3,black,trunk)
    surface('TrunkRedGuide',lambda u,v:tuple(Vector(inner(.01+.98*u,.61+.27*v))+Vector((0,0,.003))),26,3,tail,trunk,.006)
    surface('TrunkClearLens',lambda u,v:tuple(Vector(inner(.025+.95*u,.07+.26*v))+Vector((0,0,.007))),26,5,clear,trunk,.005)
    surface('TrunkLampCover',lambda u,v:tuple(Vector(inner(u,v))+Vector((0,0,-.001))),26,10,cover,trunk)
    signal=context['left_signal'] if side>0 else context['right_signal']
    curve('TailSignal',[layer(.07+.32*i/14,.22,-.003) for i in range(15)],.0035,signal)
