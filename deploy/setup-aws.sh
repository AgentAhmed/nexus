#!/usr/bin/env bash
# ============================================================
# NEXUS — AWS EC2 Deployment Script
# Tested on: Ubuntu 22.04 LTS (ami-0c7217cdde317cfec)
# Instance:  t2.micro (free tier) or t3.small (recommended)
# Run as root: bash deploy/setup-aws.sh
# ============================================================
set -e

REPO_URL="${REPO_URL:-https://github.com/YOUR_USERNAME/nexus.git}"
PROJECT_DIR="/opt/nexus"
DOMAIN="${DOMAIN:-}"   # optional: set to your domain for HTTPS

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║     NEXUS AWS EC2 Deployment             ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# ── 1. System update ──────────────────────────────────────────────────────────
echo "[1/8] System update..."
apt-get update -q && apt-get upgrade -y -q

# ── 2. Swap file (critical for t2.micro — adds 2GB virtual RAM) ───────────────
echo "[2/8] Setting up swap (needed for t2.micro)..."
if [ ! -f /swapfile ]; then
    fallocate -l 2G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
    echo "✅ 2GB swap created"
else
    echo "Swap already exists"
fi
free -h

# ── 3. Docker ────────────────────────────────────────────────────────────────
echo "[3/8] Installing Docker..."
curl -fsSL https://get.docker.com | sh
systemctl enable docker && systemctl start docker
docker --version

# ── 4. Clone repo ────────────────────────────────────────────────────────────
echo "[4/8] Cloning NEXUS..."
if [ -d "$PROJECT_DIR" ]; then
    cd "$PROJECT_DIR" && git pull
else
    git clone "$REPO_URL" "$PROJECT_DIR"
    cd "$PROJECT_DIR"
fi

# ── 5. Environment setup ──────────────────────────────────────────────────────
echo "[5/8] Environment setup..."
cd "$PROJECT_DIR"
if [ ! -f .env ]; then
    cp .env.example .env
    PUBLIC_IP=$(curl -s ifconfig.me 2>/dev/null || echo "YOUR_IP")
    sed -i "s|PUBLIC_URL=http://localhost|PUBLIC_URL=http://$PUBLIC_IP|" .env
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  REQUIRED: Add your API key to .env"
    echo "  Your server IP: $PUBLIC_IP"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    nano .env   # opens editor — add GROQ_API_KEY at minimum
fi

# ── 6. Build + start (free tier optimised) ────────────────────────────────────
echo "[6/8] Building Docker images (takes 3-5 min)..."
docker compose -f docker-compose.free.yml build --no-cache

echo "[7/8] Starting services..."
docker compose -f docker-compose.free.yml up -d

# ── 8. Firewall ───────────────────────────────────────────────────────────────
echo "[8/8] Opening firewall..."
# AWS: also open ports 8000, 3000, 80 in Security Group via console
ufw allow 22 2>/dev/null || true
ufw allow 80 2>/dev/null || true
ufw allow 8000 2>/dev/null || true
ufw allow 3000 2>/dev/null || true

# ── Done ──────────────────────────────────────────────────────────────────────
sleep 8
PUBLIC_IP=$(curl -s ifconfig.me 2>/dev/null || echo "YOUR_IP")

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if curl -sf "http://localhost:8000/api/health" >/dev/null 2>&1; then
    echo "✅  NEXUS is live!"
    echo ""
    echo "    API:       http://$PUBLIC_IP:8000"
    echo "    Dashboard: http://$PUBLIC_IP:3000"
    echo ""
    echo "    Useful commands:"
    echo "      docker compose -f docker-compose.free.yml logs -f api"
    echo "      docker compose -f docker-compose.free.yml restart api"
    echo "      docker compose -f docker-compose.free.yml down"
    echo ""
    echo "    Test the demo:"
    echo "      curl -X POST http://$PUBLIC_IP:8000/api/demo"
else
    echo "⚠  Still starting. Check logs:"
    echo "    docker compose -f docker-compose.free.yml logs api"
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
