#!/usr/bin/env bash
# ============================================================
# NEXUS — Local Setup Script (WSL / Ubuntu / Mac)
# Run: bash deploy/setup-local.sh
# ============================================================
set -e

echo ""
echo "╔══════════════════════════════════════╗"
echo "║     NEXUS Local Setup               ║"
echo "╚══════════════════════════════════════╝"
echo ""

OS=$(uname -s)

# ── 1. Python 3.11 ────────────────────────────────────────────────────────────
echo "[1/5] Checking Python..."
if ! command -v python3 &>/dev/null || python3 -c "import sys; exit(0 if sys.version_info >= (3,11) else 1)" 2>/dev/null; then
    echo "Installing Python 3.11..."
    if [ "$OS" = "Linux" ]; then
        sudo apt-get update -q && sudo apt-get install -y python3.11 python3.11-venv python3-pip
    elif [ "$OS" = "Darwin" ]; then
        brew install python@3.11
    fi
fi
python3 --version

# ── 2. Node.js 20 ────────────────────────────────────────────────────────────
echo "[2/5] Checking Node.js..."
if ! command -v node &>/dev/null || [ "$(node -v | cut -d'.' -f1 | tr -d 'v')" -lt "18" ]; then
    echo "Installing Node.js 20..."
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt-get install -y nodejs
fi
node --version

# ── 3. Docker ────────────────────────────────────────────────────────────────
echo "[3/5] Checking Docker..."
if ! command -v docker &>/dev/null; then
    echo "Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker $USER
    echo "⚠  Log out and back in for Docker group to take effect."
fi
docker --version

# ── 4. Python dependencies ────────────────────────────────────────────────────
echo "[4/5] Installing Python packages..."
pip3 install -r requirements.txt --quiet

# ── 5. Frontend dependencies ──────────────────────────────────────────────────
echo "[5/5] Installing frontend packages..."
cd frontend && npm install --silent && cd ..

# ── .env file ─────────────────────────────────────────────────────────────────
if [ ! -f .env ]; then
    cp .env.example .env
    echo ""
    echo "✅ Created .env file."
    echo ""
    echo "   Next step: add your API key to .env"
    echo "   Minimum required (free):"
    echo "     GROQ_API_KEY=   ← get free at console.groq.com"
    echo ""
    echo "   Then run: make dev"
else
    echo ".env already exists — skipping."
fi

echo ""
echo "✅ Setup complete! Commands:"
echo "   make dev        → run locally"
echo "   make docker     → run with Docker"
echo "   make demo       → test the demo endpoint"
echo ""
