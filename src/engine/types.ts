// Shared types for Compass's deterministic engines.
// NOTE: There is no AI/LLM anywhere. Every "coaching" output is authored content
// selected by pure, deterministic rules defined in this folder.

export type PatternTagId =
  | 'avoidance'
  | 'people_pleasing'
  | 'perfectionism'
  | 'self_criticism'
  | 'overcommitment'
  | 'rumination';

export type ValueDimensionId =
  | 'growth'
  | 'connection'
  | 'autonomy'
  | 'security'
  | 'contribution'
  | 'vitality';

export type Topic =
  | 'career-clarity'
  | 'burnout'
  | 'relationships'
  | 'habits'
  | 'motivation'
  | 'vitality'
  | 'general';

// ---------- Socratic questions ----------
export interface SocraticQuestion {
  id: string;
  text: string;
  topics: Topic[];
  patterns: PatternTagId[];
  weight: number;
}

// ---------- Journaling ----------
export interface JournalPrompt {
  id: string;
  text: string;
  themes: string[];
  patterns: PatternTagId[];
}

// ---------- Distortions ----------
export interface Distortion {
  id: string;
  name: string;
  aka: string[];
  description: string;
  example: string;
  reframeTemplate: string;
  questionScaffold: string;
}

// ---------- Quests ----------
export interface Quest {
  id: string;
  title: string;
  summary: string;
  why: string;
  values: ValueDimensionId[];
  patterns: PatternTagId[];
  cadence: 'once' | 'daily' | 'weekly';
  checkInPrompt: string;
}

// ---------- Flows ----------
export type FlowNodeType =
  | 'statement'
  | 'choice'
  | 'freeText'
  | 'socratic'
  | 'reframe'
  | 'action'
  | 'end';

export interface FlowOption {
  id: string;
  label: string;
  next: string;
  setPattern?: PatternTagId;
}

export interface FlowNode {
  type: FlowNodeType;
  body?: string;
  prompt?: string;
  options?: FlowOption[];
  next?: string;
  setPattern?: PatternTagId;
  scanForCrisis?: boolean;
  requireAction?: boolean;
  suggestions?: string[];
  offerQuestFromAction?: boolean;
}

export interface Flow {
  id: string;
  version: number;
  title: string;
  topic: Topic;
  estimatedMinutes: number;
  start: string;
  nodes: Record<string, FlowNode>;
}

// ---------- Onboarding ----------
export interface OnboardingResult {
  values: Record<ValueDimensionId, number>;
  patterns: Record<PatternTagId, number>;
  topicHint?: Topic;
  topValues: ValueDimensionId[];
  topPatterns: PatternTagId[];
}

// ---------- Crisis ----------
export interface CrisisScanResult {
  matched: boolean;
  matchedKeyword?: string;
}

// ---------- Pattern detection ----------
export interface PatternDetectionResult {
  tag: PatternTagId;
  count: number;
  windowDays: number;
  message: string;
}
