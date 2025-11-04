def test_read_root(client):
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    content_type = response.headers.get("content-type", "")
    if content_type.startswith("application/json"):
        data = response.json()
        assert "service" in data
        assert data["version"] == "1.0.0"
    else:
        body = response.text
        assert "<!DOCTYPE html>" in body
        assert '<div id="app">' in body


def test_health_check(client):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_startup_probe(client):
    """Test startup probe endpoint"""
    response = client.get("/startup")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"


def test_api_docs_available(client):
    """Test that API documentation is available"""
    response = client.get("/docs")
    assert response.status_code == 200
