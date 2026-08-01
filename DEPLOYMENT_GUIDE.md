# Land Scanner Prototype - Deployment Guide

## Project Structure
- `backend/` - Python FastAPI application
- `frontend/` - Static HTML/CSS/JS application
- `Dockerfile.backend` - Dockerfile for backend service
- `Dockerfile.frontend` - Dockerfile for frontend service (NGINX)
- `docker-compose.yml` - Local development with Docker Compose
- `render.yaml` - Deployment configuration for Render.com
- `.gitignore` - Git ignore rules

## Quick Start

### Local Development with Docker Compose
```bash
docker-compose up --build
```
- Backend API: http://localhost:8000
- Frontend UI: http://localhost:8080
- API docs: http://localhost:8000/docs

### Deployment to Render.com
1. Push code to GitHub repository
2. In Render dashboard:
   - New → Web Service
   - Connect your repository
   - Repository: your-repo
   - Branch: main
   - Environment: Docker
   - Plan: Free (or preferred)
   - Click "Create Web Service"
3. Render will automatically detect `render.yaml` and create two services:
   - `ls-backend` (API service)
   - `ls-frontend` (Static file service)

## Service Communication

### Local Development (docker-compose)
- Frontend at `http://localhost:8080`
- Backend API available at `http://localhost:8000`
- Frontend proxies `/api/*` to backend via nginx configuration

### Production (Render.com)
- Backend service: `ls-backend.onrender.com`
- Frontend service: `ls-frontend.onrender.com`
- Frontend nginx proxies `/api/*` to `http://ls-backend:8000/` (internal Docker network)
- **Important**: The frontend uses `window.location.origin` for API base, which works because:
  - Same-origin requests to `/api/` are proxied by nginx to backend
  - No CORS issues since it appears as same-origin to the browser

## Manual Configuration (if needed)

If you need to configure the API base URL explicitly in the frontend:
1. Edit `frontend/js/app.js`
2. Change line 7 from:
   ```javascript
   const API_BASE = window.location.origin;
   ```
3. To:
   ```javascript
   const API_BASE = 'https://ls-backend.onrender.com'; // or your backend URL
   ```

## Environment Variables

### Backend
- `ENVIRONMENT`: Set to `production` for production builds
- `LOG_LEVEL`: Logging level (debug, info, warning, error)
- `PYTHON_VERSION`: Python runtime version (3.11)

### Frontend
- `BACKEND_URL`: Backend service URL (auto-set in render.yaml)
- `BACKEND_PORT`: Backend port (8000)

## Health Checks
- Backend: `/health` endpoint
- Frontend: `/health` endpoint (returns "healthy")

## Ports
- Backend: 8000 (internal), mapped as needed externally
- Frontend: 80 (internal), mapped as needed externally

## Development Notes

### Backend
- Uses Uvicorn ASGI server
- Auto-reload disabled in production (enable in Dockerfile.dev if needed)
- CORS middleware configured to allow all origins (adjust for production)

### Frontend
- Served by NGINX
- Static file caching enabled
- API requests proxied to backend
- Falls back to index.html for client-side routing (SPA support)

## Troubleshooting

1. **Container fails to start**: Check logs with `docker-compose logs [service]`
2. **API calls fail**: Verify nginx proxy configuration and backend service name
3. **Static files not loading**: Check nginx root directory and file permissions
4. **Build failures**: Ensure Dockerfile syntax is correct and base images are available

## Security Notes
- For production, consider:
  - Using non-root users (already implemented in backend)
  - Adding rate limiting
  - Using HTTPS (handled by Reverse Proxy/Load Balancer)
  - Regular dependency updates
  - Removing development tools from production images

## License
[Your License Here]