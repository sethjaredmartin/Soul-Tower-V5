# Soul Tower — Project Setup

## First Time Setup

### 1. Create a virtual environment

```bash
# From the soul_tower project root
python -m venv venv
```

This creates a `venv/` folder that holds a clean Python installation isolated from your system Python. You only do this once per project.

### 2. Activate the virtual environment

**Windows (Command Prompt):**
```cmd
venv\Scripts\activate
```

**Windows (PowerShell):**
```powershell
venv\Scripts\Activate.ps1
```

**Mac / Linux:**
```bash
source venv/bin/activate
```

You'll know it's active when your terminal prompt shows `(venv)` at the start.

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

This installs everything the project needs into your venv — not your system Python.

### 4. Add your sheet URLs

Open `config.py` and fill in your Google Sheet published CSV URLs:

```python
SHEET_URLS: dict[str, str] = {
    "Hero":         "https://docs.google.com/...",
    "Common Cards": "https://docs.google.com/...",
    "Legendary":    "https://docs.google.com/...",
    "Calamity":     "https://docs.google.com/...",
    "Villain":      "https://docs.google.com/...",
}
```

### 5. Run the pipeline

```bash
# Fetch all sheets and generate Lua blocks
python main.py --fresh

# Use cache (after first run)
python main.py

# Named key format (Beta)
python main.py --named

# One sheet only
python main.py --sheet Hero --named
```

---

## Daily Workflow

```bash
# 1. Activate venv (every time you open a new terminal)
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux

# 2. Run the pipeline
python main.py

# 3. When done
deactivate
```

---

## What is a Virtual Environment?

A `venv` is a self-contained Python environment for a specific project. It prevents package version conflicts between projects and keeps your system Python clean.

- `venv/` — created by `python -m venv venv`, never committed to git
- `requirements.txt` — the list of packages the project needs, committed to git
- `pip install -r requirements.txt` — installs those packages into the active venv

If you delete `venv/` or set up on a new machine, just re-run steps 1-3.

---

## What is `__init__.py`?

Every folder in the `src/` directory contains an `__init__.py` file. This file does two things:

1. **Marks the folder as a Python package** — without it, Python can't import from that folder using dot notation like `from src.models import Hero`

2. **Exposes a public API** — the `src/models/__init__.py` imports from all the model files so you can write `from src.models import Hero` instead of `from src.models.hero import Hero`. One import instead of many.

You rarely need to edit `__init__.py` files. When you add a new model class, add its import to `src/models/__init__.py` so it's available from the package root.

---

## Adding to `.gitignore`

Make sure your `.gitignore` includes:

```
venv/
__pycache__/
*.pyc
data/cache/
```

The cache is local data — it should not be committed. Regenerate it with `python main.py --fresh`.
