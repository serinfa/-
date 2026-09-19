const express = require('express');
const cors = require('cors');
const store = require('./store');
const { buildFontFromStore, computeCoverage } = require('./fontFromStore');

const app = express();
app.use(cors({ exposedHeaders: ['X-Font-Stats'] }));
app.use(express.json({ limit: '10mb' }));

app.get('/api/health', (req, res) => res.json({ ok: true }));

// body: { char: string, cellSize: number, strokes: {x:number,y:number}[][] }
app.post('/api/samples', (req, res) => {
  const { char, cellSize, strokes } = req.body || {};
  if (typeof char !== 'string' || char.length === 0) {
    return res.status(400).json({ ok: false, error: 'char is required' });
  }
  if (!Array.isArray(strokes) || strokes.length === 0) {
    return res.status(400).json({ ok: false, error: 'strokes must be a non-empty array' });
  }
  if (!Number.isFinite(cellSize) || cellSize <= 0) {
    return res.status(400).json({ ok: false, error: 'cellSize must be a positive number' });
  }
  const saved = store.upsertSample(Array.from(char)[0], strokes, cellSize);
  res.json({ ok: true, sample: saved });
});

app.delete('/api/samples/:char', (req, res) => {
  store.deleteSample(req.params.char);
  res.json({ ok: true });
});

app.get('/api/samples', (req, res) => {
  res.json({ ok: true, samples: store.getAll() });
});

app.get('/api/coverage', (req, res) => {
  res.json({ ok: true, coverage: computeCoverage(store.getAll()) });
});

app.post('/api/build-font', (req, res) => {
  const familyName = (req.body && req.body.familyName) || 'My Handwriting';
  const all = store.getAll();
  if (Object.keys(all).length === 0) {
    return res.status(400).json({ ok: false, error: 'no samples captured yet' });
  }
  try {
    const { font, stats } = buildFontFromStore(all, { familyName });
    const buffer = Buffer.from(font.toArrayBuffer());
    res.setHeader('Content-Type', 'font/ttf');
    res.setHeader('Content-Disposition', `attachment; filename="${familyName.replace(/[^a-z0-9-_]/gi, '_')}.ttf"`);
    res.setHeader('X-Font-Stats', JSON.stringify(stats));
    res.send(buffer);
  } catch (err) {
    console.error(err);
    res.status(500).json({ ok: false, error: err.message });
  }
});

const PORT = process.env.PORT || 4000;
app.listen(PORT, '0.0.0.0', () => {
  console.log(`Handwriting font server listening on http://0.0.0.0:${PORT}`);
});
