"""Ten-spoke 16-inch alloy geometry based on the Taiwan Hybrid wheel close-up."""
import math
import bpy


def build_alloy(center, side, parent, context):
    mesh = context['mesh']
    lathe = context['lathe_x']
    curve = context['curve']
    alloy = bpy.data.materials.get('WheelCastAlloy') or context['material']('WheelCastAlloy',(.64,.65,.67),.80,.28)
    chrome = context['chrome']
    dark = context['dark_alloy']
    black = context['black']
    bp = context['bp']
    cx, cy, cz = center

    # Each radius has an outer width and an independent raised center ridge.
    sections = [(.039,.005,.104),(.064,.009,.112),(.108,.014,.124),
                (.163,.026,.126),(.199,.032,.118),(.216,.033,.111)]
    cross = [-1,-.72,-.45,0,.45,.72,1]
    for spoke in range(10):
        angle = spoke*math.tau/10+math.pi/10
        vertices = []
        for radius, width, ridge in sections:
            for fraction in cross:
                lateral = width*fraction
                bevel=max(0,(abs(fraction)-.45)/.55)
                relief=.007*(1-max(0,(radius-.199)/.017))
                depth = ridge-relief*bevel
                vertices.append((cx+side*depth,
                                 cy+radius*math.cos(angle)-lateral*math.sin(angle),
                                 cz+radius*math.sin(angle)+lateral*math.cos(angle)))
        rows, cols = len(sections), len(cross)
        faces = []
        for row in range(rows-1):
            for col in range(cols-1):
                i = row*cols+col
                faces.append((i,i+1,i+cols+1,i+cols))
        # Deep edges are part of the opening, with visible cast walls.
        for edge in [0,cols-1]:
            wall = []
            for row,(radius,width,ridge) in enumerate(sections):
                original = vertices[row*cols+edge]
                wall.append(len(vertices))
                vertices.append((cx+side*.071,original[1],original[2]))
            for row in range(rows-1):
                faces.append((row*cols+edge,(row+1)*cols+edge,wall[row+1],wall[row]))
        mesh('SculptedTenSpoke',vertices,faces,alloy,parent)

    lathe('RimMachinedLip',center,[(side*.103,.203),(side*.111,.211),
          (side*.113,.217),(side*.110,.220)],chrome,parent,80)
    hub = lathe('AlloyBoltWeb',center,[(side*.067,.034),(side*.067,.080),
                (side*.096,.081),(side*.107,.059),(side*.103,.034),(side*.067,.034)],alloy,parent,80)
    # Through holes expose recessed bolt cups. They are not painted dark discs.
    for index in range(5):
        a = index*math.tau/5
        bolt_y = cy+.057*math.cos(a)
        bolt_z = cz+.057*math.sin(a)
        bpy.ops.mesh.primitive_cylinder_add(vertices=24,radius=.0135,depth=.095,
            location=bp((cx+side*.095,bolt_y,bolt_z)),rotation=(0,math.pi/2,0))
        cutter = bpy.context.object
        mod = hub.modifiers.new('Recessed bolt opening','BOOLEAN')
        mod.operation = 'DIFFERENCE'
        mod.solver = 'EXACT'
        mod.object = cutter
        context['modifier_apply'](hub,mod)
        bpy.data.objects.remove(cutter,do_unlink=True)
        bolt_center = (cx,bolt_y,bolt_z)
        lathe('BoltSeat',bolt_center,[(side*.105,.0138),(side*.097,.014),
              (side*.078,.0108),(side*.076,.008)],dark,parent,28)
        lathe('LugBolt',bolt_center,[(side*.077,0),(side*.077,.008),
              (side*.090,.008),(side*.091,0)],chrome,parent,6)
    lathe('HubBadge',center,[(side*.098,0),(side*.098,.031),
          (side*.104,.031),(side*.105,0)],black,parent,48)
    for radius in [.0315]:
        curve('HubBadgeRing',[(cx+side*.106,cy+radius*math.cos(i*math.tau/40),
              cz+radius*math.sin(i*math.tau/40)) for i in range(40)],.0012,chrome,parent,True)
