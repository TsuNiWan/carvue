"""Study glazing, independently hinged doors, Study cabin and cargo geometry."""
import math
import bpy

from suv_02_surfaces import (ARCH_RADIUS, REAR_AXLE, TYRE_RADIUS, arch_bottom, belt,
                         blend, corner_path, curved_plate, hood_surface, inset_plate, profile, rear_z, roof, sample_path, side,
                         skin, width, window_point, window_ring_sections, windshield_surface)


DOORS = {
    'front': (.853, -.323, (.812, 1.186), (.145, roof(.145, 1)[1] - .014),
              (-.437, roof(-.437, 1)[1] - .014), (-.306, 1.177)),
    'rear': (-.333, -1.353, (-.354, 1.181), (-.487, roof(-.487, 1)[1] - .014),
             (-1.238, roof(-1.238, 1)[1] - .014), (-1.335, 1.249)),
}


def panel_outline(sign, front, rear, offset=0):
    bottom = [skin(sign, front, rear, i / 40, 0, offset) for i in range(41)]
    back = [skin(sign, front, rear, 1, i / 20, offset) for i in range(1, 21)]
    top = [skin(sign, front, rear, 1 - i / 40, 1, offset) for i in range(1, 41)]
    forward = [skin(sign, front, rear, 0, 1 - i / 20, offset) for i in range(1, 20)]
    return bottom + back + top + forward


def create_door(author, mats, sign, kind):
    front, rear, bottom_front, top_front, top_rear, bottom_rear = DOORS[kind]
    suffix = kind + ('Left' if sign > 0 else 'Right')
    hinge = (sign * .865, 1.10, front)
    group = author.group('door_' + suffix, hinge, author.root)
    handle_z, handle_y = rear + .20, belt(rear + .20) - .111

    def door_skin(u, v):
        x, y, z = skin(sign, front, rear, u, v)
        distance = ((z - handle_z) / .111) ** 2 + ((y - handle_y) / .028) ** 2
        recess = .018 * max(0, 1 - distance) ** 2
        return (x - sign * recess, y, z)

    author.surface(suffix + 'SculptedSkin', door_skin, 88, 50, mats['paint'], group, .021,
                   normal=(sign, 0, 0))
    outer = panel_outline(sign, front, rear)
    author.surface(suffix + 'FoldedHem', lambda u, v: (
        outer[min(len(outer) - 1, int(u * (len(outer) - 1)))][0] - sign * v * .075,
        outer[min(len(outer) - 1, int(u * (len(outer) - 1)))][1],
        outer[min(len(outer) - 1, int(u * (len(outer) - 1)))][2]),
        len(outer) - 1, 2, mats['innerPaint'], group)
    author.curve(suffix + 'LowerSeal', [(x - sign * .054, y + .006, z) for x, y, z in outer],
                 .008, mats['rubber'], group, cyclic=True)
    glass_edges = [bottom_front, top_front, top_rear, bottom_rear]
    corners = [window_point(sign, z, y) for z, y in glass_edges]
    # The fixed aperture follows the entire opening, with no crossbar at belt height.
    aperture = [skin(sign, front, rear, i / 40, 0) for i in range(41)]
    aperture += [skin(sign, front, rear, 1, i / 20) for i in range(1, 21)]
    aperture += [corners[3], corners[2], corners[1], corners[0]]
    aperture += [skin(sign, front, rear, 0, 1 - i / 20) for i in range(21)]
    author.curve(suffix + 'BodyJamb', [(x - sign * .078, y, z) for x, y, z in aperture],
                 .021, mats['innerPaint'], author.root, cyclic=True)
    author.curve(suffix + 'BodyWeatherSeal', [(x - sign * .060, y, z) for x, y, z in aperture],
                 .009, mats['rubber'], author.root, cyclic=True)

    def glazing(u, v):
        left = tuple(blend(corners[0][i], corners[1][i], v) for i in range(3))
        right = tuple(blend(corners[3][i], corners[2][i], v) for i in range(3))
        return tuple(blend(left[i], right[i], u) + (sign * .005 * math.sin(math.pi * u)
                                                  * math.sin(math.pi * v) if i == 0 else 0)
                     for i in range(3))

    author.surface(suffix + 'Glass', glazing, 28, 18, mats['glass'], group, .004,
                   normal=(sign, 0, 0))
    def belt_shoulder(u, v):
        z = blend(front, rear, u)
        amount = (z - bottom_front[0]) / (bottom_rear[0] - bottom_front[0])
        glass_y = blend(bottom_front[1], bottom_rear[1], amount)
        lower = side(sign, z, belt(z))
        upper = window_point(sign, z, glass_y)
        return tuple(blend(lower[i], upper[i], v) for i in range(3))
    author.surface(suffix + 'WindowBeltShoulder', belt_shoulder, 64, 6,
                   mats['paint'], group, .008, normal=(sign, .4, 0))
    frame = []
    for a, b in zip(corners, corners[1:] + corners[:1]):
        frame.extend([tuple(blend(a[k], b[k], i / 12) for k in range(3)) for i in range(12)])
    author.curve(suffix + 'WindowFrame', frame, .011, mats['black'], group, cyclic=True)
    author.curve(suffix + 'WindowGasket', [(x + sign * .004, y, z) for x, y, z in frame],
                 .009, mats['rubber'], group, cyclic=True)
    author.curve(suffix + 'BeltChrome', [window_point(sign, blend(bottom_front[0], bottom_rear[0], i / 32),
                 blend(bottom_front[1], bottom_rear[1], i / 32) - .007, .012) for i in range(33)],
                 .007, mats['silver'], group)

    # Flush grip: a real recessed body surface plus a dark bowl and painted upper lip.
    outline = [side(sign, handle_z + .091 * math.cos(t), handle_y + .016 * math.sin(t), -.006)
               for t in [2 * math.pi * i / 64 for i in range(64)]]
    inset_plate(author, suffix + 'HandleRecess', outline, mats['black'], group, (sign, 0, 0), .003)
    author.curve(suffix + 'FlushHandleLip', [side(sign, handle_z + blend(-.085, .085, i / 20),
                 handle_y + .013, .0005) for i in range(21)], .0055, mats['paint'], group)
    author.curve(suffix + 'HandleUndercut', [side(sign, handle_z + blend(-.077, .077, i / 20),
                 handle_y - .009, -.004) for i in range(21)], .002, mats['rubber'], group)

    # Sculpted inner card, armrest, storage bin and angular Study handle bezel.
    author.surface(suffix + 'InnerCard', lambda u, v: (
        sign * (width(blend(front, rear, u), blend(arch_bottom(blend(front, rear, u)) + .04,
                 belt(blend(front, rear, u)) - .04, v)) - .089 - .022 * math.sin(math.pi * v)),
        blend(arch_bottom(blend(front, rear, u)) + .04, belt(blend(front, rear, u)) - .04, v),
        blend(front - .025, rear + .025, u)), 44, 24, mats['leather'], group, .012,
        normal=(-sign, 0, 0))
    midpoint = (front + rear) / 2
    author.box(suffix + 'Armrest', (sign * .780, .78, midpoint), (.105, .10, (front - rear) * .64),
               mats['leather'], group, .037)
    handle_inner_z = front - .16
    bezel = [(sign * .772, .982, handle_inner_z + .075), (sign * .772, .975, handle_inner_z - .175),
             (sign * .772, .835, handle_inner_z - .24), (sign * .772, .867, handle_inner_z + .05)]
    author.curve(suffix + 'InnerHandleBezel', bezel, .016, mats['silver'], group, cyclic=True)
    author.box(suffix + 'InnerPull', (sign * .758, .942, handle_inner_z - .035), (.018, .032, .15),
               mats['black'], group, .012)
    bin_front, bin_rear = front - .12, max(rear + .12, -1.075)
    bin_points = [(sign * .787, .43, bin_front), (sign * .684, .50, bin_front - .06),
                  (sign * .687, .52, bin_rear + .05), (sign * .797, .45, bin_rear)]
    author.curve(suffix + 'StorageRim', bin_points, .018, mats['leather'], group)
    inset_plate(author, suffix + 'StorageFloor', bin_points + [(sign * .805, .40, bin_front)],
                mats['black'], group, thickness=.025)
    author.box(suffix + 'WindowSwitch', (sign * .728, .835, midpoint + .12), (.042, .011, .105),
               mats['black'], group, .004)
    author.box(suffix + 'Latch', (sign * (width(rear + .008, .73) - .045), .73, rear + .008), (.026, .061, .021),
               mats['metal'], group, .004)
    for height in (.55, .92):
        author.box(suffix + 'Hinge', (sign * (width(front, height) - .055), height, front), (.045, .070, .042),
                   mats['metal'], group, .006)

    if kind == 'front':
        mirror_z = front - .12
        author.curve(suffix + 'MirrorStalk', [(sign * .877, 1.188, mirror_z),
                     (sign * .938, 1.207, mirror_z - .038)], .027, mats['black'], group)
        author.box(suffix + 'MirrorHousing', (sign * .984, 1.222, mirror_z - .043),
                   (.164, .112, .193), mats['paint'], group, .049)
        author.box(suffix + 'MirrorLower', (sign * .984, 1.188, mirror_z - .043),
                   (.156, .034, .181), mats['black'], group, .014)
        author.box(suffix + 'MirrorGlass', (sign * .988, 1.226, mirror_z - .145),
                   (.124, .073, .006), mats['mirror'], group, .022)
        author.curve(suffix + 'MirrorIndicator', [(sign * blend(.945, 1.046, i / 20),
                     1.22, mirror_z + .049 - .028 * math.sin(i / 20 * math.pi)) for i in range(21)],
                     .0045, mats['signalLeft' if sign > 0 else 'signalRight'], group)
    return group


def cabin_shell(author, mats):
    author.surface('RoofCrown', lambda u, v: roof(blend(-1.99, .21, v), 2 * u - 1),
                   50, 65, mats['paint'], solid=.026, normal=(0, 1, 0))
    author.surface('Headliner', lambda u, v: (roof(blend(-1.89, .15, v), (2 * u - 1) * .95)[0],
                   roof(blend(-1.89, .15, v), (2 * u - 1) * .95)[1] - .041,
                   blend(-1.89, .15, v)), 24, 24, mats['headliner'], normal=(0, -1, 0))

    author.surface('Windscreen', windshield_surface, 44, 28, mats['frontGlass'], solid=.005, normal=(0, .6, 1))
    author.surface('WindscreenCowl', lambda u, v: tuple(blend(hood_surface(u, 0)[i],
                   windshield_surface(u, 0)[i], v) for i in range(3)),
                   84, 6, mats['rubber'], solid=.008, normal=(0, 1, 0))
    for sign in (-1, 1):
        edge = [windshield_surface(1 if sign > 0 else 0, i / 28) for i in range(29)]
        door_lower, door_upper = DOORS['front'][2], DOORS['front'][3]
        side_lower = window_point(sign, *door_lower)
        side_upper = roof(door_upper[0], sign)
        def a_pillar(u, v):
            glass_edge = windshield_surface(1 if sign > 0 else 0, v)
            door_edge = tuple(blend(side_lower[i], side_upper[i], v) for i in range(3))
            return tuple(blend(glass_edge[i], door_edge[i], u) for i in range(3))
        author.surface('APillarPaintBridge', a_pillar, 6, 28, mats['paint'], solid=.018,
                       normal=(sign, .3, .4))
        author.surface('APillarInside', lambda u, v: (a_pillar(u, v)[0] - sign * .018,
                       a_pillar(u, v)[1] - .014, a_pillar(u, v)[2] - .012),
                       6, 28, mats['headliner'], normal=(-sign, -.3, -.4))
        author.curve('WindscreenEdgeSeal', edge, .005, mats['rubber'])
        author.curve('RoofRail', [(roof(blend(-1.80, .10, i / 44), sign * .90)[0],
                     roof(blend(-1.80, .10, i / 44), sign * .90)[1] + .010 + .004 * math.sin(math.pi * i / 44),
                     blend(-1.80, .10, i / 44)) for i in range(45)], .014, mats['black'])
        # A fixed B-pillar is narrow and has no filled sheet beneath either door.
        pillar = [window_point(sign, -.30, 1.154), window_point(sign, -.43, roof(-.43, 1)[1]),
                  window_point(sign, -.49, roof(-.49, 1)[1]), window_point(sign, -.36, 1.159)]
        inset_plate(author, 'BPillar', pillar, mats['black'], normal=(sign, 0, 0), thickness=.046)
        author.curve('BPillarLower', [(sign * (width(-.333, blend(.30, 1.17, i / 24)) - .065),
                     blend(.30, 1.17, i / 24), -.333) for i in range(25)],
                     .030, mats['innerPaint'])
        rear_top, rear_bottom = DOORS['rear'][4], DOORS['rear'][5]
        quarter = [(rear_top[0] - .044, rear_top[1] - .012), (-1.670, 1.510), (-1.907, 1.327),
                   (-1.794, 1.281), (-1.470, belt(-1.470) + .022),
                   (rear_bottom[0] - .050, rear_bottom[1] - .003)]
        quarter_path = corner_path(quarter)
        curved_plate(author, 'HofmeisterQuarterGlass', quarter_path,
                     lambda z, y, s=sign: window_point(s, z, y, -.004), mats['glass'], normal=(sign, 0, 0), depth=.004)
        author.curve('QuarterGlassFrame', [window_point(sign, z, y, .002) for z, y in quarter_path],
                     .006, mats['silver'], cyclic=True)
        tail_edge_z = -2.32
        for _ in range(12):
            tail_edge_z = rear_z(width(tail_edge_z, belt(tail_edge_z)), belt(tail_edge_z))
        outer = [(rear_top[0] - .008, rear_top[1]), (-1.675, roof(-1.675, 1)[1]), (-2.10, 1.448),
                 (tail_edge_z, belt(tail_edge_z)), (-1.470, belt(-1.470)),
                 (rear_bottom[0] - .008, belt(rear_bottom[0] - .008))]
        # A ring joins rear-quarter glass to roof, shoulder and the hatch aperture.
        n = 72
        inner_curve, outer_curve = quarter_path, corner_path(outer)
        # The lower outer edge meets the body belt exactly, without a folded ring.
        outer_curve = [(z, belt(z)) if 36 <= i <= 60 else (z, y)
                       for i, (z, y) in enumerate(outer_curve)]
        for i in range(n):
            points = [inner_curve[i], inner_curve[(i + 1) % n],
                      outer_curve[(i + 1) % n], outer_curve[i]]
            area = sum(a[0] * b[1] - b[0] * a[1]
                       for a, b in zip(points, points[1:] + points[:1]))
            assert area < -1e-8, 'Every quarter-window ring cell must preserve winding'
        for section, pairs in enumerate(window_ring_sections(inner_curve, outer_curve)):
            inner_section = [pair[0] for pair in pairs]
            outer_section = [pair[1] for pair in pairs]
            def pillar_strip(u, v, inside=inner_section, outside=outer_section):
                index = min(len(inside) - 1, round(u * (len(inside) - 1)))
                return window_point(sign, blend(inside[index][0], outside[index][0], v),
                                    blend(inside[index][1], outside[index][1], v))
            author.surface('QuarterDivider' if section == 5 else 'DPillarShoulder', pillar_strip,
                           len(pairs) - 1, 8, mats['black' if section == 5 else 'paint'],
                           solid=.021, normal=(sign, 0, 0))
        for kind in DOORS:
            create_door(author, mats, sign, kind)
    for x in (-.37, .35):
        author.curve('WiperArm', [(x - .18, 1.220, .80), (x + .06, 1.241, .756),
                     (x + .22, 1.251, .734)], .007, mats['rubber'])


def seat(author, mats, x, z, width_value=.50):
    author.box('SeatBase', (x, .475, z), (width_value, .14, .54), mats['leather'], radius=.075)
    author.box('SeatCushion', (x, .554, z + .025), (width_value * .74, .068, .455),
               mats['leatherSoft'], radius=.033)
    # The tapered back and separate rounded bolsters retain volume from an open door.
    author.surface('SeatBack', lambda u, v: (x + (u - .5) * blend(width_value, width_value * .87, v),
                   blend(.55, 1.10, v), z - .22 - .13 * v - .040 * math.sin(math.pi * u)),
                   22, 22, mats['leatherSoft'], solid=.115, normal=(0, 0, 1))
    for sign in (-1, 1):
        author.curve('SeatBolster', [(x + sign * width_value * .40, .57, z - .20),
                     (x + sign * width_value * .40, .84, z - .27),
                     (x + sign * width_value * .34, 1.08, z - .34)], .053,
                     mats['leather'], bezier=True)
        author.curve('CushionStitch', [(x + sign * width_value * .34, .578, z + blend(-.18, .19, i / 20))
                     for i in range(21)], .0018, mats['stitch'])
        author.curve('HeadrestPost', [(x + sign * .088, 1.05, z - .34),
                     (x + sign * .088, 1.24, z - .36)], .008, mats['silver'])
    author.box('Headrest', (x, 1.206, z - .352), (width_value * .56, .21, .12),
               mats['leather'], radius=.046)
    author.box('SeatRail', (x, .352, z), (width_value * .75, .048, .42), mats['black'], radius=.009)


def interior(author, mats):
    author.box('CabinFloor', (0, .293, -.25), (1.65, .045, 2.42), mats['carpet'], radius=.018)
    author.box('CenterTunnel', (0, .407, .02), (.29, .24, 1.75), mats['leather'], radius=.075)
    for x in (-.457, .457):
        seat(author, mats, x, .02)
    for x, width_value in [(-.50, .48), (0, .40), (.50, .48)]:
        seat(author, mats, x, -1.15, width_value)
    for sign in (-1, 1):
        author.box('DoorSill', (sign * .803, .29, -.22), (.092, .065, 2.15), mats['innerPaint'], radius=.024)
        author.box('SillPlate', (sign * .805, .329, -.12), (.057, .013, 1.60), mats['silver'], radius=.005)
        author.curve('Seatbelt', [(sign * .764, 1.38, -.33), (sign * .666, .62, -.33)],
                     .014, mats['rubber'])
    author.surface('DashboardSculpture', lambda u, v: ((u - .5) * 1.61,
                   1.047 + .085 * math.sin(math.pi * v) - .020 * abs(2 * u - 1),
                   blend(.48, .917, v)), 44, 18, mats['leather'], solid=.15, normal=(0, 1, 0))
    author.box('DashboardLower', (0, .91, .707), (1.60, .17, .32), mats['leather'], radius=.07)
    author.box('CurvedDisplayHousing', (.10, 1.190, .631), (1.00, .224, .036), mats['black'], radius=.025)
    author.box('CurvedDisplayGlass', (.10, 1.196, .607), (.956, .184, .008), mats['display'], radius=.008)
    for x in [-.21, .32]:
        author.box('ScreenInterface', (x, 1.198, .601), (.215, .008, .002), mats['blue'], radius=.001)
    author.curve('DashboardInteractionBar', [((i / 40 - .5) * 1.54, 1.045, .471 + .03 * abs(i / 20 - 1))
                 for i in range(41)], .009, mats['blue'])
    author.box('CenterArmrest', (0, .69, -.25), (.28, .095, .46), mats['leather'], radius=.04)
    author.box('CenterConsole', (0, .641, .20), (.275, .065, .50), mats['black'], radius=.03)
    author.box('GearSelector', (.053, .699, .24), (.054, .032, .055), mats['silver'], radius=.012)
    author.box('RearVentPod', (0, .615, -.62), (.22, .23, .07), mats['black'], radius=.02)
    for height in (.60, .63, .66):
        author.box('RearVentSlat', (0, height, -.660), (.174, .006, .012), mats['silver'], radius=.001)
    wheel_x, wheel_y, wheel_z = .453, 1.020, .403
    points = [(wheel_x + .176 * math.cos(i / 80 * math.tau),
               wheel_y + .165 * math.sin(i / 80 * math.tau),
               wheel_z + .042 * math.sin(i / 80 * math.tau)) for i in range(80)]
    author.curve('StudySteeringRim', points, .021, mats['leather'], cyclic=True)
    author.box('SteeringHub', (wheel_x, wheel_y, wheel_z), (.19, .135, .064), mats['leather'], radius=.05)
    for sign in (-1, 1):
        author.curve('SteeringSpoke', [(wheel_x, wheel_y, wheel_z),
                     (wheel_x + sign * .151, wheel_y + .005, wheel_z)], .016, mats['silver'])
    author.curve('SteeringBottomSpoke', [(wheel_x, wheel_y - .035, wheel_z),
                 (wheel_x, wheel_y - .151, wheel_z - .032)], .018, mats['silver'])

    author.box('CargoFloor', (0, .573, -1.91), (1.40, .06, .92), mats['carpet'], radius=.035)
    author.box('CargoThreshold', (0, .583, -2.30), (1.50, .077, .13), mats['black'], radius=.025)
    author.box('CargoLatch', (0, .627, -2.335), (.063, .04, .05), mats['metal'], radius=.008)
    author.box('CargoFloorPull', (0, .610, -2.04), (.13, .012, .07), mats['silver'], radius=.012)
    for sign in (-1, 1):
        author.box('CargoWheelhouse', (sign * .692, .803, -1.69), (.23, .45, .68),
                   mats['carpet'], radius=.090)
        author.box('CargoSideLiner', (sign * .773, .869, -2.06), (.095, .46, .58),
                   mats['carpet'], radius=.042)
        author.box('CargoUtilityInset', (sign * .715, 1.025, -2.03), (.01, .065, .17),
                   mats['black'], radius=.012)
    for i in range(23):
        author.curve('ThresholdRib', [(-.69 + i * .060, .626, -2.346),
                     (-.67 + i * .060, .626, -2.251)], .0022, mats['metal'])
    # Keep cargo structure behind the actual sculpted tail, including the plate recess.
    cargo_prefixes = ('Cargo', 'ThresholdRib')
    for obj in bpy.data.objects:
        if obj.type != 'MESH' or not obj.name.startswith(cargo_prefixes):
            continue
        if obj.parent != author.root:
            continue
        for vertex in obj.data.vertices:
            x, y, z = vertex.co.x, vertex.co.z, -vertex.co.y
            vertex.co.y = -max(z, rear_z(x, y) + .071)
        obj.data.update()
