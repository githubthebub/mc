import React, { useEffect } from 'react';
import { View } from 'react-native';
import { Screen, H1, H2, Body, Card, Button, Small } from '../components/UI';
import { useStore } from '../state/store';
import { flowList, nextSocratic, socraticQuestions, tagLabel } from '../engine';
import { colors, spacing } from '../theme/theme';

export default function HomeScreen({ navigation }: any) {
  const profile = useStore((s) => s.profile);
  const insights = useStore((s) => s.patternInsights);
  const refreshInsights = useStore((s) => s.refreshInsights);

  useEffect(() => {
    const unsub = navigation.addListener('focus', refreshInsights);
    return unsub;
  }, [navigation]);

  // A deterministic "question for reflection" based on the user's profile.
  const patternTags = profile?.topPatterns ?? [];
  const q = nextSocratic(socraticQuestions, {
    topic: (profile?.topicHint as any) || 'general',
    patternTags,
  });

  return (
    <Screen>
      <Small>COMPASS</Small>
      <H1>A space to think honestly</H1>

      {insights.length > 0 && (
        <Card style={{ backgroundColor: colors.primarySoft }}>
          <Small>PATTERN NOTICED</Small>
          <Body>{insights[0].message}</Body>
          <Button label="Look at my patterns" variant="soft" onPress={() => navigation.navigate('Patterns')} />
        </Card>
      )}

      {q && (
        <Card>
          <Small>SIT WITH THIS</Small>
          <Body>{q.text}</Body>
          <Button label="Journal on it" variant="ghost" onPress={() => navigation.navigate('Journal', { seedPrompt: q.text })} />
        </Card>
      )}

      <H2>Coaching flows</H2>
      <Body muted>Short, honest conversations that end in one concrete step.</Body>
      {flowList.map((f) => (
        <Card key={f.id}>
          <H2>{f.title}</H2>
          <Small>{f.estimatedMinutes} min · {f.topic}</Small>
          <View style={{ height: spacing.sm }} />
          <Button label="Start" onPress={() => navigation.navigate('Flow', { flowId: f.id })} />
        </Card>
      ))}

      {profile && (
        <Card>
          <Small>YOUR PROFILE</Small>
          <Body>
            You lean toward {profile.topValues.slice(0, 2).join(' & ')}.
            {profile.topPatterns.length > 0
              ? ` Watch for: ${profile.topPatterns.map(tagLabel).join(', ')}.`
              : ''}
          </Body>
          <Small>Derived on-device from your onboarding answers. Not a diagnosis.</Small>
        </Card>
      )}
    </Screen>
  );
}
