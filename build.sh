#!/usr/bin/env bash
set -euo pipefail

echo "=========================================="
echo "  ADX-Auto Build Script (for Render)"
echo "=========================================="

# Navigate to project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

echo ""
echo "[1/5] Installing Python dependencies..."
cd "$PROJECT_ROOT/backend"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo ""
echo "[2/5] Checking Node.js..."
cd "$PROJECT_ROOT"
if ! command -v node &> /dev/null; then
    echo "ERROR: Node.js is not installed or not in PATH"
    echo "Please ensure NODE_VERSION env var is set in render.yaml"
    exit 1
fi
echo "Node version: $(node -v)"
echo "npm version: $(npm -v)"

echo ""
echo "[3/5] Installing Node.js dependencies for frontend..."
cd "$PROJECT_ROOT/frontend"
npm install --no-audit --no-fund --loglevel=error || npm install --no-audit --no-fund

echo ""
echo "[4/5] Building Vue3 frontend (production)..."
npm run build

echo ""
echo "[5/5] Verifying frontend dist..."
cd "$PROJECT_ROOT"
if [ -d "frontend/dist" ] && [ -f "frontend/dist/index.html" ]; then
    DIST_SIZE=$(du -sh frontend/dist 2>/dev/null | cut -f1 || echo "N/A")
    echo "Frontend build successful! Size: ${DIST_SIZE}"
    ls -la frontend/dist/
else
    echo "ERROR: Frontend build failed - dist/index.html not found"
    exit 1
fi

echo ""
echo "=========================================="
echo "  Build complete ✓"
echo "=========================================="
echo ""
echo "Ready to start: gunicorn -c gunicorn_config.py run:app"
echo ""
