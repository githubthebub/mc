# Compass 🧭

A structured personal-growth **reflection** app. Compass delivers the *value* of a
direct, challenging coach — it pushes back on excuses, gets to the real issue,
tracks recurring patterns, and turns reflection into one small action — **without any
AI/LLM and without any server**. Everything is deterministic, rules-based, and runs
entirely on-device.

> **Compass is not therapy, not counselling, and not a medical device.** It does not
> diagnose or treat anything and is not a substitute for professional mental-health
> care. See [Safety & legal](#safety--legal).

---

## Why there's no AI

Every "coaching" moment is **curated content selected by pure rules** — never generated
text. The intelligence lives in editable data files under [`/content`](./content), read
by small deterministic engines under [`src/engine`](./src/engine):

| "AI-like" capability | How it's actually done (deterministic) |
|---|---|
| Values & self-assessment | Structured questionnaire → weighted scoring → values profile + pattern tags ([`scoring.ts`](./src/engine/scoring.ts)) |
| Coaching conversations | Authored branching decision-trees; branches depend on your answers ([`flowEngine.ts`](./src/engine/flowEngine.ts)) |
| Socratic questioning | Tagged question bank, weighted + non-repeating selection ([`questionSelector.ts`](./src/engine/questionSelector.ts)) |
| CBT toolkit | You pick the distortion → pre-written, cited reframe scaffold ([`distortions.json`](./content/distortions/distortions.json)) |
| Pattern tracking | Pure counting + a threshold rule ("flagged X 5× this month") ([`patternDetector.ts`](./src/engine/patternDetector.ts)) |
| Crisis handling | Maintained keyword list → calm resources screen ([`crisisScanner.ts`](./src/engine/crisisScanner.ts)) |

No LLM. No generated text. No external API for coaching content. Same input → same output.

---

## Tech stack & why

- **Expo (React Native) + TypeScript** — cross-platform, offline-capable, and the JSON
  content model is trivial to hand-edit and diff in review.
- **`expo-secure-store`** — the data-encryption key + acknowledgement flags live in the
  OS keychain/keystore.
- **`expo-sqlite`** — structured records; sensitive free-text columns are **AES-encrypted**
  ([`crypto.ts`](./src/storage/crypto.ts)) with a device-only key before they're written.
- **`zustand`** — small local state store.
- **No analytics SDKs, no ads SDKs, no OTA updates, no network calls containing user
  content.** OTA updates are explicitly disabled in [`app.json`](./app.json).

---

## Run it

Requires Node 18+ and the [Expo](https://docs.expo.dev/) toolchain.

```bash
npm install
npm start          # then press i / a, or scan the QR with Expo Go
# npm run ios      # iOS simulator
# npm run android  # Android emulator
```

### Verify everything

```bash
npm run check      # validate-content + typecheck + tests
# or individually:
npm run validate-content   # structure, flow-graph integrity, id uniqueness, overclaim guardrail
npm run typecheck
npm test                   # deterministic engine unit tests (27 tests)
```

---

## Editing content

All curated content is versioned JSON under [`/content`](./content), separated from app
logic. See [`content/schema/README.md`](./content/schema/README.md) for the full authoring
guide. After **any** content edit:

```bash
npm run validate-content
```

The validator checks flow-graph integrity (no dangling branches), unique/stable ids,
topic/tag references, and — importantly — the **overclaim guardrail**: it fails the build
if banned marketing or clinical-promise words (`cure`, `treatment`, `life-changing`,
`better than a therapist`, …) appear in user-facing content. See
[`scripts/banned-words.json`](./scripts/banned-words.json).

Common edits:
- **Add a coaching flow** → new file in `content/flows/`, register it in
  [`src/engine/content.ts`](./src/engine/content.ts).
- **Add Socratic questions** → `content/questions/socratic.json` (unique `id`, valid topics/patterns).
- **Add journaling prompts** → `content/journaling/prompts.json`.
- **Tune pattern detection** → `content/config/app-config.json` (`windowDays`, `recurrenceThreshold`).
- **Change the age gate** → `content/config/app-config.json` (`ageGate.minAge`).
- **Fill in real crisis resources** → `content/crisis/crisis-lines.json` (**required before release**).

---

## On-device data model

Nothing leaves the device. There is no backend and no sync.

**Keychain / keystore (`expo-secure-store`)** — data-encryption key; disclaimer &
age-verification flags; onboarded flag; region.

**SQLite (`compass.db`)** — sensitive text columns AES-encrypted; low-sensitivity index
columns (category, timestamp) kept in clear so counting works without decryption:

| Table | Contents |
|---|---|
| `mood_logs` | mood scalar (1–5) + optional **encrypted** note |
| `pattern_logs` | pattern tag id + timestamp (for recurrence counting) |
| `journal_entries` | **encrypted** entry body + prompt id |
| `thought_records` | **encrypted** JSON (situation, thought, distortion, reframe) |
| `quests` / `quest_checkins` | active quests + **encrypted** check-in notes |
| `kv` | small non-sensitive JSON (profile, "recently shown" ledgers) |

**Erase**: Settings → *Erase my data* drops every table and deletes the keychain entries.
Uninstalling the app also removes the local database.

---

## Safety & legal

These are treated as non-negotiable and are wired into the app:

- **First-launch disclaimer** you must acknowledge; re-readable anytime from Settings.
- **Age gate** at a configurable threshold (default 18).
- **Crisis handling**: free text is scanned against a maintained keyword list; a match
  routes to a **calm, non-clinical** resources screen. It never counsels or diagnoses.
  The hotline list is a **configurable placeholder** — fill it per region before release.
- **No overclaiming**: enforced at author time by the content validator's guardrail.
- **Nudges toward real-world support and human connection**, not app dependence.
- **Privacy Policy & Terms** placeholders under [`content/legal`](./content/legal) state
  that data is stored only on-device.

> ⚠️ **Legal review required.** The disclaimer, Terms of Service, and Privacy Policy in
> this repo are **placeholders and are NOT legally sufficient as-is**. A licensed attorney
> must review and finalise all of them for your jurisdiction(s) and app-store requirements
> **before release**. Crisis-resource data must be verified by an appropriate professional.
> Nothing here is legal or clinical advice.

---

## Project layout

```
content/            Curated, versioned data (the "intelligence") — editable & auditable
  flows/            Branching coaching decision-trees
  questions/        Socratic question bank
  journaling/       Guided journaling prompts
  distortions/      Cognitive-distortion → reframe templates (CBT-cited)
  quests/           Micro-action quest pack
  onboarding/       Questionnaire + scoring map
  crisis/           Crisis keyword list + resources (PLACEHOLDER)
  config/           Age gate, thresholds, feature flags
  legal/            Disclaimer / Privacy / Terms (PLACEHOLDER — attorney review)
  schema/           Authoring guide
src/
  engine/           Pure, deterministic, unit-tested logic (no AI, no I/O)
  storage/          Encrypted on-device storage (SecureStore + SQLite + AES)
  state/            Zustand store
  screens/          UI screens
  components/        Shared UI kit + crisis guard
  navigation/       Gate flow + tabs
  theme/            Calm, non-gamified visual system
scripts/            Content validator + overclaim guardrail
__tests__/          Engine unit tests
```

## Non-goals

No LLM or generative text. No external API for coaching content. No collection or
transmission of personal data. No guilt-inducing streak mechanics.

## License

MIT — see [LICENSE](./LICENSE).
