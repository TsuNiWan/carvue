"""Reproducible vehicle study based on real-vehicle reference observation.

Brand identifiers are omitted; exterior design rights remain unverified.
Coordinates: X left, Y up, Z forward, in meters.
"""
import math
import json
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from vehicle_authoring import VehicleAuthoring
from mesh_aperture import cut_convex_aperture
from suv_02_surfaces import (ARCH_RADIUS, FRONT_AXLE, REAR_AXLE, TYRE_RADIUS, arch_bottom,
                         belt, blend, corner_path, curved_plate, disc, end_skin, end_width, front_face,
                         front_z, head_position, hood_surface, inset_plate, inside_polygon, nose_edge, profile, rear_z,
                         sample_path, side, skin, tail_position, width)
from suv_02_cabin import DOORS, cabin_shell, interior


author = VehicleAuthoring('suv-02', 'Reconstructed vehicle study; exterior design rights unverified')
M = {
    'paint': author.material('BodyPaint', (.49, .505, .525), .72, .265, coat=.38),
    'innerPaint': author.material('InnerPaint', (.36, .376, .393), .53, .39),
    'black': author.material('GlossBlack', (.025, .032, .039), .15, .28),
    'rubber': author.material('Rubber', (.036, .039, .043), 0, .76),
    'silver': author.material('BrushedSilver', (.72, .745, .77), .84, .24),
    'chrome': author.material('Chrome', (.89, .91, .93), .98, .17),
    'metal': author.material('DarkMetal', (.25, .28, .31), .75, .42),
    'wheel': author.material('WheelMachinedFace', (.70, .72, .76), .88, .24),
    'wheelBlack': author.material('WheelAeroInsert', (.042, .050, .061), .25, .28),
    'leather': author.material('StudyBlack', (.052, .057, .064), 0, .61),
    'leatherSoft': author.material('StudyCenter', (.067, .074, .086), 0, .75),
    'carpet': author.material('CargoCarpet', (.073, .078, .085), 0, .97),
    'headliner': author.material('AnthraciteHeadliner', (.132, .14, .15), 0, .88),
    'stitch': author.material('Stitch', (.20, .215, .23), 0, .85),
    'glass': author.material('SideGlass', (.105, .15, .17), .06, .10, alpha=.33),
    'frontGlass': author.material('FrontGlass', (.13, .17, .19), .05, .11, alpha=.24),
    'lens': author.material('ClearLampCover', (.31, .38, .44), .06, .08, alpha=.15),
    'redLens': author.material('RedLampHousing', (.34, .013, .022), .20, .19),
    'tailHousing': author.material('DarkRedTailHousing', (.115, .006, .013), .20, .19),
    'tailCover': author.material('RedLampCover', (.25, .006, .017), .08, .09, alpha=.25),
    'reflector': author.material('NonEmissiveReflector', (.50, .014, .022), .08, .28),
    'head': author.material('Headlamp', (.90, .965, 1), .04, .21, emission=(1, 1, 1)),
    'tail': author.material('Taillamp', (.80, .03, .035), .04, .22, emission=(1, .012, .008)),
    'signalLeft': author.material('SignalLeft', (.72, .24, .008), 0, .23, emission=(1, .21, .005)),
    'signalRight': author.material('SignalRight', (.72, .24, .008), 0, .23, emission=(1, .21, .005)),
    'blue': author.material('StudyBlue', (.015, .32, .68), .3, .32),
    'white': author.material('BadgeWhite', (.91, .925, .93), .1, .32),
    'mirror': author.material('MirrorSilver', (.68, .74, .78), 1, .075),
    'display': author.material('DisplayGlass', (.026, .049, .075), .10, .22),
}
APERTURE_REPORTS = []


def cut_lamp_aperture(name, outline, position, target_prefixes, parent=None):
    """Use verified double-precision support planes and preserve corner normals."""
    samples = list(outline)
    if position is tail_position:
        low = [min(p[i] for p in outline) for i in range(2)]
        high = [max(p[i] for p in outline) for i in range(2)]
        for row in range(1, 12):
            for column in range(1, 12):
                x, y = blend(low[0], high[0], column / 12), blend(low[1], high[1], row / 12)
                if inside_polygon(x, y, outline):
                    samples.append((x, y))
    front = [position(x, y, .012) for x, y in samples]
    back = [position(x, y, -.070) for x, y in samples]
    reports = cut_convex_aperture(name, front, back, target_prefixes, parent)
    for report in reports:
        report.update(outwardCutterMeters=.012, inwardCutterMeters=.070,
                      carrierSampleCount=len(samples))
    APERTURE_REPORTS.extend(reports)


def aperture_return(name, outline, position, parent=None, depth=.04):
    ring = outline + outline[:1]
    author.surface(name, lambda u, v: position(*ring[min(len(ring) - 1, int(u * (len(ring) - 1)))],
                                             blend(.001, -depth, v)), len(ring) - 1, 4,
                   M['black'], parent)


def body():
    for sign in (-1, 1):
        for name, front, rear in [('FrontFender', 2.30, .86), ('RearQuarter', -1.360, -2.395)]:
            author.surface(name, lambda u, v, s=sign, f=front, r=rear: end_skin(s, f, r, u, v),
                           100, 36, M['paint'], solid=.023, normal=(sign, 0, 0))
        author.surface('LowerRocker', lambda u, v, s=sign: side(s, blend(1.002, -1.002, u),
                       blend(.258, .398, v), -.008 + .006 * math.sin(math.pi * v)),
                       52, 10, M['black'], solid=.025, normal=(sign, 0, 0))
        author.surface('RockerSilverBlade', lambda u, v, s=sign: side(s, blend(.959, -.960, u),
                       .278 + v * .044 * min(1, u / .075, (1 - u) / .075), .007),
                       64, 5, M['silver'], solid=.006, normal=(sign, 0, 0))
        # Wheel lips are assigned to exactly the body or moving-door segment they bound.
        for axle in (FRONT_AXLE, REAR_AXLE):
            last_parent, arc_points = None, []
            for segment in range(160):
                a0 = -.23 + segment / 160 * (math.pi + .46)
                a1 = -.23 + (segment + 1) / 160 * (math.pi + .46)
                zmid = axle + ARCH_RADIUS * math.cos((a0 + a1) / 2)
                parent = author.root
                if axle == REAR_AXLE and -1.353 <= zmid <= -.333:
                    parent = bpy.data.objects['door_rear' + ('Left' if sign > 0 else 'Right')]
                points = [side(sign, axle + ARCH_RADIUS * math.cos(a),
                               TYRE_RADIUS + ARCH_RADIUS * math.sin(a), .003) for a in (a0, a1)]
                if last_parent is not None and parent != last_parent:
                    author.curve('WheelOpeningLip', arc_points, .013, M['black'], last_parent)
                    arc_points = []
                if not arc_points:
                    arc_points.append(points[0])
                arc_points.append(points[1])
                last_parent = parent
            author.curve('WheelOpeningLip', arc_points, .013, M['black'], last_parent)
            author.surface('WheelWellLiner', lambda u, v, s=sign, az=axle: (
                s * blend(.69, .925, v), TYRE_RADIUS + .391 * math.sin(math.pi * u),
                az + .391 * math.cos(math.pi * u)), 70, 9, M['rubber'], normal=(0, -1, 0))
    author.box('Underbody', (0, .249, -.02), (1.42, .047, 2.18), M['rubber'], radius=.021)

    author.surface('SculptedHood', hood_surface, 84, 64, M['paint'], solid=.025, normal=(0, 1, 0))
    for sign in (-1, 1):
        author.curve('HoodSeam', [hood_surface(.96 if sign > 0 else .04, i / 60) for i in range(61)],
                     .0024, M['black'])
    author.surface('FrontFasciaVolume', front_face, 84, 40, M['paint'], solid=.027, normal=(0, 0, 1))
    author.surface('RearBumperVolume', lambda u, v: (
        (2 * u - 1) * end_width(rear_z, blend(.255, .652, v)),
        blend(.255, .652, v), rear_z((2 * u - 1) * end_width(rear_z, blend(.255, .652, v)), blend(.255, .652, v))),
        70, 28, M['paint'], solid=.033, normal=(0, 0, -1))


def front_details():
    kidney_shape = [(.045, .997), (.25, 1.029), (.455, .973), (.434, .785),
                    (.365, .697), (.078, .692), (.035, .772)]
    for sign in (-1, 1):
        kidney_profile = corner_path(kidney_shape, .055)
        kidney_xy = [(sign * x, y) for x, y in kidney_profile]
        outline = [(x, y, front_z(x, y) + .009) for x, y in kidney_xy]
        curved_plate(author, 'KidneyRecess', kidney_xy, lambda x, y: (x, y, front_z(x, y) + .009),
                     M['black'], normal=(0, 0, 1), depth=.018)
        author.curve('KidneyMetalSurround', outline, .012, M['silver'], cyclic=True)
        for i in range(7):
            x = .078 + i * .050
            top = 1.012 - .038 * (x / .455) ** 2
            bottom = .714 + .015 * (x / .455) ** 2
            author.curve('KidneyVerticalBlade', [(sign * x, blend(bottom, top, j / 16),
                         front_z(sign * x, blend(bottom, top, j / 16)) + .026) for j in range(17)],
                         .0025, M['black'])
        for i in range(7):
            start = -.135 + i * .086
            diagonal = [(start + .85 * (.710 + j / 70 * .315 - .710), .710 + j / 70 * .315)
                        for j in range(71)]
            diagonal = [(x, y) for x, y in diagonal if inside_polygon(x, y, kidney_profile)]
            if len(diagonal) > 1:
                author.curve('KidneyDiagonalBlade', [(sign * x, y, front_z(sign * x, y) + .030)
                             for x, y in diagonal], .0045, M['metal'])
        lamp_shape = [(.485, 1.008), (.714, 1.066), (.910, 1.082), (.899, .997),
                      (.826, .949), (.564, .911), (.489, .939)]
        lamp_xy = [(sign * x, y) for x, y in sample_path(lamp_shape, 8)]
        cut_lamp_aperture('Headlamp aperture', lamp_xy, head_position,
                          ['FrontFender', 'SculptedHood', 'FrontFasciaVolume'])
        aperture_return('HeadlampWellReturn', lamp_xy, head_position, depth=.034)
        lamp_outline = [head_position(x, y, .005) for x, y in lamp_xy]
        curved_plate(author, 'HeadlampBlackHousing', lamp_xy, lambda x, y: head_position(x, y, -.028),
                     M['black'], normal=(0, 0, 1), depth=.023)
        author.curve('HeadlampPerimeter', lamp_outline, .0045, M['metal'], cyclic=True)
        for unit in range(2):
            x = .558 + unit * .160
            cup_shape = [(x - .028, .957 + unit * .021), (x + .057, .966 + unit * .021),
                         (x + .090, 1.034 + unit * .009), (x + .011, 1.034 + unit * .009)]
            cup = [head_position(sign * a, b, -.018) for a, b in cup_shape]
            inset_plate(author, 'HeadlampReflectorCup', cup, M['metal'], normal=(0, 0, 1), thickness=.012)
            guide = [(x - .043, .944 + unit * .022), (x + .029, .945 + unit * .022),
                     (x + .063, 1.021 + unit * .013), (x + .143, 1.024 + unit * .013)]
            author.curve('DoubleLDaylight', [head_position(sign * a, b, -.003) for a, b in guide],
                         .0065, M['head'], bezier=False)
            author.curve('HeadlampBlueAccent', [head_position(sign * a, b - .012, -.001)
                         for a, b in guide[1:]], .004, M['blue'])
            for j in range(4):
                author.curve('HeadlampOpticalFin', [head_position(sign * (x - .010 + j * .018), .969 + unit * .021, -.012),
                             head_position(sign * (x + .010 + j * .018), 1.009 + unit * .015, -.012)], .0018, M['silver'])
        curved_plate(author, 'HeadlampCover', lamp_xy, lambda x, y: head_position(x, y, .006),
                     M['lens'], normal=(0, 0, 1), depth=.002)
        author.curve('FrontTurnSignal', [head_position(sign * blend(.62, .84, i / 30),
                     1.047 + .017 * i / 30, .007) for i in range(31)],
                     .0035, M['signalLeft' if sign > 0 else 'signalRight'])
        cheek = [(sign * x, y) for x, y in corner_path(
            [(.614, .409), (.710, .608), (.784, .718), (.824, .647), (.854, .374)], .035)]
        curved_plate(author, 'StudyDiagonalCheek', cheek,
                     lambda x, y: (x, y, front_z(x, y) + .004), M['metal'], normal=(0, 0, 1), depth=.009)
        curtain = [(.774, .397), (.831, .391), (.827, .588), (.803, .633), (.779, .575)]
        points = [(sign * x, y) for x, y in corner_path(curtain, .075)]
        front_position = lambda x, y, offset: (x, y, front_z(x, y) + offset)
        cut_lamp_aperture('Study side intake', points, front_position, ['FrontFasciaVolume', 'StudyDiagonalCheek'])
        aperture_return('SideIntakeReturn', points, front_position, depth=.052)
        curved_plate(author, 'StudyAirCurtain', points, lambda x, y: (x, y, front_z(x, y) - .045),
                     M['black'], normal=(0, 0, 1))
        author.curve('StudyIntakeBorder', [front_position(x, y, .002) for x, y in points],
                     .0035, M['black'], cyclic=True)
        author.curve('AirCurtainSilverEdge', [(sign * .821, .410, front_z(sign * .821, .410) + .009),
                     (sign * .812, .577, front_z(sign * .812, .577) + .009)], .003, M['metal'])

    lower = [(-.703, .497), (-.660, .351), (.660, .351), (.703, .497)]
    lower_outline = corner_path(lower, .075)
    cut_lamp_aperture('Central radiator aperture', lower_outline,
                      lambda x, y, offset: (x, y, front_z(x, y) + offset), ['FrontFasciaVolume'])
    aperture_return('RadiatorReturn', lower_outline,
                    lambda x, y, offset: (x, y, front_z(x, y) + offset), depth=.062)
    curved_plate(author, 'LowerRadiatorOpening', lower_outline,
                 lambda x, y: (x, y, front_z(x, y) - .052), M['black'], normal=(0, 0, 1), depth=.021)
    for y in (.380, .421, .461):
        author.curve('LowerGrilleCrossbar', [(blend(-.651, .651, i / 60), y,
                     front_z(blend(-.651, .651, i / 60), y) + .008) for i in range(61)], .005, M['metal'])
    for i in range(15):
        x = -.61 + i * 1.22 / 14
        author.curve('LowerGrilleBlade', [(x, .361, front_z(x, .361) - .003),
                     (x, .488, front_z(x, .488) - .003)], .004, M['black'])
    author.surface('LowerGrilleCenterBridge', lambda u, v: (
        blend(-.020, .020, u), blend(.344, .507, v),
        front_z(blend(-.020, .020, u), blend(.344, .507, v)) + .012),
        4, 16, M['paint'], solid=.014, normal=(0, 0, 1))
    author.surface('StudyFrontSkidPanel', lambda u, v: ((2 * u - 1) * blend(.77, .821, v),
                   blend(.281, .325, v), front_z((2 * u - 1) * blend(.77, .821, v), blend(.281, .325, v)) + .008),
                   60, 6, M['silver'], solid=.01, normal=(0, 0, 1))
    author.box('FrontPlateMount', (0, .579, 2.321), (.484, .119, .013), M['black'], radius=.013)
    author.box('FrontPlate', (0, .580, 2.330), (.452, .095, .004), M['white'], radius=.006)


def rear_and_hatch():
    group = author.group('trunk', (0, 1.536, -1.965), author.root)
    def hatch_width(y):
        return profile([(.633, .767), (.82, .861), (1.05, .861), (1.21, .838)], y)
    def hatch(u, v):
        y = blend(.633, 1.210, v)
        t = 2 * u - 1
        w = hatch_width(y)
        x = w * t
        return (x, y, rear_z(x, y) + .019 - .016 * (1 - t * t) * math.sin(math.pi * v))
    author.surface('HatchOuterSkin', hatch, 70, 44, M['paint'], group, .028, normal=(0, 0, -1))
    for sign in (-1, 1):
        def surround(u, v, s=sign):
            y = blend(.652, 1.155, v)
            x = s * blend(hatch_width(y) + .004, end_width(rear_z, y), u)
            return (x, y, rear_z(x, y))
        author.surface('TailgateSideSurround', surround, 14, 36, M['paint'], solid=.023,
                       normal=(0, 0, -1))
    author.surface('HatchInnerLiner', lambda u, v: (hatch(u, v)[0] * .94,
                   hatch(u, v)[1] + .021, hatch(u, v)[2] + .057 + .022 * math.sin(math.pi * u)),
                   38, 24, M['leather'], group, .020, normal=(0, 0, 1))
    def rear_glass(u, v):
        t = 2 * u - 1
        bottom = hatch(u, 1)
        return (blend(bottom[0] * .988, .661 * t, v),
                blend(bottom[1] + .012, 1.539, v) + .009 * (1 - t * t) * math.sin(math.pi * v),
                blend(bottom[2] - .002, -1.983 - .025 * (1 - t * t), v))
    author.surface('HatchRearWindow', rear_glass, 46, 25, M['glass'], group, .005, normal=(0, .5, -1))
    window_loop = [rear_glass(i / 40, 0) for i in range(41)]
    window_loop += [rear_glass(1, i / 20) for i in range(1, 21)]
    window_loop += [rear_glass(1 - i / 40, 1) for i in range(1, 41)]
    window_loop += [rear_glass(0, 1 - i / 20) for i in range(1, 21)]
    author.curve('HatchWindowPaintFrame', window_loop, .014, M['paint'], group, cyclic=True)
    author.curve('HatchWindowSeal', [(x, y, z - .008) for x, y, z in window_loop],
                 .010, M['rubber'], group, cyclic=True)
    for i in range(8):
        v = .12 + i * .09
        author.curve('RearWindowHeating', [rear_glass(.03 + .94 * j / 45, v) for j in range(46)],
                     .00065, M['metal'], group)
    author.surface('RoofSpoiler', lambda u, v: ((u - .5) * 1.414,
                   1.559 + .018 * math.sin(math.pi * u) - .026 * v,
                   blend(-1.927, -2.201, v) + .025 * abs(2 * u - 1)),
                   45, 16, M['paint'], group, .027, normal=(0, 1, 0))
    author.curve('SpoilerHighBrakeLens', [(blend(-.287, .287, i / 30), 1.535, -2.203) for i in range(31)],
                 .006, M['redLens'], group)
    author.curve('HatchWiperArm', [(rear_glass(u, v)[0], rear_glass(u, v)[1], rear_glass(u, v)[2] - .012)
                 for u, v in [(.5, .09), (.30, .10), (.22, .10)]], .011, M['rubber'], group)
    author.box('HatchInnerGrip', (0, .751, -2.335), (.17, .044, .016), M['black'], group, .012)
    author.box('HatchLatch', (0, .648, -2.353), (.074, .046, .037), M['metal'], group, .008)
    rim = [hatch(i / 40, 0) for i in range(41)]
    rim += [hatch(1, i / 30) for i in range(1, 31)]
    rim += [rear_glass(1, i / 20) for i in range(1, 21)]
    rim += [rear_glass(1 - i / 40, 1) for i in range(1, 41)]
    rim += [rear_glass(0, 1 - i / 20) for i in range(1, 21)]
    rim += [hatch(0, 1 - i / 30) for i in range(1, 31)]
    author.curve('CargoAperturePaint', [(x * .98, y - .010, z + .039) for x, y, z in rim],
                 .017, M['innerPaint'], cyclic=True)
    author.curve('CargoApertureSeal', [(x * .983, y - .005, z + .021) for x, y, z in rim],
                 .012, M['rubber'], cyclic=True)
    author.curve('HatchMovingHem', [(x, y, z + .015) for x, y, z in rim],
                 .009, M['innerPaint'], group, cyclic=True)

    for sign in (-1, 1):
        # The hatch boundary is the actual inner/outer lamp ownership boundary.
        for moving in (True, False):
            target = group if moving else author.root
            if moving:
                outline2 = [(.443, 1.094), (.816, 1.113), (.859, 1.109),
                            (.858, 1.008), (.459, 1.026), (.418, 1.055)]
            else:
                outline2 = [(.858, 1.124), (.911, 1.177), (.951, 1.127),
                            (.950, 1.031), (.904, .976), (.849, 1.009)]
            lamp_xy = [(sign * x, y) for x, y in corner_path(outline2, .055)]
            cut_lamp_aperture('Tail lamp aperture', lamp_xy, tail_position,
                              ['HatchOuterSkin'] if moving else ['RearQuarter', 'TailgateSideSurround'], target)
            aperture_return('TailLampWellReturn', lamp_xy, tail_position, target, .044)
            outline = [tail_position(x, y, .004) for x, y in lamp_xy]
            curved_plate(author, 'TailLampDarkCavity', lamp_xy,
                         lambda x, y: tail_position(x, y, -.035), M['black'], target,
                         (0, 0, -1), .012, split_x=[sign * .855, sign * .90835])
            curved_plate(author, 'HatchLamp' if moving else 'FixedQuarterLamp', lamp_xy,
                         lambda x, y: tail_position(x, y, -.022), M['tailHousing'], target,
                         (0, 0, -1), .015, split_x=[sign * .855, sign * .90835])
            curved_plate(author, 'TailLampCover', lamp_xy,
                         lambda x, y: tail_position(x, y, .004), M['tailCover'], target,
                         (0, 0, -1), .002, split_x=[sign * .855, sign * .90835])
            author.curve('TailLampDarkBorder', outline, .007, M['black'], target, cyclic=True)
            if moving:
                for y in (1.045, 1.083):
                    author.curve('InnerTailArrow', [tail_position(sign * .449, y - .005, -.005),
                                 tail_position(sign * .479, y + .007, -.004),
                                 tail_position(sign * .851, y, -.004)],
                                 .0053, M['tail'], target)
            else:
                for branch in [[(.856, 1.083), (.900, 1.083), (.914, 1.147), (.947, 1.121)],
                               [(.856, 1.045), (.899, 1.045), (.913, 1.016), (.947, 1.043)]]:
                    path = [tuple(blend(a[k], b[k], i / 18) for k in range(2))
                            for a, b in zip(branch, branch[1:]) for i in range(18)] + branch[-1:]
                    author.curve('OuterTailArrow', [tail_position(sign * x, y, -.003) for x, y in path],
                                 .0085, M['tail'], target)
                author.curve('RearTurnSignal', [tail_position(sign * blend(.865, .929, i / 18), 1.099, -.001) for i in range(19)],
                             .0045, M['signalLeft' if sign > 0 else 'signalRight'], target)
        reflector = [(sign * x, y, rear_z(sign * x, y) - .012) for x, y in
                     [(.751, .353), (.889, .377), (.900, .410), (.755, .385)]]
        inset_plate(author, 'RearReflector', reflector, M['reflector'], normal=(0, 0, -1), thickness=.006)
    author.surface('RearBlackBumperBand', lambda u, v: ((2 * u - 1) * end_width(rear_z, blend(.255, .507, v)),
                   blend(.255, .507, v), rear_z((2 * u - 1) * end_width(rear_z, blend(.255, .507, v)), blend(.255, .507, v)) - .011),
                   65, 10, M['black'], solid=.015, normal=(0, 0, -1))
    for sign in (-1, 1):
        def bumper_side(u, v, s=sign):
            y = blend(.273, blend(.335, .507, u), v)
            end_x = end_width(rear_z, y)
            end_z = rear_z(end_x, y) - .011
            z = blend(-1.848, end_z, u)
            correction = end_x - width(end_z, y) - .004
            return (s * (width(z, y) + .004 + correction * u ** 8), y, z)
        author.surface('RearBumperBlackWrap', bumper_side, 30, 12, M['black'],
                       solid=.012, normal=(sign, 0, 0))
    author.surface('StudyRearSkidPanel', lambda u, v: ((2 * u - 1) * blend(.72, .83, v),
                   blend(.269, .423, v), rear_z((2 * u - 1) * blend(.72, .83, v), blend(.269, .423, v)) - .014),
                   56, 16, M['silver'], solid=.022, normal=(0, 0, -1))
    plate_recess = corner_path([(-.29, .636), (.29, .636), (.26, .494), (-.26, .494)], .12)
    curved_plate(author, 'RearPlateRecess', plate_recess, lambda x, y: (x, y, rear_z(x, y) - .006),
                 M['black'], normal=(0, 0, -1), depth=.009)
    author.curve('RearPlateBorder', [(x, y, rear_z(x, y) - .009) for x, y in
                 corner_path([(-.218, .610), (.218, .610), (.218, .515), (-.218, .515)], .065)],
                 .0025, M['silver'], cyclic=True)
    for sign in (-1, 1):
        for x in (.39, .74):
            disc(author, 'ParkingSensor', (sign * x, .468, rear_z(sign * x, .468) - .016),
                 .011, .003, M['black'], axis='z', segments=24)


def wheels():
    for sign in (-1, 1):
        for location, axle in [('front', FRONT_AXLE), ('rear', REAR_AXLE)]:
            suffix = location + ('Left' if sign > 0 else 'Right')
            center = (sign * .815, TYRE_RADIUS, axle)
            group = author.group('wheel_' + suffix, center, author.root)
            # A closed tyre section gives rounded shoulders and a distinct sidewall.
            section = [(-.1225, .239), (-.124, .302), (-.116, .340), (-.090, .359),
                       (-.065, .3638), (.065, .3638), (.090, .359), (.116, .340),
                       (.124, .302), (.1225, .239), (.095, .230), (-.095, .230)]
            cross = sample_path(section, 5)
            cross.append(cross[0])
            n = len(cross)
            author.surface('Tyre245_50R19', lambda u, v, c=center: (
                c[0] + cross[min(n - 1, int(v * (n - 1)))][0],
                c[1] + cross[min(n - 1, int(v * (n - 1)))][1] * math.cos(math.tau * u),
                c[2] + cross[min(n - 1, int(v * (n - 1)))][1] * math.sin(math.tau * u)),
                112, n - 1, M['rubber'], group)
            for shoulder in (-.081, .081):
                author.curve('TyreTreadGroove', [(center[0] + shoulder,
                             center[1] + .360 * math.cos(math.tau * i / 96),
                             center[2] + .360 * math.sin(math.tau * i / 96)) for i in range(96)],
                             .0022, M['black'], group, cyclic=True)
            outward = sign * .937
            author.surface('WheelBarrel', lambda u, v, s=sign, c=center: (
                s * blend(.7805, .9355, v), c[1] + .235 * math.cos(math.tau * u),
                c[2] + .235 * math.sin(math.tau * u)), 96, 2, M['wheelBlack'], group)
            disc(author, 'BrakeRotor', (sign * .895, center[1], axle), .177, .012, M['metal'], group)
            author.box('BrakeCaliper', (sign * .904, center[1] + .072, axle + .121),
                       (.058, .155, .077), M['metal'], group, .022)
            for r in (.238, .218):
                author.curve('RimLip', [(outward, center[1] + r * math.cos(i / 96 * math.tau),
                             axle + r * math.sin(i / 96 * math.tau)) for i in range(96)],
                             .005, M['wheel'], group, cyclic=True)
            # Style 941: five angular aero pockets and bifurcated machined faces.
            for spoke in range(5):
                angle = spoke * math.tau / 5 + .11
                pocket = [(0.080, -.26), (.209, -.39), (.230, -.19), (.229, .17),
                          (.193, .27), (.105, .18)]
                pocket_points = [(outward - sign * .003,
                                  center[1] + r * math.cos(angle + a),
                                  axle + r * math.sin(angle + a)) for r, a in pocket]
                inset_plate(author, '941AeroPocket', pocket_points, M['wheelBlack'], group,
                            (sign, 0, 0), .018, smooth=False)
                for branch in (-1, 1):
                    face = [(.050, -.085 * branch), (.138, .040 * branch),
                            (.225, .225 * branch), (.222, .335 * branch),
                            (.130, .159 * branch), (.055, .115 * branch)]
                    points = [(outward + sign * .006,
                               center[1] + r * math.cos(angle + a),
                               axle + r * math.sin(angle + a)) for r, a in face]
                    obj = inset_plate(author, '941MachinedYSpoke', points, M['wheel'], group,
                                      (sign, 0, 0), .018, smooth=False)
                    author.bevel(obj, .0025, 2)
            disc(author, 'WheelHub', (outward + sign * .009, center[1], axle), .060, .022,
                 M['wheel'], group)
            disc(author, 'WheelCenterCap', (outward + sign * .023, center[1], axle), .027, .006,
                 M['black'], group)
            for i in range(5):
                angle = i * math.tau / 5
                disc(author, 'WheelBolt', (outward + sign * .024, center[1] + .043 * math.cos(angle),
                     axle + .043 * math.sin(angle)), .0065, .007, M['metal'], group, segments=12)


cabin_shell(author, M)
body()
front_details()
rear_and_hatch()
interior(author, M)
wheels()

for obj in author.root.children_recursive:
    if obj.type == 'MESH' and any(mat and mat.name in ('BodyPaint', 'InnerPaint') for mat in obj.data.materials):
        if not obj.data.has_custom_normals:
            obj.data.set_sharp_from_angle(angle=math.radians(35))

manifest = {
    'schemaVersion': 1, 'vehicleId': 'suv-02', 'assetVersion': '1.1.0', 'units': 'meter', 'forward': '+Z',
    'framing': {'target': [0, .79, -.055], 'direction': [1.2, .47, 1.65], 'distance': 8.02},
    'joints': {}, 'frontWheels': ['wheel_frontLeft', 'wheel_frontRight'],
    'lights': {'head': ['Headlamp'], 'tail': ['Taillamp'], 'left': ['SignalLeft'], 'right': ['SignalRight']},
    'headlights': [{'position': [sign * .715, 1.0, 2.245], 'target': [sign * 1.15, .05, 8.3]}
                   for sign in (-1, 1)],
    'hotspots': [],
}
for kind in DOORS:
    for side_name, sign, label in [('Left', 1, '左'), ('Right', -1, '右')]:
        key = kind + side_name
        manifest['joints'][key] = {'node': 'door_' + key, 'axis': [0, 1, 0],
                                   'openAngle': -sign * math.radians(66)}
        manifest['hotspots'].append({'id': key, 'node': 'door_' + key,
                                    'position': [sign * .072, -.052, -.64 if kind == 'front' else -.60],
                                    'label': label + ('前門' if kind == 'front' else '後門')})
manifest['joints']['trunk'] = {'node': 'trunk', 'axis': [1, 0, 0], 'openAngle': math.radians(99)}
manifest['hotspots'] += [{'id': 'trunk', 'node': 'trunk', 'position': [0, -.43, -.52], 'label': '尾門'},
                        {'id': 'headlights', 'node': 'VehicleRoot', 'position': [.74, 1.03, 2.25],
                         'label': '車輛照明'}]

report = {
    'status': 'development', 'visualApproval': 'pending',
    'identity': 'suv-02 debranded reconstruction',
    'dimensionsMeters': {'length': 4.755, 'bodyWidth': 1.920, 'widthWithMirrors': 2.132,
                         'height': 1.660, 'wheelbase': 2.865},
    'wheels': '941 aero 8.5J x 19, 245/50 R19, independent geometry',
    'buildSources': ['scripts/modeling/build_suv_02.py', 'scripts/modeling/suv_02_surfaces.py',
                     'scripts/modeling/suv_02_cabin.py', 'scripts/modeling/vehicle_authoring.py',
                     'scripts/modeling/mesh_aperture.py', 'scripts/modeling/convex_support.py',
                     'scripts/modeling/convex-hull.mjs'],
    'surfaceConstruction': 'Independent C1 longitudinal Hermite profiles and sculpted transverse sections; no Study mesh reuse',
    'limitations': ['Tailgate inner full view and upper hinge detail lack full photographic coverage; structure is authored approximation',
                    'First geometry export requires neutral-light eight-angle and articulated-opening review before approval'],
}
(author.source / 'aperture-clipping.json').write_text(json.dumps(APERTURE_REPORTS, indent=2), encoding='utf-8')
author.export(manifest, report)
print('Vehicle_GEOMETRY_EXPORTED', str(author.output / 'vehicle.glb'))
