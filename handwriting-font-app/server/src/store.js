const fs = require('fs');
const path = require('path');

const DATA_FILE = path.join(__dirname, '..', 'data', 'samples.json');

function load() {
  try {
    return JSON.parse(fs.readFileSync(DATA_FILE, 'utf8'));
  } catch {
    return {};
  }
}

function save(store) {
  fs.mkdirSync(path.dirname(DATA_FILE), { recursive: true });
  fs.writeFileSync(DATA_FILE, JSON.stringify(store, null, 2));
}

// Each entry is keyed by the character itself (Object keys handle any
// Unicode codepoint fine as long as we only ever iterate, never sort/compare).
function upsertSample(char, strokes, cellSize) {
  const store = load();
  store[char] = { char, strokes, cellSize, sampleCount: (store[char]?.sampleCount || 0) + 1, updatedAt: new Date().toISOString() };
  save(store);
  return store[char];
}

function deleteSample(char) {
  const store = load();
  delete store[char];
  save(store);
}

function getAll() {
  return load();
}

module.exports = { upsertSample, deleteSample, getAll };
