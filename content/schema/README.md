# Content schema & authoring guide

All of Compass's "intelligence" is **data, not code**. These files are the curated
content the deterministic engines read. You can edit them by hand; run the validator
after any change:

```bash
npm run validate-content
```

The validator (`scripts/validate-content.js`, zero dependencies) checks:

1. **Every JSON file parses.**
2. **Flow graph integrity** — every `next` / option `next` points to a node that exists; `start` exists; no orphan or dangling references.
3. **Unique, stable ids** — Socratic questions, journaling prompts, quests, and distortions have unique ids.
4. **Topic/tag referential sanity** — question topics are in the declared topic list; pattern tags referenced in flows/questions exist in the onboarding pattern-tag list.
5. **The overclaim guardrail** — fails the build if banned marketing/clinical-promise words appear in any user-facing content string (see `scripts/banned-words.json`). This enforces the "no overclaiming / not-a-medical-device" rule at author time.

## File map

| Folder | What it holds |
|---|---|
| `onboarding/questionnaire.json` | Onboarding questions + deterministic scoring → values profile & pattern tags |
| `flows/*.json` | Branching coaching decision-trees (nodes: statement/choice/freeText/socratic/reframe/action/end) |
| `questions/socratic.json` | Tagged open-question bank |
| `journaling/prompts.json` | Guided journaling prompt bank |
| `distortions/distortions.json` | Cognitive-distortion → pre-written reframe templates (CBT-cited) |
| `quests/starter-quests.json` | Micro-action quest pack |
| `crisis/crisis-lines.json` | Crisis keyword list + region resources (**PLACEHOLDER** — verify before release) |
| `config/app-config.json` | Age gate, thresholds, feature flags, telemetry-off flag |
| `legal/*.md` | Placeholder Disclaimer / Privacy / Terms (**attorney review required**) |

## Authoring rules

- Keep `id` fields stable once users exist — they key stored progress and "recently shown" ledgers.
- Never add clinical-promise or overclaim language (the validator will reject it).
- Free-text nodes that collect user writing should set `"scanForCrisis": true`.
- Every coaching flow should end in a concrete, finishable action node.
