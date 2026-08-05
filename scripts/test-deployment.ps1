# Land Scanner Production Testing Script for Windows PowerShell
# Tests complete deployed system with real data

param(
    [Parameter(Mandatory=$false)]
    [string]$BackendUrl = "https://land-scanner-backend.onrender.com",
    
    [Parameter(Mandatory=$false)]
    [string]$FrontendUrl = "https://land-scanner-prototype.web.app"
)

$ErrorActionPreference = "Continue"

# Colors
$colors = @{
    Green = "Green"
    Blue = "Cyan"
    Yellow = "Yellow"
    Red = "Red"
}

# Test counters
$testsRun = 0
$testsPassed = 0
$testsFailed = 0

function Print-Header {
    Write-Host "================================================================================"
    Write-Host "LAND SCANNER PRODUCTION END-TO-END TEST" -ForegroundColor $colors.Blue
    Write-Host "================================================================================"
    Write-Host ""
}

function Print-Test {
    param([string]$Message)
    Write-Host "[TEST $($testsRun + 1)] $Message" -ForegroundColor $colors.Blue
    $script:testsRun++
}

function Print-Pass {
    Write-Host "✓ PASSED" -ForegroundColor $colors.Green
    $script:testsPassed++
}

function Print-Fail {
    param([string]$Message = "FAILED")
    Write-Host "✗ $Message" -ForegroundColor $colors.Red
    $script:testsFailed++
}

function Print-Section {
    param([string]$Message)
    Write-Host ""
    Write-Host "--- $Message ---" -ForegroundColor $colors.Blue
    Write-Host ""
}

function Assert-Status {
    param(
        [int]$Actual,
        [int]$Expected,
        [string]$Message
    )
    
    if ($Actual -eq $Expected) {
        Print-Pass
    } else {
        Print-Fail "$Message (expected $Expected, got $Actual)"
    }
}

function Assert-Contains {
    param(
        [string]$Haystack,
        [string]$Needle,
        [string]$Message
    )
    
    if ($Haystack -like "*$Needle*") {
        Print-Pass
    } else {
        Print-Fail "$Message"
    }
}

Print-Header

Write-Host "Configuration:"
Write-Host "  Backend URL: $BackendUrl"
Write-Host "  Frontend URL: $FrontendUrl"
Write-Host ""

# ===============================================================================
# TEST 1: Backend Availability
# ===============================================================================

Print-Section "TEST 1: BACKEND AVAILABILITY"

Print-Test "Backend is accessible (health endpoint)"
try {
    $response = Invoke-WebRequest -Uri "$BackendUrl/health" -Method Get -TimeoutSec 10
    Assert-Status $response.StatusCode 200 "Backend health check failed"
} catch {
    Print-Fail "Connection failed: $($_.Exception.Message)"
}

Write-Host ""
Print-Test "Backend returns health information"
try {
    $response = Invoke-WebRequest -Uri "$BackendUrl/health" -Method Get -TimeoutSec 10
    $content = $response.Content
    Assert-Contains $content "status" "Health response missing 'status'"
    Assert-Contains $content "version" "Health response missing 'version'"
} catch {
    Print-Fail "Failed to parse health response: $($_.Exception.Message)"
}

# ===============================================================================
# TEST 2: API Endpoints
# ===============================================================================

Print-Section "TEST 2: API ENDPOINTS"

Print-Test "Status endpoint is accessible"
try {
    $response = Invoke-WebRequest -Uri "$BackendUrl/status" -Method Get -TimeoutSec 10
    Assert-Status $response.StatusCode 200 "Status endpoint failed"
} catch {
    Print-Fail "Connection failed: $($_.Exception.Message)"
}

Write-Host ""
Print-Test "Status endpoint returns configuration"
try {
    $response = Invoke-WebRequest -Uri "$BackendUrl/status" -Method Get -TimeoutSec 10
    $content = $response.Content
    Assert-Contains $content "providers" "Status response missing 'providers'"
    Assert-Contains $content "rules" "Status response missing 'rules'"
} catch {
    Print-Fail "Failed to parse status response: $($_.Exception.Message)"
}

# ===============================================================================
# TEST 3: Polygon Validation
# ===============================================================================

Print-Section "TEST 3: POLYGON VALIDATION"

$validPolygon = @{
    polygon = @{
        type = "Feature"
        geometry = @{
            type = "Polygon"
            coordinates = @(
                @(
                    @(-122.47, 37.79),
                    @(-122.40, 37.79),
                    @(-122.40, 37.84),
                    @(-122.47, 37.84),
                    @(-122.47, 37.79)
                )
            )
        }
    }
} | ConvertTo-Json -Depth 10

Print-Test "Valid polygon is accepted (San Francisco)"
try {
    $response = Invoke-WebRequest -Uri "$BackendUrl/analyze" `
        -Method Post `
        -Headers @{"Content-Type" = "application/json"} `
        -Body $validPolygon `
        -TimeoutSec 120
    
    Assert-Status $response.StatusCode 200 "Analysis failed for valid polygon"
} catch {
    Print-Fail "Connection failed: $($_.Exception.Message)"
}

Write-Host ""
Print-Test "Response contains analysis results"
try {
    $response = Invoke-WebRequest -Uri "$BackendUrl/analyze" `
        -Method Post `
        -Headers @{"Content-Type" = "application/json"} `
        -Body $validPolygon `
        -TimeoutSec 120
    
    $content = $response.Content
    Assert-Contains $content "request_id" "Response missing 'request_id'"
    Assert-Contains $content "status" "Response missing 'status'"
    Assert-Contains $content "land_information" "Response missing 'land_information'"
} catch {
    Print-Fail "Failed to parse analysis response: $($_.Exception.Message)"
}

Write-Host ""
Print-Test "Response includes all 6 data categories"
try {
    $response = Invoke-WebRequest -Uri "$BackendUrl/analyze" `
        -Method Post `
        -Headers @{"Content-Type" = "application/json"} `
        -Body $validPolygon `
        -TimeoutSec 120
    
    $content = $response.Content
    Assert-Contains $content "administrative" "Missing 'administrative' data"
    Assert-Contains $content "buildings" "Missing 'buildings' data"
    Assert-Contains $content "land_cover" "Missing 'land_cover' data"
    Assert-Contains $content "roads" "Missing 'roads' data"
    Assert-Contains $content "water" "Missing 'water' data"
    Assert-Contains $content "elevation" "Missing 'elevation' data"
} catch {
    Print-Fail "Failed to validate data categories: $($_.Exception.Message)"
}

# ===============================================================================
# TEST 4: Invalid Polygon Handling
# ===============================================================================

Print-Section "TEST 4: INVALID POLYGON HANDLING"

$invalidPolygon = @{
    polygon = @{
        type = "Feature"
        geometry = @{
            type = "Polygon"
            coordinates = @(
                @(
                    @(-122.47, 37.79),
                    @(-122.40, 37.79),
                    @(-122.40, 37.80),
                    @(-122.47, 37.80),
                    @(-122.47, 37.79)
                )
            )
        }
    }
} | ConvertTo-Json -Depth 10

Print-Test "Polygon too small is rejected"
try {
    $response = Invoke-WebRequest -Uri "$BackendUrl/analyze" `
        -Method Post `
        -Headers @{"Content-Type" = "application/json"} `
        -Body $invalidPolygon `
        -TimeoutSec 10 `
        -ErrorAction Stop
} catch {
    if ($_.Exception.Response.StatusCode -eq 400 -or $_.Exception.Response.StatusCode -eq 422) {
        Print-Pass
    } else {
        Print-Fail "Expected HTTP 400/422, got $($_.Exception.Response.StatusCode)"
    }
}

# ===============================================================================
# TEST 5: Provider Data
# ===============================================================================

Print-Section "TEST 5: PROVIDER DATA"

Print-Test "All providers return valid status"
try {
    $response = Invoke-WebRequest -Uri "$BackendUrl/analyze" `
        -Method Post `
        -Headers @{"Content-Type" = "application/json"} `
        -Body $validPolygon `
        -TimeoutSec 120
    
    $content = $response.Content
    
    $providersToCheck = @(
        "osm_buildings",
        "osm_admin_boundaries",
        "osm_roads",
        "osm_water",
        "copernicus_land_cover",
        "usgs_elevation"
    )
    
    $allProvidersMentioned = $true
    foreach ($provider in $providersToCheck) {
        if ($content -notmatch $provider) {
            $allProvidersMentioned = $false
            Write-Host "  Missing provider data for: $provider" -ForegroundColor Yellow
        }
    }
    
    if ($allProvidersMentioned) {
        Print-Pass
    } else {
        Print-Fail "Not all providers mentioned in response"
    }
} catch {
    Print-Fail "Failed to analyze providers: $($_.Exception.Message)"
}

# ===============================================================================
# TEST 6: Performance
# ===============================================================================

Print-Section "TEST 6: PERFORMANCE"

Print-Test "Analysis completes within reasonable time"
try {
    $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
    
    $response = Invoke-WebRequest -Uri "$BackendUrl/analyze" `
        -Method Post `
        -Headers @{"Content-Type" = "application/json"} `
        -Body $validPolygon `
        -TimeoutSec 120
    
    $stopwatch.Stop()
    $elapsedSeconds = $stopwatch.Elapsed.TotalSeconds
    
    if ($elapsedSeconds -lt 120) {
        Print-Pass
        Write-Host "  Completed in: $($elapsedSeconds.ToString('F1')) seconds" -ForegroundColor Cyan
    } else {
        Print-Fail "Analysis took $($elapsedSeconds.ToString('F1')) seconds (expected < 120s)"
    }
} catch {
    Print-Fail "Failed to measure performance: $($_.Exception.Message)"
}

# ===============================================================================
# TEST 7: CORS Headers
# ===============================================================================

Print-Section "TEST 7: CORS HEADERS"

Print-Test "CORS headers are present"
try {
    $response = Invoke-WebRequest -Uri "$BackendUrl/health" `
        -Method Get `
        -TimeoutSec 10
    
    $corsHeader = $response.Headers.'Access-Control-Allow-Origin'
    if ($corsHeader) {
        Print-Pass
        Write-Host "  CORS Origin: $corsHeader" -ForegroundColor Cyan
    } else {
        Print-Fail "CORS headers not found"
    }
} catch {
    Print-Fail "Failed to check CORS headers: $($_.Exception.Message)"
}

# ===============================================================================
# TEST SUMMARY
# ===============================================================================

Print-Section "TEST SUMMARY"

Write-Host "Total Tests: $testsRun"
Write-Host "Passed: $testsPassed" -ForegroundColor $colors.Green
Write-Host "Failed: $testsFailed" -ForegroundColor $(if ($testsFailed -eq 0) { $colors.Green } else { $colors.Red })
Write-Host ""

$successRate = if ($testsRun -eq 0) { 0 } else { [math]::Round(($testsPassed / $testsRun) * 100, 1) }
Write-Host "Success Rate: $successRate%" -ForegroundColor $(if ($successRate -eq 100) { $colors.Green } else { $colors.Yellow })

Write-Host ""
Write-Host "================================================================================"
if ($testsFailed -eq 0) {
    Write-Host "✓ ALL TESTS PASSED - DEPLOYMENT SUCCESSFUL" -ForegroundColor $colors.Green
} else {
    Write-Host "✗ SOME TESTS FAILED - CHECK ISSUES ABOVE" -ForegroundColor $colors.Red
}
Write-Host "================================================================================"

exit $(if ($testsFailed -eq 0) { 0 } else { 1 })
