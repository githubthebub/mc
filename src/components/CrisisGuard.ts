// Helper for wiring free-text inputs to the crisis scanner. Any screen that
// collects free text calls guardText() before saving; if a keyword matches, it
// routes to the Crisis screen instead of proceeding. It never blocks saving
// silently and never diagnoses — it surfaces calm resources.

import { scanForCrisis } from '../engine/crisisScanner';

export function checkText(text: string): boolean {
  return scanForCrisis(text).matched;
}

/**
 * Returns true if the text tripped the crisis scan (caller should navigate to
 * Crisis). Returns false otherwise (caller proceeds normally).
 */
export function guardAndMaybeRoute(text: string, navigation: any): boolean {
  if (checkText(text)) {
    navigation.navigate('Crisis', { fromGuard: true });
    return true;
  }
  return false;
}
