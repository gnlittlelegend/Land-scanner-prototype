# Deployment Options

## Option 1: Single Service (Recommended for Simplicity)
- Backend serves both API and static files
- One Dockerfile, one service
- No CORS issues, simplest deployment
- Use: `Dockerfile` (original) or enhanced version

## Option 2: Microservices (Separate Containers)
- Backend:two Dockerfiles, two services
- Frontend serves static files, proxies API to backend
- Requires service discovery or configuration
- Slightly more complex but better separation

### Files Created:

**Dockerfile.backend** - Production-ready backend container
- Multi-stage build for smaller image
- Non-root user for security
- Health check endpoint
- Optimized Python base image

**Dockerfile.frontend** - NGINX-based frontend container
- Serves static files from `/usr/share/nginx/html/`
- Proxies `/api/*` requests to backend service
- Includes health check endpoint
- Uses lightweight Alpine-based NGINX

**docker-compose.yml** - Local development setup
- Backend service on port 8000
- Frontend service on port 8080
- Automatic dependency ordering
- Ready for `docker-compose up`

**frontend/nginx.conf** - NGINX configuration
- Static file serving with fallback to index.html (for SPA)
- API proxying to backend service
- Health check endpoint
- Proper headers for security

**render.yaml** - Declarative Render.com deployment
- Two services: `ls-backend` and `ls-frontend`
- Each uses its respective Dockerfile
- Automatic deployments on main branch pushes
- Health checks configured
- Environment variables for service discovery

### Deployment Instructions:

#### For Render.com:
1. Push code to GitHub repository connected
2. In Render Dashboard
  
   Service**:
   - Environment: Docker
   - Repository: Your GitHub repo
   - Branch: main
   - Dockerfile Path: ./Dockerfile.backend
   - Service Name: ls-backend
   - (Optional) Add environment variables
3. Create second service:
   - Environment: Docker
   - Repository: Your GitHub repo
   - Branch: main
   - Dockerfile Path: ./Dockerfile.frontend
   - Service Name: ls-frontend
4. Enable auto-deploy for both services

#### For Local Development:
```bash
docker-compose up --build
# Then visit:
# - Frontend: http://localhost:8080
# - Backend API: http://localhost:8000
# - Backend docs: http://localhost:8000/docs
```

### Notes:
- The frontend uses `window.location.origin` for API base URL
- With separate services, this will point to the frontend service
- The NGINX proxy forwards `/api/*` requests to the backend
- No frontend code changes required for this setup
- For direct backend access (bypassing proxy), use `/api/` prefix

### Environment Variables:
Backend:
- `DEBUG`: Set to false in production
- `LOG_LEVEL`: Info, debug, etc.
- `ENVIRONMENT`: development/staging/production

Frontend (via nginx.conf):
- Can be made configurable with envsubst if needed
- Currently uses static backend service name: `ls-backend`