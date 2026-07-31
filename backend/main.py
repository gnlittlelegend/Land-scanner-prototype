import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

app = FastAPI(
    title="Land Scanner Prototype",
    version="1.0.0",
    description="Geospatial data analysis platform"
)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "Land Scanner"}

@app.get("/status")
async def status():
    return {
        "status": "operational",
        "version": "1.0.0",
        "service": "Land Scanner Prototype"
    }

@app.post("/analyze")
async def analyze():
    return {"status": "success", "message": "Analysis endpoint - implementation pending"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)