#!/bin/bash

# Land Scanner Deployment Script
# Handles both backend (Render) and frontend (Firebase) deployment

set -e  # Exit on error

echo "================================================================================"
echo "LAND SCANNER DEPLOYMENT SCRIPT"
echo "================================================================================"
echo ""

# Color codes for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
BACKEND_SERVICE="land-scanner-backend"
FIREBASE_PROJECT="land-scanner-prototype"

# Functions
print_section() {
    echo -e "${BLUE}===> $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# Parse command line arguments
DEPLOY_TYPE=${1:-"all"}  # all, backend, frontend

echo "Deployment Type: $DEPLOY_TYPE"
echo ""

# ===============================================================================
# BACKEND DEPLOYMENT (RENDER)
# ===============================================================================

if [ "$DEPLOY_TYPE" == "backend" ] || [ "$DEPLOY_TYPE" == "all" ]; then
    print_section "DEPLOYING BACKEND TO RENDER"
    echo ""
    
    # Check if Render CLI is installed
    if ! command -v render &> /dev/null; then
        print_warning "Render CLI not found. Using Git push instead."
        print_section "Pushing to Git (Render auto-deploys)"
        
        # Verify requirements.txt is up to date
        print_section "Verifying requirements.txt"
        if [ ! -f "requirements.txt" ]; then
            print_error "requirements.txt not found"
            exit 1
        fi
        print_success "requirements.txt found"
        
        # Verify Procfile exists
        print_section "Verifying Procfile"
        if [ ! -f "Procfile" ]; then
            print_error "Procfile not found"
            exit 1
        fi
        print_success "Procfile found"
        
        # Verify Dockerfile exists
        print_section "Verifying Dockerfile"
        if [ ! -f "Dockerfile" ]; then
            print_error "Dockerfile not found"
            exit 1
        fi
        print_success "Dockerfile found"
        
        # Git push
        print_section "Pushing code to Git"
        git add .
        git commit -m "Deploy: Task 12.1 End-to-End Pipeline" || print_warning "No changes to commit"
        git push origin main
        print_success "Code pushed to main branch"
        print_section "Render will auto-deploy on Git push"
        echo "Monitor deployment at: https://dashboard.render.com/services/$BACKEND_SERVICE"
        
    else
        print_section "Deploying with Render CLI"
        render deploy --service-id=$BACKEND_SERVICE
        print_success "Backend deployed to Render"
    fi
    
    echo ""
    print_section "VERIFYING BACKEND DEPLOYMENT"
    echo "Waiting for backend to be ready..."
    sleep 10
    
    # Test health endpoint
    BACKEND_URL="https://${BACKEND_SERVICE}.onrender.com"
    print_section "Testing health endpoint: $BACKEND_URL/health"
    
    response=$(curl -s -o /dev/null -w "%{http_code}" "$BACKEND_URL/health")
    if [ "$response" == "200" ]; then
        print_success "Backend health check passed (HTTP $response)"
    else
        print_warning "Backend health check returned HTTP $response (may be starting up)"
    fi
    
    echo ""
fi

# ===============================================================================
# FRONTEND DEPLOYMENT (FIREBASE)
# ===============================================================================

if [ "$DEPLOY_TYPE" == "frontend" ] || [ "$DEPLOY_TYPE" == "all" ]; then
    print_section "DEPLOYING FRONTEND TO FIREBASE"
    echo ""
    
    # Check if Firebase CLI is installed
    if ! command -v firebase &> /dev/null; then
        print_error "Firebase CLI not installed"
        echo "Install with: npm install -g firebase-tools"
        exit 1
    fi
    print_success "Firebase CLI found"
    
    # Check if frontend directory exists
    if [ ! -d "frontend" ]; then
        print_error "frontend directory not found"
        exit 1
    fi
    print_success "frontend directory found"
    
    # Build frontend
    print_section "Building frontend (React + Vite)"
    cd frontend
    
    if [ ! -f "package.json" ]; then
        print_error "package.json not found in frontend/"
        exit 1
    fi
    
    if [ ! -d "node_modules" ]; then
        print_section "Installing dependencies"
        npm install
    fi
    
    print_section "Running Vite build"
    npm run build
    print_success "Frontend built successfully"
    
    cd ..
    
    # Deploy to Firebase
    print_section "Deploying to Firebase Hosting"
    
    # Check if logged in to Firebase
    if ! firebase projects:list > /dev/null 2>&1; then
        print_warning "Not logged into Firebase. Please login:"
        firebase login
    fi
    
    firebase deploy --only hosting --project=$FIREBASE_PROJECT
    print_success "Frontend deployed to Firebase"
    
    echo ""
    print_section "FRONTEND DEPLOYMENT DETAILS"
    FIREBASE_URL="https://${FIREBASE_PROJECT}.web.app"
    echo "Hosting URL: $FIREBASE_URL"
    firebase hosting:channel:list --project=$FIREBASE_PROJECT || true
    
    echo ""
fi

# ===============================================================================
# TESTING
# ===============================================================================

echo ""
print_section "RUNNING END-TO-END TESTS"
echo ""

if [ "$DEPLOY_TYPE" == "backend" ] || [ "$DEPLOY_TYPE" == "all" ]; then
    print_section "Testing Backend Endpoints"
    
    BACKEND_URL="${BACKEND_URL:-https://${BACKEND_SERVICE}.onrender.com}"
    
    # Test health endpoint
    print_section "GET /health"
    curl -s "$BACKEND_URL/health" | python -m json.tool || print_warning "Health check failed"
    echo ""
    
    # Test status endpoint
    print_section "GET /status"
    curl -s "$BACKEND_URL/status" | python -m json.tool || print_warning "Status check failed"
    echo ""
    
    # Test analyze endpoint with real polygon
    print_section "POST /analyze (San Francisco polygon)"
    curl -s -X POST "$BACKEND_URL/analyze" \
      -H "Content-Type: application/json" \
      -d '{
        "polygon": {
          "type": "Feature",
          "geometry": {
            "type": "Polygon",
            "coordinates": [[
              [-122.47, 37.79],
              [-122.40, 37.79],
              [-122.40, 37.84],
              [-122.47, 37.84],
              [-122.47, 37.79]
            ]]
          }
        }
      }' | python -m json.tool || print_error "Analysis failed"
    echo ""
fi

# ===============================================================================
# SUMMARY
# ===============================================================================

echo ""
echo "================================================================================"
print_success "DEPLOYMENT COMPLETE"
echo "================================================================================"
echo ""
echo "Deployment Summary:"
echo "  - Backend (Render): $BACKEND_SERVICE"
echo "  - Frontend (Firebase): $FIREBASE_PROJECT"
echo ""
echo "Access your deployment:"
if [ "$DEPLOY_TYPE" == "backend" ] || [ "$DEPLOY_TYPE" == "all" ]; then
    echo "  Backend: https://${BACKEND_SERVICE}.onrender.com"
    echo "  API Docs: https://${BACKEND_SERVICE}.onrender.com/docs"
fi
if [ "$DEPLOY_TYPE" == "frontend" ] || [ "$DEPLOY_TYPE" == "all" ]; then
    echo "  Frontend: https://${FIREBASE_PROJECT}.web.app"
fi
echo ""
echo "Next steps:"
echo "  1. Update frontend API endpoint (if needed)"
echo "  2. Test end-to-end polygon analysis"
echo "  3. Monitor provider connectivity"
echo "  4. Check deployment logs"
echo ""
