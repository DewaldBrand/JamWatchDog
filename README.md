# MQTT Message Monitor

A web-based Python application for monitoring MQTT messages in real-time with a timestamped grid display.

## Features

- Real-time MQTT message monitoring
- Hardcoded broker settings for security (configured in watchdog.py)
- Optional authentication support (username/password)
- Timestamped message grid with automatic updates
- Clean, modern web interface
- WebSocket-based live updates
- Message persistence (keeps last 1000 messages)

## Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

## Configuration

**IMPORTANT:** For security reasons, all MQTT broker settings are configured directly in the `watchdog.py` file.

Edit the configuration section in [watchdog.py](watchdog.py) (lines 14-24):

```python
mqtt_config = {
    'broker': 'localhost',        # MQTT broker address
    'port': 1883,                 # MQTT broker port
    'topic': '#',                 # Topic to subscribe to
    'username': '',               # MQTT username (optional)
    'password': ''                # MQTT password (optional)
}
```

### Topic Examples:
- `#` - Subscribe to all topics
- `sensors/#` - Subscribe to all topics under sensors/
- `sensors/temperature` - Subscribe to a specific topic

## Running the Application

1. Configure your MQTT settings in watchdog.py
2. Start the Flask application:
```bash
python watchdog.py
```

3. Open your web browser and navigate to:
```
http://localhost:5000
```

The application will automatically connect to the configured MQTT broker on startup.

## Usage

1. Start the application (it connects automatically to the configured broker)
2. Open the web interface in your browser
3. Messages will appear in the grid with:
   - Timestamp (when the message was received)
   - Topic (the MQTT topic)
   - Payload (the message content)
4. Use "Clear Messages" to clear the display

## Features

- Messages are displayed in reverse chronological order (newest first)
- JSON payloads are automatically formatted for readability
- The interface shows connection status and subscribed topic in real-time
- Supports up to 1000 messages in the display buffer
- Responsive design works on desktop and mobile devices
- Secure: No configuration changes possible through web interface

## Requirements

- Python 3.7+
- MQTT Broker (local or remote)
- Modern web browser with WebSocket support
