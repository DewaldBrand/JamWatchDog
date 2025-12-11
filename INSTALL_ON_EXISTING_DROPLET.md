# Installing JamWatchDog on Existing Digital Ocean Droplet

This guide shows how to install JamWatchDog alongside your existing Node-RED installation on the same droplet.

## Prerequisites

- Existing Digital Ocean droplet with Node-RED running
- SSH access to your droplet
- Root or sudo privileges

## Quick Installation

### Option 1: Automated Script (Recommended)

1. **SSH into your droplet:**
   ```bash
   ssh root@YOUR_DROPLET_IP
   ```

2. **Download and run the installation script:**
   ```bash
   cd /tmp
   wget https://raw.githubusercontent.com/YOUR_USERNAME/JamWatchDog/main/install_on_existing_server.sh
   chmod +x install_on_existing_server.sh
   sudo ./install_on_existing_server.sh
   ```

3. **Access your app:**
   - JamWatchDog: `http://YOUR_DROPLET_IP:5000`
   - Node-RED: `http://YOUR_DROPLET_IP:1880` (unchanged)

---

## Option 2: Manual Installation (Step by Step)

### Step 1: Install Python Dependencies

```bash
# SSH into your droplet
ssh root@YOUR_DROPLET_IP

# Update packages
apt update

# Install Python (if not already installed)
apt install python3 python3-pip python3-venv git -y
```

### Step 2: Clone JamWatchDog Repository

```bash
# Create directory for the app
cd /opt
git clone https://github.com/YOUR_USERNAME/JamWatchDog.git
cd JamWatchDog
```

### Step 3: Set Up Python Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Configure MQTT Settings

Edit the watchdog.py file to point to your MQTT broker:

```bash
nano watchdog.py
```

Update the MQTT configuration (around line 26-32):

```python
mqtt_config = {
    'broker': 'localhost',  # or 127.0.0.1 if MQTT broker is on same droplet
    'port': 1883,
    'topic': 'PING-WATCH',
    'username': '',  # Add if needed
    'password': ''   # Add if needed
}
```

Save and exit (Ctrl+X, then Y, then Enter)

### Step 5: Create Systemd Service

This ensures JamWatchDog starts automatically on boot:

```bash
nano /etc/systemd/system/jamwatchdog.service
```

Paste this content:

```ini
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
```

Save and exit (Ctrl+X, then Y, then Enter)

### Step 6: Start the Service

```bash
# Reload systemd
systemctl daemon-reload

# Enable service to start on boot
systemctl enable jamwatchdog

# Start the service
systemctl start jamwatchdog

# Check status
systemctl status jamwatchdog
```

You should see "active (running)" in green.

### Step 7: Configure Firewall

Allow port 5000 for JamWatchDog (if firewall is enabled):

```bash
# Check if ufw is active
ufw status

# If active, allow port 5000
ufw allow 5000/tcp
```

### Step 8: Access Your Application

Open your browser and go to:
- **JamWatchDog**: `http://YOUR_DROPLET_IP:5000`
- **Node-RED**: `http://YOUR_DROPLET_IP:1880` (still works as before)

---

## Option 3: Use Nginx Reverse Proxy (Recommended for Production)

This allows you to access JamWatchDog via a subdomain or path instead of port number.

### A. Access via Subdomain (e.g., `watchdog.yourdomain.com`)

1. **Create Nginx configuration:**

```bash
nano /etc/nginx/sites-available/jamwatchdog
```

Paste this:

```nginx
server {
    listen 80;
    server_name watchdog.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket support
    location /socket.io/ {
        proxy_pass http://127.0.0.1:5000/socket.io/;
        proxy_http_version 1.1;
        proxy_buffering off;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

2. **Enable the site:**

```bash
ln -s /etc/nginx/sites-available/jamwatchdog /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx
```

3. **Add DNS record:**
   - Type: A
   - Name: watchdog
   - Value: YOUR_DROPLET_IP

4. **Add SSL (optional but recommended):**

```bash
apt install certbot python3-certbot-nginx -y
certbot --nginx -d watchdog.yourdomain.com
```

### B. Access via Path (e.g., `yourdomain.com/watchdog`)

If you prefer to access via a path instead of subdomain:

1. **Edit your existing Nginx config:**

```bash
nano /etc/nginx/sites-available/default
```

Add this inside your existing server block:

```nginx
    location /watchdog/ {
        proxy_pass http://127.0.0.1:5000/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /watchdog/socket.io/ {
        proxy_pass http://127.0.0.1:5000/socket.io/;
        proxy_http_version 1.1;
        proxy_buffering off;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
    }
```

2. **Restart Nginx:**

```bash
nginx -t
systemctl restart nginx
```

3. **Access at:** `http://YOUR_DROPLET_IP/watchdog`

---

## Port Configuration Summary

Here's how your services will be configured:

| Service | Port | Access Method |
|---------|------|---------------|
| Node-RED | 1880 | `http://YOUR_IP:1880` |
| JamWatchDog | 5000 | `http://YOUR_IP:5000` |
| JamWatchDog (with subdomain) | 80/443 | `http://watchdog.yourdomain.com` |
| JamWatchDog (with path) | 80/443 | `http://yourdomain.com/watchdog` |

---

## Useful Commands

### Managing JamWatchDog Service

```bash
# Start
systemctl start jamwatchdog

# Stop
systemctl stop jamwatchdog

# Restart
systemctl restart jamwatchdog

# Check status
systemctl status jamwatchdog

# View logs (live)
journalctl -u jamwatchdog -f

# View last 100 log lines
journalctl -u jamwatchdog -n 100
```

### Updating JamWatchDog

```bash
cd /opt/JamWatchDog
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
systemctl restart jamwatchdog
```

### Check Resource Usage

```bash
# Memory usage
free -h

# Disk usage
df -h

# CPU and process info
htop

# Check which services are using which ports
netstat -tlnp
```

---

## Resource Requirements

JamWatchDog is lightweight and should run fine alongside Node-RED:

- **RAM**: ~50-100 MB
- **CPU**: Minimal (< 5% on average)
- **Disk**: ~50 MB for app + dependencies
- **Network**: Depends on MQTT message frequency

### Recommended Minimum Droplet Size

- **1 GB RAM** - Can run Node-RED + JamWatchDog comfortably
- **2 GB RAM** - Better headroom for multiple sites

If you're currently on a 512 MB droplet, consider upgrading to 1 GB.

---

## Troubleshooting

### Port 5000 Already in Use

Check what's using the port:
```bash
lsof -i :5000
```

If something else is using it, change the port in `watchdog.py`:

```python
# At the bottom of watchdog.py
port = int(os.environ.get('PORT', 5001))  # Change 5000 to 5001
```

Then restart:
```bash
systemctl restart jamwatchdog
```

### Service Won't Start

Check logs for errors:
```bash
journalctl -u jamwatchdog -n 50
```

Common issues:
- Python virtual environment not activated
- Missing dependencies
- MQTT broker unreachable
- Permission issues

### MQTT Connection Issues

If JamWatchDog can't connect to MQTT broker on the same droplet:

```bash
# Test MQTT broker connectivity
telnet localhost 1883

# Check if MQTT broker (Mosquitto) is running
systemctl status mosquitto
```

### Can't Access via Browser

1. **Check if service is running:**
   ```bash
   systemctl status jamwatchdog
   ```

2. **Check if port is open:**
   ```bash
   netstat -tlnp | grep 5000
   ```

3. **Check firewall:**
   ```bash
   ufw status
   ufw allow 5000/tcp
   ```

4. **Check Nginx (if using reverse proxy):**
   ```bash
   nginx -t
   systemctl status nginx
   ```

---

## Security Considerations

Since both apps are on the same server:

1. **Use Nginx reverse proxy** (recommended)
   - Don't expose ports 1880 and 5000 directly
   - Use Nginx with SSL/HTTPS

2. **Configure firewall properly:**
   ```bash
   # Only allow necessary ports
   ufw allow 22/tcp   # SSH
   ufw allow 80/tcp   # HTTP
   ufw allow 443/tcp  # HTTPS
   ufw deny 5000/tcp  # Block direct access if using Nginx
   ufw deny 1880/tcp  # Block direct access if using Nginx
   ufw enable
   ```

3. **Add authentication** (optional):
   - Configure Node-RED authentication
   - Add basic auth to Nginx for JamWatchDog

---

## Cost Savings

By running on your existing droplet instead of App Platform:

| Option | Monthly Cost | Savings |
|--------|-------------|---------|
| App Platform ($24) + Droplet | $30-36 | - |
| Single Droplet ($6-12) | $6-12 | **$18-24/month** |

**Annual Savings**: $216-288 per year! 💰

---

## Next Steps

1. ✅ Install JamWatchDog on existing droplet
2. ✅ Configure MQTT broker connection
3. ✅ Access via browser (port 5000 or Nginx)
4. ✅ Add your sites in configuration page
5. ✅ Optional: Set up Nginx reverse proxy with SSL

Need help? Check the logs or reach out for support!
