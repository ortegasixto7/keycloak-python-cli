import typer

from kc.core.box import print_box
from kc.core.config import GLOBAL
from kc.core.keycloak import kc_request

client_roles_app = typer.Typer(add_completion=False, help="Manage client roles")


def _is_404(err: Exception) -> bool:
    return "404" in str(err).lower()


def _validate_0_1_n(flag: str, values: list[str], n: int) -> None:
    if not (len(values) == 0 or len(values) == 1 or len(values) == n):
        raise RuntimeError(
            f"invalid {flag}: when using multiple --name flags, you must pass either no {flag}, a single {flag} to apply to all, or one {flag} per --name (in order)"
        )


def _pick(values: list[str], i: int) -> str:
    if len(values) == 0:
        return ""
    if len(values) == 1:
        return values[0]
    return values[i]


def _resolve_target_realms(rt, realm: str, all_realms: bool) -> list[str]:
    if all_realms:
        realms = kc_request("GET", "/admin/realms")
        out: list[str] = []
        for r in realms:
            name = r.get("realm")
            if name:
                out.append(name)
        return out

    r = realm or rt.default_realm or GLOBAL.realm
    if not r:
        raise RuntimeError("target realm not specified. Use --realm or set realm in config.json")
    return [r]


def _get_client_internal_id(realm: str, client_id: str) -> str:
    clients = kc_request("GET", f"/admin/realms/{realm}/clients", params={"clientId": client_id})
    for c in clients:
        if c.get("clientId") == client_id and c.get("id"):
            return c["id"]
    raise RuntimeError(f"client {client_id!r} not found")


@client_roles_app.command("create")
def create(
    ctx: typer.Context,
    client_id: str = typer.Option("", "--client-id", help="target client-id (required)"),
    name: list[str] = typer.Option(None, "--name", help="client role name(s). Repeatable; required."),
    description: list[str] = typer.Option(None, "--description", help="client role description(s). Pass none, one (applies to all), or one per --name in order."),
    all_realms: bool = typer.Option(False, "--all-realms", help="create client role in all realms"),
    realm: str = typer.Option("", "--realm", help="target realm"),
):
    rt = ctx.obj

    if not client_id:
        raise RuntimeError("missing --client-id: target client-id is required")

    names = name or []
    descs = description or []

    if len(names) == 0:
        raise RuntimeError("missing --name: provide at least one --name")

    _validate_0_1_n("--description", descs, len(names))

    target_realms = _resolve_target_realms(rt, realm=realm, all_realms=all_realms)

    created = 0
    skipped = 0
    lines: list[str] = []

    for r in target_realms:
        internal_id = _get_client_internal_id(r, client_id)
        for i, rn in enumerate(names):
            try:
                kc_request("GET", f"/admin/realms/{r}/clients/{internal_id}/roles/{rn}")
                lines.append(f"Client role {rn!r} already exists in client {client_id!r} (realm {r!r}). Skipped.")
                skipped += 1
                continue
            except Exception as e:
                if not _is_404(e):
                    raise RuntimeError(f"failed checking client role in client {client_id}, realm {r}: {e}")

            desc = _pick(descs, i)
            payload = {"name": rn, "description": desc}
            kc_request("POST", f"/admin/realms/{r}/clients/{internal_id}/roles", json=payload)
            lines.append(f"Created client role {rn!r} in client {client_id!r} (realm {r!r}).")
            created += 1

    lines.append(f"Done. Created: {created}, Skipped: {skipped}.")

    realm_label = "all realms" if all_realms else (realm or (target_realms[0] if len(target_realms) == 1 else ""))
    print_box(lines, jira_ticket=rt.jira_ticket, realm_label=realm_label)
