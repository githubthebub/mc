import React, { useState } from 'react';
import { View } from 'react-native';
import { Screen, H1, H2, Body, Card, Button, Field, Small, ChoiceButton } from '../components/UI';
import { distortionList } from '../engine';
import { guardAndMaybeRoute } from '../components/CrisisGuard';
import * as db from '../storage/db';
import { spacing } from '../theme/theme';

// CBT-style thought record. All prompts pre-written. Saved encrypted on-device.
export default function ThoughtRecordScreen({ navigation }: any) {
  const [situation, setSituation] = useState('');
  const [thought, setThought] = useState('');
  const [distortionId, setDistortionId] = useState<string | undefined>(undefined);
  const [reframe, setReframe] = useState('');
  const [saved, setSaved] = useState(false);

  const chosen = distortionList.find((d) => d.id === distortionId);

  async function save() {
    const combined = `${situation}\n${thought}\n${reframe}`;
    if (guardAndMaybeRoute(combined, navigation)) return;
    await db.addThoughtRecord({ situation, thought, distortionId, reframe });
    setSaved(true);
  }

  if (saved) {
    return (
      <Screen>
        <H1>Saved</H1>
        <Card><Body>That's on your device only. Noticing the thought and naming it is the work — nicely done.</Body></Card>
        <Button label="Done" onPress={() => navigation.goBack()} />
      </Screen>
    );
  }

  return (
    <Screen>
      <H1>Thought record</H1>
      <Small>SITUATION</Small>
      <Field multiline placeholder="What happened?" value={situation} onChangeText={setSituation} />
      <Small>THE THOUGHT</Small>
      <Field multiline placeholder="What went through your mind?" value={thought} onChangeText={setThought} />

      <Small>WHICH DISTORTION FITS? (OPTIONAL)</Small>
      <View style={{ marginBottom: spacing.sm }}>
        {distortionList.map((d) => (
          <ChoiceButton
            key={d.id}
            label={(distortionId === d.id ? '✓ ' : '') + d.name}
            onPress={() => setDistortionId(distortionId === d.id ? undefined : d.id)}
          />
        ))}
      </View>

      {chosen && (
        <Card>
          <Small>REFRAME SCAFFOLD</Small>
          <Body>{chosen.reframeTemplate}</Body>
        </Card>
      )}

      <Small>YOUR REFRAME</Small>
      <Field multiline placeholder="A fairer, truer way to see it…" value={reframe} onChangeText={setReframe} />

      <Button label="Save (stays on device)" onPress={save} disabled={!situation.trim() || !thought.trim()} />
    </Screen>
  );
}
