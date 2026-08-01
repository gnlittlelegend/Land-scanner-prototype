/**
 * Land Scanner Frontend Application
 * Handles polygon input, analysis requests, and results display
 */

// Configuration - Frontend (Static Site) calls backend API
const API_BASE = "https://land-scanner-prototype-backend.onrender.com";
const API_TIMEOUT = 60000; // 60 seconds

// Global state
let currentPolygon = null;
let analysisInProgress = false;

/**
 * Initialize the application when DOM is ready
 */
document.addEventListener('DOMContentLoaded', function() {
    initializeMap();
    attachEventListeners();
});

/**
 * Initialize Leaflet map with OpenStreetMap tiles
 * Task 11.2: Implement Leaflet map display
 */
function initializeMap() {
    // Initialize map with default center and zoom
    const map = L.map('map').setView([20, 0], 2);
    
    // Add OpenStreetMap tile layer
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 19
    }).addTo(map);
    
    // Initialize feature group for drawn items
    window.drawnItems = new L.FeatureGroup();
    map.addLayer(window.drawnItems);
    
    // Initialize draw control
    window.drawControl = new L.Control.Draw({
        edit: {
            featureGroup: window.drawnItems
        },
        draw: {
            polygon: true,
            rectangle: true,
            circle: false,
            marker: false,
            polyline: false,
            circlemarker: false
        }
    });
    map.addControl(window.drawControl);
    
    // Store map reference globally
    window.map = map;
    
    // Handle polygon drawing
    map.on('draw:created', function(e) {
        const layer = e.layer;
        window.drawnItems.clearLayers();
        window.drawnItems.addLayer(layer);
        currentPolygon = layer.toGeoJSON().geometry;
        hideError();
    });
    
    // Handle polygon editing
    map.on('draw:edited', function(e) {
        const layers = e.layers;
        layers.eachLayer(function(layer) {
            currentPolygon = layer.toGeoJSON().geometry;
        });
    });
    
    // Handle polygon deletion
    map.on('draw:deleted', function(e) {
        currentPolygon = null;
    });
}

/**
 * Attach event listeners to UI controls
 */
function attachEventListeners() {
    // Clear polygon button
    document.getElementById('clear-polygon').addEventListener('click', clearPolygon);
    
    // Analyze button
    document.getElementById('analyze-btn').addEventListener('click', analyzePolygon);
    
    // GeoJSON file upload
    document.getElementById('geojson-input').addEventListener('change', handleGeoJSONUpload);
}

/**
 * Clear the drawn polygon from the map
 * Task 11.3: Polygon drawing functionality (part of clearing)
 */
function clearPolygon() {
    window.drawnItems.clearLayers();
    currentPolygon = null;
    hideError();
    hideResults();
}

/**
 * Handle GeoJSON file upload
 * Task 11.4: Implement GeoJSON file upload
 */
function handleGeoJSONUpload(event) {
    const file = event.target.files[0];
    
    if (!file) {
        return;
    }
    
    // Validate file type
    if (!file.name.endsWith('.geojson') && !file.name.endsWith('.json')) {
        showError('Please upload a .geojson or .json file');
        event.target.value = '';
        return;
    }
    
    // Read and parse file
    const reader = new FileReader();
    reader.onload = function(e) {
        try {
            const geojson = JSON.parse(e.target.result);
            
            // Validate GeoJSON structure
            if (!geojson.type) {
                throw new Error('Invalid GeoJSON: missing type property');
            }
            
            // Handle both FeatureCollection and direct Geometry/Feature
            let features = [];
            if (geojson.type === 'FeatureCollection') {
                features = geojson.features;
            } else if (geojson.type === 'Feature') {
                features = [geojson];
            } else if (geojson.type === 'Polygon' || geojson.type === 'MultiPolygon') {
                features = [{ type: 'Feature', geometry: geojson, properties: {} }];
            } else {
                throw new Error('Unsupported GeoJSON type: ' + geojson.type);
            }
            
            if (features.length === 0) {
                throw new Error('No features found in GeoJSON file');
            }
            
            // Clear existing polygon and display the first feature
            window.drawnItems.clearLayers();
            const feature = features[0];
            const layer = L.geoJSON(feature);
            window.drawnItems.addLayer(layer);
            
            // Store the polygon geometry (not the Feature wrapper)
            currentPolygon = feature.geometry || feature;
            
            // Fit map to bounds
            const bounds = L.geoJSON(feature).getBounds();
            window.map.fitBounds(bounds, { padding: [50, 50] });
            
            hideError();
            
        } catch (error) {
            showError('Failed to parse GeoJSON: ' + error.message);
        }
        
        // Clear file input
        event.target.value = '';
    };
    
    reader.onerror = function() {
        showError('Failed to read file');
        event.target.value = '';
    };
    
    reader.readAsText(file);
}

/**
 * Analyze the current polygon
 * Task 11.5: Implement Analyze button and request sending
 */
async function analyzePolygon() {
    // Validate polygon exists
    if (!currentPolygon) {
        showError('Please draw or upload a polygon first');
        return;
    }
    
    // Validate not already analyzing
    if (analysisInProgress) {
        showError('Analysis already in progress');
        return;
    }
    
    // Show loading indicator
    showLoading();
    analysisInProgress = true;
    
    try {
        // Send analysis request to backend
        const response = await fetch(`${API_BASE}/analyze`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ polygon: currentPolygon }),
            timeout: API_TIMEOUT
        });
        
        // Handle response
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.error_message || `Server error: ${response.status}`);
        }
        
        const analysisResults = await response.json();
        
        // Display results
        displayResults(analysisResults);
        hideError();
        
    } catch (error) {
        // Show error message
        let errorMsg = 'Failed to analyze polygon';
        if (error.name === 'AbortError') {
            errorMsg = 'Analysis request timed out. Please try again.';
        } else if (error.message) {
            errorMsg = error.message;
        }
        showError(errorMsg);
        hideResults();
        
    } finally {
        // Hide loading indicator
        hideLoading();
        analysisInProgress = false;
    }
}

/**
 * Display analysis results
 * Task 11.6: Implement results display panel
 */
function displayResults(data) {
    const panel = document.getElementById('result-panel');
    const content = document.getElementById('results-content');
    
    // Build HTML for results display
    let html = '';
    
    // Display status
    if (data.status) {
        html += `<div class="status-badge status-${data.status}">${data.status.toUpperCase()}</div>`;
    }
    
    // Display processing time
    if (data.processing_time_ms) {
        html += `<p><strong>Processing Time:</strong> ${(data.processing_time_ms / 1000).toFixed(2)}s</p>`;
    }
    
    // Display analysis summary
    if (data.analysis_summary) {
        html += '<h3>Analysis Summary</h3>';
        const summary = data.analysis_summary;
        
        if (summary.polygon_area_sqkm) {
            html += `<p><strong>Area:</strong> ${summary.polygon_area_sqkm.toFixed(2)} km²</p>`;
        }
        if (summary.primary_land_cover) {
            html += `<p><strong>Primary Land Cover:</strong> ${summary.primary_land_cover}</p>`;
        }
        if (summary.key_findings && summary.key_findings.length > 0) {
            html += '<p><strong>Key Findings:</strong><ul>';
            summary.key_findings.forEach(finding => {
                html += `<li>${finding}</li>`;
            });
            html += '</ul></p>';
        }
    }
    
    // Display land information by category
    if (data.land_information) {
        html += '<h3>Land Information</h3>';
        const info = data.land_information;
        
        // Administrative information
        if (info.administrative && info.administrative.result) {
            html += '<h4>Administrative</h4>';
            const admin = info.administrative.result;
            if (admin.country) html += `<p>Country: ${admin.country}</p>`;
            if (admin.state) html += `<p>State: ${admin.state}</p>`;
            if (admin.district) html += `<p>District: ${admin.district}</p>`;
        }
        
        // Land cover information
        if (info.land_cover && info.land_cover.result) {
            html += '<h4>Land Cover</h4>';
            const cover = info.land_cover.result;
            if (cover.primary_type) html += `<p>Primary Type: ${cover.primary_type}</p>`;
            if (cover.coverage_percentage) html += `<p>Coverage: ${cover.coverage_percentage.toFixed(1)}%</p>`;
        }
        
        // Building information
        if (info.buildings && info.buildings.result) {
            html += '<h4>Buildings</h4>';
            const bldg = info.buildings.result;
            if (bldg.detected !== undefined) html += `<p>Buildings Detected: ${bldg.detected ? 'Yes' : 'No'}</p>`;
            if (bldg.estimated_count) html += `<p>Estimated Count: ${bldg.estimated_count}</p>`;
        }
        
        // Roads information
        if (info.roads && info.roads.result) {
            html += '<h4>Roads</h4>';
            const road = info.roads.result;
            if (road.road_access !== undefined) html += `<p>Road Access: ${road.road_access ? 'Yes' : 'No'}</p>`;
            if (road.main_road_types) html += `<p>Road Types: ${road.main_road_types}</p>`;
        }
        
        // Water information
        if (info.water && info.water.result) {
            html += '<h4>Water Bodies</h4>';
            const water = info.water.result;
            if (water.water_features) html += `<p>Water Features: ${water.water_features}</p>`;
            if (water.coverage_percentage) html += `<p>Coverage: ${water.coverage_percentage.toFixed(1)}%</p>`;
        }
        
        // Elevation information
        if (info.elevation && info.elevation.result) {
            html += '<h4>Elevation</h4>';
            const elev = info.elevation.result;
            if (elev.min_elevation !== undefined) html += `<p>Min Elevation: ${elev.min_elevation.toFixed(0)}m</p>`;
            if (elev.max_elevation !== undefined) html += `<p>Max Elevation: ${elev.max_elevation.toFixed(0)}m</p>`;
            if (elev.mean_elevation !== undefined) html += `<p>Mean Elevation: ${elev.mean_elevation.toFixed(0)}m</p>`;
        }
    }
    
    // Display processing status
    if (data.processing_status) {
        html += '<h3>Processing Status</h3>';
        const status = data.processing_status;
        
        if (status.validation) {
            html += `<p>Validation: <span class="status-${status.validation}">${status.validation}</span></p>`;
        }
        if (status.data_collection) {
            html += `<p>Data Collection: <span class="status-${status.data_collection}">${status.data_collection}</span></p>`;
        }
        if (status.standardization) {
            html += `<p>Standardization: <span class="status-${status.standardization}">${status.standardization}</span></p>`;
        }
        if (status.rule_engine) {
            html += `<p>Rule Engine: <span class="status-${status.rule_engine}">${status.rule_engine}</span></p>`;
        }
    }
    
    // Display provider status
    if (data.provider_status && Object.keys(data.provider_status).length > 0) {
        html += '<h3>Provider Status</h3>';
        const providers = data.provider_status;
        
        html += '<ul>';
        for (const [provider, status] of Object.entries(providers)) {
            const providerStatus = status.status || 'unknown';
            html += `<li>${provider}: <span class="status-${providerStatus}">${providerStatus}</span>`;
            if (status.error_message) {
                html += ` - ${status.error_message}`;
            }
            html += '</li>';
        }
        html += '</ul>';
    }
    
    // Display errors if any
    if (data.errors && data.errors.length > 0) {
        html += '<h3>Errors/Warnings</h3>';
        html += '<ul>';
        data.errors.forEach(error => {
            html += `<li><strong>${error.module}:</strong> ${error.message}</li>`;
        });
        html += '</ul>';
    }
    
    content.innerHTML = html;
    panel.classList.remove('hidden');
}

/**
 * Show error message
 * Task 11.7: Implement error display
 */
function showError(message) {
    const panel = document.getElementById('error-panel');
    const content = document.getElementById('error-content');
    
    content.textContent = message;
    panel.classList.remove('hidden');
}

/**
 * Hide error message
 */
function hideError() {
    const panel = document.getElementById('error-panel');
    panel.classList.add('hidden');
}

/**
 * Hide results panel
 */
function hideResults() {
    const panel = document.getElementById('result-panel');
    panel.classList.add('hidden');
}

/**
 * Show loading indicator
 */
function showLoading() {
    const indicator = document.getElementById('loading-indicator');
    indicator.classList.remove('hidden');
}

/**
 * Hide loading indicator
 */
function hideLoading() {
    const indicator = document.getElementById('loading-indicator');
    indicator.classList.add('hidden');
}