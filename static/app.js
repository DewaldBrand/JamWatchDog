const socket = io();

let messageCount = 0;

socket.on('connect', () => {
    console.log('Connected to server');
});

socket.on('disconnect', () => {
    console.log('Disconnected from server');
    updateStatus('disconnected');
});

socket.on('mqtt_status', (data) => {
    console.log('MQTT Status:', data);
    if (data.status === 'connected') {
        updateStatus('connected', data.broker, data.topic);
    } else {
        updateStatus('disconnected', data.error);
    }
});

socket.on('mqtt_message', (data) => {
    addMessage(data);
});

socket.on('connect_response', (data) => {
    if (data.success) {
        showNotification('Connected to MQTT broker', 'success');
    } else {
        showNotification('Failed to connect: ' + data.error, 'error');
    }
});

socket.on('disconnect_response', () => {
    showNotification('Disconnected from MQTT broker', 'info');
});

document.getElementById('connect-btn').addEventListener('click', () => {
    socket.emit('connect_mqtt');
    showNotification('Connecting to MQTT broker...', 'info');
});

document.getElementById('disconnect-btn').addEventListener('click', () => {
    socket.emit('disconnect_mqtt');
});

document.getElementById('clear-btn').addEventListener('click', () => {
    const tbody = document.getElementById('messages-body');
    tbody.innerHTML = '';
    messageCount = 0;
    updateMessageCount();
    showNotification('Messages cleared', 'info');
});

function updateStatus(status, _broker = '', topic = '') {
    const statusIndicator = document.getElementById('status-indicator');
    statusIndicator.className = `status ${status}`;

    if (status === 'connected') {
        statusIndicator.textContent = `Connected | Topic: ${topic}`;
    } else {
        statusIndicator.textContent = 'Disconnected';
    }
}

function addMessage(data) {
    const tbody = document.getElementById('messages-body');

    const row = document.createElement('tr');
    row.className = 'new-message';

    const timestampCell = document.createElement('td');
    timestampCell.textContent = data.timestamp;

    const topicCell = document.createElement('td');
    topicCell.textContent = data.topic;

    const payloadCell = document.createElement('td');

    try {
        const jsonPayload = JSON.parse(data.payload);
        payloadCell.textContent = JSON.stringify(jsonPayload, null, 2);
        payloadCell.style.fontFamily = "'Courier New', monospace";
        payloadCell.style.whiteSpace = 'pre-wrap';
    } catch {
        payloadCell.textContent = data.payload;
    }

    row.appendChild(timestampCell);
    row.appendChild(topicCell);
    row.appendChild(payloadCell);

    tbody.insertBefore(row, tbody.firstChild);

    messageCount++;
    updateMessageCount();

    const maxMessages = 1000;
    if (tbody.children.length > maxMessages) {
        tbody.removeChild(tbody.lastChild);
    }
}

function updateMessageCount() {
    document.getElementById('message-count').textContent = `(${messageCount})`;
}

function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.style.position = 'fixed';
    notification.style.top = '20px';
    notification.style.right = '20px';
    notification.style.padding = '15px 20px';
    notification.style.borderRadius = '8px';
    notification.style.color = 'white';
    notification.style.fontWeight = '500';
    notification.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.15)';
    notification.style.zIndex = '1000';
    notification.style.animation = 'slideIn 0.3s ease-out';
    notification.textContent = message;

    const colors = {
        success: '#10b981',
        error: '#ef4444',
        info: '#3b82f6'
    };

    notification.style.background = colors[type] || colors.info;

    document.body.appendChild(notification);

    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-in';
        setTimeout(() => {
            document.body.removeChild(notification);
        }, 300);
    }, 3000);
}

const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(400px);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }

    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(400px);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);
