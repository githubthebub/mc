import React, { useState } from 'react';
import { Alert, View } from 'react-native';
import { Screen, H1, H2, Body, Card, Button, Small } from '../components/UI';
import { useStore } from '../state/store';
import { getAllCrisisRegions, config } from '../engine';
import DisclaimerScreen from './DisclaimerScreen';

export default function SettingsScreen({ navigation }: any) {
  const region = useStore((s) => s.region);
  const setRegion = useStore((s) => s.setRegion);
  const eraseEverything = useStore((s) => s.eraseEverything);
  const [showDisclaimer, setShowDisclaimer] = useState(false);
  const regions = getAllCrisisRegions();

  function confirmErase() {
    Alert.alert(
      'Erase everything?',
      'This permanently deletes all your data from this device. It cannot be undone.',
      [
        { text: 'Cancel', style: 'cancel' },
        { text: 'Erase', style: 'destructive', onPress: () => eraseEverything() },
      ],
    );
  }

  if (showDisclaimer) {
    return (
      <Screen>
        <DisclaimerScreen embedded />
        <Button label="Close" variant="ghost" onPress={() => setShowDisclaimer(false)} />
      </Screen>
    );
  }

  return (
    <Screen>
      <H1>Settings</H1>

      <Card>
        <H2>Crisis resources</H2>
        <Body muted>Reachable any time. Pick the region that fits so the right resources show.</Body>
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: 8 }}>
          {regions.map((r) => (
            <Button key={r} label={r === region ? `✓ ${r}` : r} variant="soft" onPress={() => setRegion(r)} />
          ))}
        </View>
        <Button label="Open crisis resources" onPress={() => navigation.navigate('Crisis')} />
      </Card>

      <Card>
        <H2>The important reminder</H2>
        <Body muted>Compass is a self-reflection tool — not therapy, not medical care.</Body>
        <Button label="Read the disclaimer" variant="ghost" onPress={() => setShowDisclaimer(true)} />
      </Card>

      <Card>
        <H2>Legal</H2>
        <Small>Privacy Policy and Terms are bundled with the app (content/legal). They are placeholders pending attorney review.</Small>
      </Card>

      <Card>
        <H2>Your data</H2>
        <Body muted>Everything you enter lives only on this device, encrypted. Nothing is sent anywhere.</Body>
        <Button label="Erase my data" variant="ghost" onPress={confirmErase} />
      </Card>

      <Small>Compass v{config.version} · Age requirement: {config.ageGate.minAge}+ · Telemetry: off</Small>
    </Screen>
  );
}
