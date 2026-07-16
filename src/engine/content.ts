// Central content loader. Everything the engines read comes from versioned
// JSON in /content. Importing here keeps content access in one auditable place.

import socratic from '../../content/questions/socratic.json';
import journaling from '../../content/journaling/prompts.json';
import distortions from '../../content/distortions/distortions.json';
import quests from '../../content/quests/starter-quests.json';
import appConfig from '../../content/config/app-config.json';
import careerClarity from '../../content/flows/career-clarity.json';
import burnout from '../../content/flows/burnout.json';
import questionnaire from '../../content/onboarding/questionnaire.json';

import {
  SocraticQuestion,
  JournalPrompt,
  Distortion,
  Quest,
  Flow,
} from './types';

export const socraticQuestions = (socratic as any).questions as SocraticQuestion[];
export const journalPrompts = (journaling as any).prompts as JournalPrompt[];
export const distortionList = (distortions as any).distortions as Distortion[];
export const distortionCitation = (distortions as any).citation as string;
export const questPack = (quests as any).quests as Quest[];
export const config = appConfig as any;
export const onboarding = questionnaire as any;

export const flows: Record<string, Flow> = {
  'career-clarity': careerClarity as unknown as Flow,
  burnout: burnout as unknown as Flow,
};

export const flowList: Flow[] = Object.values(flows);

export function getFlow(id: string): Flow | undefined {
  return flows[id];
}

export function getDistortion(id: string): Distortion | undefined {
  return distortionList.find((d) => d.id === id);
}

export function getQuest(id: string): Quest | undefined {
  return questPack.find((q) => q.id === id);
}
