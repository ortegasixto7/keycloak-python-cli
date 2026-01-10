import typer

from kc.core.box import print_box
from kc.core.config import GLOBAL
from kc.core.keycloak import kc_request

client_scopes_app = typer.Typer(add_completion=False, help="Manage client scopes")


def _is_404(err: Exception) -> bool:
    return "404" in str(err).lower()


def _validate_0_1_n(flag: str, values: list[str], n: int) -> None:
    if not (len(values) == 0 or len(values) == 1 or len(values) == n):
        raise RuntimeError(f"invalid {flag}")


def _pick(values: list[str], i: int) -> str:
    if len(values) == 0:
        return ""
    if len(values) == 1:
        return values[0]
    return values[i]


def _resolve_realms(rt, realm: str, all_realms: bool) -> list[str]:
    if all_realms:
        rs = kc_request("GET", "/admin/realms")
        out: list[str] = []
        for r in rs:
            name = r.get("realm")
            if name:
                out.append(name)
        return out

    r = realm or rt.default_realm or GLOBAL.realm
    if not r:
        raise RuntimeError("target realm not specified. Use --realm or set realm in config.json")
    return [r]


def _find_by_name(realm: str, name: str) -> dict:
    scopes = kc_request("GET", f"/admin/realms/{realm}/client-scopes")
    for s in scopes:
        if s.get("name") == name:
            return s
    raise RuntimeError(f"client scope {name!r} not found")


@client_scopes_app.command("create")
def create(
    ctx: typer.Context,
    name: list[str] = typer.Option(None, "--name", help="client scope name(s). Repeatable; required."),
    description: list[str] = typer.Option(None, "--description", help="description(s). Optional; 0,1 or N"),
    protocol: list[str] = typer.Option(None, "--protocol", help="protocol(s). Optional; 0,1 or N; default openid-connect"),
    all_realms: bool = typer.Option(False, "--all-realms", help="create in all realms"),
    realm: str = typer.Option("", "--realm", help="target realm"),
):
    rt = ctx.obj

    names = name or []
    descs = description or []
    prots = protocol or []

    if len(names) == 0:
        raise RuntimeError("missing --name: provide at least one --name")

    _validate_0_1_n("--description", descs, len(names))
    _validate_0_1_n("--protocol", prots, len(names))

    realms = _resolve_realms(rt, realm=realm, all_realms=all_realms)

    created, skipped = 0, 0
    lines: list[str] = []

    for r in realms:
        for i, n in enumerate(names):
            try:
                _find_by_name(r, n)
                lines.append(f"Client scope {n!r} already exists in realm {r!r}. Skipped.")
                skipped += 1
                continue
            except Exception:
                pass

            desc = _pick(descs, i)
            proto = _pick(prots, i) or "openid-connect"
            payload = {"name": n, "description": desc, "protocol": proto}

            try:
                scope_id = kc_request("POST", f"/admin/realms/{r}/client-scopes", json=payload)
            except Exception as e:
                if "409" in str(e).lower():
                    lines.append(f"Client scope {n!r} already exists in realm {r!r}. Skipped.")
                    skipped += 1
                    continue
                raise

            # Keycloak often returns 201 with Location, so just refetch to show ID
            s = _find_by_name(r, n)
            sid = s.get("id", "")
            lines.append(f"Created client scope {n!r} (ID: {sid}) in realm {r!r}.")
            created += 1

    lines.append(f"Done. Created: {created}, Skipped: {skipped}.")
    realm_label = "all realms" if all_realms else (realm or (realms[0] if len(realms) == 1 else ""))
    print_box(lines, jira_ticket=rt.jira_ticket, realm_label=realm_label)


@client_scopes_app.command("update")
def update(
    ctx: typer.Context,
    name: list[str] = typer.Option(None, "--name", help="client scope name(s) to update. Repeatable; required."),
    description: list[str] = typer.Option(None, "--description", help="new description(s). Optional; 0,1 or N"),
    protocol: list[str] = typer.Option(None, "--protocol", help="new protocol(s). Optional; 0,1 or N"),
    new_name: list[str] = typer.Option(None, "--new-name", help="new name(s). Optional; 0,1 or N"),
    all_realms: bool = typer.Option(False, "--all-realms", help="update in all realms"),
    realm: str = typer.Option("", "--realm", help="target realm"),
    ignore_missing: bool = typer.Option(False, "--ignore-missing", help="skip scopes not found instead of failing"),
):
    rt = ctx.obj

    names = name or []
    descs = description or []
    prots = protocol or []
    new_names = new_name or []

    if len(names) == 0:
        raise RuntimeError("missing --name: provide at least one --name")
    if len(descs) == 0 and len(prots) == 0 and len(new_names) == 0:
        raise RuntimeError("nothing to update: provide --description/--protocol/--new-name")

    _validate_0_1_n("--description", descs, len(names))
    _validate_0_1_n("--protocol", prots, len(names))
    _validate_0_1_n("--new-name", new_names, len(names))

    realms = _resolve_realms(rt, realm=realm, all_realms=all_realms)

    updated, skipped = 0, 0
    lines: list[str] = []

    for r in realms:
        for i, n in enumerate(names):
            try:
                s = _find_by_name(r, n)
            except Exception:
                if ignore_missing:
                    lines.append(f"Client scope {n!r} not found in realm {r!r}. Skipped.")
                    skipped += 1
                    continue
                raise RuntimeError(f"client scope {n!r} not found in realm {r}")

            sid = s.get("id")
            if not sid:
                raise RuntimeError(f"client scope {n!r} missing id")

            if descs:
                s["description"] = _pick(descs, i)
            if prots:
                s["protocol"] = _pick(prots, i)
            if new_names:
                s["name"] = _pick(new_names, i)

            kc_request("PUT", f"/admin/realms/{r}/client-scopes/{sid}", json=s)

            final_name = s.get("name", n)
            lines.append(f"Updated client scope {n!r} in realm {r!r}. New name: {final_name!r}.")
            updated += 1

    lines.append(f"Done. Updated: {updated}, Skipped: {skipped}.")
    realm_label = "all realms" if all_realms else (realm or (realms[0] if len(realms) == 1 else ""))
    print_box(lines, jira_ticket=rt.jira_ticket, realm_label=realm_label)


@client_scopes_app.command("delete")
def delete(
    ctx: typer.Context,
    name: list[str] = typer.Option(None, "--name", help="client scope name(s) to delete. Repeatable; required."),
    all_realms: bool = typer.Option(False, "--all-realms", help="delete in all realms"),
    realm: str = typer.Option("", "--realm", help="target realm"),
    ignore_missing: bool = typer.Option(False, "--ignore-missing", help="skip scopes not found instead of failing"),
):
    rt = ctx.obj

    names = name or []
    if len(names) == 0:
        raise RuntimeError("missing --name: provide at least one --name")

    realms = _resolve_realms(rt, realm=realm, all_realms=all_realms)

    deleted, skipped = 0, 0
    lines: list[str] = []

    for r in realms:
        for n in names:
            try:
                s = _find_by_name(r, n)
            except Exception:
                if ignore_missing:
                    lines.append(f"Client scope {n!r} not found in realm {r!r}. Skipped.")
                    skipped += 1
                    continue
                raise RuntimeError(f"client scope {n!r} not found in realm {r}")

            sid = s.get("id")
            kc_request("DELETE", f"/admin/realms/{r}/client-scopes/{sid}")
            lines.append(f"Deleted client scope {n!r} (ID: {sid}) in realm {r!r}.")
            deleted += 1

    lines.append(f"Done. Deleted: {deleted}, Skipped: {skipped}.")
    realm_label = "all realms" if all_realms else (realm or (realms[0] if len(realms) == 1 else ""))
    print_box(lines, jira_ticket=rt.jira_ticket, realm_label=realm_label)


@client_scopes_app.command("list")
def list_scopes(
    ctx: typer.Context,
    all_realms: bool = typer.Option(False, "--all-realms", help="list in all realms"),
    realm: str = typer.Option("", "--realm", help="target realm"),
):
    rt = ctx.obj

    realms = _resolve_realms(rt, realm=realm, all_realms=all_realms)

    total = 0
    lines: list[str] = []

    for r in realms:
        scopes = kc_request("GET", f"/admin/realms/{r}/client-scopes")
        for s in scopes:
            n = s.get("name")
            if n:
                lines.append(n)
                total += 1

    lines.append(f"Total: {total}")
    realm_label = "all realms" if all_realms else (realm or (realms[0] if len(realms) == 1 else ""))
    print_box(lines, jira_ticket=rt.jira_ticket, realm_label=realm_label)
