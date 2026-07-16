import { scoreOnboarding } from '../src/engine/scoring';

describe('onboarding scoring', () => {
  it('maps value answers to a top-values profile deterministically', () => {
    const result = scoreOnboarding({
      q_value_rank: ['o_growth', 'o_connection'],
      q_stuck: 'o_uncomfortable',
      q_after_mistake: 'o_harsh',
      q_saying_no: 'o_yes_anyway',
      q_focus_area: 'o_burnout',
    });
    // growth and connection both score +2; ties break alphabetically for
    // determinism, so 'connection' sorts ahead of 'growth'. Both must be present.
    expect(result.topValues).toContain('growth');
    expect(result.topValues).toContain('connection');
    expect(result.topValues[0]).toBe('connection');
  });

  it('accumulates pattern tags from answers', () => {
    const result = scoreOnboarding({
      q_stuck: 'o_uncomfortable', // avoidance +2
      q_after_mistake: 'o_hides', // avoidance +1
      q_saying_no: 'o_yes_anyway', // people_pleasing +2, overcommitment +1
    });
    expect(result.patterns.avoidance).toBe(3);
    expect(result.patterns.people_pleasing).toBe(2);
    expect(result.topPatterns[0]).toBe('avoidance');
  });

  it('captures the topic hint from the focus-area question', () => {
    const result = scoreOnboarding({ q_focus_area: 'o_career' });
    expect(result.topicHint).toBe('career-clarity');
  });

  it('is stable: same answers → same output', () => {
    const answers = { q_stuck: 'o_thinking', q_focus_area: 'o_habits' };
    expect(JSON.stringify(scoreOnboarding(answers))).toBe(JSON.stringify(scoreOnboarding(answers)));
  });

  it('only reports pattern tags that were actually scored', () => {
    const result = scoreOnboarding({ q_after_mistake: 'o_moves' }); // scores nothing
    expect(result.topPatterns).toHaveLength(0);
  });
});
