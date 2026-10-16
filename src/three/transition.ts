export class Transition {
  value = 0
  private target = 0
  private origin = 0
  private elapsed = 0
  private duration = 0

  update(target: number, delta: number, fullDuration: number, fullRange = 1): number {
    if (target !== this.target) {
      this.origin = this.value
      this.target = target
      this.elapsed = 0
      this.duration = fullDuration * Math.abs(target - this.value) / fullRange
    }
    this.elapsed += Math.max(0, delta)
    const progress = this.duration > 0 ? Math.min(1, this.elapsed / this.duration) : 1
    const eased = progress * progress * (3 - 2 * progress)
    this.value = progress === 1 ? this.target : this.origin + (this.target - this.origin) * eased
    return this.value
  }
}

export function indicatorEnvelope(elapsed: number): number {
  const phase = ((elapsed % 0.9) + 0.9) % 0.9
  return phase < 0.45 ? Math.max(0, Math.min(phase / 0.05, (0.45 - phase) / 0.05, 1)) : 0
}
