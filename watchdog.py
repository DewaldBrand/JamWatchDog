from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import paho.mqtt.client as mqtt
from datetime import datetime
import os
import json

# Monkey patch for eventlet (production only - optional for local dev)
try:
    import eventlet
    eventlet.monkey_patch()
    async_mode = 'eventlet'
    print("Using eventlet for WebSocket transport")
except ImportError:
    async_mode = 'threading'
    print("Using threading mode (eventlet not available)")

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode=async_mode)

mqtt_client = None

# =============================================================================
# MQTT CONFIGURATION - EDIT THESE VALUES
# =============================================================================
mqtt_config = {
    'broker': '138.68.142.123',        # MQTT broker address (e.g., 'mqtt.example.com' or '192.168.1.100')
    'port': 1883,                 # MQTT broker port (default: 1883, SSL: 8883)
    'topic': 'PING-WATCH',        # Topic to subscribe to (# = all topics, sensors/# = all under sensors/)
    'username': '',               # MQTT username (leave empty if not required)
    'password': ''                # MQTT password (leave empty if not required)
}

# Monitoring configuration
EXPECTED_DEVICES_PER_SITE = ['GSM-1', 'GSM-2', 'ESP']  # Expected devices per site
CHECK_INTERVAL = 60  # Check every 60 seconds

# Site monitoring data
sites_data = {}  # Format: {site_id: {device_name: {'last_seen': timestamp, 'count': int}}}
current_minute_messages = {}  # Track messages received in current minute

# Configuration file path
CONFIG_FILE = 'site_config.json'
site_configurations = {}  # Loaded from JSON file
# =============================================================================

def load_site_configurations():
    """Load site configurations from JSON file"""
    global site_configurations
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                data = json.load(f)
                site_configurations = data.get('sites', {})
                print(f"Loaded {len(site_configurations)} site configurations")
        else:
            site_configurations = {}
            save_site_configurations()
    except Exception as e:
        print(f"Error loading site configurations: {e}")
        site_configurations = {}

def save_site_configurations():
    """Save site configurations to JSON file"""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump({'sites': site_configurations}, f, indent=2)
        print(f"Saved {len(site_configurations)} site configurations")
    except Exception as e:
        print(f"Error saving site configurations: {e}")

def get_site_config(site_id):
    """Get configuration for a specific site"""
    return site_configurations.get(site_id, None)

def is_site_active(site_id):
    """Check if a site is active"""
    config = get_site_config(site_id)
    if config is None:
        return True  # Default to active if not configured
    return config.get('active', True)

def get_active_devices_for_site(site_id):
    """Get list of active devices for a site"""
    config = get_site_config(site_id)
    if config is None:
        return EXPECTED_DEVICES_PER_SITE  # Default to all devices
    return config.get('active_devices', EXPECTED_DEVICES_PER_SITE)

def on_connect(client, _userdata, _flags, rc):
    if rc == 0:
        print(f"Connected to MQTT Broker at {mqtt_config['broker']}:{mqtt_config['port']}")
        client.subscribe(mqtt_config['topic'])
        socketio.emit('mqtt_status', {'status': 'connected', 'broker': mqtt_config['broker'], 'topic': mqtt_config['topic']}, namespace='/')
    else:
        print(f"Failed to connect, return code {rc}")
        socketio.emit('mqtt_status', {'status': 'disconnected', 'error': f'Connection failed: {rc}'}, namespace='/')

def on_message(_client, _userdata, msg):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    try:
        payload = msg.payload.decode('utf-8')
    except:
        payload = str(msg.payload)

    message_data = {
        'timestamp': timestamp,
        'topic': msg.topic,
        'payload': payload
    }

    # Parse payload for site monitoring (format: site_id/device_name)
    try:
        parts = payload.split('/')
        if len(parts) == 2:
            site_id, device_name = parts

            # Only process messages from active sites
            if not is_site_active(site_id):
                print(f"[{timestamp}] Site: {site_id} | Device: {device_name} | IGNORED (site inactive)")
            else:
                # Initialize site if not exists
                is_new_site = site_id not in sites_data
                if is_new_site:
                    sites_data[site_id] = {}
                    current_minute_messages[site_id] = set()
                    print(f"NEW SITE DETECTED: {site_id}")

                # Update device last seen
                sites_data[site_id][device_name] = {
                    'last_seen': datetime.now(),
                    'timestamp': timestamp
                }

                # Track for current minute analysis
                current_minute_messages[site_id].add(device_name)

                print(f"[{timestamp}] Site: {site_id} | Device: {device_name} | Current minute: {current_minute_messages[site_id]}")

                # Send immediate status update for new sites
                if is_new_site:
                    send_current_status()
    except Exception as e:
        print(f"Error parsing payload: {e}")

    socketio.emit('mqtt_message', message_data, namespace='/')
    print(f"[{timestamp}] Topic: {msg.topic} | Payload: {payload}")

def on_disconnect(_client, _userdata, _rc):
    print("Disconnected from MQTT Broker")
    socketio.emit('mqtt_status', {'status': 'disconnected'}, namespace='/')

def send_current_status():
    """Send current status without clearing data (for immediate updates)"""
    site_statuses = []

    for site_id in sites_data.keys():
        # Skip inactive sites
        if not is_site_active(site_id):
            continue

        received_devices = current_minute_messages.get(site_id, set())
        expected_devices = set(get_active_devices_for_site(site_id))

        missing_devices = expected_devices - received_devices
        missed_count = len(missing_devices)

        # Calculate alert level (0 = all good, 1-3 = missed messages)
        alert_level = min(missed_count, 3)

        # Color coding based on alert level
        colors = ['#10b981', '#f59e0b', '#ef4444', '#7f1d1d']  # green, orange, red, dark red
        color = colors[alert_level]

        site_status = {
            'site_id': site_id,
            'alert_level': alert_level,
            'color': color,
            'received': list(received_devices),
            'missing': list(missing_devices),
            'total_expected': len(expected_devices),
            'total_received': len(received_devices)
        }

        site_statuses.append(site_status)

    # Emit update to all clients
    socketio.emit('site_status_update', {'sites': site_statuses}, namespace='/')
    print(f"Status update sent: {len(site_statuses)} sites")

def check_site_status():
    """Check each site's status and calculate alert levels"""
    global current_minute_messages

    site_statuses = []

    for site_id in sites_data.keys():
        # Skip inactive sites
        if not is_site_active(site_id):
            continue

        received_devices = current_minute_messages.get(site_id, set())
        expected_devices = set(get_active_devices_for_site(site_id))

        missing_devices = expected_devices - received_devices
        missed_count = len(missing_devices)

        # Calculate alert level (0 = all good, 1-3 = missed messages)
        alert_level = min(missed_count, 3)

        # Color coding based on alert level
        colors = ['#10b981', '#f59e0b', '#ef4444', '#7f1d1d']  # green, orange, red, dark red
        color = colors[alert_level]

        site_status = {
            'site_id': site_id,
            'alert_level': alert_level,
            'color': color,
            'received': list(received_devices),
            'missing': list(missing_devices),
            'total_expected': len(expected_devices),
            'total_received': len(received_devices)
        }

        site_statuses.append(site_status)
        print(f"[CHECK] Site {site_id}: Alert Level {alert_level}, Received: {len(received_devices)}/{len(expected_devices)}")

    # Emit update to all clients
    socketio.emit('site_status_update', {'sites': site_statuses}, namespace='/')

    # Clear messages table on web interface
    socketio.emit('clear_messages', namespace='/')

    # Clear current minute tracking
    current_minute_messages = {site_id: set() for site_id in sites_data.keys()}
    print(f"[CHECK] Minute reset - tracking cleared for next cycle")

def start_monitoring_scheduler():
    """Start the periodic monitoring check"""
    import threading
    import time

    def run_scheduler():
        while True:
            time.sleep(CHECK_INTERVAL)
            check_site_status()

    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    print(f"Monitoring scheduler started (checking every {CHECK_INTERVAL}s)")

def connect_mqtt():
    global mqtt_client

    if mqtt_client:
        mqtt_client.disconnect()
        mqtt_client.loop_stop()

    mqtt_client = mqtt.Client()
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.on_disconnect = on_disconnect

    if mqtt_config['username'] and mqtt_config['password']:
        mqtt_client.username_pw_set(mqtt_config['username'], mqtt_config['password'])

    try:
        mqtt_client.connect(mqtt_config['broker'], mqtt_config['port'], 60)
        mqtt_client.loop_start()
        return True
    except Exception as e:
        print(f"Error connecting to MQTT broker: {e}")
        socketio.emit('mqtt_status', {'status': 'error', 'error': str(e)})
        return False

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/config')
def config_page():
    return render_template('config.html')

# API Routes for Site Configuration
@app.route('/api/sites', methods=['GET'])
def get_sites():
    """Get all site configurations"""
    return jsonify({'sites': site_configurations})

@app.route('/api/sites/<site_id>', methods=['GET'])
def get_site(site_id):
    """Get a specific site configuration"""
    config = get_site_config(site_id)
    if config:
        return jsonify(config)
    return jsonify({'error': 'Site not found'}), 404

@app.route('/api/sites', methods=['POST'])
def create_site():
    """Create a new site configuration"""
    data = request.json
    site_id = data.get('site_id')

    if not site_id:
        return jsonify({'error': 'site_id is required'}), 400

    if site_id in site_configurations:
        return jsonify({'error': 'Site already exists'}), 409

    site_configurations[site_id] = {
        'site_name': data.get('site_name', ''),
        'location': data.get('location', ''),
        'responsible_person': data.get('responsible_person', ''),
        'contact_email': data.get('contact_email', ''),
        'contact_phone': data.get('contact_phone', ''),
        'active': data.get('active', True),
        'active_devices': data.get('active_devices', EXPECTED_DEVICES_PER_SITE)
    }

    save_site_configurations()
    return jsonify({'message': 'Site created successfully', 'site_id': site_id}), 201

@app.route('/api/sites/<site_id>', methods=['PUT'])
def update_site(site_id):
    """Update an existing site configuration"""
    data = request.json

    if site_id not in site_configurations:
        return jsonify({'error': 'Site not found'}), 404

    # Update only provided fields
    config = site_configurations[site_id]
    config['site_name'] = data.get('site_name', config.get('site_name', ''))
    config['location'] = data.get('location', config.get('location', ''))
    config['responsible_person'] = data.get('responsible_person', config.get('responsible_person', ''))
    config['contact_email'] = data.get('contact_email', config.get('contact_email', ''))
    config['contact_phone'] = data.get('contact_phone', config.get('contact_phone', ''))
    config['active'] = data.get('active', config.get('active', True))
    config['active_devices'] = data.get('active_devices', config.get('active_devices', EXPECTED_DEVICES_PER_SITE))

    save_site_configurations()
    return jsonify({'message': 'Site updated successfully', 'site_id': site_id})

@app.route('/api/sites/<site_id>', methods=['DELETE'])
def delete_site(site_id):
    """Delete a site configuration"""
    if site_id not in site_configurations:
        return jsonify({'error': 'Site not found'}), 404

    del site_configurations[site_id]
    save_site_configurations()
    return jsonify({'message': 'Site deleted successfully'})

@socketio.on('connect')
def handle_connect():
    print('Client connected')
    if mqtt_client and mqtt_client.is_connected():
        emit('mqtt_status', {'status': 'connected', 'broker': mqtt_config['broker'], 'topic': mqtt_config['topic']})
    else:
        emit('mqtt_status', {'status': 'disconnected'})

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('connect_mqtt')
def handle_connect_mqtt():
    print('Attempting to connect to MQTT broker...')
    success = connect_mqtt()
    if success:
        emit('connect_response', {'success': True})
    else:
        emit('connect_response', {'success': False, 'error': 'Connection failed'})

@socketio.on('disconnect_mqtt')
def handle_disconnect_mqtt():
    global mqtt_client
    if mqtt_client:
        mqtt_client.disconnect()
        mqtt_client.loop_stop()
        emit('disconnect_response', {'success': True})
        emit('mqtt_status', {'status': 'disconnected'})

if __name__ == '__main__':
    # Load site configurations
    print("Loading site configurations...")
    load_site_configurations()

    # Connect to MQTT broker on startup
    print("Starting MQTT WatchDog...")
    print(f"Connecting to broker: {mqtt_config['broker']}:{mqtt_config['port']}")
    print(f"Subscribing to topic: {mqtt_config['topic']}")
    connect_mqtt()

    # Start monitoring scheduler
    start_monitoring_scheduler()

    # Get port from environment or default to 5000 (Railway compatibility)
    port = int(os.environ.get('PORT', 5000))

    # Start the web server with eventlet for production
    socketio.run(app, host='0.0.0.0', port=port, allow_unsafe_werkzeug=True)
