import React from 'react';
import { View } from 'react-native';
import { Screen, H1, Body, Button, Card, Small } from '../components/UI';
import { useStore } from '../state/store';
import { config } from '../engine';

// Configurable age gate (default 18, from content/config/app-config.json).
export default function AgeGateScreen() {
  const verifyAge = useStore((s) => s.verifyAge);
  const minAge = config.ageGate.minAge;
  return (
    <Screen>
      <H1>A quick check</H1>
      <Card>
        <Body>Compass is made for adults. You need to be {minAge} or older to use it.</Body>
        <Small>We don't collect your date of birth — this stays on your device.</Small>
      </Card>
      <View style={{ marginTop: 8 }}>
        <Button label={`I'm ${minAge} or older`} onPress={verifyAge} />
      </View>
    </Screen>
  );
}
