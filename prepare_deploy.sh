#!/bin/bash
# Quick setup script - Run this on your local machine to prepare files

echo "🔧 Preparing deployment files..."

# Check if .pem key exists
if [ ! -f "attention-bot-key.pem" ]; then
    echo "❌ Error: attention-bot-key.pem not found!"
    echo "Please place your EC2 key file in the project root."
    exit 1
fi

echo "✅ PEM key found"

# Check if EC2 IP is configured
if grep -q "YOUR_EC2_PUBLIC_IP" connect_to_server.ps1; then
    echo ""
    echo "⚠️  Please edit connect_to_server.ps1:"
    echo "   Replace 'YOUR_EC2_PUBLIC_IP' with your actual EC2 IP address"
    echo ""
    read -p "Press Enter after editing..."
fi

echo ""
echo "✅ Ready to deploy!"
echo ""
echo "Next steps:"
echo "1. Connect to server:"
echo "   PowerShell: .\connect_to_server.ps1"
echo "   Or use AWS Console EC2 Instance Connect"
echo ""
echo "2. On the server, run:"
echo "   curl -o deploy.sh https://raw.githubusercontent.com/prodavecmacdrive/hood_attention_bot/server-deployment/deploy_on_server.sh && chmod +x deploy.sh && ./deploy.sh"
echo ""
