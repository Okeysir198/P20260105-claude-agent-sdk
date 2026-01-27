"""
Pytest configuration and fixtures for backend tests.
"""
import os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Load .env file from backend directory
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

# Set a test API key before importing app (only if not already set in .env)
os.environ.setdefault("API_KEY", "test-api-key-for-testing")

# Test user credentials - loaded from environment (set in .env file)
# These should match users created in the database
DEFAULT_USERNAME = os.getenv("CLI_USERNAME", "admin")
DEFAULT_PASSWORD = os.getenv("CLI_PASSWORD")


@pytest.fixture(scope="module")
def client():
    """Create a test client for the FastAPI application."""
    from api.main import create_app

    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def api_key():
    """Return the test API key."""
    return os.environ.get("API_KEY", "test-api-key-for-testing")


@pytest.fixture
def auth_headers(api_key):
    """Return headers with API key for authenticated requests."""
    return {"X-API-Key": api_key}


@pytest.fixture
def default_user():
    """Return default test user credentials.

    Requires CLI_PASSWORD to be set in environment or .env file.
    """
    if not DEFAULT_PASSWORD:
        pytest.skip("CLI_PASSWORD not set in environment")
    return {
        "username": DEFAULT_USERNAME,
        "password": DEFAULT_PASSWORD,
    }


@pytest.fixture
def user_token(client, auth_headers, default_user):
    """Get user identity token by logging in as default user.

    Returns the JWT token from successful login.
    """
    response = client.post(
        "/api/v1/auth/login",
        json=default_user,
        headers=auth_headers,
    )
    if response.status_code == 200:
        data = response.json()
        if data.get("success"):
            return data.get("token")
    return None


@pytest.fixture
def user_auth_headers(auth_headers, user_token):
    """Return headers with both API key and user token."""
    headers = dict(auth_headers)
    if user_token:
        headers["X-User-Token"] = user_token
    return headers
