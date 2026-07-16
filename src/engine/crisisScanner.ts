// Crisis scanner — deterministic keyword matching only.
//
// SAFETY CONTRACT:
//  - This does NOT diagnose and does NOT counsel. It only detects whether a
//    maintained list of crisis keywords appears in free text, so the app can
//    surface calm, non-clinical crisis resources.
//  - Matching is case-insensitive and word-boundary aware, with an
//    exclude-phrase list to reduce obvious false positives.
//  - The keyword list lives in content/crisis/crisis-lines.json so it can be
//    maintained without touching code. Review changes with a professional.

import crisisData from '../../content/crisis/crisis-lines.json';
import { CrisisScanResult } from './types';

interface KeywordMatching {
  keywords: string[];
  excludePhrases: string[];
}

const matching: KeywordMatching = (crisisData as any).keywordMatching;

function normalize(text: string): string {
  return text.toLowerCase().replace(/\s+/g, ' ').trim();
}

function containsPhrase(haystack: string, phrase: string): boolean {
  const p = phrase.toLowerCase();
  // Word-boundary match for single tokens; substring (with surrounding space
  // padding) for multi-word phrases so we still respect boundaries.
  if (/\s/.test(p)) {
    return (' ' + haystack + ' ').includes(' ' + p + ' ') || haystack.includes(p);
  }
  const re = new RegExp(`\\b${p.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'i');
  return re.test(haystack);
}

/**
 * Scan free text for crisis-indicating keywords.
 * Returns { matched, matchedKeyword? }. Never throws.
 */
export function scanForCrisis(rawText: string): CrisisScanResult {
  if (!rawText || typeof rawText !== 'string') return { matched: false };
  const text = normalize(rawText);

  // If an explicit exclude phrase is present, and no stronger keyword is,
  // suppress. Exclude phrases handle idioms like "dead tired".
  const excluded = (matching.excludePhrases || []).some((ph) => containsPhrase(text, ph));

  for (const kw of matching.keywords || []) {
    if (containsPhrase(text, kw)) {
      // Strong, unambiguous multi-word phrases always match even if an exclude
      // phrase is also present.
      const isStrong = /\s/.test(kw);
      if (excluded && !isStrong) continue;
      return { matched: true, matchedKeyword: kw };
    }
  }
  return { matched: false };
}

export function getCrisisResources(region?: string) {
  const data: any = crisisData;
  const key = region && data.regions[region] ? region : data.defaultRegion;
  return data.regions[key];
}

export function getAllCrisisRegions(): string[] {
  return Object.keys((crisisData as any).regions);
}
