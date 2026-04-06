const express = require('express');
const multer  = require('multer');
const cors    = require('cors');
const path    = require('path');
const fs      = require('fs');

const app  = express();
const PORT = process.env.PORT || 3000;

// ── In-memory store ───────────────────────────────────────────────────────────
const db     = new Map();   // id -> item
let   nextId = 1;

function makeItem(fields) {
    return {
        id:          nextId++,
        name:        fields.name,
        category:    fields.category    || 'Uncategorized',
        description: fields.description || '',
        price:       parseFloat(fields.price) || 0,
        currency:    'USD',
        modelPath:   fields.modelPath   || null,
        thumbnail:   fields.thumbnail   || null,
        allergens:   fields.allergens   || [],
        available:   true,
        createdAt:   new Date().toISOString(),
        updatedAt:   new Date().toISOString(),
    };
}

// ── Middleware ────────────────────────────────────────────────────────────────
app.use(cors());
app.use(express.json());
app.use('/models',     express.static('uploads/models'));
app.use('/thumbnails', express.static('uploads/thumbnails'));

// Create upload directories
['uploads/models', 'uploads/thumbnails'].forEach(dir => {
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
});

// ── Multer ────────────────────────────────────────────────────────────────────
const storage = multer.diskStorage({
    destination: (_req, file, cb) => {
        cb(null, file.mimetype.includes('image') ? 'uploads/thumbnails' : 'uploads/models');
    },
    filename: (_req, file, cb) => {
        cb(null, Date.now() + '-' + Math.round(Math.random() * 1e9) + path.extname(file.originalname));
    }
});

const upload = multer({
    storage,
    limits: { fileSize: 50 * 1024 * 1024 },
    fileFilter: (_req, file, cb) => {
        const allowed = ['.glb', '.gltf', '.jpg', '.jpeg', '.png'];
        allowed.includes(path.extname(file.originalname).toLowerCase())
            ? cb(null, true)
            : cb(new Error('Only GLB, GLTF, JPG, PNG allowed.'));
    }
});

// ── Routes ────────────────────────────────────────────────────────────────────

// GET /api/menu
app.get('/api/menu', (_req, res) => {
    const { category } = _req.query;
    let items = [...db.values()].reverse();
    if (category) items = items.filter(i => i.category === category);
    res.json({ success: true, count: items.length, data: items });
});

// GET /api/menu/:id
app.get('/api/menu/:id', (req, res) => {
    const item = db.get(parseInt(req.params.id));
    if (!item) return res.status(404).json({ success: false, message: 'Menu item not found' });
    res.json({ success: true, data: item });
});

// POST /api/menu
app.post('/api/menu', upload.fields([
    { name: 'model', maxCount: 1 },
    { name: 'thumbnail', maxCount: 1 }
]), (req, res) => {
    const { name, category, description, price, allergens } = req.body;

    if (!req.files?.model) {
        return res.status(400).json({ success: false, message: '3D model file is required' });
    }

    const item = makeItem({
        name,
        category,
        description,
        price,
        modelPath: `/models/${req.files.model[0].filename}`,
        thumbnail: req.files.thumbnail ? `/thumbnails/${req.files.thumbnail[0].filename}` : null,
        allergens: allergens ? JSON.parse(allergens) : [],
    });

    db.set(item.id, item);
    res.status(201).json({ success: true, message: 'Menu item created successfully', data: item });
});

// PUT /api/menu/:id
app.put('/api/menu/:id', (req, res) => {
    const id   = parseInt(req.params.id);
    const item = db.get(id);
    if (!item) return res.status(404).json({ success: false, message: 'Menu item not found' });

    const { name, category, description, price, allergens, available } = req.body;
    const updated = {
        ...item,
        name:        name        ?? item.name,
        category:    category    ?? item.category,
        description: description ?? item.description,
        price:       price       != null ? parseFloat(price) : item.price,
        allergens:   allergens   ?? item.allergens,
        available:   available   ?? item.available,
        updatedAt:   new Date().toISOString(),
    };

    db.set(id, updated);
    res.json({ success: true, message: 'Menu item updated successfully', data: updated });
});

// DELETE /api/menu/:id
app.delete('/api/menu/:id', (req, res) => {
    const id   = parseInt(req.params.id);
    const item = db.get(id);
    if (!item) return res.status(404).json({ success: false, message: 'Menu item not found' });

    // Delete files
    [item.modelPath, item.thumbnail].forEach(p => {
        if (p) {
            const abs = path.join(__dirname, p);
            if (fs.existsSync(abs)) fs.unlinkSync(abs);
        }
    });

    db.delete(id);
    res.json({ success: true, message: 'Menu item deleted successfully', data: item });
});

// GET /api/categories
app.get('/api/categories', (_req, res) => {
    const cats = [...new Set([...db.values()].map(i => i.category))].sort();
    res.json({ success: true, data: cats });
});

// GET /api/search
app.get('/api/search', (req, res) => {
    const q = (req.query.q || '').toLowerCase();
    if (!q) return res.status(400).json({ success: false, message: 'Search query is required' });

    const results = [...db.values()].filter(i =>
        i.name.toLowerCase().includes(q) || i.description.toLowerCase().includes(q)
    );
    res.json({ success: true, count: results.length, data: results });
});

// GET /api/health
app.get('/api/health', (_req, res) => {
    res.json({
        success: true,
        message: '3D Food Menu API is running',
        store:   `${db.size} items in memory`,
        timestamp: new Date().toISOString(),
    });
});

// Serve frontend
app.use(express.static('public'));

// Error handler
app.use((err, _req, res, _next) => {
    console.error(err.stack);
    res.status(500).json({ success: false, message: err.message });
});

// ── Start ─────────────────────────────────────────────────────────────────────
app.listen(PORT, () => {
    console.log('═══════════════════════════════════════════════════');
    console.log('  3D FOOD MENU API SERVER');
    console.log('═══════════════════════════════════════════════════');
    console.log(`  http://localhost:${PORT}`);
    console.log(`  Store: in-memory Map (resets on restart)`);
    console.log('═══════════════════════════════════════════════════');
});
