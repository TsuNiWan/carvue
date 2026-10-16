"""Reproducible vehicle study based on real-vehicle reference observation.

Brand identifiers are omitted; exterior design rights remain unverified.
Coordinates: X left, Y up, Z forward, in meters.
"""
import math
import sys
from pathlib import Path
from functools import lru_cache

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).parent))
from vehicle_authoring import VehicleAuthoring, point, smoothstep
from mesh_aperture import cut_convex_aperture

car = VehicleAuthoring('sedan-02', 'Reconstructed vehicle study; exterior design rights unverified')
root = car.root
paint = car.material('BodyPaint', (.62, .035, .075), .58, .27, coat=.9)
inner_paint = car.material('InnerPaint', (.23, .028, .044), .36, .4)
glass = car.material('WindowGlass', (.040, .055, .065), rough=.18, alpha=.84)
black = car.material('GrilleBlack', (.015, .019, .022), .12, .34)
seal = car.material('WindowSeals', (.014, .017, .019), rough=.55)
chrome = car.material('PolishedAlloy', (.71, .74, .77), .91, .2)
alloy = car.material('WheelSilver', (.54, .58, .61), .84, .28)
dark_alloy = car.material('WheelInner', (.075, .078, .085), .65, .43)
rubber = car.material('TireRubber', (.019, .022, .024), rough=.79)
leather = car.material('SeatLeather', (.067, .070, .072), rough=.54)
cabin = car.material('CabinBlack', (.033, .038, .042), rough=.65)
carpet = car.material('Carpet', (.037, .039, .041), rough=.94)
lining = car.material('Headliner', (.36, .38, .38), rough=.88)
display = car.material('DisplayGlass', (.008, .022, .031), .1, .19)
plate = car.material('PlateWhite', (.76, .78, .79), rough=.45)
head = car.material('Headlamp', (.74, .82, .9), .15, .16, emission=(.78, .9, 1))
tail = car.material('Taillamp', (.45, .012, .025), .1, .19, emission=(1, .015, .035))
signal_left = car.material('SignalLeft', (.78, .30, .02), rough=.24, emission=(1, .35, .025))
signal_right = car.material('SignalRight', (.78, .30, .02), rough=.24, emission=(1, .35, .025))
reflector = car.material('Reflector', (.4, .012, .022), .15, .3)
tail_lens = car.material('TailLensRed', (.26, .018, .027), .23, .20)
lamp_glass = car.material('LampClearCover', (.46, .50, .54), .05, .09, alpha=.17)


@lru_cache(maxsize=64)
def profile_coefficients(samples):
    h = [b[0] - a[0] for a, b in zip(samples, samples[1:])]
    d = [(b[1] - a[1]) / width for a, b, width in zip(samples, samples[1:], h)]
    slopes = [d[0]]
    for i in range(1, len(samples) - 1):
        if d[i - 1] * d[i] <= 0:
            slopes.append(0)
        else:
            w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
            slopes.append((w1 + w2) / (w1 / d[i - 1] + w2 / d[i]))
    slopes.append(d[-1])
    return h, slopes


def profile(samples, value):
    """Nonuniform monotone cubic interpolation keeps shared surfaces C1."""
    if value <= samples[0][0]:
        return samples[0][1]
    if value >= samples[-1][0]:
        return samples[-1][1]
    h, slopes = profile_coefficients(tuple(samples))
    for i, ((a, av), (b, bv)) in enumerate(zip(samples, samples[1:])):
        if value <= b:
            t = (value - a) / h[i]
            return (2 * t**3 - 3 * t**2 + 1) * av + (t**3 - 2 * t**2 + t) * h[i] * slopes[i] + (-2 * t**3 + 3 * t**2) * bv + (t**3 - t**2) * h[i] * slopes[i + 1]


@lru_cache(maxsize=8192)
def end_section(y, front):
    join = 1.96 if front else -2.04
    direction = 1 if front else -1
    width = body_x(y, join)
    slope = (body_x(y, join + .0001) - body_x(y, join - .0001)) / .0002
    tip = profile([(.185, 2.175), (.27, 2.240), (.39, 2.307), (.55, 2.294),
                   (.70, 2.261), (.83, 2.243), (1.02, 2.13)], y) if front else -2.34 + .105 * ((y - .62) / .44)**2
    return width, .70 * width, width + direction * .22 * slope, join, tip, direction


def end_depth(x, y, front):
    """Match the end cap tangent to the side section at the common join."""
    width, control_a, control_b, join, tip, direction = end_section(y, front)
    target, low, high = min(abs(x), width), 0., 1.
    for _ in range(26):
        t = (low + high) / 2
        value = 3 * (1 - t)**2 * t * control_a + 3 * (1 - t) * t*t * control_b + t**3 * width
        if value < target:
            low = t
        else:
            high = t
    t = (low + high) / 2
    return ((1 - t)**3 + 3 * (1 - t)**2 * t) * tip + 3 * (1 - t) * t*t * (join + direction * .22) + t**3 * join


def front_face(x, y, inset=0):
    return (x, y, end_depth(x, y, True) - inset)


def rear_face(x, y, inset=0):
    recess = .055 * (1 - smoothstep((abs(x) - .18) / .16)) * math.exp(-((y - .52) / .175)**4)
    z = end_depth(x, y, False) + recess + inset
    return (x, y, z)


AXLES = [1.3625, -1.3625]
TYRE_RADIUS = .32535
BOTTOM = .185
width_sections = [(-2.34, .72), (-2.25, .801), (-1.9, .864), (-1.36, .876), (-.7, .864),
                  (0, .863), (.75, .868), (1.36, .882), (1.85, .851), (2.16, .779), (2.32, .64)]
belt_sections = [(-2.34, .985), (-2.2, 1.002), (-1.62, 1.053), (-1.1, 1.034),
                 (-.4, 1.004), (.3, .982), (.78, .967), (1.45, .883), (2.17, .829), (2.32, .803)]
window_sections = [(-1.455, 1.05), (-1.34, 1.13), (-1.1, 1.265), (-.9, 1.327),
                   (-.45, 1.383), (-.15, 1.378), (.18, 1.313), (.46, 1.152), (.775, .98)]
window_sections = [(z, y + .022 * smoothstep((y - profile(belt_sections, z)) / .33)) for z, y in window_sections]
body_sections = [
    (-2.34, [(0, -.065), (.24, -.035), (.56, -.015), (.85, 0), (1, -.020)]),
    (-1.36, [(0, -.068), (.24, -.030), (.48, -.006), (.74, .007), (.90, .004), (1, -.025)]),
    (-.4, [(0, -.055), (.16, -.010), (.34, -.067), (.60, -.051), (.84, -.006), (1, -.033)]),
    (.5, [(0, -.051), (.18, -.012), (.42, -.065), (.65, -.029), (.79, -.003), (1, -.030)]),
    (1.36, [(0, -.059), (.26, -.017), (.45, -.002), (.71, .005), (.89, -.002), (1, -.023)]),
    (2.32, [(0, -.045), (.25, -.018), (.55, 0), (.80, .007), (1, -.024)]),
]


def belt(z):
    return profile(belt_sections, z)


def body_x(y, z, side=1):
    t = max(0, min(1, (y - BOTTOM) / (belt(z) - BOTTOM)))
    offset = profile(body_sections[0 if z < 0 else -1][1], t)
    for (za, section_a), (zb, section_b) in zip(body_sections, body_sections[1:]):
        if za <= z <= zb:
            weight = smoothstep((z - za) / (zb - za))
            offset = profile(section_a, t) * (1 - weight) + profile(section_b, t) * weight
            break
    flare = sum(.008 * math.exp(-((math.hypot(y - TYRE_RADIUS, z - axle) - .405) / .125)**2) for axle in AXLES)
    return side * (profile(width_sections, z) + offset + flare)


def window_x(y, z, side):
    return body_x(belt(z), z, side) - side * .345 * (y - belt(z))


@lru_cache(maxsize=8192)
def body_edge(front, v=None, y=None):
    z = 1.96 if front else -2.04
    height = BOTTOM + (belt(z) - BOTTOM) * v if v is not None else y
    return (body_x(height, z), height, z)


def door_front(v):
    return .798 - .018 * v


def b_pillar(v):
    return -.365 + .025 * v


def door_rear(v):
    return -1.125 - .325 * v


doors = {}
for side, suffix in [(1, 'Left'), (-1, 'Right')]:
    doors['front' + suffix] = car.group('door_front' + suffix, (side * .833, .96, .775), root)
    doors['rear' + suffix] = car.group('door_rear' + suffix, (side * .839, .98, -.346), root)
trunk = car.group('trunk', (0, 1.043, -1.637), root)


def side_panel(name, start, end, side, parent, is_door=False):
    def untrimmed(u, v):
        u = .0025 + .995 * u if is_door else u
        z = start(v) + (end(v) - start(v)) * u
        y = BOTTOM + (belt(z) - BOTTOM) * v
        depth = 0
        if is_door:
            handle_z = -.18 if 'front' in name else -1.13
            handle_y = belt(handle_z) - .105
            radial = ((z - handle_z) / .101)**2 + ((y - handle_y + .008) / .043)**2
            depth = .018 * max(0, 1 - radial)**2
        return (body_x(y, z, side) - side * depth, y, z)
    def arch_clearance(u, v):
        _, y, z = untrimmed(u, v)
        opening = max([BOTTOM] + [TYRE_RADIUS + math.sqrt(max(0, .37**2 - (z - axle)**2)) for axle in AXLES if abs(z - axle) < .37])
        return y - opening
    clipped = {}
    def surface(u, v):
        key = round(u, 12)
        if key not in clipped:
            low, high = 0, 1
            if arch_clearance(u, 0) < 0:
                for _ in range(28):
                    middle = (low + high) / 2
                    if arch_clearance(u, middle) < 0:
                        low = middle
                    else:
                        high = middle
                clipped[key] = high
            else:
                clipped[key] = 0
        return untrimmed(u, clipped[key] + (1 - clipped[key]) * v)
    car.surface(name, surface, 120, 36 if is_door else 26, paint, parent,
                solid=.016 if is_door else .021, normal=(side, 0, 0))
    return surface


for side, suffix in [(1, 'Left'), (-1, 'Right')]:
    side_panel('FrontFender' + suffix, door_front, lambda v: body_edge(True, v=v)[2], side, root)
    side_panel('RearQuarter' + suffix, lambda v: body_edge(False, v=v)[2], door_rear, side, root)
    for front, part in [(True, 'front' + suffix), (False, 'rear' + suffix)]:
        pivot = doors[part]
        start, end = (door_front, b_pillar) if front else (b_pillar, door_rear)
        surface = side_panel('DoorSkin' + part, start, end, side, pivot, True)
        # Inner panels share the exterior's trailing edge and wheel opening.
        car.surface('DoorLiner' + part, lambda u, v: (
            surface(u, v)[0] - side * .082, surface(u, v)[1] + .01, surface(u, v)[2]),
            32, 16, cabin, pivot, solid=.022, normal=(-side, 0, 0))
        car.surface('DoorBottomReturn' + part, lambda u, v: (
            surface(u, 0)[0] - side * .082 * v, surface(u, 0)[1] + .01 * v, surface(u, 0)[2]),
            120, 4, inner_paint, pivot, solid=.006, normal=(0, -1, 0))
        front_z, rear_z = start(1) - .025, end(1) + .025
        def window(u, v):
            z = front_z + (rear_z - front_z) * u
            low = belt(z) + .009
            high = max(low + .008, profile(window_sections, z) - .007)
            y = low + (high - low) * v
            return (window_x(y, z, side), y, z)
        car.surface('DoorGlass' + part, window, 34, 12, glass, pivot, solid=.0035, normal=(side, 0, 0))
        outline = [window(i / 40, 0) for i in range(41)] + [window(1, i / 15) for i in range(1, 16)] + [window(i / 40, 1) for i in range(39, -1, -1)] + [window(0, i / 15) for i in range(14, 0, -1)]
        car.curve('WindowRubber' + part, outline, .0065, seal, pivot, cyclic=True)
        car.curve('UpperChrome' + part, [window(i / 48, 1) for i in range(49)], .0038, chrome, pivot)
        if not front:
            fraction = .74
            car.curve('RearGlassDivision' + suffix, [window(fraction, i / 16) for i in range(17)], .009, seal, pivot)
        edge = [surface(0, i / 32) for i in range(33)] + [surface(i / 32, 1) for i in range(1, 33)] + [surface(1, i / 32) for i in range(31, -1, -1)]
        # The rear bottom edge follows the wheel arch; no fixed strip crosses it.
        for index, points in enumerate([edge[:33], edge[33:65]]):
            car.curve('DoorEdge' + part + str(index), [(x - side * .014, y, z) for x, y, z in points], .006, inner_paint, pivot)
        handle_z = -.18 if front else -1.13
        handle_y = belt(handle_z) - .105
        car.curve('BodyHandle' + part, [(body_x(handle_y, handle_z - .078 + .156 * i / 24, side) + side * (.009 + .021 * math.sin(math.pi * i / 24)),
            handle_y + .004 * math.sin(math.pi * i / 24), handle_z - .078 + .156 * i / 24) for i in range(25)], .0085, paint, pivot)
        arm_z = .17 if front else -.84
        car.box('Armrest' + part, (side * .731, .66, arm_z), (.135, .060, .48 if front else .38), leather, pivot, .028)
        car.box('InnerTrim' + part, (side * .755, .812, arm_z), (.029, .038, .68 if front else .46), leather, pivot, .013)
        car.box('InnerRelease' + part, (side * .731, .80, arm_z + .12), (.012, .02, .091), chrome, pivot, .008)
        car.box('DoorStorage' + part, (side * .759, .35, arm_z), (.073, .14, .46 if front else .29), cabin, pivot, .026)
    car.surface('Rocker' + suffix, lambda u, v: (body_x(.187 + .047 * v, -1.01 + 2.015 * u, side) - side * .010 * (1 - v),
        .187 + .047 * v, -1.01 + 2.015 * u), 64, 6, inner_paint, solid=.016, normal=(side, 0, 0))
    # Fixed B pillar has depth while all exterior window frames move with doors.
    car.surface('PillarB' + suffix, lambda u, v: (
        window_x(.91 + .459 * v, -.351, side) - side * .013,
        .91 + .459 * v, -.385 + .068 * u), 3, 24, seal, root, solid=.036, normal=(side, 0, 0))


def hood(u, v):
    t = 2 * u - 1
    end = front_face(.55 * t, .827 + .035 * (1 - t * t))
    z = .80 + (end[2] - .80) * v
    half = .793 * (1 - v) + .55 * v + .134 * math.sin(math.pi * v)
    y = belt(z) + .025 * (1 - t * t) + .012 * math.exp(-((abs(t) - .70) / .15)**2) * math.sin(math.pi * v)
    y += (end[1] - belt(end[2]) - .025 * (1 - t * t)) * v**4
    return (half * t, y, z)


car.surface('LongHood', hood, 48, 58, paint, solid=.021, normal=(0, 1, 0))
def hood_corner_edge(u):
    inner = hood(1, 1)
    outer = body_edge(True, v=1)
    return front_face(inner[0] + (outer[0] - inner[0]) * u,
                      inner[1] + (outer[1] - inner[1]) * u)


for side in [-1, 1]:
    def hood_bridge(u, v):
        inner = hood(1, v)
        z = .80 + (body_edge(True, v=1)[2] - .80) * v
        outer = (body_x(belt(z), z), belt(z), z)
        leading_inner, leading_outer = hood(1, 1), body_edge(True, v=1)
        linear_end_z = leading_inner[2] + (leading_outer[2] - leading_inner[2]) * u
        correction = (hood_corner_edge(u)[2] - linear_end_z) * v**4
        return (side * (inner[0] + (outer[0] - inner[0]) * u), inner[1] + (outer[1] - inner[1]) * u,
                inner[2] + (outer[2] - inner[2]) * u + correction)
    car.surface('HoodFenderBridge' + str(side), hood_bridge, 18, 58, paint, solid=.018, normal=(0, 1, 0))


def roof(u, v):
    z = .19 - 1.13 * v
    t = 2 * u - 1
    edge_y = profile(window_sections, z)
    x = window_x(edge_y, z, 1) + .008
    return (t * x, edge_y + .025 * (1 - t * t), z)


car.surface('ArchedRoof', roof, 42, 48, paint, solid=.004, normal=(0, 1, 0))
car.surface('RoofLiner', lambda u, v: (roof(u, v)[0] * .973, roof(u, v)[1] - .037, roof(u, v)[2]),
            24, 30, lining, solid=.01, normal=(0, -1, 0))


def windshield(u, v, rear=False):
    t = 2 * u - 1
    at = 1 if rear else 0
    edge = roof(u, at)
    end_z, end_y, end_x = (-1.626, 1.065, .772) if rear else (.80, .973, .785)
    z = edge[2] + (end_z - edge[2]) * v
    destination = (t * end_x, end_y + .025 * (1 - t * t), end_z)
    before, after = roof(u, at - .0001), roof(u, at + .0001)
    start_tangent = [(after[i] - before[i]) / (-1.13 * .0002) * (end_z - edge[2]) for i in range(2)]
    h00, h10, h01, h11 = 2 * v**3 - 3 * v**2 + 1, v**3 - 2 * v**2 + v, -2 * v**3 + 3 * v**2, v**3 - v**2
    coordinates = [h00 * edge[i] + h10 * start_tangent[i] + h01 * destination[i] + h11 * (destination[i] - edge[i]) for i in range(2)]
    return (*coordinates, z)


for rear, name in [(False, 'Windshield'), (True, 'RearGlass')]:
    car.surface(name, lambda u, v: windshield(u, v, rear), 42, 30, glass, solid=.004, normal=(0, 1, -1 if rear else 1))
    for side in [0, 1]:
        points = [windshield(side, i / 40, rear) for i in range(41)]
        car.curve(name + 'Seal' + str(side), points, .009, seal)
        if not rear:
            direction = -1 if side == 0 else 1
            def a_pillar(u, v):
                inner = windshield(side, v, False)
                blend = smoothstep(v / .12)
                high = profile(window_sections, inner[2]) + .008 * blend
                outer = (window_x(high, inner[2], direction) + direction * (.008 + .009 * blend), high, inner[2])
                return tuple(inner[i] + (outer[i] - inner[i]) * u for i in range(3))
            car.surface('PillarA' + str(side), a_pillar,
                5, 44, paint, solid=.012, normal=(direction, 1, 0))
    car.curve(name + 'LowerSeal', [windshield(i / 48, 1, rear) for i in range(49)], .008, seal)
def pillar_c(u, v, side):
    inner = windshield(1, v, True)
    z = -.94 - .60 * v
    outer_y = max(belt(z), profile(window_sections, z))
    blend = smoothstep(v / .14)
    outer = (abs(window_x(outer_y, z, 1)) + .008 * (1 - smoothstep(v)), outer_y, z)
    x = inner[0] + (outer[0] - inner[0]) * u
    y = inner[1] + (outer[1] - inner[1]) * u
    return (side * x, y + .012 * math.sin(math.pi * u) * blend, inner[2] + (outer[2] - inner[2]) * u)


for side in [-1, 1]:
    car.surface('CurvedPillarC' + str(side), lambda u, v: pillar_c(u, v, side),
                18, 36, paint, solid=.023, normal=(side, 1, 0))


def fascia_top(x):
    return 1.005 + .009 * (1 - (x / .70)**2)


def fascia_bottom(x):
    return .754 + .077 * smoothstep(abs(x) / .70)


def deck(u, v):
    t = 2 * u - 1
    end = rear_face(.70 * t, fascia_top(.70 * t), .005)
    half = .720 * (1 - v) + .70 * v + .028 * math.sin(math.pi * v)
    y = 1.065 + (end[1] - 1.065) * v + .014 * math.sin(math.pi * v)
    return (half * t, y, -1.641 + (end[2] + 1.641) * v)


car.surface('TrunkDeck', deck, 38, 36, paint, trunk, solid=.023, normal=(0, 1, 0))
car.surface('TrunkLiner', lambda u, v: (deck(u, v)[0] * .952, deck(u, v)[1] - .039, deck(u, v)[2] + .013),
            24, 24, carpet, trunk, solid=.015, normal=(0, -1, 0))
def rear_glass_base(u, v):
    front, back = windshield(u, 1, True), deck(u, 0)
    return tuple(front[i] + (back[i] + (.004 if i == 2 else 0) - front[i]) * v for i in range(3))


car.surface('RearGlassBase', rear_glass_base, 42, 4, paint, solid=.010, normal=(0, 1, 0))
for side in [-1, 1]:
    def rear_shoulder(u, v):
        inner = deck(1, v)
        z = -1.641 + (body_edge(False, v=1)[2] + 1.641) * v
        outer = (body_x(belt(z), z), belt(z), z)
        return (side * (inner[0] + .004 + (outer[0] - inner[0] - .004) * u),
                inner[1] + (outer[1] - inner[1]) * u, inner[2] + (outer[2] - inner[2]) * u)
    car.surface('RearDeckShoulder' + str(side), rear_shoulder, 16, 38, paint, solid=.021, normal=(side, 1, 0))
    # The concave corner is explicitly triangulated between the shared boundaries.
    bridge = [pillar_c(i / 18, 1, side) for i in range(19)]
    bridge += [rear_shoulder(1, 0), rear_shoulder(0, 0)]
    corner = car.mesh('PillarBaseClosure' + str(side), bridge,
        [(i, i + 1, 19) for i in range(18)] + [(0, 19, 20)], paint, normal=(side, 1, 0))
    car.thickness(corner, .010)
    car.curve('TrunkGooseneck' + str(side), [(side * .51, .855, -1.54), (side * .51, .88, -1.67),
        (side * .51, .96, -1.77), (side * .51, 1.025, -1.84)], .016, inner_paint, trunk, bezier=True)
car.surface('TrunkFloor', lambda u, v: ((2 * u - 1) * .65, .307,
    -1.49 + (rear_face((2 * u - 1) * .65, .307)[2] + .045 + 1.49) * v),
    36, 24, carpet, solid=.04, normal=(0, 1, 0))
car.box('TrunkSeatBack', (0, .605, -1.485), (1.25, .59, .063), carpet, radius=.024)
for side in [-1, 1]:
    car.surface('TrunkWall' + str(side), lambda u, v: (side * .650, .32 + .51 * v,
        -1.50 + (rear_face(side * .650, .32 + .51 * v)[2] + .045 + 1.50) * u),
        30, 22, carpet, solid=.024, normal=(-side, 0, 0))
    car.box('TrunkWheelHouse' + str(side), (side * .571, .429, -1.585), (.235, .305, .37), carpet, radius=.10)
trunk_seal = [(-.70 + 1.4 * i / 30, 1.047, -1.641) for i in range(31)]
trunk_seal += [(deck(1, i / 32)[0] - .016, deck(1, i / 32)[1] - .014, deck(1, i / 32)[2] + .010) for i in range(33)]
trunk_seal += [rear_face(.685, fascia_top(.70) + (fascia_bottom(.685) - fascia_top(.70)) * i / 20, .02) for i in range(21)]
trunk_seal += [rear_face(.685 - 1.37 * i / 40, fascia_bottom(.685 - 1.37 * i / 40) - .007, .02) for i in range(41)]
trunk_seal += [rear_face(-.685, fascia_bottom(.685) + (fascia_top(.70) - fascia_bottom(.685)) * i / 20, .02) for i in range(21)]
trunk_seal += [(deck(0, 1 - i / 32)[0] + .016, deck(0, 1 - i / 32)[1] - .014, deck(0, 1 - i / 32)[2] + .010) for i in range(33)]
car.curve('TrunkApertureSeal', trunk_seal, .010, seal, cyclic=True)
car.surface('TrunkSill', lambda u, v: rear_face((2 * u - 1) * .68,
    fascia_bottom((2 * u - 1) * .68) - .031 + .034 * v, .023),
    36, 5, cabin, solid=.015, normal=(0, 1, 0))
car.surface('TrunkRearLiner', lambda u, v: rear_face((2 * u - 1) * .644,
    .31 + (fascia_bottom((2 * u - 1) * .644) - .03 - .31) * v, .046),
    36, 22, carpet, solid=.02, normal=(0, 0, 1))


def rear_bumper(u, v):
    x = (2 * u - 1) * .80
    for _ in range(8):
        y_top = fascia_bottom(x) - .005
        x = (2 * u - 1) * body_edge(False, y=y_top)[0]
    y = BOTTOM + (y_top - BOTTOM) * v
    return rear_face((2 * u - 1) * body_edge(False, y=y)[0], y)


car.surface('RearBumper', rear_bumper, 72, 34, paint, solid=.024, normal=(0, 0, -1))
car.surface('TrunkRearFascia', lambda u, v: rear_face((2 * u - 1) * .70,
    fascia_bottom((2 * u - 1) * .70) + (fascia_top((2 * u - 1) * .70) - fascia_bottom((2 * u - 1) * .70)) * v, .005),
            40, 16, paint, trunk, solid=.021, normal=(0, 0, -1))
for side in [-1, 1]:
    def outer_fascia(u, v):
        y_top = fascia_top(.70) + (body_edge(False, v=1)[1] - fascia_top(.70)) * u
        y = .831 + (y_top - .831) * v
        return rear_face(side * (.704 + (body_edge(False, y=y)[0] - .704) * u), y)
    car.surface('RearOuterFascia' + str(side), outer_fascia, 18, 24, paint, solid=.021, normal=(0, 0, -1))
    car.surface('RearReflector' + str(side), lambda u, v: rear_face(side * (.55 + .19 * u), .284 + .027 * v, -.004),
                24, 4, reflector, solid=.006, normal=(0, 0, -1))
car.surface('LowerRearValance', lambda u, v: rear_face((2 * u - 1) * (body_edge(False, y=.18 + .068 * v)[0] - .025), .18 + .068 * v, .025),
            48, 8, black, solid=.02, normal=(0, 0, -1))
car.box('RearPlateRecess', rear_face(0, .506, -.005), (.51, .243, .035), black, radius=.027)
car.box('RearPlate', rear_face(0, .515, -.024), (.438, .204, .010), plate, radius=.008)


# Visible cabin uses a low horizontal dashboard and separate seat bolsters.
car.box('CabinFloor', (0, .237, -.26), (1.56, .074, 2.19), carpet, radius=.025)
car.box('RearSeatBulkhead', (0, .70, -1.346), (1.51, .82, .06), cabin, radius=.025)
car.box('CenterTunnel', (0, .385, -.20), (.24, .24, 1.73), cabin, radius=.075)
car.box('Dashboard', (0, .881, .656), (1.50, .225, .363), cabin, radius=.083)
car.box('DashboardHorizontalPad', (0, .978, .635), (1.42, .062, .27), leather, radius=.024)
car.box('CenterDisplay', (0, 1.024, .647), (.302, .117, .024), display, radius=.012)
car.box('Console', (0, .538, .105), (.214, .078, .69), cabin, radius=.031)
car.box('ConsoleArmrest', (0, .584, -.26), (.235, .092, .28), leather, radius=.033)
car.box('GearLever', (0, .611, .19), (.045, .096, .052), leather, radius=.022)
car.box('ClimateControls', (0, .80, .455), (.29, .072, .025), dark_alloy, radius=.011)
for x in [-.58, -.34, .39, .58]:
    car.box('DashboardVent', (x, .873, .467), (.16, .035, .021), black, radius=.009)
for side in [-1, 1]:
    x = side * .377
    car.box('SeatCushion' + str(side), (x, .437, -.17), (.447, .115, .47), leather, radius=.046)
    car.box('SeatBack' + str(side), (x, .761, -.432), (.431, .586, .119), leather, radius=.051)
    for offset in [-.171, .171]:
        car.box('SeatBackBolster', (x + offset, .773, -.391), (.080, .532, .101), leather, radius=.038)
        car.box('SeatBaseBolster', (x + offset, .481, -.165), (.076, .074, .447), leather, radius=.034)
    car.box('SeatHeadrest' + str(side), (x, 1.145, -.442), (.236, .211, .104), leather, radius=.045)
    for offset in [-.064, .064]:
        car.box('HeadrestPost', (x + offset, 1.025, -.444), (.012, .080, .013), chrome, radius=.005)
    car.curve('SeatBelt' + str(side), [(side * .731, 1.095, -.345), (side * .617, .435, -.44)], .012, seal)
car.box('RearSeatCushion', (0, .451, -.964), (1.39, .143, .469), leather, radius=.065)
car.box('RearSeatBack', (0, .746, -1.224), (1.39, .516, .133), leather, radius=.052)
for x in [-.465, 0, .465]:
    car.box('RearHeadrest', (x, 1.092, -1.239), (.239, .191, .111), leather, radius=.045)
car.box('RearParcelShelf', (0, 1.026, -1.414), (1.44, .045, .31), cabin, radius=.022)
car.curve('SteeringRim', [(.385 + .158 * math.cos(i * math.tau / 64), .923 + .145 * math.sin(i * math.tau / 64), .404 + .050 * math.sin(i * math.tau / 64)) for i in range(64)],
          .014, leather, cyclic=True)
car.box('SteeringCenter', (.385, .923, .404), (.095, .097, .039), cabin, radius=.03)
for angle in [0, math.pi, math.pi * 1.5]:
    car.curve('SteeringSpoke', [(.385, .923, .404), (.385 + .147 * math.cos(angle), .923 + .135 * math.sin(angle), .404 + .047 * math.sin(angle))], .016, dark_alloy)
car.box('InstrumentCluster', (.385, .991, .581), (.30, .10, .048), display, radius=.02)


def lathe_x(name, center, section, mat, parent, side=1, segments=96):
    vertices = []
    for dx, radius in section:
        for step in range(segments):
            angle = math.tau * step / segments
            vertices.append((center[0] + side * dx, center[1] + radius * math.cos(angle), center[2] + radius * math.sin(angle)))
    faces = []
    for row in range(len(section)):
        following = (row + 1) % len(section)
        for step in range(segments):
            nxt = (step + 1) % segments
            faces.append((row * segments + step, row * segments + nxt, following * segments + nxt, following * segments + step))
    return car.mesh(name, vertices, faces, mat, parent)


tyre_section = [(-.082, .214), (-.103, .251), (-.1075, .286), (-.097, .314), (-.076, TYRE_RADIUS),
                (.076, TYRE_RADIUS), (.097, .314), (.1075, .286), (.103, .251), (.082, .214)]
for side, suffix in [(1, 'Left'), (-1, 'Right')]:
    for axle, position in zip(AXLES, ['front', 'rear']):
        center = (side * .776, TYRE_RADIUS, axle)
        wheel = car.group('wheel_' + position + suffix, center, root)
        lathe_x('Tyre', center, tyre_section, rubber, wheel, side)
        lathe_x('RimBarrel', center, [(-.078, .218), (.099, .218), (.109, .226), (.107, .232), (.091, .233), (-.078, .227)], alloy, wheel, side)
        lathe_x('BrakeDisc', center, [(.041, .046), (.041, .179), (.049, .179), (.049, .046)], dark_alloy, wheel, side)
        lathe_x('Hub', center, [(.075, .0), (.075, .043), (.105, .045), (.111, .034), (.112, .0)], dark_alloy, wheel, side)
        for spoke in range(10):
            angle = spoke * math.tau / 10 + math.pi / 10
            def spoke_surface(u, v):
                radius = .044 + .181 * u
                width = .010 + .013 * smoothstep(u)
                theta = angle + (2 * v - 1) * width / radius
                dx = .089 + .018 * smoothstep(u) + .004 * math.sin(math.pi * u) * (1 - (2 * v - 1)**2)
                return (center[0] + side * dx, center[1] + radius * math.cos(theta), center[2] + radius * math.sin(theta))
            car.surface('SilverSpoke', spoke_surface, 16, 6, alloy, wheel, solid=.013, normal=(side, 0, 0))
        for bolt in range(5):
            angle = bolt * math.tau / 5 + math.pi / 2
            bolt_center = (center[0], center[1] + .055 * math.cos(angle), center[2] + .055 * math.sin(angle))
            lathe_x('BoltSocket', bolt_center, [(.087, .013), (.102, .013), (.104, .009), (.091, .009)], black, wheel, side, 24)
            lathe_x('Bolt', bolt_center, [(.093, .0), (.093, .007), (.10, .007), (.101, .0)], chrome, wheel, side, 12)
        for dx in [-.055, -.019, .019, .055]:
            lathe_x('TreadGroove', center, [(dx - .0012, TYRE_RADIUS + .0002), (dx + .0012, TYRE_RADIUS + .0002),
                                         (dx + .0012, TYRE_RADIUS - .001)], seal, wheel, side)
        # A separate liner ends within the fixed wheel well rather than on an opening door.
        inner_wall = .776 - TYRE_RADIUS * math.sin(math.radians(30)) - .1075 * math.cos(math.radians(30)) - .020 if position == 'front' else .59
        car.surface('WheelWellLiner' + position + suffix, lambda u, v: (
            side * (inner_wall + (.82 - inner_wall) * u), TYRE_RADIUS + .377 * math.sin(math.pi * v), axle + .377 * math.cos(math.pi * v)),
            6, 42, seal, root, solid=.01, normal=(-side, 0, 0))
        car.surface('WheelWellInnerWall' + position + suffix, lambda u, v: (
            side * inner_wall, BOTTOM + (TYRE_RADIUS + .377 * math.sqrt(max(0, 1 - (2*u - 1)**2)) - BOTTOM) * v,
            axle + .377 * (2*u - 1)), 80, 6, seal, root, solid=.01, normal=(side, 0, 0))


def grille_width(y):
    return profile([(.410, .390), (.448, .484), (.515, .553), (.675, .564), (.805, .559)], y)


def grille_top(x):
    return .815 + .035 * (1 - min(1, abs(x) / .55)**2)


def grille_surface(u, v):
    t, x = 2 * u - 1, (2 * u - 1) * .559
    for _ in range(12):
        y = .414 + (grille_top(x) - .414) * v
        x = t * grille_width(y)
    return front_face(x, y, .042)


projection_reports = []
aperture_reports = []
aperture_visibility_reports = []


def surface_normal(fn, u, v, facing):
    du = Vector(fn(min(1, u + .001), v)) - Vector(fn(max(0, u - .001), v))
    dv = Vector(fn(u, min(1, v + .001))) - Vector(fn(u, max(0, v - .001)))
    normal = du.cross(dv).normalized()
    return -normal if normal.dot(Vector(facing)) < 0 else normal


def projected_lamp(name, seed, prefixes, facing, joint_gap=None):
    """Freeze a shared optical carrier on the actual uncut exterior meshes."""
    bpy.context.view_layer.update()
    candidates = [obj for obj in bpy.data.objects if obj.type == 'MESH' and any(obj.name.startswith(prefix) for prefix in prefixes)]
    nu, nv = 64, 16
    positions, normals, distances, gap_samples = [], [], [], []
    for j in range(nv + 1):
        for i in range(nu + 1):
            u, v = i / nu, j / nv
            center = Vector(seed(u, v))
            outward = surface_normal(seed, u, v, facing)
            origin = Vector(point(center + outward * .45))
            direction = Vector(point(-outward))
            hits = []
            for obj in candidates:
                inverse = obj.matrix_world.inverted()
                found, location, normal, _ = obj.ray_cast(inverse @ origin, inverse.to_3x3() @ direction, distance=.9)
                if found:
                    location = obj.matrix_world @ location
                    normal = (obj.matrix_world.to_3x3() @ normal).normalized()
                    if normal.dot(direction) < -.05:
                        hits.append(((location - origin).length, location, normal))
            if not hits:
                # A declared panel joint has no paint surface; bridge only that physical gap.
                if joint_gap and joint_gap[0] <= abs(center.x) <= joint_gap[1]:
                    positions.append(center)
                    normals.append(outward)
                    distances.append(0)
                    gap_samples.append({'u': u, 'v': v, 'absoluteX': abs(center.x)})
                    continue
                raise ValueError(f'{name}: no exterior intersection at u={u:.5f}, v={v:.5f}, point={tuple(center)}')
            _, location, normal = min(hits, key=lambda item: item[0])
            position = Vector((location.x, location.z, -location.y))
            positions.append(position)
            normals.append(Vector((normal.x, normal.z, -normal.y)))
            distances.append((position - center).length)
    projection_reports.append({'name': name, 'sampleCount': len(positions), 'projectedSampleCount': len(positions) - len(gap_samples),
        'maxSeedDistanceMeters': max(distances), 'carrierFrozenBeforeCut': True, 'declaredJointGap': joint_gap, 'jointGapSamples': gap_samples})
    def carrier(u, v, offset=0):
        x, y = max(0, min(1, u)) * nu, max(0, min(1, v)) * nv
        i, j = min(nu - 1, int(x)), min(nv - 1, int(y))
        a, b = x - i, y - j
        indices = [j * (nu + 1) + i, j * (nu + 1) + i + 1, (j + 1) * (nu + 1) + i, (j + 1) * (nu + 1) + i + 1]
        weights = [(1 - a) * (1 - b), a * (1 - b), (1 - a) * b, a * b]
        position = sum((positions[index] * weight for index, weight in zip(indices, weights)), Vector())
        normal = sum((normals[index] * weight for index, weight in zip(indices, weights)), Vector()).normalized()
        return tuple(position + normal * offset)
    return carrier


def lamp_recess(name, fn, parent, prefixes, normal, depth=.12, margin=.025):
    boundary = [(i / 44, 0) for i in range(45)] + [(1, j / 12) for j in range(1, 13)]
    boundary += [(i / 44, 1) for i in range(43, -1, -1)] + [(0, j / 12) for j in range(11, 0, -1)]
    # A bowed carrier can extend beyond the hull of its perimeter alone.
    boundary += [(i / 32, j / 12) for j in range(1, 12) for i in range(1, 32)]
    front, back = [], []
    for u, v in boundary:
        position = Vector(fn(u, v))
        outward = surface_normal(fn, u, v, normal)
        front.append(tuple(position + outward * margin))
        back.append(tuple(position - outward * (depth - margin)))
    aperture_reports.extend(cut_convex_aperture(name, front, back, prefixes))
    bpy.context.view_layer.update()
    carriers = [obj for obj in bpy.data.objects if obj.type == 'MESH' and any(obj.name.startswith(prefix) for prefix in prefixes)]
    occlusions = []
    for j in range(1, 12):
        for i in range(1, 32):
            u, v = i / 32, j / 12
            position = Vector(fn(u, v))
            outward = surface_normal(fn, u, v, normal)
            origin = Vector(point(position + outward * .03))
            direction = Vector(point(-outward))
            for obj in carriers:
                inverse = obj.matrix_world.inverted()
                found, location, _, _ = obj.ray_cast(inverse @ origin, inverse.to_3x3() @ direction, distance=.035)
                if found:
                    occlusions.append({'u': u, 'v': v, 'carrier': obj.name,
                        'distance': (obj.matrix_world @ location - origin).length})
    aperture_visibility_reports.append({'aperture': name, 'samples': 341, 'occlusions': occlusions})
    if occlusions:
        raise ValueError(f'{name}: paint blocks the optical carrier at {occlusions[:5]}')


# The Sedan's chrome wing wraps a recessed shield grille and narrow lamps.
car.surface('ShieldGrilleRecess', grille_surface, 44, 40, black, solid=.024, normal=(0, 0, 1))
for side in [-1, 1]:
    def front_corner(u, v):
        inner = hood(1, 1)
        start = (grille_width(inner[1]) + .018 - inner[0]) / (body_edge(True, v=1)[0] - inner[0])
        upper = hood_corner_edge(start + (1 - start) * u)
        y = .414 + (upper[1] - .414) * v
        def row_x(height):
            low = grille_width(height) + .018
            return low + (body_edge(True, y=height)[0] - low) * u
        x = row_x(y) + (upper[0] - row_x(upper[1])) * v**4
        return front_face(side * x, y)
    car.surface('FrontCorner' + str(side), front_corner, 30, 36, paint, solid=.024, normal=(side, 0, 1))
    car.surface('SignatureWing' + str(side), lambda u, v: front_face(side * (grille_width(.414 + .401 * v) + (.014 + .024 * v**3) * u),
        .414 + .401 * v, -.006), 5, 56, chrome, solid=.003, normal=(0, 0, 1))
car.surface('NoseUpperLip', lambda u, v: front_face(hood(u, 1)[0],
    grille_top(hood(u, 1)[0]) + (hood(u, 1)[1] - grille_top(hood(u, 1)[0])) * v),
            44, 8, paint, solid=.018, normal=(0, 0, 1))
car.surface('FrontLowerBumper', lambda u, v: front_face((2 * u - 1) * body_edge(True, y=BOTTOM + (.410 - BOTTOM) * v)[0], BOTTOM + (.410 - BOTTOM) * v),
            52, 14, paint, solid=.019, normal=(0, 0, 1))
def lower_intake(u, v):
    return front_face((2 * u - 1) * .665, .247 + .080 * v * (.25 + .75 * math.sin(math.pi * u)**.35), .008)
lamp_recess('WideLowerIntake', lower_intake, root, ['FrontLowerBumper'], (0, 0, 1), .065)
car.surface('WideLowerIntake', lower_intake, 52, 6, black, solid=.015, normal=(0, 0, 1))
car.curve('GrilleLowerChrome', [front_face(-.390 + .780 * i / 28, .414 - .012 * math.sin(math.pi * i / 28), -.005) for i in range(29)], .009, chrome)
car.curve('FrontSplitter', [front_face((2 * i / 52 - 1) * .808, .210, -.004) for i in range(53)], .010, black)
for row in range(14):
    y = .436 + .028 * row
    for column in range(-17, 18):
        x = column * .032 + (row % 2) * .016
        if abs(x) + .017 < grille_width(y) - .018 and y + .013 < grille_top(x) - .008:
            diamond = [front_face(x + dx, y + dy, .026) for dx, dy in [(0, .013), (.015, 0), (0, -.013), (-.015, 0)]]
            car.curve('GrilleMesh', diamond, .0018, dark_alloy, cyclic=True)
car.box('FrontPlateMount', front_face(0, .473, -.016), (.461, .20, .026), black, radius=.008)
car.box('FrontPlate', front_face(0, .473, -.032), (.435, .185, .007), plate, radius=.005)


def ellipse(name, center, rx, ry, mat, parent=None, depth=.004, rear=False):
    points = []
    for i in range(64):
        angle = math.tau * i / 64
        x, y = center[0] + rx * math.cos(angle), center[1] + ry * math.sin(angle)
        surface = rear_face(x, y) if rear else front_face(x, y)
        points.append((x, y, surface[2] + center[2]))
    return car.curve(name, points, depth, mat, parent, cyclic=True)


for side, suffix in [(1, 'Left'), (-1, 'Right')]:
    signal = signal_left if side == 1 else signal_right
    def head_seed(u, v):
        half_height = .006 + .037 * math.sin(math.pi * u)**.65
        y = .814 + .025 * u - 2 * half_height * (1 - v)
        edge_x, _, edge_z = body_edge(True, y=y)
        if u <= .68:
            x = .582 + (edge_x - .582) * u / .68
            return front_face(side * x, y)
        z = edge_z + (1.74 - edge_z) * (u - .68) / .32
        return (body_x(y, z, side), y, z)
    head_prefixes = ['FrontFender' + suffix, 'LongHood', 'HoodFenderBridge' + str(side), 'FrontCorner' + str(side), 'NoseUpperLip']
    lamp = projected_lamp('Headlamp' + suffix, head_seed, head_prefixes, (side, 0, 1))
    def wing_seed(u, v):
        height = 2 * (.006 + .037 * math.sin(math.pi * u)**.65)
        return head_seed(u, -(.007 + .020 * (1 - u)) * v / height)
    wing = projected_lamp('HeadlampWing' + suffix, wing_seed, head_prefixes, (side, 0, 1))
    lamp_recess('HeadlampWell' + suffix, lamp, root, head_prefixes, (side, 0, 1), .07, .003)
    car.surface('SlimHeadlampCase' + suffix, lambda u, v: lamp(u, v, -.009), 44, 12, black, solid=.019, normal=(side, 0, 1))
    car.surface('ChromeHeadlampWing' + suffix, lambda u, v: wing(u, v, .004),
                44, 5, chrome, solid=.003, normal=(side, 0, 1))
    car.curve('HeadlampUpperBlade' + suffix, [lamp(i / 48, .92, .004) for i in range(49)], .0042, head)
    car.curve('HeadlampLowerBlade' + suffix, [lamp(.10 + .85 * i / 40, .16, .004) for i in range(41)], .0035, head)
    # One main projector matches the recorded Signature lamp, with an inner reflector.
    for u in [.53]:
        center = lamp(u, .52, .006)
        car.curve('ProjectorRim' + suffix, [(center[0] + .022 * math.cos(i * math.tau / 40),
            center[1] + .020 * math.sin(i * math.tau / 40), center[2] - side * .67 * .022 * math.cos(i * math.tau / 40)) for i in range(40)],
            .0033, chrome, cyclic=True)
        car.box('ProjectorLens' + suffix, center, (.030, .029, .013), head, radius=.012)
    car.surface('InnerLampReflector' + suffix, lambda u, v: lamp(.12 + .22 * u, .32 + .32 * v, .005),
                8, 4, chrome, solid=.003, normal=(0, 0, 1))
    car.curve('FrontTurn' + suffix, [lamp(.79 + .19 * i / 12, .46, .007) for i in range(13)], .005, signal)
    car.surface('HeadlampClearCover' + suffix, lambda u, v: lamp(u, v, .016), 44, 12, lamp_glass,
                solid=.0015, normal=(side, 0, 1))
    def tail_seed(u, v):
        height = .012 + .105 * math.sin(math.pi * u)**.45
        y = .970 + .008 * u - height * (1 - v)
        edge_x, _, edge_z = body_edge(False, y=y)
        if u <= .86:
            return rear_face(side * (.415 + (edge_x - .415) * u / .86), y)
        z = edge_z + (-1.89 - edge_z) * (u - .86) / .14
        return (body_x(y, z, side), y, z)
    tail_prefixes = ['TrunkRearFascia', 'RearOuterFascia' + str(side), 'RearQuarter' + suffix, 'RearDeckShoulder' + str(side)]
    lens = projected_lamp('Taillamp' + suffix, tail_seed, tail_prefixes, (side, 0, -1), joint_gap=(.700, .704))
    lamp_recess('TaillampWell' + suffix, lens, root, tail_prefixes, (side, 0, -1), .085, .003)
    @lru_cache(maxsize=512)
    def tail_seam(v, x):
        low, high = 0, .95
        for _ in range(24):
            middle = (low + high) / 2
            if abs(lens(middle, v)[0]) < x:
                low = middle
            else:
                high = middle
        return (low + high) / 2
    # A continuous tapered housing is divided at the trunk seam, with a wraparound outer tip.
    for inner, parent, name, prefixes in [
        (True, trunk, 'Inner', ['TrunkRearFascia']),
        (False, root, 'Outer', ['RearOuterFascia' + str(side), 'RearQuarter' + suffix, 'RearDeckShoulder' + str(side)])]:
        def patch(u, v):
            seam = tail_seam(v, .697 if inner else .704)
            return lens(seam * u if inner else seam + (1 - seam) * u, v, -.006)
        car.surface('TailLens' + name + suffix, patch, 44, 12, tail_lens, parent, solid=.015, normal=(side, 0, -1))
    for center_x, parent in [(.755, root), (.640, trunk)]:
        center_u = tail_seam(.53, center_x)
        width = (Vector(lens(center_u + .01, .5)) - Vector(lens(center_u - .01, .5))).length / .02
        height = (Vector(lens(center_u, 1)) - Vector(lens(center_u, 0))).length
        radius_u, radius_v = .049 / width, .40
        def ring_point(angle, radius, depth):
            return lens(center_u + radius_u * radius * math.cos(angle), .53 + radius_v * radius * math.sin(angle), depth)
        car.surface('TailReflectorCup', lambda u, v: ring_point(math.tau * u, .78 * v, .007 * v*v),
                    64, 8, dark_alloy, parent, solid=.002, normal=(side, 0, -1))
        car.surface('TailLightRing', lambda u, v: ring_point(math.tau * u,
                    1 - (.13 + .10 * max(0, -math.sin(math.tau * u))) * v, .009 + .002 * math.sin(math.pi * v)),
                    64, 5, tail, parent, solid=.002, normal=(side, 0, -1))
        car.curve('TailCupInnerRim', [ring_point(i * math.tau / 64, .70, .006) for i in range(64)],
                    .002, chrome, parent, cyclic=True)
    car.curve('RearTurn' + suffix, [lens(.73 + .18 * i / 18, .18, .003) for i in range(19)], .0048, signal)
    # Mirror stems and caps belong to the front-door hinge.
    door = doors['front' + suffix]
    car.curve('MirrorStem' + suffix, [(side * .84, .967, .565), (side * .932, 1.02, .532)], .020, black, door)
    car.box('MirrorBase' + suffix, (side * .976, 1.052, .507), (.212, .077, .124), black, door, .030)
    car.box('MirrorCap' + suffix, (side * .976, 1.084, .525), (.208, .074, .134), paint, door, .033)
    car.box('MirrorGlass' + suffix, (side * .974, 1.057, .447), (.179, .056, .008), chrome, door, .016)
    car.curve('MirrorTurn' + suffix, [(side * (.9 + .165 * i / 24), 1.061, .583 - .015 * (i / 24)**2) for i in range(25)], .0037, signal, door)
    # Door jambs remain fixed and follow the corresponding window surface.
    car.curve('FrontDoorJamb' + suffix, [(side * .798, .24, .774), (side * .798, .75, .774),
        (side * .796, .973, .766)], .020, inner_paint)
    car.curve('RearDoorJamb' + suffix, [(side * .792, .83, -1.40), (side * .784, 1.035, -1.445)], .021, inner_paint)
    car.box('ExhaustOutlet' + suffix, rear_face(side * .617, .221, -.026), (.09, .065, .071), chrome, radius=.025)
    car.box('ExhaustBore' + suffix, rear_face(side * .617, .221, -.065), (.07, .045, .006), black, radius=.019)

for side in [-1, 1]:
    car.curve('Wiper', [(side * .09, .997, .749), (side * .45, 1.010, .729), (side * .67, 1.017, .708)], .006, black)
car.box('EngineBayClosure', (0, .779, 1.21), (1.43, .036, .74), black, radius=.025)
car.box('Underbody', (0, .192, -.02), (1.40, .034, 3.31), black, radius=.018)

# Keep the folded shell returns from tilting the exterior shading normals.
for obj in bpy.data.objects:
    if obj.type == 'MESH' and not obj.data.has_custom_normals and any(material in {paint, inner_paint} for material in obj.data.materials):
        obj.data.set_sharp_from_angle(angle=math.radians(35))

manifest = {
    'schemaVersion': 1, 'vehicleId': 'sedan-02', 'assetVersion': '1.1.0', 'units': 'meter', 'forward': '+Z',
    'framing': {'target': [0, .634, 0], 'direction': [1.2, .46, 1.65], 'distance': 7.55},
    'joints': {key: {'node': 'door_' + key, 'axis': [0, 1, 0], 'openAngle': math.radians(-67 if key.endswith('Left') else 67)} for key in doors},
    'frontWheels': ['wheel_frontLeft', 'wheel_frontRight'],
    'lights': {'head': ['Headlamp'], 'tail': ['Taillamp'], 'left': ['SignalLeft'], 'right': ['SignalRight']},
    'headlights': [{'position': [side * .72, .85, 2.15], 'target': [side * 1.15, .05, 8.2]} for side in [-1, 1]],
    'hotspots': []
}
manifest['joints']['trunk'] = {'node': 'trunk', 'axis': [1, 0, 0], 'openAngle': math.radians(70)}
for key in doors:
    side = 1 if key.endswith('Left') else -1
    label = ('左' if side == 1 else '右') + ('前門' if key.startswith('front') else '後門')
    manifest['hotspots'].append({'id': key, 'node': 'door_' + key, 'position': [side * .04, -.11, -.72 if key.startswith('front') else -.55], 'label': label})
manifest['hotspots'] += [
    {'id': 'trunk', 'node': 'trunk', 'position': [0, -.11, -.62], 'label': '行李廂'},
    {'id': 'headlights', 'node': 'VehicleRoot', 'position': [.72, .87, 2.18], 'label': '車輛照明'}]
car.export(manifest, {
    'authoringScript': 'scripts/modeling/build_sedan_02.py', 'sharedPrimitives': 'scripts/modeling/vehicle_authoring.py',
    'apertureScript': 'scripts/modeling/mesh_aperture.py',
    'referenceDimensions': {'length': 4.660, 'width': 1.795, 'height': 1.440, 'wheelbase': 2.725},
    'wheelSpecification': '18-inch silver ten-spoke, 215/45 R18', 'visualApproval': 'pending independent review',
    'opticalCarrierProjection': projection_reports,
    'apertureClipping': aperture_reports,
    'apertureVisibility': aperture_visibility_reports,
    'construction': 'Independent monotone cubic Sedan profiles; separately hinged four doors and trunk; inner rear rings move with trunk; plate remains on bumper.'})
