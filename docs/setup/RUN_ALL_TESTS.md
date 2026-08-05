# Run All Tests - Complete Guide

## Quick Start (Recommended)

### One Command - Everything
Run this to test the entire project:

```bash
# Bash/Mac/Linux
bash run_all_tests.sh

# Windows PowerShell
.\run_all_tests.ps1
```

## Manual Testing

### Open 4 Terminals

**Terminal 1: Backend Tests**
```bash
cd backend
pytest tests/ -v --tb=short
```

**Terminal 2: Frontend Tests**
```bash
cd frontend
npm run test:run
```

**Terminal 3: Backend Server (optional)**
```bash
cd backend
python -m uvicorn main:app --reload
```

**Terminal 4: Frontend Dev Server (optional)**
```bash
cd frontend
npm run dev
```

## Test Categories

### 1. Backend Unit Tests (2-3 minutes)

**Polygon Validation**
```bash
cd backend
pytest tests/test_polygon_validator.py -v -m unit
```

**API Endpoints**
```bash
cd backend
pytest tests/test_api_endpoints.py -v -m api
```

### 2. Backend Integration Tests (3-5 minutes)

**Complete Pipeline**
```bash
cd backend
pytest tests/test_integration.py -v -m integration
```

### 3. Frontend Component Tests (1-2 minutes)

**App Component**
```bash
cd frontend
npm run test:run -- App.test.jsx
```

**Individual Components**
```bash
cd frontend
npm run test:run -- components.test.jsx
```

**Integration Tests**
```bash
cd frontend
npm run test:run -- integration.test.jsx
```

## Expected Results Summary

### Backend (Should see: ~42 tests passing)
```
tests/test_polygon_validator.py ......................... PASSED
tests/test_api_endpoints.py .............................. PASSED
tests/test_integration.py ................................ PASSED

======================== 42 passed in 2.34s ==========================
```

### Frontend (Should see: ~42 tests passing)
```
✓ App Component (6 tests)
✓ Header Component (3 tests)
✓ ControlPanel Component (5 tests)
✓ ErrorPanel Component (4 tests)
✓ LoadingIndicator Component (3 tests)
✓ ResultsPanel Component (6 tests)
✓ Frontend Integration Tests (12 tests)

Test Files  3 passed (3)
Tests  42 passed (42)
```

## Coverage Reports

### Backend Coverage
```bash
cd backend
pytest tests/ --cov=backend --cov-report=html
# Open: htmlcov/index.html
```

### Frontend Coverage
```bash
cd frontend
npm run test:coverage
# Check: coverage/index.html
```

## Troubleshooting

### Backend Tests Fail

**Check Python version:**
```bash
python --version  # Should be 3.9+
```

**Reinstall dependencies:**
```bash
cd backend
pip install --upgrade -r requirements.txt
pip install pytest pytest-asyncio httpx --force-reinstall
```

**Clear Python cache:**
```bash
find . -type d -name __pycache__ -exec rm -rf {} +
find . -name "*.pyc" -delete
```

### Frontend Tests Fail

**Check Node version:**
```bash
node --version  # Should be 16+
npm --version   # Should be 8+
```

**Reinstall dependencies:**
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
npm install --save-dev vitest @testing-library/react jsdom
```

**Clear npm cache:**
```bash
npm cache clean --force
```

## Performance Metrics

### Target Times
- Backend: < 5 seconds total
- Frontend: < 10 seconds total
- Coverage: < 15 seconds total

### Slowest Tests (Backend)
```bash
cd backend
pytest tests/ --durations=5
```

### Memory Usage
```bash
# Backend
pytest tests/ --memray

# Frontend
npm run test:run -- --reporter=verbose
```

## Continuous Integration

### GitHub Actions Status
Check `.github/workflows/` for CI configuration

### Local Git Hooks
```bash
# Setup pre-commit testing
cp scripts/pre-commit .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

## Advanced Options

### Run Specific Test Group

Backend:
```bash
pytest tests/ -k "polygon"  # Run polygon-related tests
pytest tests/ -k "api"      # Run API tests
pytest tests/ -k "health"   # Run health tests
```

Frontend:
```bash
npm run test:run -- -t "should render"
npm run test:run -- -t "Error"
npm run test:run -- --grep "integration"
```

### Verbose Output

Backend:
```bash
pytest tests/ -vv -s  # Double verbose + show print statements
```

Frontend:
```bash
npm run test:run -- --reporter=verbose
```

### Watch Mode (Development)

Backend:
```bash
cd backend
pytest-watch tests/
# Requires: pip install pytest-watch
```

Frontend:
```bash
cd frontend
npm run test -- --watch
```

### Parallel Execution

Backend:
```bash
pip install pytest-xdist
pytest tests/ -n auto
```

Frontend:
```bash
npm run test:run -- --threads=4
```

## Test Quality Checklist

Before committing code, verify:

- [ ] All backend tests pass: `pytest tests/ -v`
- [ ] All frontend tests pass: `npm run test:run`
- [ ] Backend coverage > 80%: `pytest tests/ --cov=backend`
- [ ] Frontend coverage > 80%: `npm run test:coverage`
- [ ] No linting errors: `npm run lint`
- [ ] App builds successfully: `npm run build`

## Test Results Archive

Save test results:
```bash
# Backend
pytest tests/ -v > test_results_backend.txt

# Frontend  
npm run test:run > test_results_frontend.txt
```

## Support

For issues or questions about testing:

1. Check TEST_GUIDE.md for detailed documentation
2. Check START_TESTING.md for quick setup
3. Run individual test file: `pytest tests/test_*.py -v`
4. Check test output for specific error messages
5. Review test files in `backend/tests/` and `frontend/src/__tests__/`

## Summary

| Component | Tests | Time | Coverage |
|-----------|-------|------|----------|
| Backend | 42 | 2-3s | 80%+ |
| Frontend | 42 | 5-10s | 80%+ |
| **Total** | **84** | **10-15s** | **80%+** |

**Status:** ✅ Ready for deployment when all tests pass
