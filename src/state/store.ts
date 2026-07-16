// Local app state (Zustand). Coordinates the gate flags, the user's derived
// profile, and pattern logging. All persistence is on-device (SecureStore + SQLite).

import { create } from 'zustand';
import { secure } from '../storage/secureStore';
import * as db from '../storage/db';
import {
  OnboardingResult,
  PatternTagId,
  detectRecurringPatterns,
  PatternDetectionResult,
  config,
} from '../engine';

interface Profile {
  topValues: string[];
  topPatterns: PatternTagId[];
  topicHint?: string;
}

interface AppState {
  ready: boolean;
  disclaimerAck: boolean;
  ageVerified: boolean;
  onboarded: boolean;
  region: string;
  profile: Profile | null;
  patternInsights: PatternDetectionResult[];

  init: () => Promise<void>;
  acceptDisclaimer: () => Promise<void>;
  verifyAge: () => Promise<void>;
  setRegion: (r: string) => Promise<void>;
  saveOnboarding: (result: OnboardingResult) => Promise<void>;
  logPattern: (tag: PatternTagId, source?: string) => Promise<void>;
  refreshInsights: () => Promise<void>;
  eraseEverything: () => Promise<void>;
}

const PROFILE_KEY = 'profile';

export const useStore = create<AppState>((set, get) => ({
  ready: false,
  disclaimerAck: false,
  ageVerified: false,
  onboarded: false,
  region: 'GLOBAL',
  profile: null,
  patternInsights: [],

  async init() {
    const [disclaimerAck, ageVerified, onboarded, region, profile] = await Promise.all([
      secure.getDisclaimerAck(),
      secure.getAgeVerified(),
      secure.getOnboarded(),
      secure.getRegion(),
      db.kvGet<Profile | null>(PROFILE_KEY, null),
    ]);
    set({
      disclaimerAck,
      ageVerified,
      onboarded,
      region: region || 'GLOBAL',
      profile,
      ready: true,
    });
    await get().refreshInsights();
  },

  async acceptDisclaimer() {
    await secure.setDisclaimerAck(true);
    set({ disclaimerAck: true });
  },

  async verifyAge() {
    await secure.setAgeVerified(true);
    set({ ageVerified: true });
  },

  async setRegion(r: string) {
    await secure.setRegion(r);
    set({ region: r });
  },

  async saveOnboarding(result: OnboardingResult) {
    const profile: Profile = {
      topValues: result.topValues,
      topPatterns: result.topPatterns,
      topicHint: result.topicHint,
    };
    await db.kvSet(PROFILE_KEY, profile);
    // Seed initial pattern signal from onboarding (counts start the tracker).
    for (const tag of result.topPatterns) {
      await db.logPattern(tag, 'onboarding');
    }
    await secure.setOnboarded(true);
    set({ profile, onboarded: true });
    await get().refreshInsights();
  },

  async logPattern(tag: PatternTagId, source = 'manual') {
    await db.logPattern(tag, source);
    await get().refreshInsights();
  },

  async refreshInsights() {
    const logs = await db.getPatternLogs();
    const insights = detectRecurringPatterns(logs, {
      windowDays: config.patternDetection.windowDays,
      threshold: config.patternDetection.recurrenceThreshold,
      nowMs: Date.now(),
    });
    set({ patternInsights: insights });
  },

  async eraseEverything() {
    await db.eraseAllData();
    await secure.eraseAll();
    set({
      disclaimerAck: false,
      ageVerified: false,
      onboarded: false,
      region: 'GLOBAL',
      profile: null,
      patternInsights: [],
    });
  },
}));
