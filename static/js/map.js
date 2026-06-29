let citizenPickerMap = null;
let citizenMarker = null;

let dashboardMap = null;
let dashboardMarkers = [];

// Initialize map for picking location when reporting issues
function initCitizenPickerMap(defaultLat = 40.7128, defaultLng = -74.0060) {
    if (citizenPickerMap) {
        citizenPickerMap.remove();
    }
    
    citizenPickerMap = L.map('citizen-picker-map').setView([defaultLat, defaultLng], 13);
    
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors'
    }).addTo(citizenPickerMap);
    
    // Set initial values
    document.getElementById('report-lat').value = defaultLat.toFixed(6);
    document.getElementById('report-lng').value = defaultLng.toFixed(6);
    
    // Initial marker
    citizenMarker = L.marker([defaultLat, defaultLng], { draggable: true }).addTo(citizenPickerMap);
    
    // Handle dragend event to update input values
    citizenMarker.on('dragend', function (e) {
        const position = citizenMarker.getLatLng();
        document.getElementById('report-lat').value = position.lat.toFixed(6);
        document.getElementById('report-lng').value = position.lng.toFixed(6);
    });
    
    // Handle click on map to move marker
    citizenPickerMap.on('click', function (e) {
        const position = e.latlng;
        citizenMarker.setLatLng(position);
        document.getElementById('report-lat').value = position.lat.toFixed(6);
        document.getElementById('report-lng').value = position.lng.toFixed(6);
    });
}

// Update picker map location (e.g. from GPS coordinates)
function updateCitizenPickerLocation(lat, lng) {
    if (citizenPickerMap && citizenMarker) {
        const latLng = L.latLng(lat, lng);
        citizenPickerMap.setView(latLng, 15);
        citizenMarker.setLatLng(latLng);
        document.getElementById('report-lat').value = lat.toFixed(6);
        document.getElementById('report-lng').value = lng.toFixed(6);
    }
}

// Initialize and populate dashboard map showing all open reports
function initDashboardMap(issues = []) {
    if (dashboardMap) {
        dashboardMap.remove();
    }
    
    // Default center to NYC or average of issue coordinates
    let centerLat = 40.7128;
    let centerLng = -74.0060;
    
    if (issues.length > 0) {
        const sumLat = issues.reduce((acc, issue) => acc + issue.latitude, 0);
        const sumLng = issues.reduce((acc, issue) => acc + issue.longitude, 0);
        centerLat = sumLat / issues.length;
        centerLng = sumLng / issues.length;
    }
    
    dashboardMap = L.map('dashboard-map').setView([centerLat, centerLng], 12);
    
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors'
    }).addTo(dashboardMap);
    
    // Clear old markers
    dashboardMarkers.forEach(m => dashboardMap.removeLayer(m));
    dashboardMarkers = [];
    
    // Drop issue pins
    issues.forEach(issue => {
        const marker = L.marker([issue.latitude, issue.longitude]).addTo(dashboardMap);
        
        const popupContent = `
            <div style="font-family: 'Inter', sans-serif; color: #1e293b;">
                <h4 style="margin-bottom: 4px; font-weight: 700;">#${issue.id}: ${issue.title}</h4>
                <p style="font-size: 0.8rem; margin-bottom: 6px;">Category: <strong>${issue.category}</strong></p>
                <span class="priority-tag" style="background-color: #3b82f6; color: white; padding: 2px 6px; border-radius: 4px; font-size: 0.7rem;">${issue.priority}</span>
                <span class="status-tag" style="background-color: #64748b; color: white; padding: 2px 6px; border-radius: 4px; font-size: 0.7rem;">${issue.status}</span>
                <div style="margin-top: 8px;">
                    <button onclick="showIssueDetails(${issue.id})" style="background: #4f46e5; color: white; border: none; padding: 4px 8px; border-radius: 4px; font-size: 0.75rem; cursor: pointer;">Details</button>
                </div>
            </div>
        `;
        
        marker.bindPopup(popupContent);
        dashboardMarkers.push(marker);
    });
}
