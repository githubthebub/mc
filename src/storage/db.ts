// On-device SQLite storage (expo-sqlite). Structured records live here; the
// free-text/content columns are AES-encrypted (see crypto.ts) before writing.
// Nothing here ever leaves the device — there is no network code in this module.

import * as SQLite from 'expo-sqlite';
import { encrypt, decrypt } from './crypto';
import { PatternTagId } from '../engine/types';

let dbInstance: SQLite.SQLiteDatabase | null = null;

export async function getDb(): Promise<SQLite.SQLiteDatabase> {
  if (!dbInstance) {
    dbInstance = await SQLite.openDatabaseAsync('compass.db');
    await migrate(dbInstance);
  }
  return dbInstance;
}

async function migrate(db: SQLite.SQLiteDatabase): Promise<void> {
  await db.execAsync(`
    PRAGMA journal_mode = WAL;
    CREATE TABLE IF NOT EXISTS mood_logs (
      id TEXT PRIMARY KEY NOT NULL,
      created_at INTEGER NOT NULL,
      mood INTEGER NOT NULL,           -- 1..5, non-sensitive scalar
      note_enc TEXT                    -- encrypted optional note
    );
    CREATE TABLE IF NOT EXISTS pattern_logs (
      id TEXT PRIMARY KEY NOT NULL,
      created_at INTEGER NOT NULL,
      tag TEXT NOT NULL,               -- pattern category id (for counting)
      source TEXT                      -- 'flow' | 'manual' | 'thought_record'
    );
    CREATE TABLE IF NOT EXISTS journal_entries (
      id TEXT PRIMARY KEY NOT NULL,
      created_at INTEGER NOT NULL,
      prompt_id TEXT,
      body_enc TEXT NOT NULL           -- encrypted entry text
    );
    CREATE TABLE IF NOT EXISTS thought_records (
      id TEXT PRIMARY KEY NOT NULL,
      created_at INTEGER NOT NULL,
      distortion_id TEXT,
      payload_enc TEXT NOT NULL        -- encrypted JSON {situation, thought, reframe, ...}
    );
    CREATE TABLE IF NOT EXISTS quests (
      id TEXT PRIMARY KEY NOT NULL,      -- quest content id or generated id
      created_at INTEGER NOT NULL,
      title TEXT NOT NULL,
      active INTEGER NOT NULL DEFAULT 1,
      source TEXT                        -- 'pack' | 'flow'
    );
    CREATE TABLE IF NOT EXISTS quest_checkins (
      id TEXT PRIMARY KEY NOT NULL,
      quest_id TEXT NOT NULL,
      created_at INTEGER NOT NULL,
      note_enc TEXT
    );
    CREATE TABLE IF NOT EXISTS kv (
      k TEXT PRIMARY KEY NOT NULL,
      v TEXT NOT NULL                    -- small non-sensitive JSON (e.g. recently-shown ledgers, profile)
    );
  `);
}

let idCounter = 0;
function id(prefix: string, seq: number): string {
  // Local-only unique id: prefix + timestamp + a monotonic counter to avoid
  // same-millisecond collisions. Uniqueness only needs to hold on-device.
  idCounter = (idCounter + 1) % 1_000_000;
  return `${prefix}_${seq}_${idCounter}`;
}

// ---------------- Mood ----------------
export async function addMood(mood: number, note?: string): Promise<void> {
  const db = await getDb();
  const noteEnc = note ? await encrypt(note) : null;
  const now = Date.now();
  await db.runAsync(
    'INSERT INTO mood_logs (id, created_at, mood, note_enc) VALUES (?, ?, ?, ?)',
    id('mood', now), now, mood, noteEnc,
  );
}

export interface MoodRow { id: string; createdAt: number; mood: number; note: string }
export async function getMoods(limit = 60): Promise<MoodRow[]> {
  const db = await getDb();
  const rows = await db.getAllAsync<any>(
    'SELECT * FROM mood_logs ORDER BY created_at DESC LIMIT ?', limit,
  );
  const out: MoodRow[] = [];
  for (const r of rows) {
    out.push({ id: r.id, createdAt: r.created_at, mood: r.mood, note: r.note_enc ? await decrypt(r.note_enc) : '' });
  }
  return out;
}

// ---------------- Pattern logs ----------------
export async function logPattern(tag: PatternTagId, source = 'manual'): Promise<void> {
  const db = await getDb();
  const now = Date.now();
  await db.runAsync(
    'INSERT INTO pattern_logs (id, created_at, tag, source) VALUES (?, ?, ?, ?)',
    id('pat', now), now, tag, source,
  );
}

export async function getPatternLogs(): Promise<{ tag: PatternTagId; timestampMs: number }[]> {
  const db = await getDb();
  const rows = await db.getAllAsync<any>('SELECT tag, created_at FROM pattern_logs');
  return rows.map((r) => ({ tag: r.tag as PatternTagId, timestampMs: r.created_at }));
}

// ---------------- Journal ----------------
export async function addJournal(body: string, promptId?: string): Promise<void> {
  const db = await getDb();
  const now = Date.now();
  await db.runAsync(
    'INSERT INTO journal_entries (id, created_at, prompt_id, body_enc) VALUES (?, ?, ?, ?)',
    id('jrl', now), now, promptId ?? null, await encrypt(body),
  );
}

export interface JournalRow { id: string; createdAt: number; promptId: string | null; body: string }
export async function getJournal(limit = 100): Promise<JournalRow[]> {
  const db = await getDb();
  const rows = await db.getAllAsync<any>(
    'SELECT * FROM journal_entries ORDER BY created_at DESC LIMIT ?', limit,
  );
  const out: JournalRow[] = [];
  for (const r of rows) out.push({ id: r.id, createdAt: r.created_at, promptId: r.prompt_id, body: await decrypt(r.body_enc) });
  return out;
}

// ---------------- Thought records ----------------
export interface ThoughtRecord {
  situation: string;
  thought: string;
  distortionId?: string;
  reframe: string;
}
export async function addThoughtRecord(rec: ThoughtRecord): Promise<void> {
  const db = await getDb();
  const now = Date.now();
  await db.runAsync(
    'INSERT INTO thought_records (id, created_at, distortion_id, payload_enc) VALUES (?, ?, ?, ?)',
    id('tr', now), now, rec.distortionId ?? null, await encrypt(JSON.stringify(rec)),
  );
}
export async function getThoughtRecords(limit = 100): Promise<(ThoughtRecord & { id: string; createdAt: number })[]> {
  const db = await getDb();
  const rows = await db.getAllAsync<any>('SELECT * FROM thought_records ORDER BY created_at DESC LIMIT ?', limit);
  const out: any[] = [];
  for (const r of rows) {
    const payload = JSON.parse((await decrypt(r.payload_enc)) || '{}');
    out.push({ id: r.id, createdAt: r.created_at, ...payload });
  }
  return out;
}

// ---------------- Quests ----------------
export async function addQuest(questId: string, title: string, source = 'pack'): Promise<void> {
  const db = await getDb();
  await db.runAsync(
    'INSERT OR REPLACE INTO quests (id, created_at, title, active, source) VALUES (?, ?, ?, 1, ?)',
    questId, Date.now(), title, source,
  );
}
export async function getActiveQuests(): Promise<{ id: string; title: string; source: string; createdAt: number }[]> {
  const db = await getDb();
  const rows = await db.getAllAsync<any>('SELECT * FROM quests WHERE active = 1 ORDER BY created_at DESC');
  return rows.map((r) => ({ id: r.id, title: r.title, source: r.source, createdAt: r.created_at }));
}
export async function completeQuest(questId: string): Promise<void> {
  const db = await getDb();
  await db.runAsync('UPDATE quests SET active = 0 WHERE id = ?', questId);
}
export async function addQuestCheckin(questId: string, note?: string): Promise<void> {
  const db = await getDb();
  const now = Date.now();
  await db.runAsync(
    'INSERT INTO quest_checkins (id, quest_id, created_at, note_enc) VALUES (?, ?, ?, ?)',
    id('qc', now), questId, now, note ? await encrypt(note) : null,
  );
}
export async function getQuestCheckins(questId: string): Promise<{ createdAt: number; note: string }[]> {
  const db = await getDb();
  const rows = await db.getAllAsync<any>('SELECT * FROM quest_checkins WHERE quest_id = ? ORDER BY created_at DESC', questId);
  const out: { createdAt: number; note: string }[] = [];
  for (const r of rows) out.push({ createdAt: r.created_at, note: r.note_enc ? await decrypt(r.note_enc) : '' });
  return out;
}

// ---------------- Key/value (ledgers, profile) ----------------
export async function kvGet<T>(k: string, fallback: T): Promise<T> {
  const db = await getDb();
  const row = await db.getFirstAsync<any>('SELECT v FROM kv WHERE k = ?', k);
  if (!row) return fallback;
  try { return JSON.parse(row.v) as T; } catch { return fallback; }
}
export async function kvSet<T>(k: string, v: T): Promise<void> {
  const db = await getDb();
  await db.runAsync('INSERT OR REPLACE INTO kv (k, v) VALUES (?, ?)', k, JSON.stringify(v));
}

// ---------------- Erase everything ----------------
export async function eraseAllData(): Promise<void> {
  const db = await getDb();
  await db.execAsync(`
    DELETE FROM mood_logs;
    DELETE FROM pattern_logs;
    DELETE FROM journal_entries;
    DELETE FROM thought_records;
    DELETE FROM quests;
    DELETE FROM quest_checkins;
    DELETE FROM kv;
  `);
}
