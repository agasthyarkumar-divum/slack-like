"""Shared test helpers — not a conftest.py, so these are plain importable
functions rather than fixtures (channels/messages tests need multiple
independent users per test, which a single fixture can't parameterize).
"""


async def register_and_login(
    client, email: str, password: str = "correct horse battery staple", display_name: str = "Test User"
) -> dict:
    await client.post(
        "/auth/register",
        json={"email": email, "password": password, "display_name": display_name},
    )
    response = await client.post("/auth/login", json={"email": email, "password": password})
    return response.json()


def auth_header(tokens: dict) -> dict:
    return {"Authorization": f"Bearer {tokens['access_token']}"}
