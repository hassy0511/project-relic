/** 種つきの乱数（mulberry32）。sim の中ではこれだけを使う */
export class Rng {
  private s: number;

  constructor(seed = 1) {
    this.s = seed >>> 0;
  }

  next(): number {
    let t = (this.s = (this.s + 0x6d2b79f5) >>> 0);
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  }

  range(lo: number, hi: number): number {
    return lo + (hi - lo) * this.next();
  }

  int(lo: number, hiInclusive: number): number {
    return Math.floor(this.range(lo, hiInclusive + 1));
  }

  chance(p: number): boolean {
    return this.next() < p;
  }
}
