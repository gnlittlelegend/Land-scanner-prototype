# Docker Deployment Fix - Render Instructions

## Problem Resolved
✅ Render was using Python 3.14 runtime and trying to build `shapely` from source, causing failures.

## Solution Implemented
✅ **Switched to Docker runtime** - Ensures Python 3.11 is used with proper build tools.

## Changes Made

### 1. **render.yaml** - Forces Docker Runtime
```yaml
runtime: docker                    # Use Docker instead of native Python runtime
dockerfilePath: ./Dockerfile       # Points to our Dockerfile
```

### 2. **Dockerfile** - Enhanced Build Environment
- Explicitly uses `python:3.11-slim-bookworm`
- Installs all geospatial build dependencies
- Properly handles shapely and pyproj compilation

### 3. **requirements.txt** - Adjusted Versions
- `shapely==2.0.2` (compatible with 3.11)
- `pyproj==3.5.1` (has good wheel support)
- Other dependencies unchanged

## How to Deploy on Render

### Step 1: Update Render Service Configuration

Go to https://dashboard.render.com → Select **land-scanner-prototype-backend**

#### Change from Native Python to Docker:

1. Click **Settings**
2. Find the **Build & Deploy** section
3. Look for **"Runtime"** or **"Dockerfile Path"**
4. If not already set to Docker:
   - Change from "Python 3" to "Docker"
   - Set Dockerfile Path to: `./Dockerfile`

#### Update Build/Start Commands:

- **Build Command**: Leave empty (Docker will use Dockerfile's RUN commands)
- **Start Command**: Leave empty (Docker will use Dockerfile's CMD)

#### Example Configuration:
```
Runtime: Docker
Dockerfile: ./Dockerfile
Build Command: (leave empty)
Start Command: (leave empty)
```

### Step 2: Manual Deploy

1. Click **Manual Deploy** button
2. 