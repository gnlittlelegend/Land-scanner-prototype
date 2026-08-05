# Land Scanner Deployment Script for Windows
# Handles backend (Render) and frontend (Firebase) deployment on Windows PowerShell

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("all", "backend", "frontend")]
    [string]$DeployType = "all"
)

$ErrorActionPreference = "Stop"

# Color codes for output
$colors = @{
    Green = "Green"
    Blue = "Cyan"
    Yellow = "Yellow"
    Red = "Red"
}

function Print-Section {
    param([string]$Message)
    Write-Host "===> $Message" -ForegroundColor $colors.Blue
}

function Print-Success {
    param([string]$Message)
    Write-Host "✓ $Message" -ForegroundColor $colors.Green
}

function Print-Error {
    param([string]$Message)
    Write-Host "✗ $Message" -ForegroundColor $colors.Red
}

function Print-Warning {
    param([string]$Message)
    Write-Host "⚠ $Message" -ForegroundColor $colors.Yellow
}

Write-Host "================================================================================"
Write-Host "LAND SCANNER DEPLOYMENT SCRIPT (Windows)" -ForegroundColor $colors.Blue
Write-Host "================================================================================"
Write-Host ""
Write-Host "Deployment Type: $DeployType"
Write-Host ""

# Configuration
$BACKEND_SERVICE = "land-scanner-backend"
$FIREBASE_PROJECT = "land-scanner-prototype"

# ===============================================================================
# BACKEND DEPLOYMENT (RENDER)
# ===============================================================================

if ($DeployType -eq "backend" -or $DeployType -eq "all") {
    Print-Section "DEPLOYING BACKEND TO RENDER"
    Write-Host ""
    
    # Check if Git is installed
    $gitExists = $null -ne (Get-Command git -ErrorAction SilentlyContinue)
    if (-not $gitExists) {
        Print-Error "Git not found. Please install Git first."
        exit 1
    }
    Print-Success "Git found"
    
    # Verify requirements.txt
    Print-Section "Verifying requirements.txt"
    if (-not (Test-Path "requirements.txt")) {
        Print-Error "requirements.txt not found"
        exit 1
    }
    Print-Success "requirements.txt found"
    
    # Verify Procfile
    Print-Section "Verifying Procfile"
    if (-not (Test-Path "Procfile")) {
        Print-Error "Procfile not found"
        exit 1
    }
    Print-Success "Procfile found"
    
    # Verify Dockerfile
    Print-Section "Verifying Dockerfile"
    if (-not (Test-Path "Dockerfile")) {
        Print-Error "Dockerfile not found"
        exit 1
    }
    Print-Success "Dockerfile found"
    
    # Git push
    Print-Section "Pushing code to Git (Render will auto-deploy)"
    Write-Host ""
    
    git add .
    $status = $LASTEXITCODE
    
    Write-Host "Committing changes..."
    git commit -m "Deploy: Task 12.1 End-to-End Pipeline" -ErrorAction SilentlyContinue
    if ($LASTEXITCODE -eq 0) {
        Print-Success "Changes committed"
    } else {
        Print-Warning "No changes to commit (may already be committed)"
    }
    
    Write-Host "Pushing to main branch..."
    git push origin main
    if ($LASTEXITCODE -eq 0) {
        Print-Success "Code pushed to main branch"
        Print-Section "Render will auto-deploy on Git push"
        Write-Host "Monitor deployment at: https://dashboard.render.com"
    } else {
        Print-Error "Git push failed. Check your credentials and try again."
        exit 1
    }
    
    Write-Host ""
    Print-Section "Backend Deployment Initiated"
    Write-Host "The backend deployment may take 2-5 minutes. You can monitor progress at:"
    Write-Host "  https://dashboard.render.com/services/$BACKEND_SERVICE"
    Write-Host ""
    
    Write-Host "In the meantime, verify the deployment with:"
    Write-Host "  curl https://$BACKEND_SERVICE.onrender.com/health"
    Write-Host ""
    Write-Host "Or from PowerShell:"
    Write-Host "  (Invoke-WebRequest -Uri https://$BACKEND_SERVICE.onrender.com/health).StatusCode"
    Write-Host ""
}

# ===============================================================================
# FRONTEND DEPLOYMENT (FIREBASE)
# ===============================================================================

if ($DeployType -eq "frontend" -or $DeployType -eq "all") {
    Print-Section "DEPLOYING FRONTEND TO FIREBASE"
    Write-Host ""
    
    # Check if Firebase CLI is installed
    $firebaseExists = $null -ne (Get-Command firebase -ErrorAction SilentlyContinue)
    if (-not $firebaseExists) {
        Print-Error "Firebase CLI not found"
        Write-Host "Install with: npm install -g firebase-tools"
        exit 1
    }
    Print-Success "Firebase CLI found"
    
    # Check if frontend directory exists
    if (-not (Test-Path "frontend")) {
        Print-Error "frontend directory not found"
        exit 1
    }
    Print-Success "frontend directory found"
    
    # Build frontend
    Print-Section "Building frontend (React + Vite)"
    
    Push-Location frontend
    
    if (-not (Test-Path "package.json")) {
        Print-Error "package.json not found in frontend/"
        exit 1
    }
    
    if (-not (Test-Path "node_modules")) {
        Print-Section "Installing dependencies"
        npm install
        if ($LASTEXITCODE -ne 0) {
            Print-Error "npm install failed"
            exit 1
        }
    }
    
    Print-Section "Running Vite build"
    npm run build
    if ($LASTEXITCODE -ne 0) {
        Print-Error "Build failed"
        exit 1
    }
    Print-Success "Frontend built successfully"
    
    Pop-Location
    
    # Deploy to Firebase
    Print-Section "Deploying to Firebase Hosting"
    Write-Host ""
    
    # Check if logged in to Firebase
    firebase projects:list > $null 2>&1
    if ($LASTEXITCODE -ne 0) {
        Print-Warning "Not logged into Firebase. Please login:"
        firebase login
    }
    
    firebase deploy --only hosting --project=$FIREBASE_PROJECT
    if ($LASTEXITCODE -eq 0) {
        Print-Success "Frontend deployed to Firebase"
    } else {
        Print-Error "Firebase deployment failed"
        exit 1
    }
    
    Write-Host ""
    Print-Section "FRONTEND DEPLOYMENT COMPLETE"
    $FIREBASE_URL = "https://$FIREBASE_PROJECT.web.app"
    Write-Host "Frontend URL: $FIREBASE_URL"
    Write-Host ""
}

# ===============================================================================
# SUMMARY
# ===============================================================================

Write-Host ""
Write-Host "================================================================================"
Print-Success "DEPLOYMENT INITIATED"
Write-Host "================================================================================"
Write-Host ""

if ($DeployType -eq "backend" -or $DeployType -eq "all") {
    Write-Host "Backend (Render):"
    Write-Host "  URL: https://$BACKEND_SERVICE.onrender.com"
    Write-Host "  Status: Auto-deploying from Git push"
    Write-Host "  Time to live: 2-5 minutes"
    Write-Host "  Health check: https://$BACKEND_SERVICE.onrender.com/health"
    Write-Host ""
}

if ($DeployType -eq "frontend" -or $DeployType -eq "all") {
    Write-Host "Frontend (Firebase):"
    Write-Host "  URL: https://$FIREBASE_PROJECT.web.app"
    Write-Host "  Status: Deployment complete"
    Write-Host ""
}

Write-Host "Next Steps:"
Write-Host "  1. Wait for backend deployment (check Render dashboard)"
Write-Host "  2. Test backend health: (Invoke-WebRequest -Uri https://$BACKEND_SERVICE.onrender.com/health).StatusCode"
Write-Host "  3. Open frontend in browser: https://$FIREBASE_PROJECT.web.app"
Write-Host "  4. Draw a polygon and test end-to-end analysis"
Write-Host "  5. Check all 6 data providers respond correctly"
Write-Host ""
