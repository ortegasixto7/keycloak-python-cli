from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path


@dataclass
class Config:
    server_url: str = ""
    auth_realm: str = ""
    realm: str = ""
    client_id: str = ""
    client_secret: str = ""
    username: str = ""
    password: str = ""
    grant_type: str = ""


GLOBAL = Config()


def _find_default_config_path() -> str:
    try:
        exe = Path(os.path.realpath(__file__)).resolve()
    except Exception:
        exe = None

    if exe is not None:
        # approximate "next to binary" by checking current working dir first and then project root
        pass

    # check executable directory if running from a frozen app
    frozen_exe = getattr(__import__("sys"), "executable", None)
    if frozen_exe:
        p = Path(frozen_exe).resolve().parent / "config.json"
        if p.exists():
            return str(p)

    p = Path("config.json").resolve()
    if p.exists():
        return str(p)

    return ""


def load_config(path: str) -> None:
    cfg_path = path or _find_default_config_path()
    if not cfg_path:
        raise RuntimeError("config.json not found")

    with open(cfg_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    GLOBAL.server_url = data.get("server_url", "")
    GLOBAL.auth_realm = data.get("auth_realm", "") or "master"
    GLOBAL.realm = data.get("realm", "")
    GLOBAL.client_id = data.get("client_id", "")
    GLOBAL.client_secret = data.get("client_secret", "")
    GLOBAL.username = data.get("username", "")
    GLOBAL.password = data.get("password", "")
    GLOBAL.grant_type = data.get("grant_type", "") or "client_credentials"

    if not GLOBAL.server_url:
        raise RuntimeError("server_url is required")
