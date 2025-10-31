#!/bin/bash
# Deploy script to run on EC2 server
# This script automates the deployment process

set -e  # Exit on error

echo "🚀 Starting deployment process..."

# Step 1: Update system
echo "📦 Step 1: Updating system..."
sudo apt update && sudo apt upgrade -y

# Step 2: Install dependencies
echo "📦 Step 2: Installing dependencies..."
sudo apt install -y python3 python3-pip python3-venv git htop

# Step 3: Clone repository (if not exists)
echo "📥 Step 3: Setting up repository..."
if [ ! -d "$HOME/hood_attention_bot" ]; then
    cd ~
    git clone https://github.com/prodavecmacdrive/hood_attention_bot.git
    cd hood_attention_bot
    git checkout server-deployment
else
    echo "Repository already exists, updating..."
    cd ~/hood_attention_bot
    git fetch origin
    git checkout server-deployment
    git pull origin server-deployment
fi

# Step 4: Setup virtual environment
echo "🐍 Step 4: Setting up Python virtual environment..."
cd ~/hood_attention_bot
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Step 5: Setup .env file
echo "⚙️  Step 5: Checking .env file..."
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found!"
    echo "Creating .env from template..."
    cp .env.example .env
    echo "❗ Please edit .env file with your credentials:"
    echo "   nano .env"
    echo ""
    echo "Required variables:"
    echo "  - API_ID"
    echo "  - API_HASH"
    echo "  - PHONE"
    echo "  - BOT_TOKEN"
    echo "  - CHANNELS"
    echo "  - KEYWORDS"
    echo "  - TARGET_CHANNEL"
    echo ""
    read -p "Press Enter after editing .env file..."
else
    echo "✅ .env file exists"
fi

# Step 6: Test bot (manual authorization needed on first run)
echo "🤖 Step 6: Testing bot..."
echo "⚠️  If this is the first run, you'll need to authorize with Telegram"
echo "Press Ctrl+C after successful authorization to continue with service setup"
source venv/bin/activate
python3 main.py &
BOT_PID=$!
echo "Bot started with PID: $BOT_PID"
echo "Waiting 30 seconds for initialization..."
sleep 30
kill $BOT_PID 2>/dev/null || true
echo "Bot test completed"

# Step 7: Setup systemd service
echo "🔧 Step 7: Setting up systemd service..."
chmod +x start.sh
sudo cp hood_bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable hood_bot

# Step 8: Start service
echo "▶️  Step 8: Starting service..."
sudo systemctl start hood_bot

# Step 9: Check status
echo "📊 Step 9: Checking service status..."
sudo systemctl status hood_bot --no-pager

echo ""
echo "✅ Deployment completed!"
echo ""
echo "Useful commands:"
echo "  - View logs: journalctl -u hood_bot -f"
echo "  - Restart bot: sudo systemctl restart hood_bot"
echo "  - Stop bot: sudo systemctl stop hood_bot"
echo "  - Check memory: free -h"
echo ""
