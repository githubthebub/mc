import React, { useEffect, useState } from 'react';
import { View } from 'react-native';
import { Screen, H1, H2, Body, Card, Button, Field, Small } from '../components/UI';
import { useStore } from '../state/store';
import { journalPrompts, nextJournalPrompt, pushRecent, config } from '../engine';
import { guardAndMaybeRoute } from '../components/CrisisGuard';
import * as db from '../storage/db';

// Guided journaling. Prompts served deterministically from the curated bank
// (weighted by the user's patterns, non-repeating). Entries stored encrypted.
export default function JournalScreen({ route, navigation }: any) {
  const profile = useStore((s) => s.profile);
  const [prompt, setPrompt] = useState<string>('');
  const [promptId, setPromptId] = useState<string | undefined>(undefined);
  const [body, setBody] = useState('');
  const [entries, setEntries] = useState<db.JournalRow[]>([]);
  const [saved, setSaved] = useState(false);

  async function loadPrompt() {
    if (route?.params?.seedPrompt) {
      setPrompt(route.params.seedPrompt);
      setPromptId(undefined);
      return;
    }
    const ledger = await db.kvGet<string[]>('journalLedger', []);
    const p = nextJournalPrompt(journalPrompts, {
      patternTags: profile?.topPatterns ?? [],
      recentlyShownIds: ledger,
    });
    if (p) {
      setPrompt(p.text);
      setPromptId(p.id);
      await db.kvSet('journalLedger', pushRecent(ledger, p.id, config.questionSelector.recentlyShownMemory));
    }
  }

  async function refreshList() {
    setEntries(await db.getJournal(20));
  }

  useEffect(() => {
    loadPrompt();
    refreshList();
  }, []);

  async function save() {
    if (guardAndMaybeRoute(body, navigation)) return;
    await db.addJournal(body, promptId);
    setBody('');
    setSaved(true);
    await refreshList();
  }

  return (
    <Screen>
      <H1>Journal</H1>
      <Card>
        <Small>PROMPT</Small>
        <Body>{prompt}</Body>
        <Button label="Different prompt" variant="ghost" onPress={loadPrompt} />
      </Card>
      <Field multiline placeholder="Write freely. This is encrypted and stays on your device." value={body} onChangeText={setBody} />
      <Button label="Save entry" onPress={save} disabled={!body.trim()} />
      {saved && <Small>Saved on-device. ✓</Small>}

      {entries.length > 0 && (
        <>
          <H2>Recent entries</H2>
          {entries.map((e) => (
            <Card key={e.id}>
              <Small>{new Date(e.createdAt).toLocaleDateString()}</Small>
              <Body>{e.body}</Body>
            </Card>
          ))}
        </>
      )}
    </Screen>
  );
}
