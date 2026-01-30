import pytest
from fastapi.testclient import TestClient
from src.main import app

@pytest.fixture
def client():
    """
    Fixture to provide a TestClient for the FastAPI application.
    """
    with TestClient(app) as test_client:
        yield test_client

def test_health_check(client):
    """
    Test the root health check endpoint.
    """
    response = client.get("/")
    assert response.status_code == 200
    assert "status" in response.json()
    assert response.json()["status"] == "online"

def test_generate_video_endpoint_validation(client):
    """
    Test that the generate-video endpoint returns error when missing files.
    """
    # Sending it without audio or images should trigger validation error
    response = client.post("/video/generate-video")
    assert response.status_code == 422 # Unprocessable Entity

def test_status_endpoint_not_found(client):
    """
    Test polling for a non-existent task.
    """
    response = client.get("/video/status/invalid-task-id")
    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"

# Note: Integration testing of the full video generation process 
# usually involves mocking MoviePy or providing small test assets.
# For this basic setup, we focus on endpoint connectivity.
