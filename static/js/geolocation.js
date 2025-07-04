// Geolocation handling for HRMS attendance system
class GeolocationHandler {
    constructor() {
        this.watchId = null;
        this.currentPosition = null;
        this.options = {
            enableHighAccuracy: true,
            timeout: 10000,
            maximumAge: 60000 // 1 minute
        };
    }

    // Get current position
    getCurrentPosition() {
        return new Promise((resolve, reject) => {
            if (!navigator.geolocation) {
                reject(new Error('Geolocation is not supported by this browser'));
                return;
            }

            navigator.geolocation.getCurrentPosition(
                (position) => {
                    this.currentPosition = position;
                    resolve(position);
                },
                (error) => {
                    reject(this.handleGeolocationError(error));
                },
                this.options
            );
        });
    }

    // Watch position continuously
    watchPosition() {
        if (!navigator.geolocation) {
            console.warn('Geolocation is not supported by this browser');
            return;
        }

        this.watchId = navigator.geolocation.watchPosition(
            (position) => {
                this.currentPosition = position;
                this.updateLocationDisplay(position);
            },
            (error) => {
                console.warn('Geolocation error:', this.handleGeolocationError(error));
            },
            this.options
        );
    }

    // Stop watching position
    stopWatching() {
        if (this.watchId !== null) {
            navigator.geolocation.clearWatch(this.watchId);
            this.watchId = null;
        }
    }

    // Handle geolocation errors
    handleGeolocationError(error) {
        switch (error.code) {
            case error.PERMISSION_DENIED:
                return new Error('Location access denied by user');
            case error.POSITION_UNAVAILABLE:
                return new Error('Location information is unavailable');
            case error.TIMEOUT:
                return new Error('Location request timed out');
            default:
                return new Error('An unknown location error occurred');
        }
    }

    // Update location display on page
    updateLocationDisplay(position) {
        const locationElements = document.querySelectorAll('.current-location');
        const coords = position.coords;

        locationElements.forEach(element => {
            element.innerHTML = `
                <i class="fas fa-map-marker-alt me-1"></i>
                Lat: ${coords.latitude.toFixed(6)}, 
                Lng: ${coords.longitude.toFixed(6)}
                <small class="text-muted">(±${coords.accuracy}m)</small>
            `;
        });
    }

    // Check if user is within office premises (simplified geofencing)
    isWithinOfficePremises(position, officeLocation, radiusMeters = 100) {
        const lat1 = position.coords.latitude;
        const lon1 = position.coords.longitude;
        const lat2 = officeLocation.latitude;
        const lon2 = officeLocation.longitude;

        const distance = this.calculateDistance(lat1, lon1, lat2, lon2);
        return distance <= radiusMeters;
    }

    // Calculate distance between two coordinates using Haversine formula
    calculateDistance(lat1, lon1, lat2, lon2) {
        const R = 6371e3; // Earth's radius in meters
        const φ1 = lat1 * Math.PI / 180;
        const φ2 = lat2 * Math.PI / 180;
        const Δφ = (lat2 - lat1) * Math.PI / 180;
        const Δλ = (lon2 - lon1) * Math.PI / 180;

        const a = Math.sin(Δφ / 2) * Math.sin(Δφ / 2) +
                  Math.cos(φ1) * Math.cos(φ2) *
                  Math.sin(Δλ / 2) * Math.sin(Δλ / 2);
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

        return R * c; // Distance in meters
    }

    // Get address from coordinates (reverse geocoding)
    async getAddressFromCoordinates(latitude, longitude) {
        try {
            // Using a free geocoding service (OpenStreetMap Nominatim)
            const response = await fetch(
                `https://nominatim.openstreetmap.org/reverse?format=json&lat=${latitude}&lon=${longitude}&zoom=18&addressdetails=1`
            );

            if (!response.ok) {
                throw new Error('Geocoding service unavailable');
            }

            const data = await response.json();
            return data.display_name || 'Address not found';
        } catch (error) {
            console.warn('Reverse geocoding failed:', error);
            return `${latitude.toFixed(6)}, ${longitude.toFixed(6)}`;
        }
    }

    // Format position for display
    formatPosition(position) {
        return {
            latitude: position.coords.latitude.toFixed(6),
            longitude: position.coords.longitude.toFixed(6),
            accuracy: Math.round(position.coords.accuracy),
            timestamp: new Date(position.timestamp).toLocaleString()
        };
    }
}

// Initialize geolocation handler
const geoHandler = new GeolocationHandler();

// Punch-in/out with location
async function punchWithLocation(action) {
    const punchBtn = document.getElementById(action === 'in' ? 'punchInBtn' : 'punchOutBtn');

    if (punchBtn) {
        // Show loading state
        const originalContent = punchBtn.innerHTML;
        punchBtn.disabled = true;
        punchBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Getting location...';
    }

    try {
        // Get current position
        const position = await geoHandler.getCurrentPosition();
        const coords = position.coords;

        // Prepare punch data
        const punchData = {
            latitude: coords.latitude,
            longitude: coords.longitude,
            accuracy: coords.accuracy,
            timestamp: position.timestamp
        };

        // Send punch request
        const url = action === 'in' ? '/employee/punch-in' : '/employee/punch-out';

        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(punchData)
        });

        const result = await response.json();

        if (result.success) {
            if (window.HRMS) {
                window.HRMS.showNotification(result.message, 'success');
            }
            // Reload page to update UI
            setTimeout(() => location.reload(), 1000);
        } else {
            throw new Error(result.message || 'Punch failed');
        }

    } catch (error) {
        console.error('Punch error:', error);

        if (window.HRMS) {
            window.HRMS.showNotification(
                error.message || 'Unable to record attendance. Please try again.',
                'danger'
            );
        } else {
            alert(error.message || 'Unable to record attendance. Please try again.');
        }

        // Restore button state
        if (punchBtn) {
            punchBtn.disabled = false;
            punchBtn.innerHTML = originalContent;
        }
        }
    }
}

// Request location permission on page load
document.addEventListener('DOMContentLoaded', function() {
    // Check if geolocation is supported
    if (navigator.geolocation) {
        // Request permission and get initial position
        geoHandler.getCurrentPosition()
            .then(position => {
                console.log('Initial position obtained:', geoHandler.formatPosition(position));

                // Update any location displays on the page
                geoHandler.updateLocationDisplay(position);
            })
            .catch(error => {
                console.warn('Initial geolocation failed:', error.message);

                // Show warning to user
                const locationWarning = document.querySelector('.location-warning');
                if (locationWarning) {
                    locationWarning.style.display = 'block';
                }
            });

        // Start watching position if on dashboard
        if (window.location.pathname.includes('dashboard')) {
            geoHandler.watchPosition();
        }
    } else {
        console.warn('Geolocation not supported');

        // Hide location-dependent features
        const locationElements = document.querySelectorAll('.requires-location');
        locationElements.forEach(element => {
            element.style.display = 'none';
        });
    }

    // Bind punch buttons to location-aware functions
    const punchInBtn = document.getElementById('punchInBtn');
    const punchOutBtn = document.getElementById('punchOutBtn');

    if (punchInBtn) {
        punchInBtn.addEventListener('click', (e) => {
            e.preventDefault();
            punchWithLocation('in');
        });
    }

    if (punchOutBtn) {
        punchOutBtn.addEventListener('click', (e) => {
            e.preventDefault();
            punchWithLocation('out');
        });
    }
});

// Cleanup on page unload
window.addEventListener('beforeunload', function() {
    geoHandler.stopWatching();
});

// Export for use in other scripts
window.GeolocationHandler = GeolocationHandler;
window.geoHandler = geoHandler;
window.punchWithLocation = punchWithLocation;