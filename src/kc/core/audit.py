from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from datetime import datetime
from threading import Lock

from kc.core.config import GLOBAL


_LOCK = Lock()
_CSV_PATH = "kc_audit.csv"


def append_audit(
    *,
    status: str,
    command_path: str,
    raw_command: str,
    jira: str,
    target_realms: str,
    duration: str,
    details: str,
) -> None:
    with _LOCK:
        file_exists = os.path.exists(_CSV_PATH)
        with open(_CSV_PATH, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if not file_exists:
                w.writerow(
                    [
                        "timestamp",
                        "status",
                        "command_path",
                        "raw_command",
                        "jira",
                        "actor_type",
                        "actor_id",
                        "auth_realm",
                        "change_kind",
                        "target_realms",
                        "duration",
                        "details",
                    ]
                )

            actor_type, actor_id = _resolve_actor()
            w.writerow(
                [
                    datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
                    status,
                    command_path,
                    raw_command,
                    jira,
                    actor_type,
                    actor_id,
                    GLOBAL.auth_realm,
                    _resolve_change_kind(command_path),
                    target_realms,
                    duration,
                    details,
                ]
            )


def _resolve_actor() -> tuple[str, str]:
    if GLOBAL.grant_type == "password" and GLOBAL.username:
        return "user", GLOBAL.username
    if GLOBAL.client_id:
        return "client", GLOBAL.client_id
    return "unknown", ""


def _resolve_change_kind(command_path: str) -> str:
    mapping = {
        "kc users create": "users_create",
        "kc users update": "users_update",
        "kc users delete": "users_delete",
        "kc clients create": "clients_create",
        "kc clients update": "clients_update",
        "kc clients delete": "clients_delete",
        "kc clients list": "clients_list",
        "kc client-scopes create": "client_scopes_create",
        "kc client-scopes update": "client_scopes_update",
        "kc client-scopes delete": "client_scopes_delete",
        "kc client-scopes list": "client_scopes_list",
        "kc roles create": "roles_create",
        "kc roles update": "roles_update",
        "kc roles delete": "roles_delete",
        "kc realms list": "realms_list",
    }
    return mapping.get(command_path, command_path)
