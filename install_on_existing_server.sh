#!/bin/bash
# JamWatchDog - Installation Script for Existing Servers
# Run this on a server that already has other applications running

set -e  # Exit on error

echo "========================================="
echo "JamWatchDog Installation (Existing Server)"
echo "========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;36m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Please run as root (use: sudo ./install_on_existing_server.sh)${NC}"
    exit 1
fi

echo -e "${BLUE}This script will install JamWatchDog alongside your existing applications.${NC}"
echo -e "${BLUE}It will NOT interfere with Node-RED or other services.${NC}"
echo ""

# Ask for GitHub username
read -p "Enter your GitHub username: " GITHUB_USER
if [ -z "$GITHUB_USER" ]; then
    echo -e "${RED}GitHub username is required${NC}"
    exit 1
fi

# Ask for installation directory
echo ""
echo -e "${YELLOW}Choose installation directory:${NC}"
echo "  1) /opt/JamWatchDog (recommended)"
echo "  2) /home/jamwatchdog"
echo "  3) Custom path"
read -p "Enter choice [1-3] (default: 1): " INSTALL_CHOICE
INSTALL_CHOICE=${INSTALL_CHOICE:-1}

case $INSTALL_CHOICE in
    1)
        INSTALL_DIR="/opt/JamWatchDog"
        ;;
    2)
        INSTALL_DIR="/home/jamwatchdog"
        ;;
    3)
        read -p "Enter custom path: " INSTALL_DIR
        ;;
    *)
        INSTALL_DIR="/opt/JamWatchDog"
        ;;
esac

echo ""
echo -e "${GREEN}Installation directory: $INSTALL_DIR${NC}"
echo ""

# Check if directory already exists
if [ -d "$INSTALL_DIR" ]; then
    echo -e "${YELLOW}Directory $INSTALL_DIR already exists.${NC}"
    read -p "Update existing installation? [y/N]: " UPDATE_EXISTING
    if [[ $UPDATE_EXISTING =~ ^[Yy]$ ]]; then
        cd "$INSTALL_DIR"
        git pull origin main
        echo -e "${GREEN}Updated to latest version${NC}"
    else
        echo -e "${RED}Installation cancelled${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}Step 1: Installing Python dependencies...${NC}"
    apt update
    apt install python3 python3-pip python3-venv git -y

    echo -e "${GREEN}Step 2: Cloning repository...${NC}"
    mkdir -p "$(dirname "$INSTALL_DIR")"
    cd "$(dirname "$INSTALL_DIR")"
    git clone "https://github.com/$GITHUB_USER/JamWatchDog.git" "$(basename "$INSTALL_DIR")"
    cd "$INSTALL_DIR"
fi

echo -e "${GREEN}Step 3: Setting up Python virtual environment...${NC}"
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo -e "${GREEN}Step 4: Configuring MQTT settings...${NC}"
echo ""
echo -e "${YELLOW}MQTT Broker Configuration:${NC}"
read -p "MQTT Broker IP [localhost]: " MQTT_BROKER
MQTT_BROKER=${MQTT_BROKER:-localhost}

read -p "MQTT Port [1883]: " MQTT_PORT
MQTT_PORT=${MQTT_PORT:-1883}

read -p "MQTT Topic [PING-WATCH]: " MQTT_TOPIC
MQTT_TOPIC=${MQTT_TOPIC:-PING-WATCH}

read -p "MQTT Username (optional): " MQTT_USER
read -sp "MQTT Password (optional): " MQTT_PASS
echo ""

# Update watchdog.py with MQTT settings
sed -i "s/'broker': '.*'/'broker': '$MQTT_BROKER'/g" watchdog.py
sed -i "s/'port': [0-9]*/'port': $MQTT_PORT/g" watchdog.py
sed -i "s/'topic': '.*'/'topic': '$MQTT_TOPIC'/g" watchdog.py

if [ -n "$MQTT_USER" ]; then
    sed -i "s/'username': ''/'username': '$MQTT_USER'/g" watchdog.py
fi

if [ -n "$MQTT_PASS" ]; then
    sed -i "s/'password': ''/'password': '$MQTT_PASS'/g" watchdog.py
fi

echo -e "${GREEN}MQTT configuration updated${NC}"

echo -e "${GREEN}Step 5: Creating systemd service...${NC}"
cat > /etc/systemd/system/jamwatchdog.service << EOF
[Unit]
Description=JamWatchDog MQTT Monitor
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$INSTALL_DIR/venv/bin"
ExecStart=$INSTALL_DIR/venv/bin/python watchdog.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

echo -e "${GREEN}Step 6: Configuring firewall...${NC}"
if command -v ufw &> /dev/null; then
    ufw status | grep -q "Status: active"
    if [ $? -eq 0 ]; then
        echo "Opening port 5000 for JamWatchDog..."
        ufw allow 5000/tcp
        echo -e "${GREEN}Firewall configured${NC}"
    else
        echo -e "${YELLOW}UFW not active, skipping firewall configuration${NC}"
    fi
else
    echo -e "${YELLOW}UFW not installed, skipping firewall configuration${NC}"
fi

echo -e "${GREEN}Step 7: Starting JamWatchDog service...${NC}"
systemctl daemon-reload
systemctl enable jamwatchdog
systemctl start jamwatchdog

# Wait a moment for service to start
sleep 2

# Check if service is running
if systemctl is-active --quiet jamwatchdog; then
    echo -e "${GREEN}✓ Service started successfully${NC}"
else
    echo -e "${RED}✗ Service failed to start${NC}"
    echo "Checking logs..."
    journalctl -u jamwatchdog -n 20
    exit 1
fi

# Get server IP
SERVER_IP=$(hostname -I | awk '{print $1}')
if [ -z "$SERVER_IP" ]; then
    SERVER_IP=$(curl -s http://169.254.169.254/metadata/v1/interfaces/public/0/ipv4/address 2>/dev/null || echo "YOUR_SERVER_IP")
fi

echo ""
echo "========================================="
echo -e "${GREEN}Installation Complete! ✓${NC}"
echo "========================================="
echo ""
echo -e "${YELLOW}Access your application:${NC}"
echo "  Direct access:  http://$SERVER_IP:5000"
echo ""
echo -e "${YELLOW}Your existing services (unchanged):${NC}"
echo "  Node-RED:       http://$SERVER_IP:1880"
echo ""
echo -e "${YELLOW}Useful commands:${NC}"
echo "  Check status:   systemctl status jamwatchdog"
echo "  View logs:      journalctl -u jamwatchdog -f"
echo "  Restart:        systemctl restart jamwatchdog"
echo "  Stop:           systemctl stop jamwatchdog"
echo ""
echo -e "${YELLOW}Update JamWatchDog:${NC}"
echo "  cd $INSTALL_DIR"
echo "  git pull origin main"
echo "  source venv/bin/activate"
echo "  pip install -r requirements.txt"
echo "  systemctl restart jamwatchdog"
echo ""
echo -e "${BLUE}Optional: Set up Nginx reverse proxy${NC}"
echo "  See: INSTALL_ON_EXISTING_DROPLET.md"
echo ""
echo "========================================="
echo -e "${GREEN}Checking service status:${NC}"
systemctl status jamwatchdog --no-pager -l
echo "========================================="
