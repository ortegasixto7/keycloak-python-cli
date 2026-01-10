import typer

from kc.core.runtime import Runtime
from kc.commands.realms import realms_app
from kc.commands.roles import roles_app
from kc.commands.client_roles import client_roles_app
from kc.commands.users import users_app
from kc.commands.clients import clients_app
from kc.commands.client_scopes import client_scopes_app

app = typer.Typer(add_completion=False, help="Keycloak CLI")


def _init_runtime(
    ctx: typer.Context,
    config: str = typer.Option("", "--config", help="config file path (default: config.json next to the binary or current directory)"),
    realm: str = typer.Option("", "--realm", help="target realm"),
    log_file: str = typer.Option("kc.log", "--log-file", help="path to the log file"),
    jira: str = typer.Option("", "--jira", help="Jira ticket identifier for display in command output"),
):
    rt = Runtime(config_path=config, default_realm=realm, log_file=log_file, jira_ticket=jira)
    rt.start()
    ctx.obj = rt


@app.callback(invoke_without_command=True)
def main_callback(
    ctx: typer.Context,
    config: str = typer.Option("", "--config", help="config file path (default: config.json next to the binary or current directory)"),
    realm: str = typer.Option("", "--realm", help="target realm"),
    log_file: str = typer.Option("kc.log", "--log-file", help="path to the log file"),
    jira: str = typer.Option("", "--jira", help="Jira ticket identifier for display in command output"),
):
    _init_runtime(ctx, config=config, realm=realm, log_file=log_file, jira=jira)
    if ctx.invoked_subcommand is None:
        typer.echo("Keycloak CLI\n")
        typer.echo(ctx.get_help())


def main() -> None:
    from kc.core.runtime import CURRENT_RUNTIME

    try:
        app()
        rt = CURRENT_RUNTIME
        if rt is not None:
            rt.finish_ok()
    except Exception as e:
        rt = CURRENT_RUNTIME
        if rt is not None:
            rt.finish_error(e)
        raise


app.add_typer(realms_app, name="realms")
app.add_typer(roles_app, name="roles")
app.add_typer(client_roles_app, name="client-roles")
app.add_typer(users_app, name="users")
app.add_typer(clients_app, name="clients")
app.add_typer(client_scopes_app, name="client-scopes")
