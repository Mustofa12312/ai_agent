#!/bin/bash
# ============================================================
# setup.sh — One-click setup for AI Agent
# ============================================================
set -e

VENV_DIR=".venv"
PYTHON="python3"

echo "🤖 AI Agent Setup"
echo "=================================="

# Install python3-venv if needed
if ! $PYTHON -m venv --help &>/dev/null 2>&1; then
    echo "⚠️  Installing python3-venv..."
    sudo apt install -y python3-venv python3-full
fi

# Create virtual environment
if [ ! -d "$VENV_DIR" ]; then
    echo "📦 Creating virtual environment..."
    $PYTHON -m venv $VENV_DIR
fi

# Activate and install
echo "📥 Installing dependencies..."
$VENV_DIR/bin/pip install --upgrade pip -q
$VENV_DIR/bin/pip install -r requirements.txt -q

# Copy .env if not exists
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo ""
    echo "⚠️  File .env dibuat dari template!"
    echo "   → Edit .env dan masukkan GEMINI_API_KEY kamu"
fi

echo ""
echo "✅ Setup selesai!"
echo ""
echo "📋 Langkah selanjutnya:"
echo "  1. Edit .env → tambahkan GEMINI_API_KEY"
echo "  2. Jalankan: source .venv/bin/activate"
echo "  3. Jalankan: python main.py"
echo ""
echo "🚀 Atau gunakan shortcut:"
echo "  source .venv/bin/activate && python main.py"
