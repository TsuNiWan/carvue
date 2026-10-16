import { describe, expect, it } from 'vitest'
import { advanceScenario, createScenarioState, evaluateScenario, resetScenario, scenarioZones, type ScenarioState, type Side } from './scenarios'

const vehicleLength = 4.6
const state = (overrides: Partial<ScenarioState> = {}): ScenarioState => ({ ...createScenarioState(), ...overrides })
const pedestrianProgressAt = (x: number) => (x + 6) / 12
const blindProgressAt = (z: number, length = vehicleLength) => (z + length / 2 + 8) / (length + 16)
const parkingProgressAt = (distance: number) => (6 - distance) / (6 - scenarioZones.parkingStopDistance)

describe('pedestrian detection', () => {
  it.each([-1, 1])('includes camera and danger boundaries on side %s', (side) => {
    const frameAt = (x: number) => evaluateScenario(state({ progress: pedestrianProgressAt(x * side) }), 'off', vehicleLength)
    expect(frameAt(3.01).level).toBe('safe')
    expect(frameAt(3).level).toBe('notice')
    expect(frameAt(1.21).level).toBe('notice')
    expect(frameAt(1.2).level).toBe('danger')
    expect(frameAt(0).level).toBe('danger')
  })

  it('enters and then leaves the detection area', () => {
    expect([0, 0.3, 0.5, 0.7, 1].map((progress) => evaluateScenario(state({ progress }), 'off', vehicleLength).level))
      .toEqual(['safe', 'notice', 'danger', 'notice', 'safe'])
  })
})

describe('blind spot detection', () => {
  it.each<Side>(['left', 'right'])('detects the rear and front boundaries on the %s side', (side) => {
    const frameAt = (z: number) => evaluateScenario(state({ id: 'blindSpot', side, progress: blindProgressAt(z) }), 'off', vehicleLength)
    const rearBoundary = -vehicleLength / 2 - scenarioZones.blindRearExtension
    expect(frameAt(rearBoundary - 0.01).level).toBe('safe')
    expect(frameAt(rearBoundary).level).toBe('notice')
    expect(frameAt(scenarioZones.blindFrontZ).level).toBe('notice')
    expect(frameAt(scenarioZones.blindFrontZ + 0.01).level).toBe('safe')
    expect(Math.sign(frameAt(-1).actor.x)).toBe(side === 'left' ? 1 : -1)
  })

  it.each<Side>(['left', 'right'])('only escalates matching signals or hazards on the %s side', (side) => {
    const sample = state({ id: 'blindSpot', side, progress: blindProgressAt(-1) })
    expect(evaluateScenario(sample, 'off', vehicleLength).level).toBe('notice')
    expect(evaluateScenario(sample, side, vehicleLength).level).toBe('danger')
    expect(evaluateScenario(sample, side === 'left' ? 'right' : 'left', vehicleLength).level).toBe('notice')
    expect(evaluateScenario(sample, 'hazard', vehicleLength).level).toBe('danger')
    expect(evaluateScenario({ ...sample, progress: 0 }, 'hazard', vehicleLength).level).toBe('safe')
  })
})

describe('parking distance', () => {
  it.each([
    [3.01, 'safe'], [3, 'notice'], [1.01, 'notice'], [1, 'danger'], [0.45, 'danger'],
  ] as const)('reports %s meters as %s', (distance, level) => {
    const frame = evaluateScenario(state({ id: 'parking', progress: parkingProgressAt(distance) }), 'off', vehicleLength)
    expect(frame.level).toBe(level)
    expect(frame.distance).toBeCloseTo(distance)
    expect(frame.actor.z).toBeCloseTo(-vehicleLength / 2 - distance)
  })

  it('stops before the rear bumper without penetrating it', () => {
    const frame = evaluateScenario(state({ id: 'parking', progress: 1 }), 'off', vehicleLength)
    expect(frame.distance).toBeCloseTo(0.45)
    expect(frame.actor.z).toBeLessThan(-vehicleLength / 2)
  })
})

describe('deterministic playback', () => {
  it.each(['pedestrian', 'blindSpot', 'parking'] as const)('scrubs %s backwards without history affecting the result', (id) => {
    const forward = [0, 0.25, 0.5, 0.75, 1].map((progress) => evaluateScenario(state({ id, progress }), 'left', vehicleLength))
    const backward = [1, 0.75, 0.5, 0.25, 0].map((progress) => evaluateScenario(state({ id, progress }), 'left', vehicleLength))
    expect(backward.reverse()).toEqual(forward)
  })

  it.each([4.4, 4.8])('anchors detection and actors to a %s meter car', (length) => {
    const pedestrian = evaluateScenario(state({ progress: 0.5 }), 'off', length)
    const parking = evaluateScenario(state({ id: 'parking', progress: 1 }), 'off', length)
    const blind = evaluateScenario(state({ id: 'blindSpot', progress: blindProgressAt(-length / 2 - 3, length) }), 'off', length)
    expect(pedestrian.actor.z - length / 2).toBeCloseTo(3)
    expect(pedestrian.level).toBe('danger')
    expect(-parking.actor.z - length / 2).toBeCloseTo(0.45)
    expect(blind.level).toBe('notice')
  })

  it('does not mutate paused progress', () => {
    const paused = state({ progress: 0.4 })
    expect(advanceScenario(paused, 3)).toEqual(paused)
    expect(paused.progress).toBe(0.4)
  })

  it('advances in seconds and stops at the end', () => {
    const playing = state({ progress: 0.4, playing: true })
    expect(advanceScenario(playing, 1).progress).toBeCloseTo(0.5)
    expect(advanceScenario(playing, 100)).toEqual({ ...playing, progress: 1, playing: false })
    expect(playing.progress).toBe(0.4)
    expect(advanceScenario(playing, -1).progress).toBe(0.4)
  })

  it('resets playback while preserving scenario and side', () => {
    const playing = state({ id: 'blindSpot', side: 'right', progress: 0.8, playing: true })
    expect(resetScenario(playing)).toEqual({ id: 'blindSpot', side: 'right', progress: 0, playing: false })
  })
})
