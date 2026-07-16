import { rankSocratic, nextSocratic, pushRecent } from '../src/engine/questionSelector';
import { socraticQuestions } from '../src/engine/content';

describe('questionSelector', () => {
  it('is deterministic for identical inputs', () => {
    const a = nextSocratic(socraticQuestions, { topic: 'burnout', patternTags: ['people_pleasing'] });
    const b = nextSocratic(socraticQuestions, { topic: 'burnout', patternTags: ['people_pleasing'] });
    expect(a?.id).toBe(b?.id);
  });

  it('weights questions matching the user pattern tags higher', () => {
    const ranked = rankSocratic(socraticQuestions, { topic: 'burnout', patternTags: ['people_pleasing'] });
    // The top result for burnout + people_pleasing should carry that tag.
    expect(ranked[0].patterns).toContain('people_pleasing');
  });

  it('only returns questions for the active topic', () => {
    const ranked = rankSocratic(socraticQuestions, { topic: 'relationships', patternTags: [] });
    for (const q of ranked) expect(q.topics).toContain('relationships');
  });

  it('excludes recently shown questions', () => {
    const first = nextSocratic(socraticQuestions, { topic: 'career-clarity', patternTags: [] })!;
    const second = nextSocratic(socraticQuestions, {
      topic: 'career-clarity',
      patternTags: [],
      recentlyShownIds: [first.id],
    })!;
    expect(second.id).not.toBe(first.id);
  });

  it('cycles back once everything has been shown (never returns null with a non-empty bank)', () => {
    const allIds = socraticQuestions.map((q) => q.id);
    const q = nextSocratic(socraticQuestions, { topic: 'general', patternTags: [], recentlyShownIds: allIds });
    expect(q).not.toBeNull();
  });

  it('pushRecent maintains a bounded FIFO ledger', () => {
    let ledger: string[] = [];
    for (let i = 0; i < 20; i++) ledger = pushRecent(ledger, 'q' + i, 5);
    expect(ledger.length).toBe(5);
    expect(ledger[ledger.length - 1]).toBe('q19');
    // re-pushing an existing id moves it to the end without duplicating
    ledger = pushRecent(ledger, 'q17', 5);
    expect(ledger.filter((x) => x === 'q17').length).toBe(1);
  });
});
