# Digital Ocean Deployment Guide for JamWatchDog

This guide will help you deploy your MQTT WatchDog application to Digital Ocean using their App Platform or a Droplet.

## Table of Contents
1. [Method 1: App Platform (Recommended - Easiest)](#method-1-app-platform-recommended)
2. [Method 2: Droplet with Ubuntu](#method-2-droplet-deployment)
3. [Configuration](#configuration)
4. [Troubleshooting](#troubleshooting)

---

## Method 1: App Platform (Recommended)

Digital Ocean's App Platform is similar to Railway/Heroku - fully managed with automatic deployments.

### Prerequisites
- Digital Ocean account
- GitHub repository with your code (JamWatchDog)

### Step 1: Create App from GitHub

1. **Login to Digital Ocean**
   - Go to https://cloud.digitalocean.com
   - Navigate to **Apps** in the left sidebar
   - Click **Create App**

2. **Connect GitHub Repository**
   - Choose **GitHub** as source
   - Click **Authorize Digital Ocean** to connect GitHub
   - Select your repository: `JamWatchDog`
   - Select branch: `main`
   - Click **Next**

3. **Configure App Settings**
   - **Name**: `jamwatchdog` (or your preferred name)
   - **Region**: Choose closest to your location
   - **Branch**: `main`
   - **Autodeploy**: Enable (deploys automatically on git push)

### Step 2: Configure Build Settings

Digital Ocean should auto-detect it's a Python app. Verify these settings:

- **Type**: Web Service
- **Environment**: Python
- **Build Command**: (leave default or use `pip install -r requirements.txt`)
- **Run Command**: `python watchdog.py`
- **HTTP Port**: `8080` (Digital Ocean default)

### Step 3: Set Environment Variables (Optional)

If you need to override any settings:

1. Go to **Settings** → **Environment Variables**
2. Add variables:
   ```
   PORT=8080
   PYTHON_VERSION=3.10.12
   ```

### Step 4: Choose Plan

- **Basic Plan**: $5/month - Good for starting
  - 512 MB RAM
  - 1 vCPU
  - Sufficient for moderate MQTT traffic

- **Professional Plan**: $12/month - For production
  - 1 GB RAM
  - 1 vCPU
  - Better performance

### Step 5: Deploy

1. Click **Create Resources**
2. Wait 3-5 minutes for deployment
3. Once deployed, you'll get a URL like: `https://jamwatchdog-xxxxx.ondigitalocean.app`
4. Visit the URL to access your app!

### Step 6: Custom Domain (Optional)

1. Go to **Settings** → **Domains**
2. Click **Add Domain**
3. Enter your domain (e.g., `watchdog.yourdomain.com`)
4. Add the CNAME record to your DNS provider:
   ```
   Type: CNAME
   Name: watchdog
   Value: jamwatchdog-xxxxx.ondigitalocean.app
   ```

---

## Method 2: Droplet Deployment

For more control, deploy on a virtual server (Droplet).

### Step 1: Create a Droplet

1. **Go to Droplets**
   - Click **Create** → **Droplets**

2. **Choose Configuration**
   - **Image**: Ubuntu 22.04 LTS
   - **Plan**: Basic
   - **CPU Options**: Regular (shared CPU)
   - **Size**: $6/month (1 GB RAM, 1 vCPU, 25 GB SSD)
   - **Datacenter**: Choose closest region
   - **Authentication**: SSH Key (recommended) or Password
   - **Hostname**: `jamwatchdog`

3. **Click Create Droplet**
   - Wait 1-2 minutes for creation
   - Note the IP address (e.g., `164.92.xxx.xxx`)

### Step 2: Connect to Droplet

Using SSH (Mac/Linux/Windows with PowerShell):

```bash
ssh root@YOUR_DROPLET_IP
```

Or use Digital Ocean's browser console (click on droplet → **Console**)

### Step 3: Install Dependencies

```bash
# Update system
apt update && apt upgrade -y

# Install Python and pip
apt install python3 python3-pip python3-venv git -y

# Install supervisor (for keeping app running)
apt install supervisor -y

# Install nginx (web server/reverse proxy)
apt install nginx -y
```

### Step 4: Clone Your Repository

```bash
# Navigate to web directory
cd /opt

# Clone your repository
git clone https://github.com/YOUR_USERNAME/JamWatchDog.git
cd JamWatchDog

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

### Step 5: Create Systemd Service

Create a service file to run the app automatically:

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

### Step 6: Configure Nginx (Reverse Proxy)

```bash
nano /etc/nginx/sites-available/jamwatchdog
```

Paste this configuration:

```nginx
server {
    listen 80;
    server_name YOUR_DROPLET_IP;

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

Replace `YOUR_DROPLET_IP` with your actual IP address.

Enable the site:

```bash
ln -s /etc/nginx/sites-available/jamwatchdog /etc/nginx/sites-enabled/
rm /etc/nginx/sites-enabled/default
nginx -t  # Test configuration
systemctl restart nginx
```

### Step 7: Start the Application

```bash
# Enable and start the service
systemctl daemon-reload
systemctl enable jamwatchdog
systemctl start jamwatchdog

# Check status
systemctl status jamwatchdog
```

You should see "active (running)" in green.

### Step 8: Configure Firewall

```bash
# Allow HTTP, HTTPS, and SSH
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable
```

### Step 9: Access Your Application

Open browser and go to:
```
http://YOUR_DROPLET_IP
```

You should see your JamWatchDog application!

### Step 10: Set Up SSL with Let's Encrypt (Optional but Recommended)

```bash
# Install Certbot
apt install certbot python3-certbot-nginx -y

# Get SSL certificate (replace with your domain)
certbot --nginx -d watchdog.yourdomain.com

# Follow the prompts
# Choose option 2 (redirect HTTP to HTTPS)
```

Now access via HTTPS:
```
https://watchdog.yourdomain.com
```

---

## Configuration

### Update MQTT Settings

Edit the configuration in `watchdog.py`:

```bash
nano /opt/JamWatchDog/watchdog.py
```

Update these lines (around line 26-32):

```python
mqtt_config = {
    'broker': 'YOUR_MQTT_BROKER_IP',
    'port': 1883,
    'topic': 'PING-WATCH',
    'username': '',
    'password': ''
}
```

Restart the service:

```bash
systemctl restart jamwatchdog
```

### Persist Site Configurations

The `site_config.json` file is stored in `/opt/JamWatchDog/site_config.json` and will persist across restarts.

To backup:

```bash
cp /opt/JamWatchDog/site_config.json ~/site_config_backup.json
```

---

## Maintenance Commands

### View Logs

```bash
# View application logs
journalctl -u jamwatchdog -f

# View last 100 lines
journalctl -u jamwatchdog -n 100

# View nginx logs
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

### Restart Application

```bash
systemctl restart jamwatchdog
```

### Update Application

```bash
cd /opt/JamWatchDog
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
systemctl restart jamwatchdog
```

### Check Status

```bash
systemctl status jamwatchdog
systemctl status nginx
```

---

## Troubleshooting

### Application Won't Start

Check logs:
```bash
journalctl -u jamwatchdog -n 50
```

Common issues:
- **Port already in use**: Change port in `watchdog.py`
- **Missing dependencies**: Run `pip install -r requirements.txt`
- **Permission errors**: Ensure files owned by correct user

### WebSocket Connection Issues

Check nginx configuration:
```bash
nginx -t
systemctl restart nginx
```

Ensure WebSocket headers are set correctly in nginx config.

### MQTT Not Connecting

1. Check MQTT broker is accessible:
   ```bash
   telnet YOUR_MQTT_BROKER_IP 1883
   ```

2. Check firewall on MQTT broker allows connections

3. Verify credentials in `watchdog.py`

### High Memory Usage

Upgrade to larger Droplet:
- Go to Droplet → **Resize**
- Choose larger plan
- Application will restart automatically

---

## Cost Comparison

### App Platform
- **Basic**: $5/month (512 MB RAM)
- **Professional**: $12/month (1 GB RAM)
- ✅ Easiest setup
- ✅ Auto-scaling
- ✅ Automatic SSL
- ✅ GitHub integration

### Droplet
- **Basic**: $6/month (1 GB RAM)
- **Standard**: $12/month (2 GB RAM)
- ✅ Full control
- ✅ Can run multiple apps
- ✅ SSH access
- ⚠️ Manual maintenance

---

## Recommended: App Platform for Simplicity

For this application, **App Platform is recommended** because:
1. Automatic deployments from GitHub
2. Built-in SSL/HTTPS
3. No server maintenance
4. Easy scaling
5. Similar cost to Droplet

Use Droplet only if you need:
- Full server control
- Multiple applications on same server
- Custom system configurations
- SSH access for debugging

---

## Support

- **Digital Ocean Docs**: https://docs.digitalocean.com
- **Community**: https://www.digitalocean.com/community
- **Support**: Available via ticket system

Happy Deploying! 🚀
