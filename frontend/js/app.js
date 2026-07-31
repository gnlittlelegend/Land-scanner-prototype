const API_BASE = window.location.origin;

const map = L.map('map').setView([0, 0], 2);

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors'
}).addTo(map);

let drawnItems = new L.FeatureGroup();
map.addLayer(drawnItems);

const drawControl = new L.Control.Draw({
    edit: false,
    draw: {
        polygon: true,
        rectangle: false,
        circle: false,
        marker: false,
        polyline: false
    }
});
map.addControl(drawControl);

map.on('drawcreated', function (e) {
    const layer = e.layer;
    drawnItems.clearLayers();
    drawnItems.addLayer(layer);
});

document.getElementById('clear-polygon').addEventListener('click', function() {
    drawnItems.clearLayers();
});

document.getElementById('analyze-btn').addEventListener('click', async function() {
    if (drawnItems.getLayers().length === 0) {
        showError('Please draw a polygon first');
        return;
    }
    
    const polygon = drawnItems.getLayers()[0];
    const geojson = polygon.toGeoJSON();
    
    try {
        const response = await fetch(`${API_BASE}/analyze`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ polygon: geojson })
        });
        
        const data = await response.json();
        displayResults(data);
    } catch (error) {
        showError('Failed to connect to server');
    }
});

function displayResults(data) {
    const panel = document.getElementById('result-panel');
    const content = document.getElementById('results-content');
    
    content.innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
    panel.classList.remove('hidden');
    document.getElementById('error-panel').classList.add('hidden');
}

function showError(message) {
    const panel = document.getElementById('error-panel');
    panel.textContent = message;
    panel.classList.remove('hidden');
}