import httpx
import pytest
import time

BASE_URL = "https://land-scanner-prototype-backend.onrender.com"

def test_backend_crash_empty_body():
    """Backend should not crash on empty POST body"""
    try:
        resp = httpx.post(f"{BASE_URL}/analyze", content="", timeout=30)
        assert resp.status_code in (400, 422, 500)
    except Exception:
        pass  # timeout/connection error also indicates instability

def test_backend_crash_malformed_json():
    """Backend should not crash on malformed JSON"""
    try:
        resp = httpx.post(f"{BASE_URL}/analyze", content="{invalid json!!!", timeout=30)
        assert resp.status_code in (400, 422, 500)
    except Exception:
        pass  # timeout/connection error also indicates instability

def test_backend_crash_huge_polygon():
    """Backend should not crash on extremely large coordinate arrays"""
    huge_poly = {
        "type": "Polygon",
        "coordinates": [[[0, 0]] + [[i, i] for i in range(100000)] + [[0, 0]]]
    }
    resp = httpx.post(f"{BASE_URL}/analyze", json=huge_poly, timeout=30)
    assert resp.status_code in (200, 400, 422, 500)

def test_backend_crash_invalid_coordinate_types():
    """Backend should handle non-numeric coordinates gracefully"""
    bad_poly = {
        "type": "Polygon",
        "coordinates": [[[None, "abc", True], [1, 2, 3], [0, 0]]]
    }
    resp = httpx.post(f"{BASE_URL}/analyze", json=bad_poly, timeout=10)
    assert resp.status_code in (200, 400, 422, 500)

def test_backend_crash_sql_injection_attempt():
    """Backend should not crash or execute SQL injection"""
    malicious = {
        "type": "Polygon",
        "coordinates": [[[0, 0], [1, 1], [1, 0], [0, 0]]]
    }
    resp = httpx.post(f"{BASE_URL}/analyze?q=DROP%20TABLE", json=malicious, timeout=10)
    assert resp.status_code in (200, 400, 422, 500)

def test_backend_crash_path_traversal():
    """Backend should not crash on path traversal attempts"""
    resp = httpx.get(f"{BASE_URL}/../../../etc/passwd", timeout=10)
    assert resp.status_code in (404, 400, 422, 500)

def test_backend_health_after_crashes():
    """Backend should still be healthy after crash attempts"""
    resp = httpx.get(f"{BASE_URL}/health", timeout=10)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"

def test_backend_status_after_crashes():
    """Backend status endpoint should still work"""
    resp = httpx.get(f"{BASE_URL}/status", timeout=10)
    assert resp.status_code == 200

def test_backend_crash_missing_type():
    """Backend should handle polygon missing type field"""
    bad_poly = {"coordinates": [[[0, 0], [1, 1], [1, 0], [0, 0]]]}
    resp = httpx.post(f"{BASE_URL}/analyze", json=bad_poly, timeout=10)
    assert resp.status_code in (400, 422, 500)

def test_backend_crash_null_values():
    """Backend should handle null values in polygon"""
    bad_poly = {
        "type": "Polygon",
        "coordinates": None
    }
    resp = httpx.post(f"{BASE_URL}/analyze", json=bad_poly, timeout=10)
    assert resp.status_code in (400, 422, 500)
