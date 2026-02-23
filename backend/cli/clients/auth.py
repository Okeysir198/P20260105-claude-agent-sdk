"""Authentication utilities for CLI clients."""
import getpass

import httpx


async def perform_login(
    http_url: str,
    username: str,
    password: str | None,
    api_key: str | None = None,
) -> str:
    """Perform user login to obtain JWT token.

    Prompts for password via getpass if not provided.

    Raises:
        RuntimeError: If login fails or password is required but not provided.
    """
    if not password:
        password = getpass.getpass(f"Password for {username}: ")
        if not password:
            raise RuntimeError("Password is required for authentication")

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-API-Key"] = api_key

    async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
        response = await client.post(
            f"{http_url}/api/v1/auth/login",
            json={"username": username, "password": password},
        )

        if response.status_code != 200:
            raise RuntimeError(f"Login failed: {response.text}")

        data = response.json()
        if not data.get("success"):
            raise RuntimeError(f"Login failed: {data.get('error', 'Unknown error')}")

        token = data.get("token")
        if not token:
            raise RuntimeError("Login response missing token")

        return token
