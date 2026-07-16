// Flow engine — walks an authored branching decision-tree.
//
// Pure and deterministic: given a flow and the current node id + a chosen
// option, it returns the next node. It never generates text; every node's
// content is authored in content/flows/*.json. It also reports which pattern
// tags a taken branch implies (setPattern), so the app can log them.

import { Flow, FlowNode, FlowOption, PatternTagId } from './types';

export interface FlowStep {
  nodeId: string;
  node: FlowNode;
  done: boolean;
}

export function startFlow(flow: Flow): FlowStep {
  const node = flow.nodes[flow.start];
  return { nodeId: flow.start, node, done: node.type === 'end' };
}

export function getNode(flow: Flow, nodeId: string): FlowNode | null {
  return flow.nodes[nodeId] ?? null;
}

/**
 * Advance from a node.
 * - For choice nodes, pass the chosen option id.
 * - For all other node types, optionId is ignored and we follow `next`.
 * Returns the next FlowStep, plus any pattern tag the branch set.
 */
export function advance(
  flow: Flow,
  currentNodeId: string,
  optionId?: string,
): { step: FlowStep | null; setPattern?: PatternTagId } {
  const node = flow.nodes[currentNodeId];
  if (!node) return { step: null };

  let nextId: string | undefined;
  let setPattern: PatternTagId | undefined = node.setPattern;

  if (node.type === 'choice') {
    const opt: FlowOption | undefined = (node.options || []).find((o) => o.id === optionId);
    if (!opt) return { step: null }; // invalid choice
    nextId = opt.next;
    if (opt.setPattern) setPattern = opt.setPattern;
  } else if (node.type === 'end') {
    return { step: { nodeId: currentNodeId, node, done: true }, setPattern };
  } else {
    nextId = node.next;
  }

  if (!nextId || !flow.nodes[nextId]) return { step: null, setPattern };
  const nextNode = flow.nodes[nextId];
  return {
    step: { nodeId: nextId, node: nextNode, done: nextNode.type === 'end' },
    setPattern,
  };
}

/** True if this node collects user free text that must be crisis-scanned. */
export function nodeNeedsCrisisScan(node: FlowNode): boolean {
  return node.type === 'freeText' && node.scanForCrisis === true;
}

/** True if reaching this node should offer to turn the user's action into a quest. */
export function nodeOffersQuest(node: FlowNode): boolean {
  return node.type === 'end' && node.offerQuestFromAction === true;
}
