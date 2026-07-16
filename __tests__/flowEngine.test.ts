import { startFlow, advance, getNode } from '../src/engine/flowEngine';
import { getFlow, flowList } from '../src/engine/content';

describe('flowEngine', () => {
  it('loads both seed flows with valid start nodes', () => {
    expect(flowList.length).toBeGreaterThanOrEqual(2);
    for (const f of flowList) {
      expect(f.nodes[f.start]).toBeTruthy();
    }
  });

  it('starts at the flow start node', () => {
    const flow = getFlow('career-clarity')!;
    const step = startFlow(flow);
    expect(step.nodeId).toBe(flow.start);
    expect(step.done).toBe(false);
  });

  it('advances a choice node along the chosen branch and reports pattern tags', () => {
    const flow = getFlow('career-clarity')!;
    // whats_the_itch -> cant_choose sets rumination
    const { step, setPattern } = advance(flow, 'whats_the_itch', 'cant_choose');
    expect(setPattern).toBe('rumination');
    expect(step?.nodeId).toBe('choose_probe');
  });

  it('returns null step for an invalid option', () => {
    const flow = getFlow('career-clarity')!;
    const { step } = advance(flow, 'whats_the_itch', 'not_a_real_option');
    expect(step).toBeNull();
  });

  it('every reachable path terminates at an end node', () => {
    for (const flow of flowList) {
      // BFS from start; ensure no dangling next pointers and at least one end.
      const seen = new Set<string>();
      const queue = [flow.start];
      let sawEnd = false;
      while (queue.length) {
        const id = queue.shift()!;
        if (seen.has(id)) continue;
        seen.add(id);
        const node = getNode(flow, id)!;
        expect(node).toBeTruthy();
        if (node.type === 'end') { sawEnd = true; continue; }
        const targets: string[] = [];
        if (node.next) targets.push(node.next);
        (node.options || []).forEach((o) => targets.push(o.next));
        for (const t of targets) {
          expect(flow.nodes[t]).toBeTruthy(); // no dangling references
          queue.push(t);
        }
      }
      expect(sawEnd).toBe(true);
    }
  });
});
