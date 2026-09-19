// Turns raw pen strokes (as captured from a touchscreen: an array of
// {x,y} points per finger-down..finger-up segment) into filled polygon
// contours, as if the stroke were drawn with a felt-tip pen of a given
// width. Output contours are ready to hand to opentype.js as glyph paths.

function normalize(v) {
  const len = Math.hypot(v.x, v.y) || 1;
  return { x: v.x / len, y: v.y / len };
}

function sub(a, b) {
  return { x: a.x - b.x, y: a.y - b.y };
}

function add(a, b, scale = 1) {
  return { x: a.x + b.x * scale, y: a.y + b.y * scale };
}

// Light smoothing to reduce touchscreen jitter without losing corners.
function smooth(points) {
  if (points.length < 3) return points;
  const out = [points[0]];
  for (let i = 1; i < points.length - 1; i++) {
    const p0 = points[i - 1];
    const p1 = points[i];
    const p2 = points[i + 1];
    out.push({ x: (p0.x + 2 * p1.x + p2.x) / 4, y: (p0.y + 2 * p1.y + p2.y) / 4 });
  }
  out.push(points[points.length - 1]);
  return out;
}

function dedupe(points) {
  const out = [];
  for (const p of points) {
    const last = out[out.length - 1];
    if (!last || Math.hypot(p.x - last.x, p.y - last.y) > 0.01) out.push(p);
  }
  return out;
}

function perVertexNormals(points) {
  const segNormals = [];
  for (let i = 0; i < points.length - 1; i++) {
    const d = normalize(sub(points[i + 1], points[i]));
    segNormals.push({ x: -d.y, y: d.x });
  }
  const normals = [];
  for (let i = 0; i < points.length; i++) {
    if (i === 0) normals.push(segNormals[0]);
    else if (i === points.length - 1) normals.push(segNormals[segNormals.length - 1]);
    else normals.push(normalize(add(segNormals[i - 1], segNormals[i])));
  }
  return normals;
}

function signedArea(points) {
  let a = 0;
  for (let i = 0; i < points.length; i++) {
    const p = points[i];
    const q = points[(i + 1) % points.length];
    a += p.x * q.y - q.x * p.y;
  }
  return a / 2;
}

function circleContour(center, radius, segments = 16) {
  const pts = [];
  for (let i = 0; i < segments; i++) {
    const a = (i / segments) * Math.PI * 2;
    pts.push({ x: center.x + Math.cos(a) * radius, y: center.y + Math.sin(a) * radius });
  }
  return pts;
}

function arcContour(center, from, to, radius, segments = 6) {
  let a0 = Math.atan2(from.y - center.y, from.x - center.x);
  let a1 = Math.atan2(to.y - center.y, to.x - center.x);
  let diff = a1 - a0;
  while (diff <= -Math.PI) diff += Math.PI * 2;
  while (diff > Math.PI) diff -= Math.PI * 2;
  const pts = [];
  for (let i = 1; i < segments; i++) {
    const a = a0 + (diff * i) / segments;
    pts.push({ x: center.x + Math.cos(a) * radius, y: center.y + Math.sin(a) * radius });
  }
  return pts;
}

/**
 * @param {{x:number,y:number}[]} rawPoints single stroke, pixel coords
 * @param {number} halfWidth pen half-width in the same pixel units
 * @returns {{x:number,y:number}[][]} one or two closed contours
 */
function strokeToContours(rawPoints, halfWidth) {
  let points = dedupe(rawPoints);
  if (points.length === 0) return [];
  if (points.length === 1) {
    return [circleContour(points[0], halfWidth)];
  }
  points = smooth(points);

  // Users rarely land a loop-closing stroke back on the exact start pixel,
  // so be fairly forgiving about what counts as "closed".
  const closed = points.length > 3 && Math.hypot(points[0].x - points[points.length - 1].x, points[0].y - points[points.length - 1].y) < halfWidth * 4;
  const normals = perVertexNormals(points);
  const left = points.map((p, i) => add(p, normals[i], halfWidth));
  const right = points.map((p, i) => add(p, normals[i], -halfWidth));

  if (closed) {
    const outerIsLeft = Math.abs(signedArea(left)) >= Math.abs(signedArea(right));
    const outer = outerIsLeft ? left : right;
    let inner = outerIsLeft ? right : left;
    if (Math.sign(signedArea(outer)) === Math.sign(signedArea(inner))) {
      inner = inner.slice().reverse();
    }
    return [outer, inner];
  }

  const startCap = arcContour(points[0], right[0], left[0], halfWidth);
  const endCap = arcContour(points[points.length - 1], left[left.length - 1], right[right.length - 1], halfWidth);
  const contour = [...left, ...endCap, ...right.slice().reverse(), ...startCap];
  return [contour];
}

/**
 * @param {{x:number,y:number}[][]} strokes strokes in pixel coords within [0,cellSize]
 * @param {number} cellSize the writing cell's size in pixels (square)
 * @param {number} strokeWidthRatio pen width as a fraction of cellSize
 * @returns {{x:number,y:number}[][]} contours normalized to unit square, y-up, origin bottom-left
 */
function strokesToUnitContours(strokes, cellSize, strokeWidthRatio = 0.06) {
  const halfWidth = (cellSize * strokeWidthRatio) / 2;
  const contours = [];
  for (const stroke of strokes) {
    for (const contour of strokeToContours(stroke, halfWidth)) {
      contours.push(
        contour.map((p) => ({ x: p.x / cellSize, y: 1 - p.y / cellSize }))
      );
    }
  }
  return contours;
}

module.exports = { strokeToContours, strokesToUnitContours };
