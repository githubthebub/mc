import { scanForCrisis, getCrisisResources } from '../src/engine/crisisScanner';

describe('crisisScanner', () => {
  it('matches explicit crisis phrases', () => {
    expect(scanForCrisis('I want to die').matched).toBe(true);
    expect(scanForCrisis('sometimes I think about suicide').matched).toBe(true);
    expect(scanForCrisis('I keep thinking I should hurt myself').matched).toBe(true);
  });

  it('is case-insensitive and whitespace-tolerant', () => {
    expect(scanForCrisis('I  WANT   to DIE').matched).toBe(true);
  });

  it('does not match benign text', () => {
    expect(scanForCrisis('I had a great day and finished my report').matched).toBe(false);
    expect(scanForCrisis('this deadline is killing it at work').matched).toBe(false);
    expect(scanForCrisis('I was dead tired after the gym').matched).toBe(false);
  });

  it('strong multi-word phrases still match even near excluded idioms', () => {
    expect(scanForCrisis('dead tired, and honestly I want to die').matched).toBe(true);
  });

  it('never throws on bad input', () => {
    // @ts-expect-error testing runtime robustness
    expect(scanForCrisis(null).matched).toBe(false);
    expect(scanForCrisis('').matched).toBe(false);
  });

  it('returns placeholder resources for a region', () => {
    const res = getCrisisResources('US');
    expect(res.resources.length).toBeGreaterThan(0);
    expect(getCrisisResources('NOPE')).toBeTruthy(); // falls back to default region
  });
});
