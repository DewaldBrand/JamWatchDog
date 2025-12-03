const socket = io();

let messageCount = 0;
let countdownValue = 60;
let countdownInterval = null;

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

socket.on('site_status_update', (data) => {
    updateSiteMonitoring(data.sites);
});

socket.on('clear_messages', () => {
    const tbody = document.getElementById('messages-body');
    tbody.innerHTML = '';
    messageCount = 0;
    updateMessageCount();
    console.log('Messages table cleared automatically');
});

socket.on('unconfigured_sites_update', (data) => {
    updateUnconfiguredSites(data.sites);
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

function updateSiteMonitoring(sites) {
    const tbody = document.getElementById('sites-body');

    if (!sites || sites.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="no-sites">No sites detected yet. Waiting for MQTT messages...</td></tr>';
        return;
    }

    // Reset countdown when update received
    resetCountdown();

    tbody.innerHTML = '';

    const alertLabels = ['ALL OK', 'ALERT 1', 'ALERT 2', 'ALERT 3'];

    sites.forEach(site => {
        const row = document.createElement('tr');
        row.className = 'site-row';
        row.style.borderLeftColor = site.color;

        const alertLabel = alertLabels[site.alert_level];

        // Received devices
        let receivedHTML = '';
        site.received.forEach(dev => {
            receivedHTML += `<span class="device-item device-received">✓ ${dev}</span>`;
        });

        // Missing devices
        let missingHTML = '';
        site.missing.forEach(dev => {
            missingHTML += `<span class="device-item device-missing">✗ ${dev}</span>`;
        });

        row.innerHTML = `
            <td><strong>${site.site_id}</strong></td>
            <td><span class="site-status-badge" style="background: ${site.color}">${alertLabel}</span></td>
            <td class="device-count">${site.total_received}/${site.total_expected}</td>
            <td class="device-list-cell">${receivedHTML || '-'}</td>
            <td class="device-list-cell">${missingHTML || '-'}</td>
        `;

        tbody.appendChild(row);
    });
}

function startCountdown() {
    if (countdownInterval) {
        clearInterval(countdownInterval);
    }

    countdownInterval = setInterval(() => {
        countdownValue--;
        document.getElementById('countdown').textContent = countdownValue;

        if (countdownValue <= 0) {
            countdownValue = 60;
        }
    }, 1000);
}

function resetCountdown() {
    countdownValue = 60;
    document.getElementById('countdown').textContent = countdownValue;
}

function updateUnconfiguredSites(sites) {
    const panel = document.getElementById('unconfigured-panel');
    const tbody = document.getElementById('unconfigured-body');
    const countBadge = document.getElementById('orphan-count');

    if (!sites || sites.length === 0) {
        panel.style.display = 'none';
        return;
    }

    panel.style.display = 'block';
    countBadge.textContent = sites.length;
    tbody.innerHTML = '';

    sites.forEach(site => {
        const row = document.createElement('tr');

        // Device list
        const deviceTags = site.devices.map(dev =>
            `<span class="device-tag">${dev}</span>`
        ).join('');

        row.innerHTML = `
            <td><strong>${site.site_id}</strong></td>
            <td><div class="device-list">${deviceTags}</div></td>
            <td style="text-align: center;">${site.device_count}</td>
            <td>${site.first_seen}</td>
            <td>${site.last_seen}</td>
            <td>
                <button class="btn-configure" onclick="configureOrphanSite('${site.site_id}', ${JSON.stringify(site.devices).replace(/"/g, '&quot;')})">
                    Configure
                </button>
            </td>
        `;

        tbody.appendChild(row);
    });
}

function configureOrphanSite(siteId, devices) {
    // Redirect to config page with site ID pre-filled
    window.location.href = `/config?add=${siteId}&devices=${devices.join(',')}`;
}

// Start countdown on page load
startCountdown();

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
