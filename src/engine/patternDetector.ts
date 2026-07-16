// Pattern detector — counting and simple thresholds only. No inference.
//
// The spec is explicit: "No inference beyond counting and simple rules."
// This module counts how often each pattern tag was logged within a rolling
// window and, if it crosses a configurable threshold, produces a gentle,
// non-clinical call-out string. That's the entire "intelligence" here.

import appConfig from '../../content/config/app-config.json';
import { PatternTagId, PatternDetectionResult } from './types';

export interface TagLog {
  tag: PatternTagId;
  timestampMs: number;
}

const LABELS: Record<PatternTagId, string> = {
  avoidance: 'avoidance',
  people_pleasing: 'people-pleasing',
  perfectionism: 'perfectionism',
  self_criticism: 'harsh self-criticism',
  overcommitment: 'over-commitment',
  rumination: 'rumination',
};

export interface DetectorOptions {
  windowDays?: number;
  threshold?: number;
  nowMs: number; // injected for determinism/testability (no Date.now in engine)
}

export function detectRecurringPatterns(
  logs: TagLog[],
  opts: DetectorOptions,
): PatternDetectionResult[] {
  const windowDays = opts.windowDays ?? appConfig.patternDetection.windowDays;
  const threshold = opts.threshold ?? appConfig.patternDetection.recurrenceThreshold;
  const cutoff = opts.nowMs - windowDays * 24 * 60 * 60 * 1000;

  const counts = new Map<PatternTagId, number>();
  for (const log of logs) {
    if (log.timestampMs >= cutoff) {
      counts.set(log.tag, (counts.get(log.tag) ?? 0) + 1);
    }
  }

  const results: PatternDetectionResult[] = [];
  for (const [tag, count] of counts.entries()) {
    if (count >= threshold) {
      results.push({
        tag,
        count,
        windowDays,
        message: buildMessage(tag, count, windowDays),
      });
    }
  }
  // Most frequent first; deterministic tie-break by tag name.
  results.sort((a, b) => (b.count !== a.count ? b.count - a.count : a.tag.localeCompare(b.tag)));
  return results;
}

function buildMessage(tag: PatternTagId, count: number, windowDays: number): string {
  const label = LABELS[tag];
  const span = windowDays >= 28 ? 'this month' : `the last ${windowDays} days`;
  // Honest, direct, non-clinical. Names the pattern; doesn't diagnose.
  return `You've flagged ${label} ${count} times in ${span}. That's worth a straight look — not a verdict, just a pattern showing up. What's the thread connecting these?`;
}

export function tagLabel(tag: PatternTagId): string {
  return LABELS[tag];
}
