const { strokesToUnitContours } = require('./strokeOutline');
const { synthesizeSyllableContours, buildFont } = require('./fontBuilder');
const hangul = require('./hangul');

function isCompatJamo(char) {
  return hangul.LEAD_JAMO.includes(char) || hangul.VOWEL_JAMO.includes(char) || hangul.TRAIL_JAMO.includes(char);
}

function capturedUnitContours(store) {
  const map = new Map();
  for (const [char, sample] of Object.entries(store)) {
    map.set(char, strokesToUnitContours(sample.strokes, sample.cellSize));
  }
  return map;
}

/**
 * Builds the full glyph set: every directly captured character, plus every
 * Hangul syllable that can be synthesized from the jamo the user has
 * captured so far (a direct capture of that same syllable always wins).
 */
function resolveGlyphs(store) {
  const captured = capturedUnitContours(store);
  const glyphs = new Map(captured);

  const capturedLeads = hangul.LEAD_JAMO.filter((j) => captured.has(j));
  const capturedVowels = hangul.VOWEL_JAMO.filter((j) => captured.has(j));
  const capturedTrails = hangul.TRAIL_JAMO.filter((j) => j && captured.has(j));

  const getJamoContours = (jamo) => captured.get(jamo) || null;
  let synthesizedCount = 0;

  for (const lead of capturedLeads) {
    for (const vowel of capturedVowels) {
      for (const trail of [null, ...capturedTrails]) {
        const syllable = hangul.composeSyllable(lead, vowel, trail);
        if (!syllable || glyphs.has(syllable)) continue; // direct capture wins
        const contours = synthesizeSyllableContours(lead, vowel, trail, getJamoContours);
        if (contours) {
          glyphs.set(syllable, contours);
          synthesizedCount++;
        }
      }
    }
  }

  return { glyphs, synthesizedCount, capturedCount: captured.size };
}

function buildFontFromStore(store, meta) {
  const { glyphs, synthesizedCount, capturedCount } = resolveGlyphs(store);
  const font = buildFont(glyphs, meta);
  return { font, stats: { capturedCount, synthesizedCount, totalGlyphs: glyphs.size } };
}

function computeCoverage(store) {
  const chars = Object.keys(store);
  const leads = hangul.LEAD_JAMO.filter((j) => chars.includes(j));
  const vowels = hangul.VOWEL_JAMO.filter((j) => chars.includes(j));
  const trails = hangul.TRAIL_JAMO.filter((j) => j && chars.includes(j));
  const syllables = chars.filter((c) => hangul.isHangulSyllable(c));
  const other = chars.filter((c) => !isCompatJamo(c) && !hangul.isHangulSyllable(c));
  const { synthesizedCount, glyphs } = resolveGlyphs(store);

  return {
    totalCapturedCharacters: chars.length,
    hangul: {
      leadsCaptured: leads,
      leadsTotal: hangul.LEAD_JAMO.length,
      vowelsCaptured: vowels,
      vowelsTotal: hangul.VOWEL_JAMO.length,
      trailsCaptured: trails,
      trailsTotal: hangul.TRAIL_JAMO.length - 1,
      syllablesCapturedDirectly: syllables.length,
      syllablesSynthesizable: synthesizedCount,
      totalUsableSyllables: syllables.length + synthesizedCount,
    },
    otherCharacters: other,
    totalGlyphsInFont: glyphs.size,
  };
}

module.exports = { buildFontFromStore, computeCoverage, resolveGlyphs };
