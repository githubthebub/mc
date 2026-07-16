import React from 'react';
import { Screen, H1, H2, Body, Card, Button, Small } from '../components/UI';

// Menu for the CBT-style toolkit. All content is pre-written and cited; nothing
// is generated. This is psychoeducation, not therapy.
export default function ToolkitScreen({ navigation }: any) {
  return (
    <Screen>
      <H1>Toolkit</H1>
      <Body muted>Simple, evidence-informed exercises. Pre-written, not generated — and not a substitute for professional care.</Body>

      <Card>
        <H2>Thought record</H2>
        <Body muted>Untangle a sticky thought: situation → thought → distortion → reframe.</Body>
        <Button label="Open" onPress={() => navigation.navigate('ThoughtRecord')} />
      </Card>

      <Card>
        <H2>Spot the distortion</H2>
        <Body muted>Recognise a common thinking trap and get a pre-written reframe scaffold.</Body>
        <Button label="Open" onPress={() => navigation.navigate('Distortions')} />
      </Card>

      <Card>
        <H2>Clarify your values</H2>
        <Body muted>See what you said matters most, and turn it into a small aligned action.</Body>
        <Button label="Open" onPress={() => navigation.navigate('Values')} />
      </Card>
    </Screen>
  );
}
