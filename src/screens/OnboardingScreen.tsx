import React, { useState } from 'react';
import { View } from 'react-native';
import { Screen, H1, H2, Body, Button, ChoiceButton, Card, Small } from '../components/UI';
import { useStore } from '../state/store';
import { onboarding, scoreOnboarding, OnboardingAnswers } from '../engine';
import { spacing } from '../theme/theme';

// Structured onboarding questionnaire. Deterministically maps answers to a
// values profile + pattern tags (see engine/scoring). No inference.
export default function OnboardingScreen() {
  const saveOnboarding = useStore((s) => s.saveOnboarding);
  const questions = onboarding.questions;
  const [step, setStep] = useState(-1); // -1 shows the intro first
  const [answers, setAnswers] = useState<OnboardingAnswers>({});
  const [rankPick, setRankPick] = useState<string[]>([]);

  if (step === -1) {
    return (
      <Screen>
        <H1>{onboarding.intro.title}</H1>
        <Card><Body>{onboarding.intro.body}</Body></Card>
        <Button label="Begin" onPress={() => setStep(0)} />
      </Screen>
    );
  }

  const q = questions[step];
  const isRank = q.type === 'rank_top_two';

  function choose(optId: string) {
    if (isRank) {
      const already = rankPick.includes(optId);
      const nextPick = already ? rankPick.filter((x) => x !== optId) : [...rankPick, optId].slice(-2);
      setRankPick(nextPick);
      return;
    }
    commit({ ...answers, [q.id]: optId });
  }

  function commit(next: OnboardingAnswers) {
    setAnswers(next);
    if (step + 1 >= questions.length) {
      const result = scoreOnboarding(next);
      saveOnboarding(result);
    } else {
      setStep(step + 1);
      setRankPick([]);
    }
  }

  return (
    <Screen>
      <Small>Question {step + 1} of {questions.length}</Small>
      <H1>{q.prompt}</H1>
      {isRank && <Body muted>Pick the two that fit best.</Body>}
      {q.options.map((o: any) => (
        <ChoiceButton
          key={o.id}
          label={(isRank && rankPick.includes(o.id) ? '✓ ' : '') + o.label}
          onPress={() => choose(o.id)}
        />
      ))}
      {isRank && (
        <View style={{ marginTop: spacing.md }}>
          <Button
            label="Next"
            variant="primary"
            disabled={rankPick.length === 0}
            onPress={() => commit({ ...answers, [q.id]: rankPick })}
          />
        </View>
      )}
    </Screen>
  );
}
