import React, { useEffect, useState } from 'react';
import { View } from 'react-native';
import { Screen, H1, H2, Body, Card, Button, Field, Small } from '../components/UI';
import { useStore } from '../state/store';
import { questPack, Quest } from '../engine';
import * as db from '../storage/db';

// Micro-action quests: reflection → quest → check-in. Encouraging, never
// punishing — no streak anxiety, no guilt copy.
export default function QuestsScreen({ navigation }: any) {
  const profile = useStore((s) => s.profile);
  const [active, setActive] = useState<{ id: string; title: string; source: string }[]>([]);
  const [checkinFor, setCheckinFor] = useState<string | null>(null);
  const [note, setNote] = useState('');

  async function refresh() {
    setActive(await db.getActiveQuests());
  }
  useEffect(() => {
    const unsub = navigation.addListener('focus', refresh);
    refresh();
    return unsub;
  }, [navigation]);

  // Surface pack quests that match the user's patterns first (deterministic).
  const patternTags = profile?.topPatterns ?? [];
  const suggested = [...questPack].sort((a, b) => {
    const score = (q: Quest) => q.patterns.filter((p) => patternTags.includes(p)).length;
    return score(b) - score(a) || a.id.localeCompare(b.id);
  });

  async function adopt(q: Quest) {
    await db.addQuest(q.id, q.title, 'pack');
    await refresh();
  }
  async function complete(id: string) {
    await db.completeQuest(id);
    await refresh();
  }
  async function submitCheckin(id: string) {
    await db.addQuestCheckin(id, note.trim() || undefined);
    setNote('');
    setCheckinFor(null);
  }

  const activeIds = new Set(active.map((a) => a.id));

  return (
    <Screen>
      <H1>Quests</H1>
      <Body muted>Small, finishable actions. Progress here is meant to encourage — there are no streaks to break.</Body>

      {active.length > 0 && (
        <>
          <H2>Active</H2>
          {active.map((a) => (
            <Card key={a.id}>
              <Body>{a.title}</Body>
              {checkinFor === a.id ? (
                <>
                  <Field multiline placeholder="How did it go? (optional, stays on device)" value={note} onChangeText={setNote} />
                  <Button label="Save check-in" onPress={() => submitCheckin(a.id)} />
                </>
              ) : (
                <View style={{ flexDirection: 'row', gap: 8 }}>
                  <View style={{ flex: 1 }}><Button label="Check in" variant="ghost" onPress={() => setCheckinFor(a.id)} /></View>
                  <View style={{ flex: 1 }}><Button label="Mark done" variant="soft" onPress={() => complete(a.id)} /></View>
                </View>
              )}
            </Card>
          ))}
        </>
      )}

      <H2>Suggested for you</H2>
      {suggested.filter((q) => !activeIds.has(q.id)).map((q) => (
        <Card key={q.id}>
          <H2>{q.title}</H2>
          <Body muted>{q.summary}</Body>
          <Small>WHY</Small>
          <Body>{q.why}</Body>
          <Button label="Add this quest" onPress={() => adopt(q)} />
        </Card>
      ))}
    </Screen>
  );
}
