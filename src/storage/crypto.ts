// Application-layer encryption for sensitive content (journal entries, thought
// records, flow free-text). Uses AES via crypto-es (pure JS, offline) with a
// 256-bit key held in the OS keychain/keystore (see secureStore.ts).
//
// Why app-layer: it guarantees the user's written content is encrypted at rest
// regardless of platform SQLite specifics, and keeps the trust boundary simple
// and auditable. Non-sensitive index columns (kind, timestamp, pattern tag)
// stay in clear so we can count/query without decrypting everything.
//
// NOTE: This protects data at rest on the device. It is not a substitute for a
// device passcode; document that expectation for users (see PRIVACY.md).

import CryptoES from 'crypto-es';
import { secure } from './secureStore';

let cachedKey: string | null = null;

async function key(): Promise<string> {
  if (!cachedKey) cachedKey = await secure.getOrCreateEncryptionKey();
  return cachedKey;
}

export async function encrypt(plain: string): Promise<string> {
  const k = await key();
  return CryptoES.AES.encrypt(plain ?? '', k).toString();
}

export async function decrypt(cipher: string): Promise<string> {
  if (!cipher) return '';
  const k = await key();
  try {
    const bytes = CryptoES.AES.decrypt(cipher, k);
    return bytes.toString(CryptoES.enc.Utf8);
  } catch {
    return ''; // never throw on read; a corrupt/foreign blob yields empty
  }
}

export function resetKeyCache(): void {
  cachedKey = null;
}
