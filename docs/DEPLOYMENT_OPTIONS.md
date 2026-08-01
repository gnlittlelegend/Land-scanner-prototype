# Deployment Options

## Option 1: Single Service (Recommended for Simplicity)
- Backend serves both API and static files
- One Dockerfile, one service
- No CORS issues, simplest deployment
- Use: `Dockerfile.single`

## Option 2: Microservices (Separate Containers)
- Backend: Dockerfile.backend
- Frontend: Dockerfile.frontend
- Two services communicate via internal network
- Frontend proxies API requests to backend
- Better separation of concerns

### Files Created:

**Dockerfile.single** - Single service deployment (backend serves static files)
- Backend API + static file serving in one container
- Simplest deployment option
- No service discovery or networking complexity
- Uses FastAPI's StaticFiles to serve frontend/

**Dockerfile.backend** - Backend-only service for microservices approach
- Multi-stage build for smaller image
- Non-root user for security
- Health check endpoint
- Optimized Python base image
- Serves only API endpoints

**Dockerfile.frontend** - Frontend-only service for microservices approach
- NGINX serves static files from `/usr/share/nginx/html/`
- Proxies `/api/*` requests to backend service
- Includes health check endpoint
- Uses lightweight Alpine-based NGINX

**docker-compose.yml** - Local development setup (microservices version)
- Backend service on port 8000
- Frontend service on port 8080
- Automatic dependency ordering
- Ready for `docker-compose up`

**frontend/nginx.conf** - NGINX configuration for frontend service
- Static file serving with fallback to index.html (for SPA)
- API proxying to backend service (`ls-backend:8000`)
- Health check endpoint
- Proper headers for security

**render.yaml** - Declarative Render.com deployment (microservices version)
- Two services: `ls-backend` and `ls-frontend`
- Each uses its respective Dockerfile
- Automatic deployments on main branch pushes
- Health checks configured
- Environment variables for service discovery

### Deployment Instructions:

#### For Single Service (Simplest):
1. Push code to GitHub repository
2. In Render dashboard:
   - New → Web Service
   - Connect your repository
   - Environment: Docker
   - Repository: your-repo
   - Branch: main
   - Dockerfile Path: ./Dockerfile.single
   - Service Name: ls-simple (or your preferred name)
   - Plan: Free (or preferred)
   - Create Web Service
3. Single service handles both API and frontend

#### For Microservices (Recommended for scaling):
1. Push code to GitHub repository
2. In Render dashboard, create two services:

   **Backend Service**:
   - Environment: Docker
   - Repository: Your GitHub repo
   - Branch: main
   - Dockerfile Path: ./Dockerfile.backend
   - Service Name: ls-backend
   - (Optional) Add environment variables (DEBUG=false, LOG_LEVEL=info)

   **Frontend Service**:
   - Environment: Docker
   - Repository: Your GitHub repo
   - Branch: main
   - Dockerfile Path: ./Dockerfile.frontend
   - Service Name: ls-frontend
   - (Optional) Add environment variables if needed
   - Enable auto-deploy

#### For Local Development:
```bash
# Single service:
docker build -f Dockerfile.single -t ls-simple .
docker run -p 8000:8000 ls-simple
# Then visit: http://localhost:8000 (serves both API and frontend)

# Microservices:
docker-compose up --build
# Then visit:
# - Frontend: http://localhost:8080
# - Backend API: http://localhost:8000
# - Backend docs: http://localhost:8000/docs
```

### Service Communication:

#### Single Service:
- All requests (API and static) go to same instance
- Frontend accessed at root path `/`
- API accessed at `/api/*` endpoints
- No networking between services needed

#### Microservices:
- Frontend service: `ls-frontend.onrender.com`
- Backend service: `ls-backend.internal Dockerfile://ls-backend:8000/
-nginx
Dockerfile: Dockerfile.
- When frontend loads from `ls-frontend.onrender.com`:
  - `window.location.origin` = `https://ls-frontend.onrender.com`
  - API calls to `/analyze` go to `https://ls-frontend.onrender.com/analyze`
  - NGINX in frontend service proxies `/api/*` to `http://ls-backend:8000/`
  - Browser sees same-origin requests (no CORS issues)
  - Backend receives requests at `/analyze` endpoint

### Environment Variables:

#### Backend (both single and backend service):
- `DEBUG`: Set to false in production
- `LOG_LEVEL`: Info, debug, etc. (default: info)
- `ENVIRONMENT`: development/staging/production (default: production)

#### Frontend (microservices only):
- Configured via nginx.conf - backend service name is hardcoded as `ls-backend`
- To change, modify `frontend/nginx.conf` and rebuild

### Health Checks:
- Backend: `/health` endpoint (returns JSON status)
- Frontend: `/health` endpoint (returns "healthy" text)

### Ports:
- Backend: 8000 (internal)
- Frontend: 80 (internal)
- External mapping handled by platform (Render, Docker, etc.)

### Security Notes:
- Both Dockerfiles use non-root users
- Base images are minimal (slim-bookworm, alpine)
- Only necessary packages installed
- Health checks enable automated restart policies
- Consider adding rate limiting, WAF, or API gateway for production

### Switching Between Approaches:
To use single service instead of microservices:
1. Update render.yaml to use `Dockerfile.single` for one service
2. Remove the frontend service definition
3. Or deploy just the backend service with static file serving

To use microservices:
1. Ensure both Dockerfile.backend and Dockerfile.frontend exist
2. Update references in docker-compose.yml and render.yaml as needed
3. Deploy both services