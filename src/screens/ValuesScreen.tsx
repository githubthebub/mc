import React from 'react';
import { Screen, H1, H2, Body, Card, Button, Small } from '../components/UI';
import { useStore } from '../state/store';
import { onboarding, tagLabel } from '../engine';

// Values-clarification: reflect the user's derived profile back and point at one
// aligned action. Content-driven, deterministic.
export default function ValuesScreen({ navigation }: any) {
  const profile = useStore((s) => s.profile);
  const dims = onboarding.valuesProfile.dimensions as { id: string; label: string }[];
  const label = (id: string) => dims.find((d) => d.id === id)?.label ?? id;

  if (!profile) {
    return (
      <Screen>
        <H1>Your values</H1>
        <Body muted>Finish onboarding to see your values profile.</Body>
      </Screen>
    );
  }

  return (
    <Screen>
      <H1>What matters to you</H1>
      <Card>
        <Small>YOUR TOP VALUES</Small>
        {profile.topValues.map((v) => (
          <Body key={v}>• {label(v)}</Body>
        ))}
        <Small>Derived on-device from your onboarding answers. Edit anytime by re-doing onboarding in Settings.</Small>
      </Card>

      {profile.topPatterns.length > 0 && (
        <Card>
          <Small>PATTERNS TO WATCH</Small>
          {profile.topPatterns.map((p) => (
            <Body key={p}>• {tagLabel(p)}</Body>
          ))}
        </Card>
      )}

      <Card>
        <H2>Make it real</H2>
        <Body>Values only matter when they move you. Pick one small action this week that honours your top value.</Body>
        <Button label="Browse quests" onPress={() => navigation.navigate('Quests')} />
      </Card>
    </Screen>
  );
}
