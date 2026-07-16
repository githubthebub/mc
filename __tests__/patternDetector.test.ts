import { detectRecurringPatterns } from '../src/engine/patternDetector';

const DAY = 24 * 60 * 60 * 1000;

describe('patternDetector', () => {
  const now = 1_700_000_000_000; // fixed for determinism

  it('flags a tag once it crosses the threshold within the window', () => {
    const logs = Array.from({ length: 5 }, (_, i) => ({ tag: 'avoidance' as const, timestampMs: now - i * DAY }));
    const results = detectRecurringPatterns(logs, { nowMs: now, threshold: 5, windowDays: 30 });
    expect(results).toHaveLength(1);
    expect(results[0].tag).toBe('avoidance');
    expect(results[0].count).toBe(5);
    expect(results[0].message).toContain('avoidance');
  });

  it('does not flag below threshold', () => {
    const logs = Array.from({ length: 4 }, (_, i) => ({ tag: 'avoidance' as const, timestampMs: now - i * DAY }));
    expect(detectRecurringPatterns(logs, { nowMs: now, threshold: 5, windowDays: 30 })).toHaveLength(0);
  });

  it('ignores logs outside the rolling window', () => {
    const logs = Array.from({ length: 6 }, (_, i) => ({ tag: 'rumination' as const, timestampMs: now - (40 + i) * DAY }));
    expect(detectRecurringPatterns(logs, { nowMs: now, threshold: 5, windowDays: 30 })).toHaveLength(0);
  });

  it('sorts multiple flagged patterns by count desc, deterministically', () => {
    const logs = [
      ...Array.from({ length: 6 }, () => ({ tag: 'perfectionism' as const, timestampMs: now })),
      ...Array.from({ length: 8 }, () => ({ tag: 'people_pleasing' as const, timestampMs: now })),
    ];
    const results = detectRecurringPatterns(logs, { nowMs: now, threshold: 5, windowDays: 30 });
    expect(results.map((r) => r.tag)).toEqual(['people_pleasing', 'perfectionism']);
  });

  it('never diagnoses — message is a reflective nudge', () => {
    const logs = Array.from({ length: 5 }, () => ({ tag: 'self_criticism' as const, timestampMs: now }));
    const [r] = detectRecurringPatterns(logs, { nowMs: now, threshold: 5, windowDays: 30 });
    expect(r.message).toMatch(/not a verdict/i);
  });
});
