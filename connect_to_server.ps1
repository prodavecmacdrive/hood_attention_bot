# PowerShell script to connect to AWS EC2 instance
# Usage: .\connect_to_server.ps1

$PEM_KEY = "attention-bot-key.pem"
$EC2_USER = "ubuntu"
$EC2_IP = "16.171.113.196"  # Replace with your actual EC2 Public IP

Write-Host "Connecting to EC2 instance..." -ForegroundColor Green
Write-Host "IP: $EC2_IP" -ForegroundColor Yellow

# Set proper permissions for PEM key (Windows)
icacls $PEM_KEY /inheritance:r 2>$null
icacls $PEM_KEY /grant:r "$($env:USERNAME):(R)" 2>$null

# Connect via SSH
ssh -i $PEM_KEY "$EC2_USER@$EC2_IP"
