#!/usr/bin/env bash
# ============================================================
# NEXUS — One-command deploy script for Vultr VM (Ubuntu 22+)
# Run as root: bash setup.sh
# ============================================================
set -e

REPO_URL="https://github.com/AgentAhmed/nexus.git"   # <-- update this
PROJECT_DIR="/opt/nexus"

echo "============================================"
echo "  NEXUS Deployment Script"
echo "  Team: Andromeda | AI Agent Olympics 2026"
echo "============================================"

# ── 1. System packages ────────────────────────────────────────
echo "[1/6] Installing system packages..."
apt-get update -q
apt-get install -y --no-install-recommends \
    git curl docker.io docker-compose-v2 nginx certbot

# ── 2. Docker ────────────────────────────────────────────────
echo "[2/6] Configuring Docker..."
systemctl enable docker
systemctl start docker
docker --version

# ── 3. Clone / update repo ────────────────────────────────────
echo "[3/6] Cloning repository..."
if [ -d "$PROJECT_DIR" ]; then
    cd "$PROJECT_DIR" && git pull
else
    git clone "$REPO_URL" "$PROJECT_DIR"
    cd "$PROJECT_DIR"
fi

# ── 4. Environment file ───────────────────────────────────────
echo "[4/6] Setting up environment..."
if [ ! -f "$PROJECT_DIR/.env" ]; then
    cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
    echo ""
    echo "⚠️  IMPORTANT: Edit your .env file before continuing!"
    echo "   nano $PROJECT_DIR/.env"
    echo ""
    echo "   Required: GEMINI_API_KEY"
    echo "   Optional: VULTR_API_KEY, SPEECHMATICS_API_KEY, FEATHERLESS_API_KEY"
    echo ""
    read -p "Press Enter after editing .env to continue deployment..."
fi

# Get the public IP automatically
PUBLIC_IP=$(curl -s ifconfig.me)
echo "Your server IP: $PUBLIC_IP"
sed -i "s|YOUR_VULTR_IP|$PUBLIC_IP|g" "$PROJECT_DIR/.env"

# ── 5. Docker Compose build + start ──────────────────────────
echo "[5/6] Building and starting services..."
cd "$PROJECT_DIR"
docker compose pull phoenix redis 2>/dev/null || true
docker compose build --no-cache api frontend
docker compose up -d

# ── 6. Health check ───────────────────────────────────────────
echo "[6/6] Checking health..."
sleep 10
if curl -sf "http://localhost/api/health" > /dev/null 2>&1; then
    echo ""
    echo "✅  NEXUS is live!"
    echo ""
    echo "  🌐 Dashboard:     http://$PUBLIC_IP"
    echo "  🔌 API:           http://$PUBLIC_IP/api"
    echo "  🔬 Phoenix:       http://$PUBLIC_IP:6006"
    echo ""
    echo "  📋 Useful commands:"
    echo "     docker compose logs -f api        # API logs"
    echo "     docker compose logs -f frontend   # Frontend logs"
    echo "     docker compose restart api        # Restart API"
    echo "     docker compose down               # Stop everything"
else
    echo "⚠️  Service may still be starting. Check logs:"
    echo "   docker compose logs api"
fi
