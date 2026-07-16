import React from 'react';
import { Linking } from 'react-native';
import { Screen, H1, H2, Body, Card, Button, Small } from '../components/UI';
import { useStore } from '../state/store';
import { getCrisisResources } from '../engine';
import { colors } from '../theme/theme';

// Calm, non-clinical crisis resources screen. Shown when the crisis scanner
// matches free text, or opened from Settings. It does NOT counsel or diagnose —
// it points toward people who can help. Resource data is a configurable
// placeholder (content/crisis/crisis-lines.json).
export default function CrisisScreen({ navigation }: any) {
  const region = useStore((s) => s.region);
  const res = getCrisisResources(region);

  return (
    <Screen>
      <H1>You matter — let's find you a person</H1>
      <Card style={{ backgroundColor: colors.crisisBg }}>
        <Body>{res.message}</Body>
        <Body>
          If you might be in danger, please contact your local emergency services now. Reaching one
          real person — a hotline, a friend, someone you trust — is the strongest next step.
        </Body>
      </Card>

      {res.resources.map((r: any, i: number) => (
        <Card key={i}>
          <H2>{r.name}</H2>
          <Body>{r.contact}</Body>
          {r.type === 'directory' && r.contact.startsWith('http') && (
            <Button label="Open directory" onPress={() => Linking.openURL(r.contact)} />
          )}
        </Card>
      ))}

      <Card>
        <Body muted>
          Compass is a reflection tool, not a crisis service and not a substitute for professional
          care. It can't help in an emergency — a trained human can.
        </Body>
      </Card>

      <Button label="Back" variant="ghost" onPress={() => navigation.goBack()} />
      <Small>Resource list is configurable in content/crisis/crisis-lines.json — verify before release.</Small>
    </Screen>
  );
}
