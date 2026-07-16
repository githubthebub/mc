#!/usr/bin/env node
/*
 * Compass content validator — ZERO dependencies (plain Node).
 * Verifies content integrity so authors can edit JSON safely, and enforces
 * the "no overclaiming / not a medical device" guardrail at author time.
 *
 * Run: npm run validate-content   (or: node scripts/validate-content.js)
 * Exits non-zero on any error, so it can gate CI / commits.
 */
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const CONTENT = path.join(ROOT, 'content');
const errors = [];
const warnings = [];
const err = (m) => errors.push(m);
const warn = (m) => warnings.push(m);

function readJson(rel) {
  const p = path.join(CONTENT, rel);
  try {
    return JSON.parse(fs.readFileSync(p, 'utf8'));
  } catch (e) {
    err(`Failed to parse ${rel}: ${e.message}`);
    return null;
  }
}

// ---- Collect user-facing strings (skip keys starting with "_" and known meta keys) ----
const META_KEYS = new Set(['_README', '_note', '_readme', 'citation', 'aka', 'note', 'version', 'id', 'topics', 'themes', 'patterns', 'values', 'cadence', 'type', 'next', 'start', 'setPattern', 'scanForCrisis', 'requireAction', 'offerQuestFromAction', 'weight', 'estimatedMinutes', 'scores', 'keywords', 'excludePhrases', 'keywordMatching', 'defaultRegion', 'contact', 'type']);
function collectStrings(node, acc) {
  if (node == null) return;
  if (typeof node === 'string') { acc.push(node); return; }
  if (Array.isArray(node)) { node.forEach((n) => collectStrings(n, acc)); return; }
  if (typeof node === 'object') {
    for (const [k, v] of Object.entries(node)) {
      if (k.startsWith('_') || META_KEYS.has(k)) continue;
      collectStrings(v, acc);
    }
  }
}

// ---- Overclaim guardrail ----
function checkBannedWords() {
  const cfg = JSON.parse(fs.readFileSync(path.join(__dirname, 'banned-words.json'), 'utf8'));
  const banned = cfg.banned.map((w) => w.toLowerCase());
  const allow = cfg.allowContexts.map((w) => w.toLowerCase());
  // Scan user-facing content files only (not legal placeholders / crisis data).
  const files = [
    'flows/career-clarity.json',
    'flows/burnout.json',
    'questions/socratic.json',
    'journaling/prompts.json',
    'distortions/distortions.json',
    'quests/starter-quests.json',
    'onboarding/questionnaire.json',
    'config/app-config.json',
  ];
  for (const rel of files) {
    const data = readJson(rel);
    if (!data) continue;
    const strings = [];
    collectStrings(data, strings);
    for (const s of strings) {
      const low = s.toLowerCase();
      const exempt = allow.some((a) => low.includes(a));
      for (const w of banned) {
        const re = new RegExp(`\\b${w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'i');
        if (re.test(low) && !exempt) {
          err(`Overclaim guardrail: banned phrase "${w}" found in ${rel}: "${s.slice(0, 80)}…"`);
        }
      }
    }
  }
}

// ---- Flow graph integrity ----
function checkFlow(rel) {
  const flow = readJson(rel);
  if (!flow) return;
  if (!flow.nodes || !flow.start) { err(`${rel}: missing nodes or start`); return; }
  if (!flow.nodes[flow.start]) err(`${rel}: start node "${flow.start}" does not exist`);
  const ids = new Set(Object.keys(flow.nodes));
  const referenced = new Set([flow.start]);
  for (const [nid, node] of Object.entries(flow.nodes)) {
    const targets = [];
    if (node.next) targets.push(node.next);
    if (Array.isArray(node.options)) node.options.forEach((o) => { if (o.next) targets.push(o.next); });
    for (const t of targets) {
      referenced.add(t);
      if (!ids.has(t)) err(`${rel}: node "${nid}" points to missing node "${t}"`);
    }
    if (node.type === 'choice' && (!node.options || node.options.length === 0)) {
      err(`${rel}: choice node "${nid}" has no options`);
    }
    if (node.type === 'end' && node.next) warn(`${rel}: end node "${nid}" has a next (ignored)`);
  }
  for (const id of ids) {
    if (!referenced.has(id)) warn(`${rel}: node "${id}" is unreachable`);
  }
  return flow;
}

// ---- Unique id checks ----
function checkUniqueIds(rel, arrayKey, root) {
  const data = readJson(rel);
  if (!data) return;
  const arr = data[arrayKey] || (Array.isArray(data) ? data : (root ? data[root] : null));
  const list = Array.isArray(arr) ? arr : null;
  if (!list) { err(`${rel}: expected array at "${arrayKey}"`); return; }
  const seen = new Set();
  for (const item of list) {
    if (!item.id) { err(`${rel}: item missing id`); continue; }
    if (seen.has(item.id)) err(`${rel}: duplicate id "${item.id}"`);
    seen.add(item.id);
  }
  return list;
}

// ---- Referential: patterns & topics ----
function checkReferences() {
  const onboarding = readJson('onboarding/questionnaire.json');
  const socratic = readJson('questions/socratic.json');
  if (!onboarding || !socratic) return;
  const patternIds = new Set((onboarding.patternTags || []).map((p) => p.id));
  const topicSet = new Set(socratic.topics || []);
  for (const q of socratic.questions || []) {
    for (const t of q.topics || []) {
      if (!topicSet.has(t)) err(`socratic.json: question ${q.id} has unknown topic "${t}"`);
    }
    for (const pt of q.patterns || []) {
      if (!patternIds.has(pt)) warn(`socratic.json: question ${q.id} references pattern "${pt}" not in onboarding pattern list`);
    }
  }
}

// ================= run =================
console.log('Validating Compass content…\n');
checkFlow('flows/career-clarity.json');
checkFlow('flows/burnout.json');
checkUniqueIds('questions/socratic.json', 'questions');
checkUniqueIds('journaling/prompts.json', 'prompts');
checkUniqueIds('quests/starter-quests.json', 'quests');
checkUniqueIds('distortions/distortions.json', 'distortions');
checkReferences();
checkBannedWords();

// sanity: seed-content minimums from the spec
const socratic = readJson('questions/socratic.json');
if (socratic && (socratic.questions || []).length < 50) {
  err(`Spec requires ~50 Socratic questions; found ${socratic.questions.length}`);
}

if (warnings.length) {
  console.log('Warnings:');
  warnings.forEach((w) => console.log('  ⚠ ' + w));
  console.log('');
}
if (errors.length) {
  console.log('Errors:');
  errors.forEach((e) => console.log('  ✗ ' + e));
  console.log(`\n❌ Content validation FAILED with ${errors.length} error(s).`);
  process.exit(1);
}
console.log('✅ Content valid. All checks passed.');
