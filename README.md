# Land Scanner Prototype

A geospatial data analysis platform that collects information from multiple open geospatial data sources and transforms that information into useful land intelligence.

## Project Vision

Demonstrate that multiple public datasets can be combined to generate meaningful information about a selected land area without relying on heavy Artificial Intelligence processing.

## Tech Stack

- **Backend**: Python, FastAPI
- **Frontend**: HTML, CSS, JavaScript, Leaflet
- **Hosting**: Render

## Installation

```bash
pip install -r requirements.txt
```

## Running Locally

```bash
uvicorn backend.main:app --reload
```

## API Endpoints

- `POST /analyze` - Start land analysis
- `GET /health` - Health check
- `GET /status` - Prototype status

## Project Structure

```
LandScannerPrototype/
├── backend/
├── frontend/
├── config/
├── docs/
├── tests/
├── scripts/
├── sample_data/
├── logs/
├── README.md
├── requirements.txt
└── .gitignore
```