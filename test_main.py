from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["locations_loaded"] >= 12  # Allow for expanded locations


def test_alias_matches_location():
    response = client.get("/locate", params={"query": "where is the CSE block"})
    assert response.status_code == 200
    body = response.json()
    assert body["found"] is True
    assert body["name"] == "Computer Science and Engineering Department"
    assert body["directions"]
    assert body["directions_source"] in {"OpenStreetMap/OSRM", "needs_verified_directions"}


def test_unknown_query_does_not_guess():
    response = client.get("/locate", params={"query": "asdkfjhasdf"})
    assert response.status_code == 200
    body = response.json()
    assert body["found"] is False
    assert body["directions"] is None
    assert body["candidates"] == []


def test_api_key_is_enforced_when_configured(monkeypatch):
    import main

    monkeypatch.setattr(main, "API_KEY", "test-secret")
    assert client.get("/locate", params={"query": "CSE"}).status_code == 401
    assert client.get("/locate", params={"query": "CSE"}, headers={"x-api-key": "test-secret"}).status_code == 200


def test_locations_endpoint():
    """Test that /locations returns the full list of campus locations."""
    response = client.get("/locations")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert len(body) >= 12
    # Check structure
    first = body[0]
    assert "id" in first
    assert "name" in first
    assert "aliases" in first
    assert "latitude" in first
    assert "longitude" in first


def test_hostel_query():
    """Test that newly added hostel locations are findable."""
    response = client.get("/locate", params={"query": "kailash hostel"})
    assert response.status_code == 200
    body = response.json()
    assert body["found"] is True
    assert "Kailash" in body["name"]


def test_gate_query():
    """Test that gate locations are findable."""
    response = client.get("/locate", params={"query": "main gate"})
    assert response.status_code == 200
    body = response.json()
    assert body["found"] is True
    assert "Gate" in body["name"]


def test_named_origin():
    """Test that named origin parameter resolves correctly."""
    response = client.get("/locate", params={"query": "CSE", "origin": "kailash hostel"})
    assert response.status_code == 200
    body = response.json()
    assert body["found"] is True
    assert body["name"] == "Computer Science and Engineering Department"


def test_hindi_query_normalization():
    """Test that Hindi query framing is stripped correctly."""
    response = client.get("/locate", params={"query": "kahan hai library"})
    assert response.status_code == 200
    body = response.json()
    assert body["found"] is True
    assert "Library" in body["name"]


def test_frontend_returns_html():
    """Test that the root endpoint serves the HTML frontend."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")