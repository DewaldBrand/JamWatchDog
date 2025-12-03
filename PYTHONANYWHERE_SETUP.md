# Deploying to PythonAnywhere

## Important Limitations

**NOTE:** PythonAnywhere's free tier has significant limitations for this application:

1. **No WebSocket Support**: Free accounts don't support WebSockets, which this app requires for real-time updates
2. **No Always-On Tasks**: MQTT client needs to run continuously, which requires a paid account
3. **Outbound Internet Restrictions**: Free accounts can only connect to whitelisted sites

## Recommended Alternatives

For a real-time MQTT monitoring application, consider these alternatives:

1. **Heroku** (Free tier available, supports WebSockets)
2. **Railway.app** (Free tier, good for Python apps)
3. **Render** (Free tier, supports background workers)
4. **DigitalOcean App Platform** (Paid, but affordable)
5. **Your own VPS** (DigitalOcean, Linode, AWS EC2)

## If You Have a PythonAnywhere Paid Account

If you have a paid PythonAnywhere account, follow these steps:

### 1. Upload Files

Upload all files to PythonAnywhere:
```
JamWatchDog/
├── watchdog.py
├── requirements.txt
├── templates/
│   └── index.html
└── static/
    ├── app.js
    └── style.css
```

### 2. Install Dependencies

Open a Bash console on PythonAnywhere and run:
```bash
cd ~/JamWatchDog
pip3.10 install --user -r requirements.txt
```

### 3. Configure Web App

1. Go to the "Web" tab
2. Click "Add a new web app"
3. Choose "Manual configuration"
4. Choose Python 3.10

### 4. Configure WSGI File

Edit the WSGI configuration file (`/var/www/yourusername_pythonanywhere_com_wsgi.py`):

```python
import sys
import os

# Add your project directory to the sys.path
project_home = '/home/yourusername/JamWatchDog'
if project_home not in sys.path:
    sys.path = [project_home] + sys.path

# Set environment variable
os.environ['PYTHONANYWHERE'] = 'true'

# Import your Flask app
from watchdog import app as application
```

### 5. Configure Static Files

In the Web tab, add static file mappings:
- URL: `/static/`
- Directory: `/home/yourusername/JamWatchDog/static/`

### 6. Enable Always-On Task (Paid Feature)

Since MQTT needs to run continuously:
1. Go to "Tasks" tab
2. Create a new always-on task
3. Command: `python3.10 /home/yourusername/JamWatchDog/mqtt_worker.py`

### 7. WebSocket Configuration (Paid Feature)

For WebSocket support on PythonAnywhere, you need to:
1. Use a different port for WebSockets
2. Configure nginx to proxy WebSocket connections
3. This is complex and requires support from PythonAnywhere staff

## Simplified Polling Alternative

For free PythonAnywhere accounts, you can modify the app to use HTTP polling instead of WebSockets, but this is not ideal for real-time monitoring.

## Recommended: Deploy to Railway.app (Free Alternative)

Railway.app is better suited for this application:

1. Create account at https://railway.app
2. Install Railway CLI or use GitHub integration
3. Create `Procfile`:
   ```
   web: python watchdog.py
   ```
4. Railway automatically detects Python and installs requirements
5. Deploy with one command: `railway up`

Railway provides:
- ✓ WebSocket support
- ✓ Always-on processes
- ✓ No outbound connection restrictions
- ✓ Free tier available

Would you like instructions for deploying to Railway.app or another platform instead?
