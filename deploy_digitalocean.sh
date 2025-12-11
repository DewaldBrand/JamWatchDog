#!/bin/bash
# JamWatchDog - Digital Ocean Droplet Deployment Script
# Run this script on a fresh Ubuntu 22.04 droplet

set -e  # Exit on error

echo "========================================="
echo "JamWatchDog Digital Ocean Deployment"
echo "========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Please run as root (use: sudo ./deploy_digitalocean.sh)${NC}"
    exit 1
fi

echo -e "${GREEN}Step 1: Updating system packages...${NC}"
apt update && apt upgrade -y

echo -e "${GREEN}Step 2: Installing Python and dependencies...${NC}"
apt install python3 python3-pip python3-venv git nginx supervisor ufw -y

echo -e "${GREEN}Step 3: Cloning repository...${NC}"
cd /opt
if [ -d "JamWatchDog" ]; then
    echo "Directory exists, pulling latest changes..."
    cd JamWatchDog
    git pull origin main
else
    echo "Cloning repository..."
    read -p "Enter your GitHub username: " GITHUB_USER
    git clone https://github.com/$GITHUB_USER/JamWatchDog.git
    cd JamWatchDog
fi

echo -e "${GREEN}Step 4: Setting up Python virtual environment...${NC}"
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo -e "${GREEN}Step 5: Creating systemd service...${NC}"
cat > /etc/systemd/system/jamwatchdog.service << 'EOF'
[Unit]
Description=JamWatchDog MQTT Monitor
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/JamWatchDog
Environment="PATH=/opt/JamWatchDog/venv/bin"
ExecStart=/opt/JamWatchDog/venv/bin/python watchdog.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

echo -e "${GREEN}Step 6: Configuring Nginx...${NC}"
DROPLET_IP=$(curl -s http://169.254.169.254/metadata/v1/interfaces/public/0/ipv4/address)
echo "Detected IP: $DROPLET_IP"

cat > /etc/nginx/sites-available/jamwatchdog << EOF
server {
    listen 80;
    server_name $DROPLET_IP;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_cache_bypass \$http_upgrade;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # WebSocket support
    location /socket.io/ {
        proxy_pass http://127.0.0.1:5000/socket.io/;
        proxy_http_version 1.1;
        proxy_buffering off;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "Upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    }
}
EOF

ln -sf /etc/nginx/sites-available/jamwatchdog /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t

echo -e "${GREEN}Step 7: Configuring firewall...${NC}"
ufw --force enable
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw status

echo -e "${GREEN}Step 8: Starting services...${NC}"
systemctl daemon-reload
systemctl enable jamwatchdog
systemctl restart jamwatchdog
systemctl restart nginx

echo ""
echo "========================================="
echo -e "${GREEN}Deployment Complete!${NC}"
echo "========================================="
echo ""
echo "Your application is now running at:"
echo -e "${YELLOW}http://$DROPLET_IP${NC}"
echo ""
echo "Useful commands:"
echo "  Check status:    systemctl status jamwatchdog"
echo "  View logs:       journalctl -u jamwatchdog -f"
echo "  Restart app:     systemctl restart jamwatchdog"
echo "  Update code:     cd /opt/JamWatchDog && git pull && systemctl restart jamwatchdog"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Visit http://$DROPLET_IP to access your app"
echo "2. Configure MQTT broker settings in /opt/JamWatchDog/watchdog.py"
echo "3. Optional: Set up SSL with: certbot --nginx"
echo ""
echo "========================================="
