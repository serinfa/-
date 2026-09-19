const fs = require('fs');
const path = require('path');
const opentype = require('opentype.js');
const { strokesToUnitContours } = require('../src/strokeOutline');
const { synthesizeSyllableContours, buildFont } = require('../src/fontBuilder');
const hangul = require('../src/hangul');

const CELL = 100;

// Synthetic strokes approximating how someone would draw each jamo inside a
// 100x100 writing cell (pixel coords, y-down, as a touchscreen would report).
const rawStrokes = {
  'ㄱ': [[{ x: 20, y: 20 }, { x: 78, y: 20 }, { x: 78, y: 82 }]],
  'ㅏ': [
    [{ x: 45, y: 10 }, { x: 45, y: 90 }],
    [{ x: 45, y: 48 }, { x: 78, y: 48 }],
  ],
  'ㄴ': [[{ x: 22, y: 15 }, { x: 22, y: 82 }, { x: 82, y: 82 }]],
  'ㅇ': [
    // a roughly circular closed stroke (explicitly returns to its start point,
    // the way a finger lifting off after tracing a loop would)
    (() => {
      const pts = Array.from({ length: 24 }, (_, i) => {
        const a = (i / 24) * Math.PI * 2;
        return { x: 50 + Math.cos(a) * 30, y: 50 + Math.sin(a) * 30 };
      });
      pts.push({ x: pts[0].x, y: pts[0].y });
      return pts;
    })(),
  ],
};

const unitContoursByChar = new Map();
for (const [char, strokes] of Object.entries(rawStrokes)) {
  unitContoursByChar.set(char, strokesToUnitContours(strokes, CELL));
}

function getJamoContours(jamo) {
  return unitContoursByChar.get(jamo) || null;
}

function assert(cond, msg) {
  if (!cond) throw new Error('FAIL: ' + msg);
  console.log('ok  -', msg);
}

// 1. direct capture sanity: contours should be well-formed polygons
for (const [char, contours] of unitContoursByChar.entries()) {
  assert(contours.length >= 1, `${char} produced at least one contour`);
  for (const c of contours) assert(c.length >= 3, `${char} contour has >=3 points`);
}
assert(unitContoursByChar.get('ㅇ').length === 2, 'closed stroke ㅇ produced an outer+inner (ring) contour pair');

// 2. compose 가 (ㄱ+ㅏ, no trail) from jamo that were never written as a whole syllable
const ga = synthesizeSyllableContours('ㄱ', 'ㅏ', null, getJamoContours);
assert(ga && ga.length >= 2, '가 synthesized from ㄱ + ㅏ');

// 3. compose 간 (ㄱ+ㅏ+ㄴ, with trail)
const gan = synthesizeSyllableContours('ㄱ', 'ㅏ', 'ㄴ', getJamoContours);
assert(gan && gan.length >= 3, '간 synthesized from ㄱ + ㅏ + ㄴ');

// 4. missing jamo -> composition correctly returns null instead of guessing
const missing = synthesizeSyllableContours('ㅁ', 'ㅏ', null, getJamoContours);
assert(missing === null, 'composing with an uncaptured jamo (ㅁ) returns null');

// 5. round-trip decompose/compose against the standard Unicode algorithm
const decoded = hangul.decomposeSyllable('간');
assert(decoded.lead === 'ㄱ' && decoded.vowel === 'ㅏ' && decoded.trail === 'ㄴ', 'decomposeSyllable(간) matches expected jamo');
assert(hangul.composeSyllable('ㄱ', 'ㅏ', 'ㄴ') === '간', 'composeSyllable(ㄱ,ㅏ,ㄴ) === 간');

// 6. build an actual .ttf and parse it back
const glyphMap = new Map();
glyphMap.set('ㄱ', unitContoursByChar.get('ㄱ'));
glyphMap.set('ㅏ', unitContoursByChar.get('ㅏ'));
glyphMap.set('ㅇ', unitContoursByChar.get('ㅇ'));
glyphMap.set('가', ga);
glyphMap.set('간', gan);

const font = buildFont(glyphMap, { familyName: 'MyHandwritingTest' });
const outPath = path.join(__dirname, 'output-test-font.ttf');
fs.writeFileSync(outPath, Buffer.from(font.toArrayBuffer()));
assert(fs.existsSync(outPath), '.ttf file written to disk');

const fileBuffer = fs.readFileSync(outPath);
const arrayBuffer = fileBuffer.buffer.slice(fileBuffer.byteOffset, fileBuffer.byteOffset + fileBuffer.byteLength);
const reparsed = opentype.parse(arrayBuffer);
assert(reparsed.charToGlyphIndex('가') !== 0, 'reparsed font has a real glyph for 가 (not .notdef)');
assert(reparsed.charToGlyphIndex('간') !== 0, 'reparsed font has a real glyph for 간');
assert(reparsed.charToGlyphIndex('ㄱ') !== 0, 'reparsed font has a real glyph for ㄱ');
const missingGlyph = reparsed.charToGlyphIndex('힣');
assert(missingGlyph === 0, 'uncaptured/unsynthesized syllable 힣 correctly falls back to .notdef');

console.log('\nAll checks passed. Font written to', outPath);
