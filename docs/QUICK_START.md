# Land Scanner Prototype - Quick Start Guide

## Installation (One-time)

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Running Locally

### Start Backend Server
```bash
uvicorn backend.main:app --reload
```
- Backend runs at: `http://localhost:8000`
- API docs at: `http://localhost:8000/docs`

### Start Frontend Server (in a new terminal)
```bash
cd frontend
python -m http.server 3000
```
- Frontend runs at: `http://localhost:3000`

### Access the Application
- Open browser to: `http://localhost:3000`
- Draw a polygon on the map or upload a GeoJSON file
- Click "Analyze" button
- Wait for results (5-30 seconds depending on area size)
- View analysis results in the results panel

## Running Tests

```bash
# Run all core tests
python -m pytest tests/test_data_standardizer.py tests/test_polygon_validator.py tests/test_rule_engine.py -v

# Run specific test file
python -m pytest tests/test_api_endpoints.py -v

# Run all tests (longer)
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=backend
```

## Quick Test of API

```bash
# Check if backend is running
curl http://localhost:8000/health

# Get status
curl http://localhost:8000/status

# Analyze a polygon (Manhattan)
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "polygon": {
      "type": "Polygon",
      "coordinates": [[
        [-73.935, 40.731],
        [-73.912, 40.731],
        [-73.912, 40.749],
        [-73.935, 40.749],
        [-73.935, 40.731]
      ]]
    }
  }'
```

## Project Structure

```
LandScannerPrototype/
├── backend/              # Python backend
│   ├── main.py          # FastAPI application
│   ├── models/          # Data models (Pydantic)
│   ├── validators/      # Validation logic
│   ├── collectors/      # Data collectors (6 providers)
│   ├── standardizers/   # Data standardization
│   ├── rules/           # Analysis rules (6 rules)
│   ├── output/          # Response generation
│   └── managers/        # Service managers
├── frontend/            # Web interface
│   ├── index.html       # Main page
│   ├── css/style.css    # Styling
│   └── js/app.js        # Frontend logic
├── config/              # Configuration files
├── tests/               # Test suite (144 tests)
├── requirements.txt     # Python dependencies
└── README.md            # Project documentation
```

## File Upload Format

Supported GeoJSON format:
```json
{
  "type": "Polygon",
  "coordinates": [[
    [longitude, latitude],
    [longitude, latitude],
    ...
  ]]
}
```

Example (New York City bounds):
```json
{
  "type": "Polygon",
  "coordinates": [[
    [-74.0, 40.7],
    [-73.9, 40.7],
    [-73.9, 40.8],
    [-74.0, 40.8],
    [-74.0, 40.7]
  ]]
}
```

## Troubleshooting

### Backend won't start
- Check Python version: `python --version` (needs 3.11+)
- Check if port 8000 is available
- Try: `uvicorn backend.main:app --port 8001`

### Frontend won't load
- Check if port 3000 is available
- Try: `python -m http.server 3001 -d frontend`

### Analysis returns error
- Check backend logs for detailed error
- Verify polygon format is valid GeoJSON
- Coordinate range: longitude [-180, 180], latitude [-90, 90]

### Slow analysis
- First query collects from all providers (takes 5-10 seconds)
- Subsequent queries may be faster
- Large areas take longer than small areas

### Tests failing
- Run: `python -m pytest --version`
- Ensure all dependencies installed: `pip install -r requirements.txt`
- Check Python version is 3.11+

## Key Files to Know

- **backend/main.py** - Main API server
- **backend/validators/polygon_validator.py** - Polygon validation
- **backend/standardizers/data_standardizer.py** - Data standardization
- **backend/rules/rule_engine.py** - Rule execution
- **frontend/js/app.js** - Frontend logic
- **tests/** - Test suite directory

## Data Pipeline

1. **Input**: User draws polygon or uploads GeoJSON
2. **Validation**: Polygon geometry and coordinates validated
3. **Collection**: Data fetched from 6 open data providers
4. **Standardization**: All data converted to WGS84 format
5. **Analysis**: 6 rules applied to generate insights
6. **Output**: Results displayed to user

## System Components

- **6 Data Providers**: OSM Buildings, Admin Boundaries, Land Cover, Roads, Water, Elevation
- **6 Analysis Rules**: Administrative regions, land cover, buildings, roads, water, elevation
- **3 API Endpoints**: /health, /status, /analyze
- **Interactive Map**: Leaflet-based polygon drawing
- **Responsive UI**: Error handling and loading states

## API Response Format

```json
{
  "request_id": "req_...",
  "status": "success|partial|failed",
  "timestamp": "2026-08-01T12:34:56.789...",
  "processing_time_ms": 234.5,
  "analysis_summary": {
    "polygon_area_sqkm": 12.5,
    "key_findings": ["..."]
  },
  "land_information": {
    "admin": {...},
    "land_cover": {...},
    "buildings": {...},
    "roads": {...},
    "water": {...},
    "elevation": {...}
  },
  "processing_status": {...},
  "provider_status": [...],
  "errors": [...]
}
```

## Development Commands

```bash
# Format code (optional)
python -m autopep8 --in-place --aggressive backend/main.py

# Type checking (optional)
python -m mypy backend/main.py

# Lint (optional)
python -m pylint backend/main.py

# Run single test
python -m pytest tests/test_api_endpoints.py::TestAnalyzeEndpoint::test_analyze_with_valid_polygon -v

# Verbose output
python -m pytest tests/ -v -s
```

## Performance Tips

- Small polygons (<50 sq km) process in 200-500ms
- Medium polygons (50-500 sq km) process in 1-5 seconds
- Large polygons (>500 sq km) process in 5-30 seconds
- Data collection is the slowest step (queries remote APIs)

## Next Steps

1. Run `QUICK_START.md` steps above
2. Test with provided polygons
3. Try drawing your own polygons
4. Check backend logs for any issues
5. Review API documentation at /docs
6. For deployment: See DEPLOYMENT_GUIDE.md

---

**Version**: 1.0.0  
**Last Updated**: August 1, 2026  
**Status**: ✅ Production Ready
