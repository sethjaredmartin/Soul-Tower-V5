#!/bin/bash
# ============================================================
# Soul Tower Developer Kit - Setup Script
# Run this once after unpacking the archive.
# ============================================================

set -e

echo ""
echo "==================================="
echo "  Soul Tower Developer Kit Setup"
echo "==================================="
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 is required but not found."
    echo "Install Python 3.10+ and try again."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "[OK] Python $PYTHON_VERSION found"

# Create additional project directories that aren't in the kit
echo ""
echo "Creating project directories..."
mkdir -p src/models
mkdir -p src/pipeline
mkdir -p src/tts
mkdir -p src/api
mkdir -p data/cache
mkdir -p data/game_lua_data
mkdir -p assets

echo "[OK] Directory structure created"

# Install Python dependencies
echo ""
echo "Installing Python dependencies..."
cd backend
pip install -r requirements.txt
cd ..

echo "[OK] Dependencies installed"

# Initialize the SQLite database
echo ""
echo "Initializing analytics database..."
cd backend
python3 -c "
from analytics_server import init_db
init_db()
print('[OK] Database initialized at soul_tower_analytics.db')
"
cd ..

# Summary
echo ""
echo "==================================="
echo "  Setup complete!"
echo "==================================="
echo ""
echo "Next steps:"
echo ""
echo "  1. Start the analytics server:"
echo "     cd backend && python3 analytics_server.py"
echo ""
echo "  2. Verify it works:"
echo "     curl http://localhost:5050/api/health"
echo ""
echo "  3. Read CLAUDE.md for project conventions"
echo "  4. Read docs/ARCHITECTURE.md for system design"
echo ""
echo "  For TTS:"
echo "  - Board.lua goes on each player board tile"
echo "  - Global.lua + ZoneHandler.lua go in the Global script"
echo "  - See README.md for detailed TTS setup instructions"
echo ""
