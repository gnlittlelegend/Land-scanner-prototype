# Land Scanner Frontend - React

Modern React-based frontend for the Land Scanner geospatial analysis application.

## Features

- Interactive map with Leaflet for polygon drawing and editing
- GeoJSON file upload support
- Real-time analysis with backend API
- Comprehensive results display
- Error handling with user feedback
- Responsive design

## Tech Stack

- **React 18** - UI framework
- **Vite** - Fast build tool and dev server
- **Leaflet** - Interactive maps
- **Leaflet-Draw** - Polygon drawing and editing
- **CSS3** - Modern styling

## Installation

```bash
cd frontend
npm install
```

## Development

Start the development server:

```bash
npm run dev
```

The application will open at `http://localhost:3000`

## Build

Create a production build:

```bash
npm run build
```

Output will be in the `dist/` directory.

## Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── ControlPanel.jsx      # File upload and analyze controls
│   │   ├── ErrorPanel.jsx        # Error message display
│   │   ├── Header.jsx            # App header
│   │   ├── LoadingIndicator.jsx  # Loading spinner
│   │   ├── MapContainer.jsx      # Leaflet map with drawing
│   │   └── ResultsPanel.jsx      # Analysis results display
│   ├── App.jsx                   # Main app component
│   ├── main.jsx                  # React entry point
│   └── index.css                 # Global styles
├── index.html                    # HTML entry point
├── vite.config.js               # Vite configuration
└── package.json                 # Dependencies
```

## API Integration

The frontend connects to the backend API at:
```
https://land-scanner-prototype-backend.onrender.com/analyze
```

### Request Format

```json
{
  "polygon": {
    "type": "Polygon",
    "coordinates": [[[lng, lat], [lng, lat], ...]]
  }
}
```

### Response Format

Includes analysis results with:
- Processing status
- Land information (administrative, land cover, buildings, roads, water, elevation)
- Provider status
- Errors/warnings

## Usage

1. **Draw a Polygon**: Use the drawing tools on the map to create a polygon
2. **Upload GeoJSON**: Or upload a GeoJSON file to load a polygon
3. **Analyze**: Click the "Analyze" button to send the polygon to the backend
4. **View Results**: See detailed analysis results in the results panel

## Environment

Set backend API URL via `API_BASE` constant in `src/App.jsx`

## Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
