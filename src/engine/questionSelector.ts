// Question / prompt selector — deterministic, weighted, non-repeating.
//
// Given the active topic, the user's pattern tags, and a ledger of recently
// shown ids, this returns the SAME question every time for the same inputs.
// There is no randomness. "Weighting" means questions more relevant to the
// user's patterns score higher; ties break by id for stability.

import { SocraticQuestion, JournalPrompt, PatternTagId, Topic } from './types';

export interface SelectorInput {
  topic?: Topic;
  patternTags?: PatternTagId[];
  recentlyShownIds?: string[];
}

interface Scored<T> {
  item: T;
  score: number;
}

function scoreQuestion(q: SocraticQuestion, patternTags: PatternTagId[]): number {
  const base = q.weight ?? 1;
  // +2 per matching pattern tag: content aimed at the user's patterns surfaces first.
  const overlap = q.patterns.filter((p) => patternTags.includes(p)).length;
  return base + overlap * 2;
}

/**
 * Deterministically rank Socratic questions for a topic + pattern set,
 * excluding recently shown ones. Returns the full ranked list (best first).
 */
export function rankSocratic(
  all: SocraticQuestion[],
  input: SelectorInput,
): SocraticQuestion[] {
  const { topic, patternTags = [], recentlyShownIds = [] } = input;
  const recent = new Set(recentlyShownIds);

  let pool = all.filter((q) => !topic || topic === 'general' || q.topics.includes(topic));
  if (pool.length === 0) pool = all; // fall back to whole bank rather than nothing

  let eligible = pool.filter((q) => !recent.has(q.id));
  // If everything has been shown recently, reset the exclusion (cycle again).
  if (eligible.length === 0) eligible = pool;

  const scored: Scored<SocraticQuestion>[] = eligible.map((q) => ({
    item: q,
    score: scoreQuestion(q, patternTags),
  }));

  scored.sort((a, b) => {
    if (b.score !== a.score) return b.score - a.score;
    return a.item.id.localeCompare(b.item.id); // deterministic tie-break
  });

  return scored.map((s) => s.item);
}

/** Pick the single best next Socratic question (or null if the bank is empty). */
export function nextSocratic(
  all: SocraticQuestion[],
  input: SelectorInput,
): SocraticQuestion | null {
  const ranked = rankSocratic(all, input);
  return ranked[0] ?? null;
}

/** Same deterministic selection logic, for journaling prompts (theme + patterns). */
export function nextJournalPrompt(
  all: JournalPrompt[],
  input: { theme?: string; patternTags?: PatternTagId[]; recentlyShownIds?: string[] },
): JournalPrompt | null {
  const { theme, patternTags = [], recentlyShownIds = [] } = input;
  const recent = new Set(recentlyShownIds);

  let pool = all.filter((p) => !theme || p.themes.includes(theme));
  if (pool.length === 0) pool = all;
  let eligible = pool.filter((p) => !recent.has(p.id));
  if (eligible.length === 0) eligible = pool;

  const scored = eligible.map((p) => ({
    item: p,
    score: 1 + p.patterns.filter((t) => patternTags.includes(t)).length * 2,
  }));
  scored.sort((a, b) => (b.score !== a.score ? b.score - a.score : a.item.id.localeCompare(b.item.id)));
  return scored[0]?.item ?? null;
}

/**
 * Maintain a bounded "recently shown" ledger (most-recent last). Returns a new
 * array; callers persist it locally so selection stays non-repeating across
 * sessions.
 */
export function pushRecent(ledger: string[], id: string, memory: number): string[] {
  const next = ledger.filter((x) => x !== id);
  next.push(id);
  while (next.length > memory) next.shift();
  return next;
}
