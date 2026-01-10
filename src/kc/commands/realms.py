import typer

from kc.core.box import print_box
from kc.core.keycloak import kc_request

realms_app = typer.Typer(add_completion=False, help="Manage realms")


@realms_app.command("list")
def list_realms(ctx: typer.Context):
    rt = ctx.obj
    try:
        realms = kc_request("GET", "/admin/realms")
        lines = []
        for r in realms:
            name = r.get("realm")
            if name:
                lines.append(name)
        lines.append(f"Total: {len(realms)}")
        print_box(lines, jira_ticket=rt.jira_ticket, realm_label="all realms")
    except Exception as e:
        rt.finish_error(e)
        raise
