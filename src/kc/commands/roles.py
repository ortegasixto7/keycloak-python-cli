import typer

from kc.core.box import print_box
from kc.core.config import GLOBAL
from kc.core.keycloak import kc_request

roles_app = typer.Typer(add_completion=False, help="Manage roles")


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


def _validate_0_1_n(flag: str, values: list[str], n: int) -> None:
    if not (len(values) == 0 or len(values) == 1 or len(values) == n):
        raise RuntimeError(
            f"invalid {flag}: when using multiple --name flags, you must pass either no {flag}, a single {flag} to apply to all, or one {flag} per --name (in order)"
        )


def _is_404(err: Exception) -> bool:
    return "404" in str(err).lower()


def _pick(values: list[str], i: int) -> str:
    if len(values) == 0:
        return ""
    if len(values) == 1:
        return values[0]
    return values[i]


@roles_app.command("create")
def roles_create(
    ctx: typer.Context,
    name: list[str] = typer.Option(None, "--name", help="role name(s). You can repeat --name multiple times."),
    description: list[str] = typer.Option(None, "--description", help="role description(s). Pass none, one (applies to all), or one per --name in order."),
    all_realms: bool = typer.Option(False, "--all-realms", help="create role in all realms"),
    realm: str = typer.Option("", "--realm", help="target realm"),
    interactive: bool = typer.Option(False, "-i", "--interactive", help="prompt for role parameters interactively"),
):
    rt = ctx.obj

    role_names = name or []
    role_descs = description or []

    if interactive:
        if not rt.jira_ticket:
            jira = typer.prompt("Jira ticket (optional, leave empty to skip)", default="", show_default=False)
            rt.jira_ticket = jira
        if not all_realms and not realm:
            ans = typer.prompt("Create role in all realms? [y/N]", default="N", show_default=False)
            if ans.strip().lower() in {"y", "yes"}:
                all_realms = True
        if not all_realms and not realm:
            realm = typer.prompt("Target realm (leave empty to use default/config)", default="", show_default=False)
        if len(role_names) == 0:
            raw = typer.prompt("Role name(s) (comma-separated)")
            role_names = [p.strip() for p in raw.split(",") if p.strip()]
        if len(role_descs) == 0:
            d = typer.prompt("Role description (optional, applies to all names)", default="", show_default=False)
            if d.strip():
                role_descs = [d.strip()]

    if len(role_names) == 0:
        raise RuntimeError("missing --name: provide at least one --name")

    _validate_0_1_n("--description", role_descs, len(role_names))

    target_realms = _resolve_target_realms(rt, realm=realm, all_realms=all_realms)

    created = 0
    skipped = 0
    lines: list[str] = []

    for r in target_realms:
        for i, rn in enumerate(role_names):
            try:
                kc_request("GET", f"/admin/realms/{r}/roles/{rn}")
                lines.append(f"Role {rn!r} already exists in realm {r!r}. Skipped.")
                skipped += 1
                continue
            except Exception as e:
                if not _is_404(e):
                    raise RuntimeError(f"failed checking role in realm {r}: {e}")

            desc = _pick(role_descs, i)
            payload = {"name": rn, "description": desc}
            kc_request("POST", f"/admin/realms/{r}/roles", json=payload)
            lines.append(f"Created role {rn!r} in realm {r!r}.")
            created += 1

    lines.append(f"Done. Created: {created}, Skipped: {skipped}.")

    realm_label = ""
    if all_realms:
        realm_label = "all realms"
    elif realm:
        realm_label = realm
    elif len(target_realms) == 1:
        realm_label = target_realms[0]

    print_box(lines, jira_ticket=rt.jira_ticket, realm_label=realm_label)


@roles_app.command("update")
def roles_update(
    ctx: typer.Context,
    name: list[str] = typer.Option(None, "--name", help="role name(s) to update. Repeatable; required."),
    description: list[str] = typer.Option(None, "--description", help="new description(s). Pass none, one (applies to all), or one per --name in order."),
    new_name: list[str] = typer.Option(None, "--new-name", help="new role name(s). Pass none, one (applies to all), or one per --name in order."),
    all_realms: bool = typer.Option(False, "--all-realms", help="update role(s) in all realms"),
    realm: str = typer.Option("", "--realm", help="target realm"),
    ignore_missing: bool = typer.Option(False, "--ignore-missing", help="skip roles not found instead of failing"),
):
    rt = ctx.obj

    role_names = name or []
    role_descs = description or []
    new_names = new_name or []

    if len(role_names) == 0:
        raise RuntimeError("missing --name: provide at least one --name")
    if len(role_descs) == 0 and len(new_names) == 0:
        raise RuntimeError("nothing to update: provide --description and/or --new-name")

    _validate_0_1_n("--description", role_descs, len(role_names))
    _validate_0_1_n("--new-name", new_names, len(role_names))

    target_realms = _resolve_target_realms(rt, realm=realm, all_realms=all_realms)

    updated = 0
    skipped = 0
    lines: list[str] = []

    for r in target_realms:
        for i, rn in enumerate(role_names):
            try:
                role = kc_request("GET", f"/admin/realms/{r}/roles/{rn}")
            except Exception as e:
                if _is_404(e):
                    if ignore_missing:
                        lines.append(f"Role {rn!r} not found in realm {r!r}. Skipped.")
                        skipped += 1
                        continue
                    raise RuntimeError(f"role {rn!r} not found in realm {r}")
                raise RuntimeError(f"failed fetching role {rn!r} in realm {r}: {e}")

            if len(role_descs) > 0:
                role["description"] = _pick(role_descs, i)
            if len(new_names) > 0:
                role["name"] = _pick(new_names, i)

            kc_request("PUT", f"/admin/realms/{r}/roles/{rn}", json=role)
            final_name = role.get("name", rn)
            lines.append(f"Updated role {rn!r} in realm {r!r}. New name: {final_name!r}.")
            updated += 1

    lines.append(f"Done. Updated: {updated}, Skipped: {skipped}.")

    realm_label = ""
    if all_realms:
        realm_label = "all realms"
    elif realm:
        realm_label = realm
    elif len(target_realms) == 1:
        realm_label = target_realms[0]

    print_box(lines, jira_ticket=rt.jira_ticket, realm_label=realm_label)


@roles_app.command("delete")
def roles_delete(
    ctx: typer.Context,
    name: list[str] = typer.Option(None, "--name", help="role name(s) to delete. Repeatable; required."),
    all_realms: bool = typer.Option(False, "--all-realms", help="delete role(s) in all realms"),
    realm: str = typer.Option("", "--realm", help="target realm"),
    ignore_missing: bool = typer.Option(False, "--ignore-missing", help="skip roles not found instead of failing"),
):
    rt = ctx.obj

    role_names = name or []
    if len(role_names) == 0:
        raise RuntimeError("missing --name: provide at least one --name")

    target_realms = _resolve_target_realms(rt, realm=realm, all_realms=all_realms)

    deleted = 0
    skipped = 0
    lines: list[str] = []

    for r in target_realms:
        for rn in role_names:
            try:
                kc_request("DELETE", f"/admin/realms/{r}/roles/{rn}")
                lines.append(f"Deleted role {rn!r} in realm {r!r}.")
                deleted += 1
            except Exception as e:
                if _is_404(e):
                    if ignore_missing:
                        lines.append(f"Role {rn!r} not found in realm {r!r}. Skipped.")
                        skipped += 1
                        continue
                    raise RuntimeError(f"role {rn!r} not found in realm {r}")
                raise RuntimeError(f"failed deleting role {rn!r} in realm {r}: {e}")

    lines.append(f"Done. Deleted: {deleted}, Skipped: {skipped}.")

    realm_label = ""
    if all_realms:
        realm_label = "all realms"
    elif realm:
        realm_label = realm
    elif len(target_realms) == 1:
        realm_label = target_realms[0]

    print_box(lines, jira_ticket=rt.jira_ticket, realm_label=realm_label)
