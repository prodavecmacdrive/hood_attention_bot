#!/bin/bash
# Final setup script - run this on EC2 server after filling .env file

set -e

echo "🚀 Final setup script starting..."

# Step 1: Update repository
echo "📥 Step 1: Updating repository..."
cd ~/hood_attention_bot
git pull origin server-deployment

# Step 2: Create .env file if not exists
echo "⚙️  Step 2: Setting up .env file..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo ""
    echo "❗ IMPORTANT: Edit .env file with your real credentials:"
    echo "   nano ~/hood_attention_bot/.env"
    echo ""
    echo "Required variables:"
    echo "  - API_ID (from my.telegram.org)"
    echo "  - API_HASH (from my.telegram.org)"
    echo "  - PHONE (your phone number with +)"
    echo "  - BOT_TOKEN (from @BotFather)"
    echo "  - CHANNELS (channels to monitor)"
    echo "  - KEYWORDS (keywords to filter)"
    echo "  - TARGET_CHANNEL (your channel for alerts)"
    echo ""
    read -p "Press Enter after editing .env file to continue..."
else
    echo "✅ .env file already exists"
    read -p "Do you want to edit it? (y/N): " edit_env
    if [ "$edit_env" = "y" ] || [ "$edit_env" = "Y" ]; then
        nano .env
    fi
fi

# Step 3: Fix systemd service paths
echo "🔧 Step 3: Fixing systemd service paths..."
cd ~/hood_attention_bot
sed -i 's|/home/ubuntu/attention_bot|/home/ubuntu/hood_attention_bot|g' hood_bot.service

# Step 4: Setup systemd service
echo "🔧 Step 4: Setting up systemd service..."
chmod +x start.sh
sudo cp hood_bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable hood_bot

echo ""
echo "✅ Setup completed!"
echo ""
echo "📋 Next steps:"
echo ""
echo "1) First authorization (IMPORTANT - do this once):"
echo "   cd ~/hood_attention_bot"
echo "   source venv/bin/activate"
echo "   python3 main.py"
echo "   - Enter Telegram code from your phone"
echo "   - Enter 2FA password if you have it"
echo "   - Press Ctrl+C after 'session' file is created"
echo ""
echo "2) Start the service:"
echo "   sudo systemctl start hood_bot"
echo ""
echo "3) Check logs:"
echo "   journalctl -u hood_bot -f"
echo ""
echo "4) Check status:"
echo "   sudo systemctl status hood_bot"
echo ""
