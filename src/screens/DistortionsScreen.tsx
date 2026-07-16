import React, { useState } from 'react';
import { Screen, H1, H2, Body, Card, Button, Small, ChoiceButton } from '../components/UI';
import { distortionList, distortionCitation, Distortion } from '../engine';

// The user picks which distortion applies; the app shows the matching
// pre-written reframe template. Deterministic lookup, no generation.
export default function DistortionsScreen() {
  const [selected, setSelected] = useState<Distortion | null>(null);

  if (selected) {
    return (
      <Screen>
        <Small>THINKING TRAP</Small>
        <H1>{selected.name}</H1>
        <Card>
          <Body muted>{selected.description}</Body>
          <Small>EXAMPLE</Small>
          <Body>“{selected.example}”</Body>
        </Card>
        <Card>
          <Small>A WAY TO REFRAME IT</Small>
          <Body>{selected.reframeTemplate}</Body>
          <Small>TRY THIS</Small>
          <Body>{selected.questionScaffold}</Body>
        </Card>
        <Button label="Back to the list" variant="ghost" onPress={() => setSelected(null)} />
        <Small>{distortionCitation}</Small>
      </Screen>
    );
  }

  return (
    <Screen>
      <H1>Which trap fits?</H1>
      <Body muted>Pick the one closest to the thought you're having. You choose — the app doesn't decide for you.</Body>
      {distortionList.map((d) => (
        <ChoiceButton key={d.id} label={d.name} onPress={() => setSelected(d)} />
      ))}
      <Small>{distortionCitation}</Small>
    </Screen>
  );
}
