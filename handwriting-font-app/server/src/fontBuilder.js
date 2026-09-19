const opentype = require('opentype.js');
const hangul = require('./hangul');

const UNITS_PER_EM = 1000;
const ASCENDER = 800;
const DESCENDER = -200;

// Sub-boxes (in the 0..1 unit square, x right, y up) that a lead/vowel/trail
// jamo's own unit-square drawing gets rescaled into when synthesizing a
// syllable the user never wrote as a whole.
function layoutFor(orientation, hasTrail) {
  let lead, vowel;
  if (orientation === 'horizontal') {
    lead = { x0: 0, x1: 1, y0: 0.5, y1: 1 };
    vowel = { x0: 0, x1: 1, y0: 0, y1: 0.52 };
  } else if (orientation === 'combined') {
    lead = { x0: 0, x1: 0.5, y0: 0.45, y1: 1 };
    vowel = { x0: 0.32, x1: 1, y0: 0, y1: 1 };
  } else {
    lead = { x0: 0, x1: 0.5, y0: 0, y1: 1 };
    vowel = { x0: 0.46, x1: 1, y0: 0, y1: 1 };
  }
  if (!hasTrail) return { lead, vowel, trail: null };

  const compress = (box) => ({ x0: box.x0, x1: box.x1, y0: 0.34 + box.y0 * 0.66, y1: 0.34 + box.y1 * 0.66 });
  return {
    lead: compress(lead),
    vowel: compress(vowel),
    trail: { x0: 0, x1: 1, y0: 0, y1: 0.32 },
  };
}

function placeInBox(unitContours, box) {
  const w = box.x1 - box.x0;
  const h = box.y1 - box.y0;
  return unitContours.map((contour) =>
    contour.map((p) => ({ x: box.x0 + p.x * w, y: box.y0 + p.y * h }))
  );
}

/**
 * Synthesizes unit-square contours for a Hangul syllable from its jamo
 * components, when the syllable itself was never captured directly.
 * @param {string} lead compatibility jamo, e.g. 'ㄱ'
 * @param {string} vowel compatibility jamo, e.g. 'ㅏ'
 * @param {string|null} trail compatibility jamo or null
 * @param {(jamoChar:string) => ({x:number,y:number}[][]|null)} getJamoContours
 * @returns {{x:number,y:number}[][]|null}
 */
function synthesizeSyllableContours(lead, vowel, trail, getJamoContours) {
  const leadShape = getJamoContours(lead);
  const vowelShape = getJamoContours(vowel);
  if (!leadShape || !vowelShape) return null;

  let trailShape = null;
  if (trail) {
    trailShape = getJamoContours(trail);
    if (!trailShape) {
      const parts = hangul.TRAIL_CLUSTER_PARTS[trail];
      if (parts) {
        const [a, b] = parts;
        const shapeA = getJamoContours(a);
        const shapeB = getJamoContours(b);
        if (shapeA && shapeB) {
          trailShape = [
            ...placeInBox(shapeA, { x0: 0, x1: 0.48, y0: 0, y1: 1 }),
            ...placeInBox(shapeB, { x0: 0.52, x1: 1, y0: 0, y1: 1 }),
          ];
        }
      }
      if (!trailShape) return null;
    }
  }

  const orientation = hangul.VOWEL_ORIENTATION[vowel];
  const layout = layoutFor(orientation, !!trail);
  const contours = [
    ...placeInBox(leadShape, layout.lead),
    ...placeInBox(vowelShape, layout.vowel),
  ];
  if (trail) contours.push(...placeInBox(trailShape, layout.trail));
  return contours;
}

function contoursToPath(unitContours) {
  const path = new opentype.Path();
  for (const contour of unitContours) {
    if (contour.length < 3) continue;
    path.moveTo(contour[0].x * UNITS_PER_EM, contour[0].y * UNITS_PER_EM);
    for (let i = 1; i < contour.length; i++) {
      path.lineTo(contour[i].x * UNITS_PER_EM, contour[i].y * UNITS_PER_EM);
    }
    path.close();
  }
  return path;
}

/**
 * @param {Map<string, {x:number,y:number}[][]>} glyphContoursByChar unit-square contours per character
 * @param {{familyName:string, styleName?:string}} meta
 */
function buildFont(glyphContoursByChar, meta) {
  const notdefPath = new opentype.Path();
  const notdefGlyph = new opentype.Glyph({
    name: '.notdef',
    unicode: 0,
    advanceWidth: UNITS_PER_EM,
    path: notdefPath,
  });

  const glyphs = [notdefGlyph];
  for (const [char, contours] of glyphContoursByChar.entries()) {
    const codepoint = char.codePointAt(0);
    glyphs.push(
      new opentype.Glyph({
        name: `uni${codepoint.toString(16).toUpperCase().padStart(4, '0')}`,
        unicode: codepoint,
        advanceWidth: UNITS_PER_EM * 1.05,
        path: contoursToPath(contours),
      })
    );
  }

  return new opentype.Font({
    familyName: meta.familyName,
    styleName: meta.styleName || 'Regular',
    unitsPerEm: UNITS_PER_EM,
    ascender: ASCENDER,
    descender: DESCENDER,
    glyphs,
  });
}

module.exports = { buildFont, synthesizeSyllableContours, UNITS_PER_EM };
