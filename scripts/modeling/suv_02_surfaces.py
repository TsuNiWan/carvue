"""Independent Study longitudinal and cross-car profiles in CARVUE metres.

The profiles follow the lower 20 Study orthographic drawing and Study photos.
They are authored surfaces, not factory CAD or a scaled sedan body.
"""
import math


FRONT_AXLE = 1.4325
REAR_AXLE = -1.4325
TYRE_RADIUS = .3638
ARCH_RADIUS = .407


def blend(a, b, t):
    return a + (b - a) * t


def profile(points, value):
    """Shape-preserving cubic Hermite interpolation with shared C1 tangents."""
    if value <= points[0][0]:
        return points[0][1]
    if value >= points[-1][0]:
        return points[-1][1]
    slopes = [(b[1] - a[1]) / (b[0] - a[0]) for a, b in zip(points, points[1:])]
    tangents = [slopes[0]]
    for i in range(1, len(points) - 1):
        left, right = slopes[i - 1], slopes[i]
        if left * right <= 0:
            tangents.append(0)
        else:
            h0, h1 = points[i][0] - points[i - 1][0], points[i + 1][0] - points[i][0]
            w0, w1 = 2 * h1 + h0, h1 + 2 * h0
            tangents.append((w0 + w1) / (w0 / left + w1 / right))
    tangents.append(slopes[-1])
    for i, ((a, av), (b, bv)) in enumerate(zip(points, points[1:])):
        if value <= b:
            h, t = b - a, (value - a) / (b - a)
            return ((2 * t ** 3 - 3 * t ** 2 + 1) * av
                    + (t ** 3 - 2 * t ** 2 + t) * h * tangents[i]
                    + (-2 * t ** 3 + 3 * t ** 2) * bv
                    + (t ** 3 - t ** 2) * h * tangents[i + 1])
    return points[-1][1]


BELT = [(-2.40, 1.13), (-2.14, 1.20), (-1.72, 1.255), (-1.31, 1.222),
        (-.65, 1.177), (.10, 1.16), (.86, 1.175), (1.42, 1.115), (1.96, 1.046), (2.30, .985)]
WIDTH = [(-2.4425, .914), (-2.14, .944), (-1.56, .957), (-1.1, .948),
         (-.35, .93), (.40, .924), (1.35, .957), (1.76, .943), (2.11, .90), (2.3125, .83)]
ROOF = [(-1.99, 1.532), (-1.66, 1.590), (-1.00, 1.635), (-.47, 1.657),
        (-.05, 1.645), (.21, 1.586)]
ROOF_WIDTH = [(-1.99, .653), (-1.55, .716), (-.45, .741), (.0, .730), (.21, .695)]


def belt(z):
    return profile(BELT, z)


def width(z, y):
    top = belt(z)
    t = max(0, min(1, (y - .27) / (top - .27)))
    # The lower door has a shallow concavity, and the upper shoulder rounds inward.
    raised_shoulder = profile([(-2.4425, .20), (-1.66, .92), (-1.12, 1), (-.45, -.25),
                               (.55, -.12), (1.43, .78), (2.3125, .1)], z)
    shaped_t = t - .11 * raised_shoulder * math.sin(math.pi * t)
    cross = profile([(0, -.056), (.12, -.015), (.29, -.045), (.49, -.058),
                     (.73, -.011), (.87, .003), (1, -.040)], shaped_t)
    lower_sculpt = profile([(-2.4425, .12), (-1.75, .24), (-1.30, 1), (-.80, .78),
                            (.15, .70), (.80, .36), (1.35, .18), (2.3125, .05)], z)
    cross -= .041 * lower_sculpt * math.exp(-((t - .39) / .21) ** 2)
    return profile(WIDTH, z) + cross


def side(sign, z, y, offset=0):
    return (sign * (width(z, y) + offset), y, z)


def arch_bottom(z, base=.273):
    result = base
    for axle in (FRONT_AXLE, REAR_AXLE):
        distance = z - axle
        if abs(distance) < ARCH_RADIUS:
            result = max(result, TYRE_RADIUS + math.sqrt(ARCH_RADIUS ** 2 - distance ** 2))
    return result


def skin(sign, front, rear, u, v, offset=0):
    z = blend(front, rear, u)
    y = blend(arch_bottom(z), belt(z), v)
    return side(sign, z, y, offset)


def roof(z, t):
    return (profile(ROOF_WIDTH, z) * t,
            profile(ROOF, z) - .046 * abs(t) ** 2.5, z)


def window_x(sign, y, z):
    lower = width(z, belt(z)) - .015
    upper = profile(ROOF_WIDTH, max(-1.99, min(.21, z)))
    amount = max(0, min(1, (y - belt(z)) / max(.20, profile(ROOF, z) - .046 - belt(z))))
    return sign * blend(lower, upper, amount)


def window_point(sign, z, y, offset=0):
    return (window_x(sign, y, z) + sign * offset, y, z)


def nose_corner(y):
    return profile([(.255, 2.025), (.65, 2.045), (.91, 2.015), (1.16, 1.975)], y)


def front_z(x, y):
    cheek = max(0, min(1, (abs(x) - .43) / .18)) * max(0, min(1, (.94 - abs(x)) / .10))
    diagonal = .86 - .55 * (abs(x) - .45)
    fold = .018 * math.exp(-((y - diagonal) / .105) ** 2)
    lower_return = -.037 * math.exp(-((y - diagonal + .13) / .14) ** 2)
    nose = profile([(.255, 2.275), (.44, 2.3125), (.65, 2.300),
                    (.78, 2.278), (.93, 2.225), (1.13, 2.150)], y)
    corner = nose_corner(y)
    edge_width = width(corner, y)
    t = min(1, abs(x) / edge_width)
    if 1 - t < 1e-10:
        t = 1
    # Match the longitudinal side-panel tangent at the shared bumper edge.
    side_slope = max(.001, -(width(corner + .0001, y) - width(corner - .0001, y)) / .0002)
    q = min(.48, 2 * (nose - corner) * side_slope / edge_width)
    rounding = q / math.sqrt(1 - 2 * q)
    normalization = math.sqrt(1 + rounding * rounding) - rounding
    section = (math.sqrt(rounding * rounding + max(0, 1 - t ** 4)) - rounding) / normalization
    return (corner + (nose - corner) * section
            + cheek * (fold + lower_return) * (1 - t * t) ** 2)


def rear_z(x, y):
    crown = profile([(.255, -2.3425), (.35, -2.4025), (.45, -2.4425), (.56, -2.405),
                     (.66, -2.361), (.78, -2.418), (.88, -2.420), (1.05, -2.412),
                     (1.22, -2.350)], y)
    return crown + .067 * (abs(x) / .96) ** 2


def nose_edge(v):
    z = 2.02
    for _ in range(12):
        y = blend(.273, belt(z), v)
        x = width(z, y)
        z = nose_corner(y)
    return (x, y, z)


def front_face(u, v):
    edge = nose_edge(v)
    x = math.sin((u - .5) * math.pi) * edge[0]
    return (x, edge[1], front_z(x, edge[1]))


def hood_surface(u, v):
    linear_t = 2 * u - 1
    t = blend(linear_t, math.sin((u - .5) * math.pi), v * v)
    terminal = front_face(u, 1)
    z = blend(.872, terminal[2], v)
    crown = .036 * (1 - t * t)
    ridge = .012 * math.exp(-((abs(t) - .68) / .11) ** 2) * math.sin(math.pi * v)
    end_t = math.sin((u - .5) * math.pi)
    end_z = terminal[2]
    end = (width(end_z, belt(end_z)) * end_t,
           belt(end_z) + .036 * (1 - end_t * end_t), end_z)
    amount = max(0, (v - .65) / .35)
    amount = amount * amount * (3 - 2 * amount)
    base = (width(z, belt(z)) * t, belt(z) + crown + ridge, z)
    return tuple(base[i] + amount * (terminal[i] - end[i]) for i in range(3))


def windshield_surface(u, v):
    t = 2 * u - 1
    bottom = (.827 * t, 1.196 + .018 * (1 - t * t), .866 - .034 * (1 - t * t))
    top = roof(.21, t)
    return tuple(blend(bottom[i], top[i], v) for i in range(3))


def end_skin(sign, front, rear, u, v):
    front_is_nose, rear_is_tail = front > 2.25, rear < -2.35
    base_front, base_rear = 2.0 if front_is_nose else front, -2.35 if rear_is_tail else rear
    z = blend(base_front, base_rear, u)
    # Wheel-opening columns must not slide across the circular boundary as Y changes.
    if front_is_nose:
        amount = max(0, min(1, (z - 1.88) / .12))
        z += (nose_edge(v)[2] - base_front) * amount * amount * (3 - 2 * amount)
    if rear_is_tail:
        for _ in range(12):
            y = blend(.273, belt(rear), v)
            rear = rear_z(width(rear, y), y)
        amount = max(0, min(1, (-z - 1.95) / .40))
        z += (rear - base_rear) * amount * amount * (3 - 2 * amount)
    y = blend(arch_bottom(z), belt(z), v)
    return side(sign, z, y)


def end_width(z_function, y):
    x = .89
    for _ in range(12):
        x = width(z_function(x, y), y)
    return x


def head_position(x, y, offset=0):
    y -= .008 + .035 * max(0, (abs(x) - .485) / .425)
    sign = 1 if x >= 0 else -1
    corner = nose_corner(y)
    edge = width(corner, y)
    epsilon = .0001
    if abs(x) <= edge:
        z = front_z(x, y)
        normal = (-(front_z(x + epsilon, y) - front_z(x - epsilon, y)) / (2 * epsilon),
                  -(front_z(x, y + epsilon) - front_z(x, y - epsilon)) / (2 * epsilon), 1)
    else:
        phase = min(1, (abs(x) - edge) / max(.018, .922 - edge))
        z = corner - .235 * phase
        x = sign * width(z, y)
        normal = (sign, -(width(z, y + epsilon) - width(z, y - epsilon)) / (2 * epsilon),
                  -(width(z + epsilon, y) - width(z - epsilon, y)) / (2 * epsilon))
    magnitude = math.sqrt(sum(value * value for value in normal))
    return tuple(value + offset * normal[i] / magnitude for i, value in enumerate((x, y, z)))


def tail_position(x, y, offset=0):
    sign = 1 if x >= 0 else -1
    if abs(x) <= .855:
        amount = abs(x) / .855
        amount = amount * amount * (3 - 2 * amount)
        return (x + sign * offset * amount, y, rear_z(x, y) - offset)
    phase = max(0, min(1, (abs(x) - .855) / .097))
    edge = end_width(rear_z, y)
    if phase <= .55:
        amount = phase / .55
        actual_x = blend(.855, edge, amount)
        return (sign * (actual_x + offset), y, rear_z(actual_x, y) - offset)
    amount = (phase - .55) / .45
    z = rear_z(edge, y) + .335 * amount
    # Both offset shells share the same miter at the rear-to-side crease.
    return (sign * (width(z, y) + offset), y, z - offset * (1 - amount))


def sample_path(points, count=8):
    """Sample a closed path with bounded C1 corner rounding."""
    result = []
    n = len(points)
    for i in range(n):
        a, b, c, d = [points[j % n] for j in (i - 1, i, i + 1, i + 2)]
        for j in range(count):
            t = j / count
            result.append(tuple(.5 * ((2 * b[k]) + (-a[k] + c[k]) * t
                                      + (2 * a[k] - 5 * b[k] + 4 * c[k] - d[k]) * t * t
                                      + (-a[k] + 3 * b[k] - 3 * c[k] + d[k]) * t ** 3)
                                for k in range(len(b))))
    return result


def corner_path(points, fraction=.085, steps=6):
    """Small quadratic corner fillets separated by straight design edges."""
    result = []
    for i, b in enumerate(points):
        a, c = points[i - 1], points[(i + 1) % len(points)]
        entry = tuple(blend(b[k], a[k], fraction) for k in range(2))
        leave = tuple(blend(b[k], c[k], fraction) for k in range(2))
        next_entry = tuple(blend(c[k], b[k], fraction) for k in range(2))
        for j in range(steps):
            t = j / steps
            result.append(tuple((1 - t) ** 2 * entry[k] + 2 * t * (1 - t) * b[k] + t * t * leave[k]
                                for k in range(2)))
        for j in range(steps):
            result.append(tuple(blend(leave[k], next_entry[k], j / steps) for k in range(2)))
    return result


def inside_polygon(x, y, outline):
    inside = False
    for a, b in zip(outline, outline[1:] + outline[:1]):
        if (a[1] > y) != (b[1] > y):
            if x < (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]) + a[0]:
                inside = not inside
    return inside


def window_ring_sections(inner, outer):
    """Align the nested window and body loops by a common radial correspondence."""
    center = tuple(sum(p[k] for p in inner) / len(inner) for k in range(2))
    first_angle = math.atan2(inner[0][1] - center[1], inner[0][0] - center[0])
    signed_area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(inner, inner[1:] + inner[:1]))
    direction = 1 if signed_area > 0 else -1
    angles = sorted({round((direction * (math.atan2(p[1] - center[1], p[0] - center[0])
                                        - first_angle)) % math.tau, 12) for p in inner + outer})

    def intersection(loop, angle):
        ray = (math.cos(first_angle + direction * angle), math.sin(first_angle + direction * angle))
        hits = []
        for index, (a, b) in enumerate(zip(loop, loop[1:] + loop[:1])):
            edge = (b[0] - a[0], b[1] - a[1])
            relative = (a[0] - center[0], a[1] - center[1])
            denominator = ray[0] * edge[1] - ray[1] * edge[0]
            if abs(denominator) < 1e-14:
                continue
            distance = (relative[0] * edge[1] - relative[1] * edge[0]) / denominator
            fraction = (relative[0] * ray[1] - relative[1] * ray[0]) / denominator
            if distance > 0 and -1e-9 <= fraction <= 1 + 1e-9:
                hits.append((distance, index))
        assert hits, 'A window radial correspondence must hit a closed boundary'
        distance, index = min(hits)
        return tuple(center[k] + distance * ray[k] for k in range(2)), index, distance

    pairs = []
    for angle in angles:
        inside, _, inner_distance = intersection(inner, angle)
        outside, _, outer_distance = intersection(outer, angle)
        assert outer_distance > inner_distance + 1e-5, 'The fixed window must remain inside its body opening'
        pairs.append((inside, outside))
    sections = [[] for _ in range(6)]
    for i, angle in enumerate(angles):
        end = angles[i + 1] if i + 1 < len(angles) else angles[0] + math.tau
        _, edge, _ = intersection(inner, (angle + end) / 2)
        section = sections[edge // 12]
        if not section:
            section.append(pairs[i])
        section.append(pairs[(i + 1) % len(pairs)])
    assert all(section for section in sections)
    return sections


def disc(author, name, center, radius, depth, mat, parent=None, axis='x', segments=64):
    vertices = []
    for side_value in (-depth / 2, depth / 2):
        for i in range(segments):
            angle = 2 * math.pi * i / segments
            a, b = radius * math.cos(angle), radius * math.sin(angle)
            offset = (side_value, a, b) if axis == 'x' else (a, b, side_value)
            vertices.append(tuple(center[k] + offset[k] for k in range(3)))
    faces = [(i, (i + 1) % segments, (i + 1) % segments + segments, i + segments)
             for i in range(segments)]
    faces += [tuple(reversed(range(segments))), tuple(range(segments, 2 * segments))]
    return author.mesh(name, vertices, faces, mat, parent)


def triangulate_outline(outline):
    """Ear-clip a simple polygon, including narrow concave machined spokes."""
    normal = [sum((a[(k + 1) % 3] - b[(k + 1) % 3])
                  * (a[(k + 2) % 3] + b[(k + 2) % 3])
                  for a, b in zip(outline, outline[1:] + outline[:1])) for k in range(3)]
    axis = max(range(3), key=lambda k: abs(normal[k]))
    projection = [tuple(p[k] for k in range(3) if k != axis) for p in outline]

    def cross(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

    area = sum(a[0] * b[1] - b[0] * a[1]
               for a, b in zip(projection, projection[1:] + projection[:1]))
    assert abs(area) > 1e-14, 'A plate must enclose a nonzero projected area'
    direction = 1 if area > 0 else -1
    remaining, faces = list(range(len(outline))), []
    while len(remaining) > 3:
        for j, b in enumerate(remaining):
            a, c = remaining[j - 1], remaining[(j + 1) % len(remaining)]
            pa, pb, pc = projection[a], projection[b], projection[c]
            if direction * cross(pa, pb, pc) <= 1e-14:
                continue
            occupied = any(all(direction * value >= -1e-14 for value in (
                cross(pa, pb, projection[k]), cross(pb, pc, projection[k]), cross(pc, pa, projection[k])))
                for k in remaining if k not in (a, b, c))
            if occupied:
                continue
            faces.append((a, b, c))
            remaining.pop(j)
            break
        else:
            raise AssertionError('The plate outline must be simple and triangulable')
    faces.append(tuple(remaining))
    areas = [cross(*(projection[i] for i in face)) for face in faces]
    assert all(direction * value > 0 for value in areas), 'Every plate triangle must preserve winding'
    assert abs(sum(areas) - area) <= max(1e-12, abs(area) * 1e-9), 'Plate triangles must cover the polygon exactly'
    return faces


def inset_plate(author, name, outline, mat, parent=None, normal=None, thickness=.005, smooth=True):
    faces = triangulate_outline(outline)
    obj = author.mesh(name, outline, faces, mat, parent, normal=normal, smooth=smooth)
    if thickness:
        author.thickness(obj, thickness)
    return obj


def curved_plate(author, name, outline, position, mat, parent=None, normal=None, depth=.008, split_x=()):
    """Retessellate an inset against its curved carrier, avoiding planar-fan intersections."""
    center = tuple(sum(p[k] for p in outline) / len(outline) for k in range(2))
    rings, count = 10, len(outline)
    logical_vertices = [center]
    for ring in range(1, rings + 1):
        t = ring / rings
        logical_vertices.extend((blend(center[0], p[0], t), blend(center[1], p[1], t)) for p in outline)
    faces = [(0, 1 + i, 1 + (i + 1) % count) for i in range(count)]
    for ring in range(rings - 1):
        start = 1 + ring * count
        faces.extend((start + i, start + (i + 1) % count, start + (i + 1) % count + count,
                      start + i + count) for i in range(count))
    if split_x:
        cells = [[logical_vertices[i] for i in face] for face in faces]
        for plane in split_x:
            divided = []
            for cell in cells:
                lower, upper = [], []
                for a, b in zip(cell, cell[1:] + cell[:1]):
                    da, db = a[0] - plane, b[0] - plane
                    (lower if da <= 0 else upper).append(a)
                    if (da < 0 < db) or (db < 0 < da):
                        p = (plane, blend(a[1], b[1], da / (da - db)))
                        lower.append(p)
                        upper.append(p)
                    elif da == 0:
                        upper.append(a)
                divided.extend(part for part in (lower, upper) if len(part) >= 3)
            cells = divided
        logical_vertices, faces, ids = [], [], {}
        for cell in cells:
            indices = []
            for p in cell:
                key = tuple(round(c, 12) for c in p)
                if key not in ids:
                    ids[key] = len(logical_vertices)
                    logical_vertices.append(p)
                indices.append(ids[key])
            for i in range(1, len(indices) - 1):
                face = (indices[0], indices[i], indices[i + 1])
                if len(set(face)) == 3:
                    faces.append(face)
        assert all(not (min(logical_vertices[i][0] for i in face) < plane - 1e-10
                            and max(logical_vertices[i][0] for i in face) > plane + 1e-10)
                   for plane in split_x for face in faces), 'A carrier crease must be a mesh edge'
    vertices = [position(*p) for p in logical_vertices]
    obj = author.mesh(name, vertices, faces, mat, parent, normal=normal)
    if depth:
        author.thickness(obj, depth)
    if split_x:
        obj.data.set_sharp_from_angle(angle=math.radians(35))
    return obj
