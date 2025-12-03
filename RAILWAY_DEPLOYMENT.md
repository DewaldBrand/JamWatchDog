# Deploying MQTT WatchDog to Railway.app

Railway.app is perfect for this application because it supports WebSockets, always-on processes, and has no restrictions on outbound MQTT connections.

## Prerequisites

- GitHub account (recommended) or Railway CLI
- Your application files ready

## Method 1: Deploy via GitHub (Recommended)

### Step 1: Create a GitHub Repository

1. Go to https://github.com and sign in
2. Click the "+" icon in the top right, select "New repository"
3. Name it: `mqtt-watchdog`
4. Choose "Public" or "Private"
5. Click "Create repository"

### Step 2: Push Your Code to GitHub

Open Git Bash or terminal in your project directory and run:

```bash
cd "d:\Projects\EagleMicro\Claude Code\JamWatchDog"

# Initialize git repository
git init

# Add all files
git add .

# Create initial commit
git commit -m "Initial commit - MQTT WatchDog application"

# Add your GitHub repository as remote (replace YOUR_USERNAME)
git remote add origin https://github.com/YOUR_USERNAME/mqtt-watchdog.git

# Push to GitHub
git branch -M main
git push -u origin main
```

### Step 3: Sign Up for Railway

1. Go to https://railway.app
2. Click "Login" in the top right
3. Click "Login with GitHub"
4. Authorize Railway to access your GitHub account

### Step 4: Create New Project on Railway

1. Click "New Project" on the Railway dashboard
2. Select "Deploy from GitHub repo"
3. If this is your first time, click "Configure GitHub App" to grant Railway access to your repositories
4. Select your `mqtt-watchdog` repository
5. Click "Deploy Now"

### Step 5: Configure Environment (Optional)

If you want to use environment variables instead of hardcoded config:

1. Click on your deployed service
2. Go to "Variables" tab
3. Add variables (optional):
   - `MQTT_BROKER`: 138.68.142.123
   - `MQTT_PORT`: 1883
   - `MQTT_TOPIC`: BRUCE-PING
   - `MQTT_USERNAME`: (if needed)
   - `MQTT_PASSWORD`: (if needed)

### Step 6: Wait for Deployment

Railway will automatically:
- Detect Python application
- Install dependencies from `requirements.txt`
- Run the application using `Procfile`
- Assign a public URL

This takes about 2-3 minutes.

### Step 7: Access Your Application

1. Once deployed, you'll see "Success" status
2. Click on your service
3. Go to "Settings" tab
4. Under "Networking", you'll see your public URL
5. Click "Generate Domain" if not already generated
6. Your app will be available at: `https://your-app-name.up.railway.app`

---

## Method 2: Deploy via Railway CLI

### Step 1: Install Railway CLI

**Windows (PowerShell):**
```powershell
iwr https://railway.app/install.ps1 | iex
```

**macOS/Linux:**
```bash
curl -fsSL https://railway.app/install.sh | sh
```

### Step 2: Login to Railway

```bash
railway login
```

This will open your browser to authenticate.

### Step 3: Initialize and Deploy

```bash
cd "d:\Projects\EagleMicro\Claude Code\JamWatchDog"

# Initialize Railway project
railway init

# Give your project a name when prompted: mqtt-watchdog

# Deploy
railway up
```

### Step 4: Generate Public Domain

```bash
railway domain
```

Your app will be deployed and accessible!

---

## Method 3: Deploy Without GitHub

### Step 1: Create Railway Account

1. Go to https://railway.app
2. Sign up with email or GitHub

### Step 2: Create New Project

1. Click "New Project"
2. Select "Empty Project"
3. Click "+ New" → "Empty Service"

### Step 3: Manual Deploy

Railway doesn't support direct file uploads, so you'll need to:
1. Use Railway CLI (Method 2 above), OR
2. Use GitHub (Method 1 above)

---

## Configuration Options

### Option A: Keep Hardcoded Configuration (Current Setup)

Your current `watchdog.py` has hardcoded values:
```python
mqtt_config = {
    'broker': '138.68.142.123',
    'port': 1883,
    'topic': 'BRUCE-PING',
    'username': '',
    'password': ''
}
```

This works fine on Railway!

### Option B: Use Environment Variables (More Flexible)

If you want to change configuration without redeploying, modify `watchdog.py`:

```python
import os

mqtt_config = {
    'broker': os.environ.get('MQTT_BROKER', '138.68.142.123'),
    'port': int(os.environ.get('MQTT_PORT', 1883)),
    'topic': os.environ.get('MQTT_TOPIC', 'BRUCE-PING'),
    'username': os.environ.get('MQTT_USERNAME', ''),
    'password': os.environ.get('MQTT_PASSWORD', '')
}
```

Then set environment variables in Railway dashboard under "Variables" tab.

---

## Troubleshooting

### Application Not Starting

1. Check the "Deployments" tab for error logs
2. Common issues:
   - Missing dependencies → Check `requirements.txt`
   - Port issues → Railway automatically sets PORT, but our app uses 5000

### Fix Port Issue

Railway expects apps to use the PORT environment variable. Update `watchdog.py`:

```python
if __name__ == '__main__':
    print("Starting MQTT WatchDog...")
    print(f"Connecting to broker: {mqtt_config['broker']}:{mqtt_config['port']}")
    print(f"Subscribing to topic: {mqtt_config['topic']}")
    connect_mqtt()

    # Get port from environment or default to 5000
    port = int(os.environ.get('PORT', 5000))

    # Start the web server
    socketio.run(app, debug=False, host='0.0.0.0', port=port)
```

### WebSocket Issues

If WebSockets don't work:
1. Railway fully supports WebSockets, no configuration needed
2. Check browser console for connection errors
3. Ensure you're using HTTPS (Railway provides this automatically)

### MQTT Connection Issues

If MQTT won't connect:
1. Check Railway logs: Click service → "Deployments" → View logs
2. Verify your MQTT broker is accessible from Railway's servers
3. Check firewall rules on your MQTT broker

---

## Cost

**Railway Free Tier:**
- $5 free credit per month
- No credit card required
- Enough for small projects like this
- App sleeps after 500 hours/month (still plenty!)

**If you exceed free tier:**
- Pay-as-you-go: ~$0.000231/minute
- For this app: approximately $10-15/month for 24/7 operation

---

## Monitoring Your App

### View Logs
1. Go to Railway dashboard
2. Click your service
3. Click "Deployments"
4. Click the latest deployment
5. View real-time logs

### Check Status
- Green checkmark = Running
- Red X = Failed
- Orange = Building

---

## Updating Your App

### Via GitHub:
```bash
# Make changes to your code
git add .
git commit -m "Updated configuration"
git push
```

Railway automatically redeploys on every push!

### Via CLI:
```bash
railway up
```

---

## Custom Domain (Optional)

1. Go to service "Settings"
2. Under "Networking" → "Custom Domain"
3. Add your domain: `watchdog.yourdomain.com`
4. Add the provided CNAME record to your DNS provider
5. Railway handles SSL automatically

---

## Security Recommendations

1. **Don't commit sensitive data to GitHub**
   - Use environment variables for passwords
   - Add `.env` to `.gitignore` if using local env files

2. **Use environment variables on Railway**
   - Set MQTT credentials in Railway dashboard
   - Never hardcode passwords in public repos

3. **Enable authentication** (optional)
   - Add basic auth to your Flask app
   - Or use Railway's built-in authentication

---

## Next Steps

1. Deploy using Method 1 (GitHub) - easiest
2. Access your app at the Railway URL
3. Monitor logs to ensure MQTT connects successfully
4. Share the URL with your team

Your MQTT WatchDog will be live and monitoring 24/7!

---

## Support

- Railway Docs: https://docs.railway.app
- Railway Discord: https://discord.gg/railway
- Railway Status: https://status.railway.app

If you encounter issues, the Railway community is very responsive on Discord.
