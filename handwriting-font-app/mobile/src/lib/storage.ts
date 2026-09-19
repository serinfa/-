import AsyncStorage from '@react-native-async-storage/async-storage';
import type { Stroke, StoredSample } from './types';

const KEY = 'handwriting-samples-v1';
const SERVER_URL_KEY = 'handwriting-server-url-v1';

async function readAll(): Promise<Record<string, StoredSample>> {
  const raw = await AsyncStorage.getItem(KEY);
  return raw ? JSON.parse(raw) : {};
}

async function writeAll(all: Record<string, StoredSample>): Promise<void> {
  await AsyncStorage.setItem(KEY, JSON.stringify(all));
}

export async function saveSample(char: string, strokes: Stroke[], cellSize: number): Promise<void> {
  const all = await readAll();
  const prevCount = all[char]?.sampleCount ?? 0;
  all[char] = { char, strokes, cellSize, sampleCount: prevCount + 1, updatedAt: new Date().toISOString() };
  await writeAll(all);
}

export async function getAllSamples(): Promise<Record<string, StoredSample>> {
  return readAll();
}

export async function deleteSample(char: string): Promise<void> {
  const all = await readAll();
  delete all[char];
  await writeAll(all);
}

export async function getServerUrl(): Promise<string> {
  return (await AsyncStorage.getItem(SERVER_URL_KEY)) || 'http://localhost:4000';
}

export async function setServerUrl(url: string): Promise<void> {
  await AsyncStorage.setItem(SERVER_URL_KEY, url);
}
