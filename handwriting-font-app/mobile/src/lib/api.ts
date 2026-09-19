import type { StoredSample } from './types';

export type CoverageResponse = {
  totalCapturedCharacters: number;
  hangul: {
    leadsCaptured: string[];
    leadsTotal: number;
    vowelsCaptured: string[];
    vowelsTotal: number;
    trailsCaptured: string[];
    trailsTotal: number;
    syllablesCapturedDirectly: number;
    syllablesSynthesizable: number;
    totalUsableSyllables: number;
  };
  otherCharacters: string[];
  totalGlyphsInFont: number;
};

async function request(baseUrl: string, path: string, options?: RequestInit) {
  const res = await fetch(`${baseUrl}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const body = await res.text().catch(() => '');
    throw new Error(`${res.status} ${res.statusText}: ${body}`);
  }
  return res;
}

export async function checkHealth(baseUrl: string): Promise<boolean> {
  try {
    const res = await fetch(`${baseUrl}/api/health`);
    return res.ok;
  } catch {
    return false;
  }
}

export async function syncSamples(baseUrl: string, samples: Record<string, StoredSample>): Promise<void> {
  const list = Object.values(samples).map((s) => ({ char: s.char, cellSize: s.cellSize, strokes: s.strokes }));
  for (const sample of list) {
    await request(baseUrl, '/api/samples', { method: 'POST', body: JSON.stringify(sample) });
  }
}

export async function fetchCoverage(baseUrl: string): Promise<CoverageResponse> {
  const res = await request(baseUrl, '/api/coverage');
  const json = await res.json();
  return json.coverage;
}

export async function buildFont(baseUrl: string, familyName: string): Promise<{ base64: string; stats: any }> {
  const res = await request(baseUrl, '/api/build-font', { method: 'POST', body: JSON.stringify({ familyName }) });
  const stats = JSON.parse(res.headers.get('X-Font-Stats') || '{}');
  const buffer = await res.arrayBuffer();
  const base64 = arrayBufferToBase64(buffer);
  return { base64, stats };
}

// Hermes (React Native's default JS engine) doesn't ship btoa, so encode by hand.
const BASE64_CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';

function arrayBufferToBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let out = '';
  for (let i = 0; i < bytes.length; i += 3) {
    const b0 = bytes[i];
    const b1 = bytes[i + 1];
    const b2 = bytes[i + 2];
    out += BASE64_CHARS[b0 >> 2];
    out += BASE64_CHARS[((b0 & 0x03) << 4) | (b1 === undefined ? 0 : b1 >> 4)];
    out += b1 === undefined ? '=' : BASE64_CHARS[((b1 & 0x0f) << 2) | (b2 === undefined ? 0 : b2 >> 6)];
    out += b2 === undefined ? '=' : BASE64_CHARS[b2 & 0x3f];
  }
  return out;
}
