// Standard Unicode Hangul syllable decomposition/composition tables.
// Syllable = SBase + (leadIndex * VCount + vowelIndex) * TCount + trailIndex
const SBase = 0xac00;
const LCount = 19;
const VCount = 21;
const TCount = 28;
const SCount = LCount * VCount * TCount;

// Compatibility Jamo (what a person actually writes as a standalone character,
// e.g. typing "ㅋㅋㅋ" or "ㅠㅠ" in casual text) in the fixed order used by the
// composition algorithm below.
const LEAD_JAMO = ['ㄱ', 'ㄲ', 'ㄴ', 'ㄷ', 'ㄸ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅃ', 'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅉ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ'];
const VOWEL_JAMO = ['ㅏ', 'ㅐ', 'ㅑ', 'ㅒ', 'ㅓ', 'ㅔ', 'ㅕ', 'ㅖ', 'ㅗ', 'ㅘ', 'ㅙ', 'ㅚ', 'ㅛ', 'ㅜ', 'ㅝ', 'ㅞ', 'ㅟ', 'ㅠ', 'ㅡ', 'ㅢ', 'ㅣ'];
// index 0 means "no final consonant"
const TRAIL_JAMO = [null, 'ㄱ', 'ㄲ', 'ㄳ', 'ㄴ', 'ㄵ', 'ㄶ', 'ㄷ', 'ㄹ', 'ㄺ', 'ㄻ', 'ㄼ', 'ㄽ', 'ㄾ', 'ㄿ', 'ㅀ', 'ㅁ', 'ㅂ', 'ㅄ', 'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ'];

// Clustered finals that aren't written standalone in casual text; decompose
// them into the two consonants that make them up so we can synthesize from
// jamo the user *has* written.
const TRAIL_CLUSTER_PARTS = {
  'ㄳ': ['ㄱ', 'ㅅ'], 'ㄵ': ['ㄴ', 'ㅈ'], 'ㄶ': ['ㄴ', 'ㅎ'],
  'ㄺ': ['ㄹ', 'ㄱ'], 'ㄻ': ['ㄹ', 'ㅁ'], 'ㄼ': ['ㄹ', 'ㅂ'],
  'ㄽ': ['ㄹ', 'ㅅ'], 'ㄾ': ['ㄹ', 'ㅌ'], 'ㄿ': ['ㄹ', 'ㅍ'],
  'ㅀ': ['ㄹ', 'ㅎ'], 'ㅄ': ['ㅂ', 'ㅅ'],
};

// Vowels drawn mostly as a vertical stroke to the right of the initial
// consonant (가, 나, ...) vs. mostly horizontal, drawn under it (고, 노, ...)
// vs. a combined diagonal shape (과, 눠, ...). This drives the layout grid
// used when synthesizing a syllable that wasn't written as a whole.
const VOWEL_ORIENTATION = {
  'ㅏ': 'vertical', 'ㅐ': 'vertical', 'ㅑ': 'vertical', 'ㅒ': 'vertical',
  'ㅓ': 'vertical', 'ㅔ': 'vertical', 'ㅕ': 'vertical', 'ㅖ': 'vertical', 'ㅣ': 'vertical',
  'ㅗ': 'horizontal', 'ㅛ': 'horizontal', 'ㅜ': 'horizontal', 'ㅠ': 'horizontal', 'ㅡ': 'horizontal',
  'ㅘ': 'combined', 'ㅙ': 'combined', 'ㅚ': 'combined', 'ㅝ': 'combined',
  'ㅞ': 'combined', 'ㅟ': 'combined', 'ㅢ': 'combined',
};

function isHangulSyllable(char) {
  const cp = char.codePointAt(0);
  return cp >= SBase && cp < SBase + SCount;
}

function decomposeSyllable(char) {
  const cp = char.codePointAt(0);
  if (cp < SBase || cp >= SBase + SCount) return null;
  const sIndex = cp - SBase;
  const lIndex = Math.floor(sIndex / (VCount * TCount));
  const vIndex = Math.floor((sIndex % (VCount * TCount)) / TCount);
  const tIndex = sIndex % TCount;
  return {
    lead: LEAD_JAMO[lIndex],
    vowel: VOWEL_JAMO[vIndex],
    trail: TRAIL_JAMO[tIndex],
    orientation: VOWEL_ORIENTATION[VOWEL_JAMO[vIndex]],
  };
}

function composeSyllable(lead, vowel, trail) {
  const lIndex = LEAD_JAMO.indexOf(lead);
  const vIndex = VOWEL_JAMO.indexOf(vowel);
  const tIndex = trail ? TRAIL_JAMO.indexOf(trail) : 0;
  if (lIndex < 0 || vIndex < 0 || tIndex < 0) return null;
  const cp = SBase + (lIndex * VCount + vIndex) * TCount + tIndex;
  return String.fromCodePoint(cp);
}

module.exports = {
  LEAD_JAMO,
  VOWEL_JAMO,
  TRAIL_JAMO,
  TRAIL_CLUSTER_PARTS,
  VOWEL_ORIENTATION,
  isHangulSyllable,
  decomposeSyllable,
  composeSyllable,
};
