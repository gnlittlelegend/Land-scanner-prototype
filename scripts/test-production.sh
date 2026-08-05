#!/bin/bash

# Land Scanner Production End-to-End Testing Script
# Tests complete pipeline with real data from deployed system

set -e

echo "================================================================================"
echo "LAND SCANNER PRODUCTION END-TO-END TEST"
echo "================================================================================"
echo ""

# Configuration
BACKEND_URL="${BACKEND_URL:-https://land-scanner-backend.onrender.com}"
FRONTEND_URL="${FRONTEND_URL:-https://land-scanner-prototype.web.app}"

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Helper functions
print_test() {
    echo -e "${BLUE}[TEST $((TESTS_RUN + 1))] $1${NC}"
    TESTS_RUN=$((TESTS_RUN + 1))
}

pass() {
    echo -e "${GREEN}✓ PASSED${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
}

fail() {
    echo -e "${RED}✗ FAILED: $1${NC}"
    TESTS_FAILED=$((TESTS_FAILED + 1))
}

assert_status() {
    local actual=$1
    local expected=$2
    local message=$3
    
    if [ "$actual" == "$expected" ]; then
        pass
    else
        fail "$message (expected $expected, got $actual)"
    fi
}

assert_contains() {
    local haystack=$1
    local needle=$2
    local message=$3
    
    if echo "$haystack" | grep -q "$needle"; then
        pass
    else
        fail "$message"
    fi
}

# ===============================================================================
# TEST 1: Backend Availability
# ===============================================================================

print_test "Backend is accessible"
response=$(curl -s -o /dev/null -w "%{http_code}" "$BACKEND_URL/health")
assert_status "$response" "200" "Backend health check failed"

echo ""
print_test "Backend returns health information"
response=$(curl -s "$BACKEND_URL/health")
assert_contains "$response" "status" "Health response missing status"
assert_contains "$response" "version" "Health response missing version"
assert_contains "$response" "healthy" "Backend not healthy"

# ===============================================================================
# TEST 2: API Endpoints
# ===============================================================================

echo ""
print_test "Status endpoint is accessible"
response=$(curl -s -o /dev/null -w "%{http_code}" "$BACKEND_URL/status")
assert_status "$response" "200" "Status endpoint failed"

echo ""
print_test "Status endpoint returns configuration"
response=$(curl -s "$BACKEND_URL/status")
assert_contains "$response" "providers" "Status response missing providers"
assert_contains "$response" "rules" "Status response missing rules"

# ===============================================================================
# TEST 3: Polygon Validation
# ===============================================================================

echo ""
print_test "Valid polygon is accepted"
response=$(curl -s -X POST "$BACKEND_URL/analyze" \
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
  }')

status=$(echo "$response" | python -c "import sys, json; print(json.load(sys.stdin).get('status', 'error'))" 2>/dev/null || echo "error")
if [ "$status" != "error" ]; then
    pass
else
    fail "Valid polygon was rejected"
fi

# ===============================================================================
# TEST 4: Response Format
# ===============================================================================

echo ""
print_test "Response includes request_id"
assert_contains "$response" "request_id" "Response missing request_id"

echo ""
print_test "Response includes timestamp"
assert_contains "$response" "timestamp" "Response missing timestamp"

echo ""
print_test "Response includes analysis_summary"
assert_contains "$response" "analysis_summary" "Response missing analysis_summary"

echo ""
print_test "Response includes land_information"
assert_contains "$response" "land_information" "Response missing land_information"

echo ""
print_test "Response includes processing_status"
assert_contains "$response" "processing_status" "Response missing processing_status"

echo ""
print_test "Response includes provider_status"
assert_contains "$response" "provider_status" "Response missing provider_status"

# ===============================================================================
# TEST 5: Invalid Polygon Handling
# ===============================================================================

echo ""
print_test "Invalid polygon (too small) is rejected"
response=$(curl -s -X POST "$BACKEND_URL/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "polygon": {
      "type": "Feature",
      "geometry": {
        "type": "Polygon",
        "coordinates": [[
          [0, 0],
          [0.001, 0],
          [0.001, 0.001],
          [0, 0.001],
          [0, 0]
        ]]
      }
    }
  }')

http_code=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BACKEND_URL/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "polygon": {
      "type": "Feature",
      "geometry": {
        "type": "Polygon",
        "coordinates": [[
          [0, 0],
          [0.001, 0],
          [0.001, 0.001],
          [0, 0.001],
          [0, 0]
        ]]
      }
    }
  }')

if [ "$http_code" == "400" ] || [ "$http_code" == "422" ]; then
    pass
else
    fail "Invalid polygon not rejected (HTTP $http_code)"
fi

echo ""
print_test "Missing polygon field is rejected"
response=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BACKEND_URL/analyze" \
  -H "Content-Type: application/json" \
  -d '{}')

if [ "$response" == "422" ]; then
    pass
else
    fail "Missing polygon field not rejected (HTTP $response)"
fi

# ===============================================================================
# TEST 6: Real Data Collection
# ===============================================================================

echo ""
print_test "Backend collects data from real providers"
response=$(curl -s -X POST "$BACKEND_URL/analyze" \
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
  }')

# Check if response contains provider status
assert_contains "$response" "provider_status" "Provider status not in response"

echo ""
print_test "At least one provider returns data"
# Extract provider_status and check for available providers
providers=$(echo "$response" | python -c "
import sys, json
data = json.load(sys.stdin)
status = data.get('provider_status', {})
available = [p for p in status if status[p].get('available')]
print(len(available))
" 2>/dev/null || echo "0")

if [ "$providers" -gt "0" ]; then
    pass
else
    fail "No providers returned data"
fi

# ===============================================================================
# TEST 7: Rule Engine Execution
# ===============================================================================

echo ""
print_test "Rule engine executes and returns results"
assert_contains "$response" "administrative" "Administrative rule missing"
assert_contains "$response" "land_cover" "Land cover rule missing"
assert_contains "$response" "buildings" "Buildings rule missing"

# ===============================================================================
# TEST 8: Error Handling
# ===============================================================================

echo ""
print_test "System handles malformed JSON gracefully"
http_code=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BACKEND_URL/analyze" \
  -H "Content-Type: application/json" \
  -d 'invalid json')

if [ "$http_code" == "422" ] || [ "$http_code" == "400" ]; then
    pass
else
    fail "Malformed JSON not handled properly (HTTP $http_code)"
fi

# ===============================================================================
# TEST 9: CORS Configuration
# ===============================================================================

echo ""
print_test "CORS headers are present"
response=$(curl -s -i "$BACKEND_URL/health" 2>&1)
if echo "$response" | grep -i "Access-Control-Allow"; then
    pass
else
    print_test "CORS headers not found (may be optional)"
fi

# ===============================================================================
# TEST 10: Performance
# ===============================================================================

echo ""
print_test "Analysis completes within reasonable time"
start_time=$(date +%s%N)

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
  }' > /dev/null

end_time=$(date +%s%N)
duration_ms=$(( (end_time - start_time) / 1000000 ))

if [ "$duration_ms" -lt 120000 ]; then  # 2 minutes
    pass
    echo "  Response time: ${duration_ms}ms"
else
    fail "Analysis took too long (${duration_ms}ms > 120000ms)"
fi

# ===============================================================================
# TEST 11: Frontend Availability
# ===============================================================================

echo ""
print_test "Frontend is accessible"
response=$(curl -s -o /dev/null -w "%{http_code}" "$FRONTEND_URL")
if [ "$response" == "200" ] || [ "$response" == "301" ] || [ "$response" == "302" ]; then
    pass
else
    fail "Frontend not accessible (HTTP $response)"
fi

# ===============================================================================
# TEST SUMMARY
# ===============================================================================

echo ""
echo "================================================================================"
echo "TEST SUMMARY"
echo "================================================================================"
echo "Total Tests: $TESTS_RUN"
echo -e "Passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "Failed: ${RED}$TESTS_FAILED${NC}"
echo ""

if [ "$TESTS_FAILED" -eq 0 ]; then
    echo -e "${GREEN}✓ ALL TESTS PASSED${NC}"
    echo ""
    echo "Production Deployment Status: VERIFIED"
    echo ""
    echo "Your deployment is ready:"
    echo "  - Backend: $BACKEND_URL"
    echo "  - Frontend: $FRONTEND_URL"
    echo ""
    exit 0
else
    echo -e "${RED}✗ SOME TESTS FAILED${NC}"
    echo ""
    echo "Troubleshooting:"
    echo "  1. Check backend logs: render logs -s land-scanner-backend"
    echo "  2. Check frontend logs: firebase hosting:channel:list"
    echo "  3. Verify provider connectivity"
    echo "  4. Check environment variables"
    echo ""
    exit 1
fi
