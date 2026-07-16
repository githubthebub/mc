// Onboarding scoring — deterministic mapping from answers to a values profile
// and pattern tags. The weights live in content/onboarding/questionnaire.json,
// so the mapping is auditable and editable without code changes.

import questionnaire from '../../content/onboarding/questionnaire.json';
import {
  OnboardingResult,
  PatternTagId,
  ValueDimensionId,
  Topic,
} from './types';

// answers: questionId -> selected option id(s)
export type OnboardingAnswers = Record<string, string | string[]>;

export function scoreOnboarding(answers: OnboardingAnswers): OnboardingResult {
  const values: Record<string, number> = {};
  const patterns: Record<string, number> = {};
  let topicHint: Topic | undefined;

  for (const dim of (questionnaire as any).valuesProfile.dimensions) values[dim.id] = 0;
  for (const p of (questionnaire as any).patternTags) patterns[p.id] = 0;

  for (const q of (questionnaire as any).questions) {
    const raw = answers[q.id];
    if (raw == null) continue;
    const chosen = Array.isArray(raw) ? raw : [raw];
    for (const optId of chosen) {
      const opt = q.options.find((o: any) => o.id === optId);
      if (!opt || !opt.scores) continue;
      if (opt.scores.values) {
        for (const [k, v] of Object.entries(opt.scores.values)) values[k] = (values[k] ?? 0) + (v as number);
      }
      if (opt.scores.patterns) {
        for (const [k, v] of Object.entries(opt.scores.patterns)) patterns[k] = (patterns[k] ?? 0) + (v as number);
      }
      if (opt.scores.topicHint) topicHint = opt.scores.topicHint as Topic;
    }
  }

  const topValues = rankKeys(values).slice(0, 3) as ValueDimensionId[];
  const topPatterns = rankKeys(patterns).filter((k) => patterns[k] > 0).slice(0, 3) as PatternTagId[];

  return {
    values: values as Record<ValueDimensionId, number>,
    patterns: patterns as Record<PatternTagId, number>,
    topicHint,
    topValues,
    topPatterns,
  };
}

function rankKeys(map: Record<string, number>): string[] {
  return Object.keys(map).sort((a, b) => {
    if (map[b] !== map[a]) return map[b] - map[a];
    return a.localeCompare(b); // deterministic
  });
}
