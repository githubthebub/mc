import React from 'react';
import { View } from 'react-native';
import { Screen, H1, Body, Button, Card, Small } from '../components/UI';
import { useStore } from '../state/store';
import { spacing } from '../theme/theme';

// First-launch disclaimer the user must acknowledge. Also reachable from Settings.
export default function DisclaimerScreen({ embedded = false }: { embedded?: boolean }) {
  const acceptDisclaimer = useStore((s) => s.acceptDisclaimer);
  return (
    <Screen>
      <H1>Before you start</H1>
      <Card>
        <Body>
          Compass is a self-reflection and personal-growth tool. It is not therapy, not counselling,
          and not a medical device.
        </Body>
        <Body>
          It does not diagnose or treat anything, and it is not a substitute for professional
          mental-health care. The questions and reflections here are general self-help content.
        </Body>
        <Body>
          If you're struggling, reaching out to a licensed professional or a person you trust matters
          more than any app. You can open crisis resources any time from Settings.
        </Body>
        <Small>You can read this again from Settings whenever you like.</Small>
      </Card>
      {!embedded && (
        <View style={{ marginTop: spacing.md }}>
          <Button label="I understand — continue" onPress={acceptDisclaimer} />
        </View>
      )}
    </Screen>
  );
}
