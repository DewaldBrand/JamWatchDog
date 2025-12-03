from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import paho.mqtt.client as mqtt
from datetime import datetime
import os

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
# =============================================================================

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

            # Initialize site if not exists
            if site_id not in sites_data:
                sites_data[site_id] = {}
                current_minute_messages[site_id] = set()

            # Update device last seen
            sites_data[site_id][device_name] = {
                'last_seen': datetime.now(),
                'timestamp': timestamp
            }

            # Track for current minute analysis
            current_minute_messages[site_id].add(device_name)

            print(f"[{timestamp}] Site: {site_id} | Device: {device_name}")
    except Exception as e:
        print(f"Error parsing payload: {e}")

    socketio.emit('mqtt_message', message_data, namespace='/')
    print(f"[{timestamp}] Topic: {msg.topic} | Payload: {payload}")

def on_disconnect(_client, _userdata, _rc):
    print("Disconnected from MQTT Broker")
    socketio.emit('mqtt_status', {'status': 'disconnected'}, namespace='/')

def check_site_status():
    """Check each site's status and calculate alert levels"""
    global current_minute_messages

    site_statuses = []

    for site_id in sites_data.keys():
        received_devices = current_minute_messages.get(site_id, set())
        expected_devices = set(EXPECTED_DEVICES_PER_SITE)

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
        print(f"Site {site_id}: Alert Level {alert_level}, Received: {len(received_devices)}/3")

    # Emit update to all clients
    socketio.emit('site_status_update', {'sites': site_statuses}, namespace='/')

    # Clear current minute tracking
    current_minute_messages = {site_id: set() for site_id in sites_data.keys()}

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
