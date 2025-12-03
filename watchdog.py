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

    socketio.emit('mqtt_message', message_data, namespace='/')
    print(f"[{timestamp}] Topic: {msg.topic} | Payload: {payload}")

def on_disconnect(_client, _userdata, _rc):
    print("Disconnected from MQTT Broker")
    socketio.emit('mqtt_status', {'status': 'disconnected'}, namespace='/')

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

    # Get port from environment or default to 5000 (Railway compatibility)
    port = int(os.environ.get('PORT', 5000))

    # Start the web server with eventlet for production
    socketio.run(app, host='0.0.0.0', port=port, allow_unsafe_werkzeug=True)
