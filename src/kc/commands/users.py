import secrets
import string
from typing import Optional

import typer

from kc.core.box import print_box
from kc.core.config import GLOBAL
from kc.core.keycloak import kc_request

users_app = typer.Typer(add_completion=False, help="Manage users")


def _is_404(err: Exception) -> bool:
    return "404" in str(err).lower()


def _validate_0_1_n(flag: str, values: list[str], n: int) -> None:
    if not (len(values) == 0 or len(values) == 1 or len(values) == n):
        raise RuntimeError(
            f"invalid {flag}: when using multiple --username, you must pass either no {flag}, a single {flag} to apply to all, or one {flag} per --username (in order)"
        )


def _pick(values: list[str], i: int) -> str:
    if len(values) == 0:
        return ""
    if len(values) == 1:
        return values[0]
    return values[i]


def _resolve_target_realms(rt, realms: list[str], all_realms: bool) -> list[str]:
    if all_realms:
        rs = kc_request("GET", "/admin/realms")
        out: list[str] = []
        for r in rs:
            name = r.get("realm")
            if name:
                out.append(name)
        return out

    if realms:
        return list(realms)

    r = rt.default_realm or GLOBAL.realm
    if not r:
        raise RuntimeError("target realm not specified. Use --realm or set realm in config.json")
    return [r]


def _search_user(realm: str, username: str) -> Optional[dict]:
    users = kc_request("GET", f"/admin/realms/{realm}/users", params={"username": username})
    for u in users:
        if u.get("username") == username:
            return u
    return None


def _validate_password_strength(pw: str) -> None:
    if len(pw) < 6:
        raise RuntimeError("password must be at least 6 characters long")

    has_lower = any(c.islower() for c in pw)
    has_upper = any(c.isupper() for c in pw)
    has_digit = any(c.isdigit() for c in pw)
    has_special = any(not c.isalnum() for c in pw)

    if not (has_lower and has_upper and has_digit and has_special):
        raise RuntimeError(
            "password must contain at least one lowercase letter, one uppercase letter, one digit, and one special character"
        )


def _generate_strong_password(n: int) -> str:
    if n < 4:
        raise RuntimeError("password length must be at least 4")

    lower = string.ascii_lowercase
    upper = string.ascii_uppercase
    digits = string.digits
    specials = "!@#$%^&*()-_=+[]{}|;:,.<>/?"

    pools = [lower, upper, digits, specials]
    all_chars = lower + upper + digits + specials

    # guarantee at least one from each pool
    pw = [secrets.choice(p) for p in pools]
    pw.extend(secrets.choice(all_chars) for _ in range(n - len(pools)))

    secrets.SystemRandom().shuffle(pw)
    return "".join(pw)


def _get_client_internal_id(realm: str, client_id: str) -> str:
    clients = kc_request("GET", f"/admin/realms/{realm}/clients", params={"clientId": client_id})
    for c in clients:
        if c.get("clientId") == client_id and c.get("id"):
            return c["id"]
    raise RuntimeError(f"client {client_id!r} not found in realm {realm}")


def _get_realm_role(realm: str, role_name: str) -> dict:
    return kc_request("GET", f"/admin/realms/{realm}/roles/{role_name}")


def _get_client_role(realm: str, internal_client_id: str, role_name: str) -> dict:
    return kc_request("GET", f"/admin/realms/{realm}/clients/{internal_client_id}/roles/{role_name}")


@users_app.command("create")
def create(
    ctx: typer.Context,
    username: list[str] = typer.Option(None, "--username", help="username(s). Repeatable; required."),
    email: list[str] = typer.Option(None, "--email", help="email(s). Optional; 0, 1 or N matching --username."),
    first_name: list[str] = typer.Option(None, "--first-name", help="first name(s). Optional; 0, 1 or N matching --username."),
    last_name: list[str] = typer.Option(None, "--last-name", help="last name(s). Optional; 0, 1 or N matching --username."),
    password: list[str] = typer.Option(None, "--password", help="password(s). Optional; 0, 1 or N matching --username."),
    enabled: bool = typer.Option(True, "--enabled", help="whether the user(s) are enabled; defaults to true"),
    realm: list[str] = typer.Option(None, "--realm", help="target realm(s). If omitted, uses default or config.json"),
    all_realms: bool = typer.Option(False, "--all-realms", help="create users in all realms"),
    realm_role: list[str] = typer.Option(None, "--realm-role", help="realm role name(s) to assign to each created user"),
    client_role: list[str] = typer.Option(None, "--client-role", help="client role name(s) to assign to each created user"),
    client_id: str = typer.Option("", "--client-id", help="client-id whose roles will be assigned to created users"),
):
    rt = ctx.obj

    usernames = username or []
    emails = email or []
    firsts = first_name or []
    lasts = last_name or []
    passwords = password or []
    realm_roles = realm_role or []
    client_roles = client_role or []

    if len(usernames) == 0:
        raise RuntimeError("missing --username: provide at least one --username")

    for flag, values in [("--email", emails), ("--first-name", firsts), ("--last-name", lasts), ("--password", passwords)]:
        _validate_0_1_n(flag, values, len(usernames))

    if client_roles and not client_id:
        raise RuntimeError("missing --client-id when using --client-role")

    target_realms = _resolve_target_realms(rt, realm or [], all_realms)

    created = 0
    skipped = 0
    lines: list[str] = []
    pw_audit: list[str] = []

    for r in target_realms:
        internal_client_id = _get_client_internal_id(r, client_id) if client_roles else ""

        for i, un in enumerate(usernames):
            if _search_user(r, un) is not None:
                lines.append(f"User {un!r} already exists in realm {r!r}. Skipped.")
                skipped += 1
                continue

            em = _pick(emails, i)
            fn = _pick(firsts, i)
            ln = _pick(lasts, i)
            pw = _pick(passwords, i)

            if not pw:
                pw = _generate_strong_password(12)
                lines.append(f"Generated password for user {un!r} in realm {r!r}.")

            _validate_password_strength(pw)

            payload: dict = {
                "username": un,
                "enabled": enabled,
                "emailVerified": bool(em),
            }
            if em:
                payload["email"] = em
            if fn:
                payload["firstName"] = fn
            if ln:
                payload["lastName"] = ln

            # create user
            kc_request("POST", f"/admin/realms/{r}/users", json=payload)

            u = _search_user(r, un)
            if u is None or not u.get("id"):
                raise RuntimeError(f"failed creating user {un!r} in realm {r}: user not found after create")
            user_id = u["id"]

            # set password
            cred = {"type": "password", "value": pw, "temporary": False}
            kc_request("PUT", f"/admin/realms/{r}/users/{user_id}/reset-password", json=cred)

            # assign realm roles
            if realm_roles:
                roles_payload = [_get_realm_role(r, rn) for rn in realm_roles]
                kc_request("POST", f"/admin/realms/{r}/users/{user_id}/role-mappings/realm", json=roles_payload)

            # assign client roles
            if client_roles:
                roles_payload = [_get_client_role(r, internal_client_id, rn) for rn in client_roles]
                kc_request(
                    "POST",
                    f"/admin/realms/{r}/users/{user_id}/role-mappings/clients/{internal_client_id}",
                    json=roles_payload,
                )

            lines.append(f"Created user {un!r} (ID: {user_id}) in realm {r!r}.")
            lines.append(f"Password for user {un!r} in realm {r!r}: {pw}")
            pw_audit.append(pw)
            created += 1

    lines.append(f"Done. Created: {created}, Skipped: {skipped}.")

    if pw_audit:
        rt.audit_details = "passwords: " + ", ".join(pw_audit)

    realm_label = "all realms" if all_realms else (realm[0] if realm and len(realm) == 1 else (target_realms[0] if len(target_realms) == 1 else ""))
    print_box(lines, jira_ticket=rt.jira_ticket, realm_label=realm_label)


@users_app.command("update")
def update(
    ctx: typer.Context,
    username: list[str] = typer.Option(None, "--username", help="username(s) to update. Repeatable; required."),
    email: list[str] = typer.Option(None, "--email", help="new email(s). Optional; 0, 1 or N matching --username."),
    first_name: list[str] = typer.Option(None, "--first-name", help="new first name(s). Optional; 0, 1 or N."),
    last_name: list[str] = typer.Option(None, "--last-name", help="new last name(s). Optional; 0, 1 or N."),
    password: list[str] = typer.Option(None, "--password", help="new password(s). Optional; 0, 1 or N."),
    enabled: Optional[str] = typer.Option(None, "--enabled", help="set enabled state for users (true/false)"),
    realm: list[str] = typer.Option(None, "--realm", help="target realm(s). If omitted, uses default or config.json"),
    all_realms: bool = typer.Option(False, "--all-realms", help="update users in all realms"),
    ignore_missing: bool = typer.Option(False, "--ignore-missing", help="skip users not found instead of failing"),
):
    rt = ctx.obj

    usernames = username or []
    emails = email or []
    firsts = first_name or []
    lasts = last_name or []
    passwords = password or []

    if len(usernames) == 0:
        raise RuntimeError("missing --username: provide at least one --username")

    enabled_changed = enabled is not None

    if len(emails) == 0 and len(firsts) == 0 and len(lasts) == 0 and len(passwords) == 0 and not enabled_changed:
        raise RuntimeError("nothing to update: provide at least one of --email/--first-name/--last-name/--password/--enabled")

    for flag, values in [("--email", emails), ("--first-name", firsts), ("--last-name", lasts), ("--password", passwords)]:
        _validate_0_1_n(flag, values, len(usernames))

    target_realms = _resolve_target_realms(rt, realm or [], all_realms)

    updated = 0
    skipped = 0
    lines: list[str] = []
    pw_audit: list[str] = []

    for r in target_realms:
        for i, un in enumerate(usernames):
            u = _search_user(r, un)
            if u is None or not u.get("id"):
                if ignore_missing:
                    lines.append(f"User {un!r} not found in realm {r!r}. Skipped.")
                    skipped += 1
                    continue
                raise RuntimeError(f"user {un!r} not found in realm {r}")

            user_id = u["id"]

            em = _pick(emails, i)
            fn = _pick(firsts, i)
            ln = _pick(lasts, i)
            pw = _pick(passwords, i)

            if pw:
                _validate_password_strength(pw)

            patch: dict = {"id": user_id}
            if em:
                patch["email"] = em
                patch["emailVerified"] = True
            if fn:
                patch["firstName"] = fn
            if ln:
                patch["lastName"] = ln
            if enabled_changed:
                val = enabled.lower()
                if val in {"true", "1", "t", "yes", "y"}:
                    patch["enabled"] = True
                elif val in {"false", "0", "f", "no", "n"}:
                    patch["enabled"] = False
                else:
                    raise RuntimeError("invalid value for --enabled: use true/false")

            kc_request("PUT", f"/admin/realms/{r}/users/{user_id}", json=patch)

            if pw:
                cred = {"type": "password", "value": pw, "temporary": False}
                kc_request("PUT", f"/admin/realms/{r}/users/{user_id}/reset-password", json=cred)
                lines.append(f"Updated password for user {un!r} in realm {r!r}.")
                lines.append(f"New password for user {un!r} in realm {r!r}: {pw}")
                pw_audit.append(pw)

            lines.append(f"Updated user {un!r} (ID: {user_id}) in realm {r!r}.")
            updated += 1

    lines.append(f"Done. Updated: {updated}, Skipped: {skipped}.")

    if pw_audit:
        rt.audit_details = "passwords: " + ", ".join(pw_audit)

    realm_label = "all realms" if all_realms else (realm[0] if realm and len(realm) == 1 else (target_realms[0] if len(target_realms) == 1 else ""))
    print_box(lines, jira_ticket=rt.jira_ticket, realm_label=realm_label)


@users_app.command("delete")
def delete(
    ctx: typer.Context,
    username: list[str] = typer.Option(None, "--username", help="username(s) to delete. Repeatable; required."),
    realm: list[str] = typer.Option(None, "--realm", help="target realm(s). If omitted, uses default or config.json"),
    all_realms: bool = typer.Option(False, "--all-realms", help="delete users in all realms"),
    ignore_missing: bool = typer.Option(False, "--ignore-missing", help="skip users not found instead of failing"),
):
    rt = ctx.obj

    usernames = username or []
    if len(usernames) == 0:
        raise RuntimeError("missing --username: provide at least one --username")

    target_realms = _resolve_target_realms(rt, realm or [], all_realms)

    deleted = 0
    skipped = 0
    lines: list[str] = []

    for r in target_realms:
        for un in usernames:
            u = _search_user(r, un)
            if u is None or not u.get("id"):
                if ignore_missing:
                    lines.append(f"User {un!r} not found in realm {r!r}. Skipped.")
                    skipped += 1
                    continue
                raise RuntimeError(f"user {un!r} not found in realm {r}")

            user_id = u["id"]
            kc_request("DELETE", f"/admin/realms/{r}/users/{user_id}")
            lines.append(f"Deleted user {un!r} (ID: {user_id}) in realm {r!r}.")
            deleted += 1

    lines.append(f"Done. Deleted: {deleted}, Skipped: {skipped}.")

    realm_label = "all realms" if all_realms else (realm[0] if realm and len(realm) == 1 else (target_realms[0] if len(target_realms) == 1 else ""))
    print_box(lines, jira_ticket=rt.jira_ticket, realm_label=realm_label)
