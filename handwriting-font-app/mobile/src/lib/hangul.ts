// Same tables as server/src/hangul.js, kept in sync by hand (the mobile app
// only needs these for quick local coverage estimates — the server is the
// source of truth when it actually builds the font).
export const LEAD_JAMO = ['ㄱ', 'ㄲ', 'ㄴ', 'ㄷ', 'ㄸ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅃ', 'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅉ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ'];
export const VOWEL_JAMO = ['ㅏ', 'ㅐ', 'ㅑ', 'ㅒ', 'ㅓ', 'ㅔ', 'ㅕ', 'ㅖ', 'ㅗ', 'ㅘ', 'ㅙ', 'ㅚ', 'ㅛ', 'ㅜ', 'ㅝ', 'ㅞ', 'ㅟ', 'ㅠ', 'ㅡ', 'ㅢ', 'ㅣ'];
export const TRAIL_JAMO = ['ㄱ', 'ㄲ', 'ㄳ', 'ㄴ', 'ㄵ', 'ㄶ', 'ㄷ', 'ㄹ', 'ㄺ', 'ㄻ', 'ㄼ', 'ㄽ', 'ㄾ', 'ㄿ', 'ㅀ', 'ㅁ', 'ㅂ', 'ㅄ', 'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ'];

const SBase = 0xac00;
const LCount = 19;
const VCount = 21;
const TCount = 28;
const SCount = LCount * VCount * TCount;

export function isHangulSyllable(char: string): boolean {
  const cp = char.codePointAt(0) ?? 0;
  return cp >= SBase && cp < SBase + SCount;
}

export function isCompatJamo(char: string): boolean {
  return LEAD_JAMO.includes(char) || VOWEL_JAMO.includes(char) || TRAIL_JAMO.includes(char);
}
