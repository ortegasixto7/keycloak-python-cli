import typer

from kc.core.box import print_box
from kc.core.config import GLOBAL
from kc.core.keycloak import kc_raw_request, kc_request

clients_app = typer.Typer(add_completion=False, help="Manage clients")


def _is_404(err: Exception) -> bool:
    return "404" in str(err).lower()


def _pick(values, i):
    if values is None:
        return None, False
    if len(values) == 1:
        return values[0], True
    if len(values) > 1:
        return values[i], True
    return None, False


def _parse_bool(val: str, flag: str) -> bool:
    v = val.strip().lower()
    if v in {"true", "1", "t", "yes", "y"}:
        return True
    if v in {"false", "0", "f", "no", "n"}:
        return False
    raise RuntimeError(f"invalid value for {flag}: use true/false")


def _resolve_realms(rt, realms: list[str], all_realms: bool) -> list[str]:
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


def _get_client_by_client_id(realm: str, client_id: str) -> dict:
    clients = kc_request("GET", f"/admin/realms/{realm}/clients", params={"clientId": client_id})
    for c in clients:
        if c.get("clientId") == client_id:
            return c
    raise RuntimeError(f"client {client_id!r} not found")


@clients_app.command("create")
def create(
    ctx: typer.Context,
    client_id: list[str] = typer.Option(None, "--client-id", help="client-id(s). Repeatable; required."),
    name: list[str] = typer.Option(None, "--name", help="name(s). Optional; 0, 1 or N matching --client-id."),
    public: list[str] = typer.Option(None, "--public", help="public client(s). Optional; 0, 1 or N; default false (pass true/false)"),
    secret: list[str] = typer.Option(None, "--secret", help="secret(s). Optional; ignored for public clients"),
    enabled: list[str] = typer.Option(None, "--enabled", help="enabled flag(s). Optional; 0, 1 or N; default true (pass true/false)"),
    protocol: list[str] = typer.Option(None, "--protocol", help="protocol(s). Optional; 0, 1 or N; e.g. openid-connect"),
    root_url: list[str] = typer.Option(None, "--root-url", help="root URL(s). Optional; 0, 1 or N"),
    base_url: list[str] = typer.Option(None, "--base-url", help="base URL(s). Optional; 0, 1 or N"),
    redirect_uri: list[str] = typer.Option(None, "--redirect-uri", help="redirect URI list; applies to all targeted clients"),
    web_origin: list[str] = typer.Option(None, "--web-origin", help="web origin list; applies to all targeted clients"),
    standard_flow: list[str] = typer.Option(None, "--standard-flow", help="enable standard flow(s). Optional; 0,1 or N (true/false)"),
    direct_access: list[str] = typer.Option(None, "--direct-access", help="enable direct access grants(s). Optional; 0,1 or N (true/false)"),
    implicit_flow: list[str] = typer.Option(None, "--implicit-flow", help="enable implicit flow(s). Optional; 0,1 or N (true/false)"),
    service_accounts: list[str] = typer.Option(None, "--service-accounts", help="enable service accounts(s). Optional; 0,1 or N (true/false)"),
    realm: list[str] = typer.Option(None, "--realm", help="target realm(s). If omitted, uses default or config.json"),
    all_realms: bool = typer.Option(False, "--all-realms", help="apply to all realms"),
):
    rt = ctx.obj

    ids = client_id or []
    if len(ids) == 0:
        raise RuntimeError("missing --client-id: provide at least one --client-id")

    realms = _resolve_realms(rt, realm or [], all_realms)

    created, skipped = 0, 0
    lines: list[str] = []

    for r in realms:
        for i, cid in enumerate(ids):
            try:
                _get_client_by_client_id(r, cid)
                lines.append(f"Client {cid!r} already exists in realm {r!r}. Skipped.")
                skipped += 1
                continue
            except Exception:
                pass

            nm, _ = _pick(name or [], i)
            pub, has_pub = _pick(public or [], i)
            en, has_en = _pick(enabled or [], i)
            proto, _ = _pick(protocol or [], i)
            ru, _ = _pick(root_url or [], i)
            bu, _ = _pick(base_url or [], i)
            std, _ = _pick(standard_flow or [], i)
            da, _ = _pick(direct_access or [], i)
            imp, _ = _pick(implicit_flow or [], i)
            svc, _ = _pick(service_accounts or [], i)
            sec, _ = _pick(secret or [], i)

            payload: dict = {"clientId": cid}
            if nm:
                payload["name"] = nm

            payload["enabled"] = _parse_bool(str(en), "--enabled") if has_en else True
            payload["publicClient"] = _parse_bool(str(pub), "--public") if has_pub else False

            if proto:
                payload["protocol"] = proto
            if ru:
                payload["rootUrl"] = ru
            if bu:
                payload["baseUrl"] = bu

            if std is not None:
                payload["standardFlowEnabled"] = _parse_bool(str(std), "--standard-flow")
            if da is not None:
                payload["directAccessGrantsEnabled"] = _parse_bool(str(da), "--direct-access")
            if imp is not None:
                payload["implicitFlowEnabled"] = _parse_bool(str(imp), "--implicit-flow")
            if svc is not None:
                payload["serviceAccountsEnabled"] = _parse_bool(str(svc), "--service-accounts")

            resp = kc_raw_request("POST", f"/admin/realms/{r}/clients", json=payload)

            # fetch created client to get its internal id
            created_client = _get_client_by_client_id(r, cid)
            internal_id = created_client.get("id", "")

            if sec and not payload.get("publicClient", False):
                import sys

                sys.stderr.write(
                    f"Warning: --secret provided for client {cid!r} but explicit secret setting is not supported. Skipped setting secret.\n"
                )

            # Apply redirect URIs and web origins as full replacement (Go applies list to all clients)
            if redirect_uri:
                kc_request("PUT", f"/admin/realms/{r}/clients/{internal_id}", json={"id": internal_id, "redirectUris": list(redirect_uri)})
            if web_origin:
                kc_request("PUT", f"/admin/realms/{r}/clients/{internal_id}", json={"id": internal_id, "webOrigins": list(web_origin)})

            lines.append(f"Created client {cid!r} (ID: {internal_id}) in realm {r!r}.")
            created += 1

    lines.append(f"Done. Created: {created}, Skipped: {skipped}.")
    realm_label = "all realms" if all_realms else (realm[0] if realm and len(realm) == 1 else (realms[0] if len(realms) == 1 else ""))
    print_box(lines, jira_ticket=rt.jira_ticket, realm_label=realm_label)


@clients_app.command("update")
def update(
    ctx: typer.Context,
    client_id: list[str] = typer.Option(None, "--client-id", help="client-id(s) to update. Repeatable; required."),
    name: list[str] = typer.Option(None, "--name", help="new name(s). Optional; 0, 1 or N"),
    public: list[str] = typer.Option(None, "--public", help="set public flag(s). Optional; 0, 1 or N (true/false)"),
    secret: list[str] = typer.Option(None, "--secret", help="new secret(s). Optional; ignored for public clients"),
    enabled: list[str] = typer.Option(None, "--enabled", help="set enabled flag(s). Optional; 0, 1 or N (true/false)"),
    protocol: list[str] = typer.Option(None, "--protocol", help="protocol(s). Optional; 0, 1 or N"),
    root_url: list[str] = typer.Option(None, "--root-url", help="root URL(s). Optional; 0, 1 or N"),
    base_url: list[str] = typer.Option(None, "--base-url", help="base URL(s). Optional; 0, 1 or N"),
    redirect_uri: list[str] = typer.Option(None, "--redirect-uri", help="redirect URI list to replace; applies to all targeted clients"),
    web_origin: list[str] = typer.Option(None, "--web-origin", help="web origin list to replace; applies to all targeted clients"),
    standard_flow: list[str] = typer.Option(None, "--standard-flow", help="enable standard flow(s). Optional; 0,1 or N (true/false)"),
    direct_access: list[str] = typer.Option(None, "--direct-access", help="enable direct access grants(s). Optional; 0,1 or N (true/false)"),
    implicit_flow: list[str] = typer.Option(None, "--implicit-flow", help="enable implicit flow(s). Optional; 0,1 or N (true/false)"),
    service_accounts: list[str] = typer.Option(None, "--service-accounts", help="enable service accounts(s). Optional; 0,1 or N (true/false)"),
    new_client_id: list[str] = typer.Option(None, "--new-client-id", help="new client-id(s). Optional; 0,1 or N"),
    ignore_missing: bool = typer.Option(False, "--ignore-missing", help="skip clients not found instead of failing"),
    realm: list[str] = typer.Option(None, "--realm", help="target realm(s). If omitted, uses default or config.json"),
    all_realms: bool = typer.Option(False, "--all-realms", help="apply to all realms"),
):
    rt = ctx.obj

    ids = client_id or []
    if len(ids) == 0:
        raise RuntimeError("missing --client-id: provide at least one --client-id")

    any_update = any(
        [
            bool(name),
            bool(public),
            bool(secret),
            bool(enabled),
            bool(protocol),
            bool(root_url),
            bool(base_url),
            bool(redirect_uri),
            bool(web_origin),
            bool(standard_flow),
            bool(direct_access),
            bool(implicit_flow),
            bool(service_accounts),
            bool(new_client_id),
        ]
    )
    if not any_update:
        raise RuntimeError("nothing to update: provide at least one field flag")

    realms = _resolve_realms(rt, realm or [], all_realms)

    updated, skipped = 0, 0
    lines: list[str] = []

    for r in realms:
        for i, cid in enumerate(ids):
            try:
                c = _get_client_by_client_id(r, cid)
            except Exception:
                if ignore_missing:
                    lines.append(f"Client {cid!r} not found in realm {r!r}. Skipped.")
                    skipped += 1
                    continue
                raise RuntimeError(f"client {cid!r} not found in realm {r}")

            internal_id = c.get("id")
            if not internal_id:
                raise RuntimeError(f"client {cid!r} has no internal id")

            nm, has_nm = _pick(name or [], i)
            pub, has_pub = _pick(public or [], i)
            en, has_en = _pick(enabled or [], i)
            proto, has_proto = _pick(protocol or [], i)
            ru, has_ru = _pick(root_url or [], i)
            bu, has_bu = _pick(base_url or [], i)
            std, has_std = _pick(standard_flow or [], i)
            da, has_da = _pick(direct_access or [], i)
            imp, has_imp = _pick(implicit_flow or [], i)
            svc, has_svc = _pick(service_accounts or [], i)
            sec, has_sec = _pick(secret or [], i)
            ncid, has_ncid = _pick(new_client_id or [], i)

            patch: dict = {"id": internal_id}
            if has_nm and nm is not None:
                patch["name"] = nm
            if has_pub:
                patch["publicClient"] = _parse_bool(str(pub), "--public")
            if has_en:
                patch["enabled"] = _parse_bool(str(en), "--enabled")
            if has_std:
                patch["standardFlowEnabled"] = _parse_bool(str(std), "--standard-flow")
            if has_da:
                patch["directAccessGrantsEnabled"] = _parse_bool(str(da), "--direct-access")
            if has_imp:
                patch["implicitFlowEnabled"] = _parse_bool(str(imp), "--implicit-flow")
            if has_svc:
                patch["serviceAccountsEnabled"] = _parse_bool(str(svc), "--service-accounts")
            if redirect_uri:
                patch["redirectUris"] = list(redirect_uri)
            if web_origin:
                patch["webOrigins"] = list(web_origin)

            kc_request("PUT", f"/admin/realms/{r}/clients/{internal_id}", json=patch)

            if has_sec and sec and not patch.get("publicClient", c.get("publicClient", False)):
                import sys

                sys.stderr.write(
                    f"Warning: --secret provided for client {cid!r} but explicit secret setting is not supported. Skipped setting secret.\n"
                )

            if has_ncid and ncid:
                kc_request("PUT", f"/admin/realms/{r}/clients/{internal_id}", json={"id": internal_id, "clientId": ncid})

            lines.append(f"Updated client {cid!r} (ID: {internal_id}) in realm {r!r}.")
            updated += 1

    lines.append(f"Done. Updated: {updated}, Skipped: {skipped}.")
    realm_label = "all realms" if all_realms else (realm[0] if realm and len(realm) == 1 else (realms[0] if len(realms) == 1 else ""))
    print_box(lines, jira_ticket=rt.jira_ticket, realm_label=realm_label)


@clients_app.command("delete")
def delete(
    ctx: typer.Context,
    client_id: list[str] = typer.Option(None, "--client-id", help="client-id(s) to delete. Repeatable; required."),
    ignore_missing: bool = typer.Option(False, "--ignore-missing", help="skip clients not found instead of failing"),
    realm: list[str] = typer.Option(None, "--realm", help="target realm(s). If omitted, uses default or config.json"),
    all_realms: bool = typer.Option(False, "--all-realms", help="apply to all realms"),
):
    rt = ctx.obj

    ids = client_id or []
    if len(ids) == 0:
        raise RuntimeError("missing --client-id: provide at least one --client-id")

    realms = _resolve_realms(rt, realm or [], all_realms)

    deleted, skipped = 0, 0
    lines: list[str] = []

    for r in realms:
        for cid in ids:
            try:
                c = _get_client_by_client_id(r, cid)
            except Exception:
                if ignore_missing:
                    lines.append(f"Client {cid!r} not found in realm {r!r}. Skipped.")
                    skipped += 1
                    continue
                raise RuntimeError(f"client {cid!r} not found in realm {r}")

            internal_id = c.get("id")
            kc_request("DELETE", f"/admin/realms/{r}/clients/{internal_id}")
            lines.append(f"Deleted client {cid!r} (ID: {internal_id}) in realm {r!r}.")
            deleted += 1

    lines.append(f"Done. Deleted: {deleted}, Skipped: {skipped}.")
    realm_label = "all realms" if all_realms else (realm[0] if realm and len(realm) == 1 else (realms[0] if len(realms) == 1 else ""))
    print_box(lines, jira_ticket=rt.jira_ticket, realm_label=realm_label)


@clients_app.command("list")
def list_clients(
    ctx: typer.Context,
    client_id: list[str] = typer.Option(None, "--client-id", help="filter by client-id (single value supported)"),
    realm: list[str] = typer.Option(None, "--realm", help="target realm(s). If omitted, uses default or config.json"),
    all_realms: bool = typer.Option(False, "--all-realms", help="apply to all realms"),
):
    rt = ctx.obj

    ids = client_id or []
    realms = _resolve_realms(rt, realm or [], all_realms)

    total = 0
    lines: list[str] = []

    for r in realms:
        params = {}
        if len(ids) == 1:
            params["clientId"] = ids[0]
        clients = kc_request("GET", f"/admin/realms/{r}/clients", params=params)
        for c in clients:
            cid = c.get("clientId")
            if cid:
                lines.append(cid)
                total += 1

    lines.append(f"Total: {total}")
    realm_label = "all realms" if all_realms else (realm[0] if realm and len(realm) == 1 else (realms[0] if len(realms) == 1 else ""))
    print_box(lines, jira_ticket=rt.jira_ticket, realm_label=realm_label)


scopes_app = typer.Typer(add_completion=False, help="Manage client scope assignments")


def _find_client_scope_id(realm: str, scope_name: str) -> str:
    scopes = kc_request("GET", f"/admin/realms/{realm}/client-scopes")
    for s in scopes:
        if s.get("name") == scope_name and s.get("id"):
            return s["id"]
    raise RuntimeError(f"client scope {scope_name!r} not found in realm {realm}")


@scopes_app.command("assign")
def scopes_assign(
    ctx: typer.Context,
    client_id: str = typer.Option("", "--client-id", help="target client-id (required)"),
    scope: list[str] = typer.Option(None, "--scope", help="client scope name(s) to assign (required)"),
    type: str = typer.Option("default", "--type", help="assignment type: default|optional"),
    realm: list[str] = typer.Option(None, "--realm", help="target realm(s). If omitted, uses default or config.json"),
    all_realms: bool = typer.Option(False, "--all-realms", help="apply to all realms"),
):
    rt = ctx.obj

    if not client_id:
        raise RuntimeError("missing --client-id")
    scopes = scope or []
    if len(scopes) == 0:
        raise RuntimeError("missing --scope: provide at least one --scope")
    if type not in {"default", "optional"}:
        raise RuntimeError("invalid --type: must be 'default' or 'optional'")

    realms = _resolve_realms(rt, realm or [], all_realms)

    assigned, skipped = 0, 0
    lines: list[str] = []

    for r in realms:
        c = _get_client_by_client_id(r, client_id)
        internal_id = c.get("id")
        if not internal_id:
            raise RuntimeError(f"client {client_id!r} not found in realm {r}")

        for sn in scopes:
            scope_id = _find_client_scope_id(r, sn)
            if type == "default":
                try:
                    kc_request("PUT", f"/admin/realms/{r}/clients/{internal_id}/default-client-scopes/{scope_id}")
                except Exception as e:
                    if "409" in str(e).lower():
                        lines.append(f"Scope {sn!r} already default for client {client_id!r} in realm {r!r}. Skipped.")
                        skipped += 1
                        continue
                    raise
            else:
                try:
                    kc_request("PUT", f"/admin/realms/{r}/clients/{internal_id}/optional-client-scopes/{scope_id}")
                except Exception as e:
                    if "409" in str(e).lower():
                        lines.append(f"Scope {sn!r} already optional for client {client_id!r} in realm {r!r}. Skipped.")
                        skipped += 1
                        continue
                    raise

            lines.append(f"Assigned {type} scope {sn!r} to client {client_id!r} in realm {r!r}.")
            assigned += 1

    lines.append(f"Done. Assigned: {assigned}, Skipped: {skipped}.")
    realm_label = "all realms" if all_realms else (realm[0] if realm and len(realm) == 1 else (realms[0] if len(realms) == 1 else ""))
    print_box(lines, jira_ticket=rt.jira_ticket, realm_label=realm_label)


@scopes_app.command("remove")
def scopes_remove(
    ctx: typer.Context,
    client_id: str = typer.Option("", "--client-id", help="target client-id (required)"),
    scope: list[str] = typer.Option(None, "--scope", help="client scope name(s) to remove (required)"),
    type: str = typer.Option("default", "--type", help="assignment type: default|optional"),
    ignore_missing: bool = typer.Option(False, "--ignore-missing", help="skip scopes not found/assigned instead of failing"),
    realm: list[str] = typer.Option(None, "--realm", help="target realm(s). If omitted, uses default or config.json"),
    all_realms: bool = typer.Option(False, "--all-realms", help="apply to all realms"),
):
    rt = ctx.obj

    if not client_id:
        raise RuntimeError("missing --client-id")
    scopes = scope or []
    if len(scopes) == 0:
        raise RuntimeError("missing --scope: provide at least one --scope")
    if type not in {"default", "optional"}:
        raise RuntimeError("invalid --type: must be 'default' or 'optional'")

    realms = _resolve_realms(rt, realm or [], all_realms)

    removed, skipped = 0, 0
    lines: list[str] = []

    for r in realms:
        c = _get_client_by_client_id(r, client_id)
        internal_id = c.get("id")
        if not internal_id:
            raise RuntimeError(f"client {client_id!r} not found in realm {r}")

        for sn in scopes:
            try:
                scope_id = _find_client_scope_id(r, sn)
            except Exception:
                if ignore_missing:
                    lines.append(f"Client scope {sn!r} not found in realm {r!r}. Skipped.")
                    skipped += 1
                    continue
                raise

            try:
                if type == "default":
                    kc_request("DELETE", f"/admin/realms/{r}/clients/{internal_id}/default-client-scopes/{scope_id}")
                else:
                    kc_request("DELETE", f"/admin/realms/{r}/clients/{internal_id}/optional-client-scopes/{scope_id}")
            except Exception as e:
                if _is_404(e) and ignore_missing:
                    lines.append(f"{type.capitalize()} scope {sn!r} not assigned to client {client_id!r} in realm {r!r}. Skipped.")
                    skipped += 1
                    continue
                raise

            lines.append(f"Removed {type} scope {sn!r} from client {client_id!r} in realm {r!r}.")
            removed += 1

    lines.append(f"Done. Removed: {removed}, Skipped: {skipped}.")
    realm_label = "all realms" if all_realms else (realm[0] if realm and len(realm) == 1 else (realms[0] if len(realms) == 1 else ""))
    print_box(lines, jira_ticket=rt.jira_ticket, realm_label=realm_label)


clients_app.add_typer(scopes_app, name="scopes")
