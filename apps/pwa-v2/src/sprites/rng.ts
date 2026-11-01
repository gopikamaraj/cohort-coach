// A tiny seeded generator, step for step the same as services/api/sprites/rng.py (xorshift32).
export class Rng {
  state: number;

  constructor(seed: number) {
    // BigInt for the first step: seed * 2654435761 can pass 2**53.
    this.state = Number((BigInt(seed) * 2654435761n + 1n) & 0xffffffffn) || 1;
  }

  next(): number {
    let x = this.state;
    x = (x ^ (x << 13)) >>> 0;
    x = (x ^ (x >>> 17)) >>> 0;
    x = (x ^ (x << 5)) >>> 0;
    this.state = x;
    return x;
  }

  /** An integer in 0..n-1. */
  below(n: number): number {
    return this.next() % n;
  }

  /** Fisher-Yates, in place; returns the array. */
  shuffle(items: number[]): number[] {
    for (let i = items.length - 1; i > 0; i--) {
      const j = this.below(i + 1);
      const a = items[i] as number;
      items[i] = items[j] as number;
      items[j] = a;
    }
    return items;
  }
}
