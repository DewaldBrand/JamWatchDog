const modal = document.getElementById('site-modal');
const addSiteBtn = document.getElementById('add-site-btn');
const closeBtn = document.querySelector('.close');
const cancelBtn = document.getElementById('cancel-btn');
const siteForm = document.getElementById('site-form');
const sitesList = document.getElementById('sites-list');

let isEditMode = false;

// Load sites on page load
document.addEventListener('DOMContentLoaded', () => {
    loadSites();
    checkForAutoAdd();
});

// Check if we should auto-open the add modal with pre-filled data
function checkForAutoAdd() {
    const urlParams = new URLSearchParams(window.location.search);
    const addSiteId = urlParams.get('add');
    const devices = urlParams.get('devices');

    if (addSiteId) {
        // Open modal with pre-filled site ID
        isEditMode = false;
        document.getElementById('modal-title').textContent = 'Add New Site';
        siteForm.reset();
        document.getElementById('edit-site-id').value = '';
        document.getElementById('site-id').value = addSiteId;
        document.getElementById('site-id').disabled = false;
        document.getElementById('site-active').checked = true;

        // Check devices if provided
        if (devices) {
            const deviceList = devices.split(',');
            document.querySelectorAll('.device-checkbox').forEach(cb => {
                cb.checked = deviceList.includes(cb.value);
            });
        } else {
            document.querySelectorAll('.device-checkbox').forEach(cb => cb.checked = true);
        }

        modal.classList.add('show');

        // Clear URL parameters
        window.history.replaceState({}, document.title, '/config');
    }
}

// Open modal for adding new site
addSiteBtn.addEventListener('click', () => {
    isEditMode = false;
    document.getElementById('modal-title').textContent = 'Add New Site';
    siteForm.reset();
    document.getElementById('edit-site-id').value = '';
    document.getElementById('site-id').disabled = false;
    document.getElementById('site-active').checked = true;
    document.querySelectorAll('.device-checkbox').forEach(cb => cb.checked = true);
    modal.classList.add('show');
});

// Close modal
closeBtn.addEventListener('click', closeModal);
cancelBtn.addEventListener('click', closeModal);

window.addEventListener('click', (e) => {
    if (e.target === modal) {
        closeModal();
    }
});

function closeModal() {
    modal.classList.remove('show');
}

// Handle form submission
siteForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const siteId = document.getElementById('site-id').value.trim();
    const editSiteId = document.getElementById('edit-site-id').value;

    const activeDevices = [];
    document.querySelectorAll('.device-checkbox:checked').forEach(cb => {
        activeDevices.push(cb.value);
    });

    const siteData = {
        site_id: siteId,
        site_name: document.getElementById('site-name').value.trim(),
        location: document.getElementById('site-location').value.trim(),
        responsible_person: document.getElementById('responsible-person').value.trim(),
        contact_email: document.getElementById('contact-email').value.trim(),
        contact_phone: document.getElementById('contact-phone').value.trim(),
        active: document.getElementById('site-active').checked,
        active_devices: activeDevices
    };

    try {
        let response;
        if (isEditMode && editSiteId) {
            // Update existing site
            response = await fetch(`/api/sites/${editSiteId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(siteData)
            });
        } else {
            // Create new site
            response = await fetch('/api/sites', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(siteData)
            });
        }

        const result = await response.json();

        if (response.ok) {
            showNotification(result.message || 'Site saved successfully', 'success');
            closeModal();
            loadSites();
        } else {
            showNotification(result.error || 'Failed to save site', 'error');
        }
    } catch (error) {
        showNotification('Error saving site: ' + error.message, 'error');
    }
});

// Load sites from server
async function loadSites() {
    try {
        const response = await fetch('/api/sites');
        const data = await response.json();

        if (data.sites && Object.keys(data.sites).length > 0) {
            renderSites(data.sites);
        } else {
            showEmptyState();
        }
    } catch (error) {
        console.error('Error loading sites:', error);
        showNotification('Error loading sites', 'error');
    }
}

// Render sites list
function renderSites(sites) {
    sitesList.innerHTML = '';

    Object.entries(sites).forEach(([siteId, site]) => {
        const siteCard = document.createElement('div');
        siteCard.className = `site-card ${site.active ? 'active' : 'inactive'}`;

        const deviceBadges = site.active_devices.map(device =>
            `<span class="device-badge enabled">${device}</span>`
        ).join('');

        const allDevices = ['GSM-1', 'GSM-2', 'ESP'];
        const inactiveDevices = allDevices.filter(d => !site.active_devices.includes(d));
        const inactiveBadges = inactiveDevices.map(device =>
            `<span class="device-badge disabled">${device}</span>`
        ).join('');

        siteCard.innerHTML = `
            <div class="site-info">
                <div class="site-header">
                    <span class="site-id">${siteId}</span>
                    <span class="site-name">${site.site_name}</span>
                    <span class="site-badge ${site.active ? 'active' : 'inactive'}">
                        ${site.active ? 'Active' : 'Inactive'}
                    </span>
                </div>
                <div class="site-details">
                    <div class="site-detail">
                        <span class="site-detail-label">Location</span>
                        <span class="site-detail-value">${site.location}</span>
                    </div>
                    <div class="site-detail">
                        <span class="site-detail-label">Responsible Person</span>
                        <span class="site-detail-value">${site.responsible_person}</span>
                    </div>
                    <div class="site-detail">
                        <span class="site-detail-label">Contact Phone</span>
                        <span class="site-detail-value">${site.contact_phone}</span>
                    </div>
                    ${site.contact_email ? `
                    <div class="site-detail">
                        <span class="site-detail-label">Contact Email</span>
                        <span class="site-detail-value">${site.contact_email}</span>
                    </div>
                    ` : ''}
                </div>
                <div class="site-detail">
                    <span class="site-detail-label">Active Devices</span>
                    <div class="device-badges">
                        ${deviceBadges}
                        ${inactiveBadges}
                    </div>
                </div>
            </div>
            <div class="site-actions">
                <button class="btn btn-small btn-edit" onclick="editSite('${siteId}')">Edit</button>
                <button class="btn btn-small btn-delete" onclick="deleteSite('${siteId}')">Delete</button>
            </div>
        `;

        sitesList.appendChild(siteCard);
    });
}

// Show empty state
function showEmptyState() {
    sitesList.innerHTML = `
        <div class="empty-state">
            <div class="empty-state-icon">📍</div>
            <div class="empty-state-text">No sites configured yet</div>
            <p>Click "Add New Site" to get started</p>
        </div>
    `;
}

// Edit site
async function editSite(siteId) {
    try {
        const response = await fetch(`/api/sites/${siteId}`);
        const site = await response.json();

        if (response.ok) {
            isEditMode = true;
            document.getElementById('modal-title').textContent = 'Edit Site';
            document.getElementById('edit-site-id').value = siteId;
            document.getElementById('site-id').value = siteId;
            document.getElementById('site-id').disabled = true;
            document.getElementById('site-name').value = site.site_name;
            document.getElementById('site-location').value = site.location;
            document.getElementById('responsible-person').value = site.responsible_person;
            document.getElementById('contact-email').value = site.contact_email || '';
            document.getElementById('contact-phone').value = site.contact_phone;
            document.getElementById('site-active').checked = site.active;

            // Set device checkboxes
            document.querySelectorAll('.device-checkbox').forEach(cb => {
                cb.checked = site.active_devices.includes(cb.value);
            });

            modal.classList.add('show');
        } else {
            showNotification('Error loading site details', 'error');
        }
    } catch (error) {
        showNotification('Error loading site: ' + error.message, 'error');
    }
}

// Delete site
async function deleteSite(siteId) {
    if (!confirm(`Are you sure you want to delete site ${siteId}?`)) {
        return;
    }

    try {
        const response = await fetch(`/api/sites/${siteId}`, {
            method: 'DELETE'
        });

        const result = await response.json();

        if (response.ok) {
            showNotification(result.message || 'Site deleted successfully', 'success');
            loadSites();
        } else {
            showNotification(result.error || 'Failed to delete site', 'error');
        }
    } catch (error) {
        showNotification('Error deleting site: ' + error.message, 'error');
    }
}

// Show notification
function showNotification(message, type = 'success') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    document.body.appendChild(notification);

    setTimeout(() => {
        notification.remove();
    }, 3000);
}
