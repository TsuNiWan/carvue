import assert from 'node:assert/strict'
import { Vector3 } from 'three'
import { ConvexHull } from 'three/addons/math/ConvexHull.js'

let input = ''
for await (const chunk of process.stdin) input += chunk
const coordinates = JSON.parse(input)
assert.ok(Array.isArray(coordinates) && coordinates.length >= 4, 'A hull needs at least four points')
assert.ok(coordinates.every(point => Array.isArray(point) && point.length === 3 && point.every(Number.isFinite)))
const points = coordinates.map(point => new Vector3(...point))
const hull = new ConvexHull().setFromPoints(points)
assert.ok(hull.faces.length >= 4, 'The hull must enclose a finite volume')
const planes = hull.faces.map(face => ({ normal: face.normal.toArray(), offset: -face.constant }))
const center = points.reduce((sum, point) => sum.add(point), new Vector3()).divideScalar(points.length)
let maxHullErrorMeters = -Infinity
let volume = 0
for (const face of hull.faces) {
  assert.ok(Math.abs(face.normal.length() - 1) < 1e-8)
  for (const point of points) maxHullErrorMeters = Math.max(maxHullErrorMeters, face.distanceToPoint(point))
  const vertices = []
  let edge = face.edge
  do {
    assert.ok(edge.twin?.face, 'Every hull edge must have a neighbouring face')
    vertices.push(edge.head().point.clone().sub(center))
    edge = edge.next
  } while (edge !== face.edge)
  assert.equal(vertices.length, 3)
  volume += vertices[0].dot(new Vector3().crossVectors(vertices[1], vertices[2])) / 6
}
assert.ok(maxHullErrorMeters <= 1e-7, `A hull plane excludes an input point by ${maxHullErrorMeters} m`)
assert.ok(Number.isFinite(volume) && volume > 1e-10, 'The closed hull must have positive volume')
process.stdout.write(JSON.stringify({
  method: 'Three.js ConvexHull with double-precision supporting planes',
  planes, maxHullErrorMeters, volumeCubicMeters: volume,
  min: [0, 1, 2].map(axis => Math.min(...coordinates.map(point => point[axis]))),
  max: [0, 1, 2].map(axis => Math.max(...coordinates.map(point => point[axis]))),
}))
