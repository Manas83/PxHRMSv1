// Geolocation handling for HRMS attendance system

let userLocation = null;
let watchId = null;

// Configuration
const LOCATION_CONFIG = {
    enableHighAccuracy: true,
    timeout: 10000,
    maximumAge: 300000 // 5 minutes
};

// Initialize geolocation
function initializeGeolocation() {
    if (navigator.geolocation) {
        console.log('Geolocation is supported');
        getCurrentLocation();
    } else {
        console.error('Geolocation is not supported by this browser');
        showLocationError('Geolocation is not supported by your browser');
    }
}

// Get current location
function getCurrentLocation() {
    return new Promise((resolve, reject) => {
        if (!navigator.geolocation) {
            reject(new Error('Geolocation is not supported by this browser.'));
            return;
        }

        navigator.geolocation.getCurrentPosition(
            position => {
                userLocation = {
                    latitude: position.coords.latitude,
                    longitude: position.coords.longitude
                };
                resolve(userLocation);
            },
            error => {
                let errorMessage = 'An unknown error occurred.';
                switch(error.code) {
                    case error.PERMISSION_DENIED:
                        errorMessage = 'User denied the request for Geolocation.';
                        break;
                    case error.POSITION_UNAVAILABLE:
                        errorMessage = 'Location information is unavailable.';
                        break;
                    case error.TIMEOUT:
                        errorMessage = 'The request to get user location timed out.';
                        break;
                }
                reject(new Error(errorMessage));
            },
            {
                enableHighAccuracy: true,
                timeout: 10000,
                maximumAge: 0
            }
        );
    });
}

// Handle location errors
function handleLocationError(error) {
    let errorMessage = '';

    switch(error.code) {
        case error.PERMISSION_DENIED:
            errorMessage = 'Location access denied by user. Attendance will be recorded without location.';
            break;
        case error.POSITION_UNAVAILABLE:
            errorMessage = 'Location information is unavailable. Please try again.';
            break;
        case error.TIMEOUT:
            errorMessage = 'Location request timed out. Please try again.';
            break;
        default:
            errorMessage = 'An unknown error occurred while retrieving location.';
            break;
    }

    showLocationError(errorMessage);
}

// Show location success
function showLocationSuccess() {
    const locationStatus = document.getElementById('locationStatus');
    if (locationStatus) {
        locationStatus.innerHTML = '<i class="fas fa-check-circle"></i> Location detected successfully';
        locationStatus.className = 'alert alert-success';
    }
}

// Show location error
function showLocationError(message) {
    const locationStatus = document.getElementById('locationStatus');
    if (locationStatus) {
        locationStatus.innerHTML = '<i class="fas fa-exclamation-triangle"></i> ' + message;
        locationStatus.className = 'alert alert-warning';
    }
}

// Update location display
function updateLocationDisplay() {
    if (userLocation) {
        const locationInfo = document.getElementById('locationInfo');
        if (locationInfo) {
            locationInfo.innerHTML = `
                <small class="text-muted">
                    <i class="fas fa-map-marker-alt"></i>
                    Lat: ${userLocation.latitude.toFixed(6)}, 
                    Lng: ${userLocation.longitude.toFixed(6)}
                    (±${Math.round(0)}m)
                </small>
            `;
        }
    }
}

// Submit attendance with location
function submitAttendance(action) {
    const form = document.getElementById('attendanceForm');
    const submitBtn = document.getElementById('submitBtn');

    if (!form) {
        console.error('Attendance form not found');
        return;
    }

    // Disable submit button to prevent double submission
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
    }

    // Add location data to form if available
    if (userLocation) {
        // Remove existing location inputs
        const existingLatInput = form.querySelector('input[name="latitude"]');
        const existingLngInput = form.querySelector('input[name="longitude"]');
        const existingAccInput = form.querySelector('input[name="accuracy"]');

        if (existingLatInput) existingLatInput.remove();
        if (existingLngInput) existingLngInput.remove();
        if (existingAccInput) existingAccInput.remove();

        // Add new location inputs
        const latInput = document.createElement('input');
        latInput.type = 'hidden';
        latInput.name = 'latitude';
        latInput.value = userLocation.latitude;
        form.appendChild(latInput);

        const lngInput = document.createElement('input');
        lngInput.type = 'hidden';
        lngInput.name = 'longitude';
        lngInput.value = userLocation.longitude;
        form.appendChild(lngInput);

        const accInput = document.createElement('input');
        accInput.type = 'hidden';
        accInput.name = 'accuracy';
        accInput.value = 0;
        form.appendChild(accInput);
    }

    // Add action to form
    const actionInput = document.createElement('input');
    actionInput.type = 'hidden';
    actionInput.name = 'action';
    actionInput.value = action;
    form.appendChild(actionInput);

    // Submit form
    form.submit();
}

// Check work mode based on location
function checkWorkMode(latitude, longitude) {
    // This is a simplified check - in real implementation,
    // you would check against office coordinates with a radius
    const officeCoordinates = {
        latitude: 40.7128,  // Example: NYC coordinates
        longitude: -74.0060,
        radius: 100 // meters
    };

    if (latitude && longitude) {
        const distance = calculateDistance(
            latitude, longitude,
            officeCoordinates.latitude, officeCoordinates.longitude
        );

        return distance <= officeCoordinates.radius ? 'onsite' : 'offsite';
    }

    return 'unknown';
}

// Calculate distance between two coordinates (Haversine formula)
function calculateDistance(lat1, lon1, lat2, lon2) {
    const R = 6371e3; // Earth's radius in meters
    const φ1 = lat1 * Math.PI/180;
    const φ2 = lat2 * Math.PI/180;
    const Δφ = (lat2-lat1) * Math.PI/180;
    const Δλ = (lon2-lon1) * Math.PI/180;

    const a = Math.sin(Δφ/2) * Math.sin(Δφ/2) +
              Math.cos(φ1) * Math.cos(φ2) *
              Math.sin(Δλ/2) * Math.sin(Δλ/2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));

    return R * c; // Distance in meters
}

function allowPunchWithoutLocation() {
    userLocation = null;
    return Promise.resolve(null);
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    // Only initialize geolocation on attendance pages
    if (document.getElementById('attendanceForm') || document.getElementById('locationStatus')) {
        initializeGeolocation();
    }

    // Add event listeners for punch buttons
    const punchInBtn = document.getElementById('punchInBtn');
    const punchOutBtn = document.getElementById('punchOutBtn');

    if (punchInBtn) {
        punchInBtn.addEventListener('click', function() {
            submitAttendance('punch_in');
        });
    }

    if (punchOutBtn) {
        punchOutBtn.addEventListener('click', function() {
            submitAttendance('punch_out');
        });
    }
});

// Export functions for global access
window.GeolocationManager = {
    getCurrentLocation: getCurrentLocation,
    submitAttendance: submitAttendance,
    userLocation: function() { return userLocation; },
    checkWorkMode: checkWorkMode
};

// Make functions available globally
window.getCurrentLocation = getCurrentLocation;
window.allowPunchWithoutLocation = allowPunchWithoutLocation;
window.userLocation = userLocation;