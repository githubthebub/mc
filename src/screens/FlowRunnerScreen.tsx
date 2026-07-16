import React, { useState } from 'react';
import { View } from 'react-native';
import { Screen, H1, H2, Body, Button, ChoiceButton, Card, Field, Small } from '../components/UI';
import { useStore } from '../state/store';
import {
  getFlow,
  startFlow,
  advance,
  nodeNeedsCrisisScan,
  nodeOffersQuest,
  FlowNode,
} from '../engine';
import { guardAndMaybeRoute } from '../components/CrisisGuard';
import * as db from '../storage/db';
import { spacing } from '../theme/theme';

// Walks an authored branching flow. Pure engine drives navigation between
// nodes; this screen only renders and collects input.
export default function FlowRunnerScreen({ route, navigation }: any) {
  const flow = getFlow(route.params.flowId)!;
  const logPattern = useStore((s) => s.logPattern);
  const [nodeId, setNodeId] = useState(startFlow(flow).nodeId);
  const [text, setText] = useState('');
  const [lastAction, setLastAction] = useState('');

  const node: FlowNode = flow.nodes[nodeId];

  async function go(optionId?: string) {
    // Crisis-scan free text before advancing/saving.
    if (nodeNeedsCrisisScan(node) && text.trim()) {
      if (guardAndMaybeRoute(text, navigation)) return;
    }
    if (node.type === 'action' && text.trim()) setLastAction(text.trim());

    const { step, setPattern } = advance(flow, nodeId, optionId);
    if (setPattern) await logPattern(setPattern, 'flow');
    setText('');
    if (step) setNodeId(step.nodeId);
  }

  function finish() {
    navigation.goBack();
  }

  async function makeQuest() {
    if (lastAction) {
      await db.addQuest(`flow_${flow.id}_${Date.now()}`, lastAction, 'flow');
    }
    navigation.navigate('Quests');
  }

  return (
    <Screen>
      <Small>{flow.title.toUpperCase()}</Small>

      {node.body && <Card><Body>{node.body}</Body></Card>}
      {node.prompt && <H2>{node.prompt}</H2>}

      {node.type === 'choice' &&
        (node.options || []).map((o) => (
          <ChoiceButton key={o.id} label={o.label} onPress={() => go(o.id)} />
        ))}

      {(node.type === 'freeText' || node.type === 'action') && (
        <>
          <Field
            multiline
            placeholder={node.type === 'action' ? 'One small, concrete step…' : 'Write freely — this stays on your device.'}
            value={text}
            onChangeText={setText}
          />
          {node.type === 'action' && node.suggestions && (
            <Card>
              <Small>NEED A STARTING POINT?</Small>
              {node.suggestions.map((s, i) => (
                <ChoiceButton key={i} label={s} onPress={() => setText(s)} />
              ))}
            </Card>
          )}
          <Button label="Continue" onPress={() => go()} disabled={node.type === 'action' && !text.trim()} />
        </>
      )}

      {['statement', 'reframe', 'socratic'].includes(node.type) && (
        <View style={{ marginTop: spacing.sm }}>
          <Button label="Continue" onPress={() => go()} />
        </View>
      )}

      {node.type === 'end' && (
        <View style={{ marginTop: spacing.sm }}>
          {nodeOffersQuest(node) && lastAction ? (
            <Button label="Turn my step into a quest" onPress={makeQuest} />
          ) : null}
          <Button label="Done" variant={lastAction ? 'ghost' : 'primary'} onPress={finish} />
        </View>
      )}
    </Screen>
  );
}
