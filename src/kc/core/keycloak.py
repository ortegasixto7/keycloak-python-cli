from __future__ import annotations

from typing import Any, Dict, Optional

import httpx

from kc.core.config import GLOBAL


_TOKEN_CACHE: dict[str, str] = {}


def _token_cache_key() -> str:
    return f"{GLOBAL.server_url}|{GLOBAL.auth_realm}|{GLOBAL.grant_type}|{GLOBAL.client_id}|{GLOBAL.username}"


def login() -> str:
    key = _token_cache_key()
    if key in _TOKEN_CACHE:
        return _TOKEN_CACHE[key]

    token_url = f"{GLOBAL.server_url.rstrip('/')}/realms/{GLOBAL.auth_realm}/protocol/openid-connect/token"

    if GLOBAL.grant_type == "password":
        data = {
            "grant_type": "password",
            "username": GLOBAL.username,
            "password": GLOBAL.password,
            "client_id": "admin-cli",
        }
    else:
        data = {
            "grant_type": "client_credentials",
            "client_id": GLOBAL.client_id,
            "client_secret": GLOBAL.client_secret,
        }

    with httpx.Client(timeout=30.0) as c:
        r = c.post(token_url, data=data)
        r.raise_for_status()
        payload = r.json()

    token = payload.get("access_token")
    if not token:
        raise RuntimeError("login failed: missing access_token")

    _TOKEN_CACHE[key] = token
    return token


def kc_raw_request(
    method: str,
    path: str,
    *,
    json: Any = None,
    params: Optional[dict[str, Any]] = None,
    timeout: float = 60.0,
) -> httpx.Response:
    token = login()
    url = f"{GLOBAL.server_url.rstrip('/')}{path}"

    headers = {"Authorization": f"Bearer {token}"}

    with httpx.Client(timeout=timeout) as c:
        r = c.request(method, url, headers=headers, json=json, params=params)

    if r.status_code >= 400:
        msg = r.text.strip()
        raise RuntimeError(f"{r.status_code}: {msg}")

    return r


def kc_request(method: str, path: str, *, json: Any = None, params: Optional[dict[str, Any]] = None) -> Any:
    r = kc_raw_request(method, path, json=json, params=params)

    if r.status_code == 204:
        return None

    ct = r.headers.get("content-type", "")
    if "application/json" in ct:
        return r.json()
    return r.text
