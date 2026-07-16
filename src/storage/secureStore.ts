// Secure key/flag storage, backed by the OS keychain/keystore via expo-secure-store.
// Holds: the data-encryption key, and small acknowledgement flags. No user content
// is ever stored here or anywhere off-device.

import * as SecureStore from 'expo-secure-store';
import * as Crypto from 'expo-crypto';

const KEY_ENC = 'compass.dek.v1'; // data encryption key
const KEY_DISCLAIMER = 'compass.ack.disclaimer.v1';
const KEY_AGE = 'compass.ack.age.v1';
const KEY_ONBOARDED = 'compass.onboarded.v1';
const KEY_REGION = 'compass.region.v1';

async function getOrCreateEncryptionKey(): Promise<string> {
  let key = await SecureStore.getItemAsync(KEY_ENC);
  if (!key) {
    // 256-bit random key, hex-encoded. Generated on-device, never transmitted.
    const bytes = await Crypto.getRandomBytesAsync(32);
    key = Array.from(bytes).map((b) => b.toString(16).padStart(2, '0')).join('');
    await SecureStore.setItemAsync(KEY_ENC, key, {
      keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY,
    });
  }
  return key;
}

async function getBool(k: string): Promise<boolean> {
  return (await SecureStore.getItemAsync(k)) === 'true';
}
async function setBool(k: string, v: boolean): Promise<void> {
  await SecureStore.setItemAsync(k, v ? 'true' : 'false');
}

export const secure = {
  getOrCreateEncryptionKey,
  getDisclaimerAck: () => getBool(KEY_DISCLAIMER),
  setDisclaimerAck: (v: boolean) => setBool(KEY_DISCLAIMER, v),
  getAgeVerified: () => getBool(KEY_AGE),
  setAgeVerified: (v: boolean) => setBool(KEY_AGE, v),
  getOnboarded: () => getBool(KEY_ONBOARDED),
  setOnboarded: (v: boolean) => setBool(KEY_ONBOARDED, v),
  getRegion: () => SecureStore.getItemAsync(KEY_REGION),
  setRegion: (r: string) => SecureStore.setItemAsync(KEY_REGION, r),
  // Full local wipe (Settings → Erase my data also drops the SQLite tables).
  async eraseAll(): Promise<void> {
    for (const k of [KEY_ENC, KEY_DISCLAIMER, KEY_AGE, KEY_ONBOARDED, KEY_REGION]) {
      await SecureStore.deleteItemAsync(k);
    }
  },
};
