import React, { useEffect, useState } from 'react';
import { View } from 'react-native';
import { Screen, H1, H2, Body, Card, Button, Small } from '../components/UI';
import { useStore } from '../state/store';
import { onboarding, tagLabel } from '../engine';
import * as db from '../storage/db';
import { PatternTagId } from '../engine';

// Mood + pattern tracking. The app counts recurrences deterministically and
// gently names them (see engine/patternDetector). No inference beyond counting.
export default function PatternsScreen({ navigation }: any) {
  const insights = useStore((s) => s.patternInsights);
  const logPattern = useStore((s) => s.logPattern);
  const refreshInsights = useStore((s) => s.refreshInsights);
  const [moods, setMoods] = useState<db.MoodRow[]>([]);
  const tags = onboarding.patternTags as { id: PatternTagId; label: string; description: string }[];

  async function refresh() {
    setMoods(await db.getMoods(30));
    await refreshInsights();
  }
  useEffect(() => {
    const unsub = navigation.addListener('focus', refresh);
    refresh();
    return unsub;
  }, [navigation]);

  async function addMood(v: number) {
    await db.addMood(v);
    await refresh();
  }

  const moodFaces = ['🌧️', '☁️', '⛅', '🌤️', '☀️'];

  return (
    <Screen>
      <H1>Patterns</H1>

      <Card>
        <Small>HOW'S TODAY, HONESTLY?</Small>
        <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginTop: 8 }}>
          {moodFaces.map((f, i) => (
            <Button key={i} label={f} variant="soft" onPress={() => addMood(i + 1)} />
          ))}
        </View>
        <Small>No streaks, no pressure. Just a check-in when you want one.</Small>
      </Card>

      {insights.length > 0 ? (
        insights.map((ins) => (
          <Card key={ins.tag} style={{ marginTop: 8 }}>
            <Small>RECURRING — {ins.count}× IN {ins.windowDays} DAYS</Small>
            <Body>{ins.message}</Body>
            <Button label="Reflect on this" variant="ghost" onPress={() => navigation.navigate('Journal', { seedPrompt: ins.message })} />
          </Card>
        ))
      ) : (
        <Card>
          <Body muted>No recurring patterns flagged yet. As you use flows and tag themes, the app will gently point out anything that keeps coming up — just by counting, never guessing.</Body>
        </Card>
      )}

      <H2>Flag a theme</H2>
      <Body muted>Noticing something? Tag it. Enough tags and it'll show up above.</Body>
      {tags.map((t) => (
        <Card key={t.id}>
          <H2>{t.label}</H2>
          <Small>{t.description}</Small>
          <View style={{ height: 8 }} />
          <Button label={`Flag ${t.label.toLowerCase()}`} variant="soft" onPress={() => logPattern(t.id, 'manual')} />
        </Card>
      ))}

      {moods.length > 0 && (
        <>
          <H2>Recent check-ins</H2>
          <Card>
            {moods.slice(0, 10).map((m) => (
              <Body key={m.id}>{moodFaces[m.mood - 1]}  {new Date(m.createdAt).toLocaleDateString()}</Body>
            ))}
          </Card>
        </>
      )}
    </Screen>
  );
}
