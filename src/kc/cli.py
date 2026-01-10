import shlex
import subprocess
import sys
from pathlib import Path

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
    cmd_file: str = typer.Option("", "--cmd-file", help="path to a text file with one CLI command per line"),
    continue_on_error: bool = typer.Option(False, "--continue-on-error", help="when using --cmd-file, continue processing even if a command fails"),
):
    _init_runtime(ctx, config=config, realm=realm, log_file=log_file, jira=jira)

    if cmd_file:
        _run_cmd_file(
            cmd_file=cmd_file,
            base_flags={"config": config, "realm": realm, "log_file": log_file, "jira": jira},
            continue_on_error=continue_on_error,
        )
        raise typer.Exit()

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


def _run_cmd_file(cmd_file: str, base_flags: dict, continue_on_error: bool) -> None:
    path = Path(cmd_file)
    if not path.exists():
        raise RuntimeError(f"cmd file not found: {cmd_file}")

    base_parts = []
    if base_flags.get("config"):
        base_parts.extend(["--config", base_flags["config"]])
    if base_flags.get("realm"):
        base_parts.extend(["--realm", base_flags["realm"]])
    if base_flags.get("log_file"):
        base_parts.extend(["--log-file", base_flags["log_file"]])
    if base_flags.get("jira"):
        base_parts.extend(["--jira", base_flags["jira"]])

    with path.open("r", encoding="utf-8") as f:
        lines = f.readlines()

    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        args = shlex.split(line)
        full_args = [sys.argv[0], *base_parts, *args]

        proc = subprocess.run(full_args, capture_output=True, text=True)
        sys.stdout.write(proc.stdout)
        sys.stderr.write(proc.stderr)

        if proc.returncode != 0 and not continue_on_error:
            raise typer.Exit(code=proc.returncode)


app.add_typer(realms_app, name="realms")
app.add_typer(roles_app, name="roles")
app.add_typer(client_roles_app, name="client-roles")
app.add_typer(users_app, name="users")
app.add_typer(clients_app, name="clients")
app.add_typer(client_scopes_app, name="client-scopes")
