# keycloak-cli

## Description
CLI to interact with Keycloak.

## Usage
Install the project and run the `kc.exe` command to see the general help.

```bash
kc.exe --help
```

## Install

From the repo root:

```bash
python -m pip install -e .
```

### Build standalone executables (Windows)
If you need a single executable (e.g., `kc.exe`) that does not require Python to be installed, use PyInstaller on Windows.

1. Install Python 3.9+ on Windows (from python.org or via winget).
2. Clone the repo and open a terminal (PowerShell/CMD) in the repo root.
3. Install the project in editable mode:
   ```powershell
   pip install -e .
   ```
4. Install PyInstaller:
   ```powershell
   python -m pip install pyinstaller
   ```
5. Build the main executable:
   ```powershell
   python -m PyInstaller --onefile --console src/kc/cli.py --name kc.exe
   ```
   The executable will be created at `dist/kc.exe`.
6. (Optional) Build the fixed entrypoint:
   ```powershell
   pyinstaller --onefile --console src/kc/roles_create_fixed.py --name kc.exe-roles-create-fixed.exe
   ```
   The executable will be created at `dist/kc.exe-roles-create-fixed.exe`.
7. Test:
   ```powershell
   cd dist
   .\kc.exe --help
   .\kc.exe --config ..\config.json realms list
   ```
You can copy `kc.exe` (and optionally `kc.exe-roles-create-fixed.exe`) to any Windows machine without Python.

## Global flags
- `--config <path>`
  Configuration file (default: `config.json` next to the executable (when packaged) or in the current directory).
- `--realm <name>`
  Default realm to use.
- `--jira <ticket>`
  Jira ticket identifier used only for display in the boxed command output header.
- `--log-file <path>`
  Path to the log file (default: `kc.log`).
- `--cmd-file <path>`
  Execute commands from a text file (one CLI line per line; lines starting with `#` are ignored).
- `--continue-on-error`
  When used with `--cmd-file`, continue processing remaining lines even if a command fails (default: stop on first error).

### Batch execution from file
The CLI supports executing multiple commands from a single file in **Plain Text**, **JSON**, or **YAML** formats.

#### Plain Text format (`.txt`)
- One CLI command per line.
- Lines starting with `#` are ignored.
- Example `commands.txt`:
  ```text
  # List realms
  realms list
  roles create --realm master --name example_role --description "Example role"
  ```

#### JSON format (`.json`)
The CLI supports two JSON structures:

**Option A: Simple List**
```json
[
  "realms list",
  "roles create --name role_one",
  { "cmd": "users create --username juan" }
]
```

**Option B: Object with `commands` key**
```json
{
  "commands": [
    "realms list",
    "roles create --name role_two",
    { "cmd": "roles create --name expert_role" }
  ]
}
```

#### YAML format (`.yaml` / `.yml`)
Similarly, YAML supports two structures:

**Option A: Simple List**
```yaml
- realms list
- "roles create --name role_yaml"
- cmd: "users create --username pedro"
```

**Option B: Object with `commands` key**
```yaml
commands:
  - realms list
  - "users create --realm master --username msmith"
  - cmd: "roles create --name yaml_role"
```


#### Run:
```bash
kc.exe --config config.json --cmd-file commands.json
# or continue even if a command fails
kc.exe --config config.json --cmd-file commands.yaml --continue-on-error
```
Global flags like `--realm`, `--log-file`, `--jira` apply to every command in the file.

## Commands and examples

> Note: all commands also accept the global `--jira <ticket>` flag. It only affects the visual header of the boxed output; it does not change the behavior of the command.

### Realms
- **List realms**
  ```bash
  kc.exe realms list --jira <TICKET>
  ```

### Roles
- **Create a role in a specific realm**
  ```bash
  kc.exe roles create --name <ROLE> --description "<DESCRIPTION>" --realm <REALM> --jira <TICKET>
  ```

- **Create a role using the default realm**
  ```bash
  kc.exe roles create --name <ROLE> --description "<DESCRIPTION>" --jira <TICKET>
  ```

- **Create a role in all realms**
  ```bash
  kc.exe roles create --name <ROLE> --description "<DESCRIPTION>" --jira <TICKET> --all-realms
  ```

 - **Create multiple roles with a single description (applied to all)**
   ```bash
   kc.exe roles create \
     --realm myrealm \
     --name admin \
     --name operator \
     --name auditor \
     --description "Base system roles" \
     --jira <TICKET>
   ```

 - **Create multiple roles with per-role descriptions (ordered)**
   ```bash
   kc.exe roles create \
     --realm myrealm \
     --name admin --description "Full access" \
     --name operator --description "Limited operations" \
     --name auditor --description "Read-only" \
     --jira <TICKET>
   ```

 - **Create multiple roles without description**
   ```bash
   kc.exe roles create --realm myrealm --name viewer --name reporter --jira <TICKET>
   ```

 - **Create multiple roles in all realms**
   ```bash
   kc.exe roles create --all-realms --name viewer --name auditor --description "Global read" --jira <TICKET>
   ```

- **Create roles interactively (realm, names, description prompted)**
  ```bash
  kc.exe roles create -i --jira <TICKET>
  ```

- **Create roles interactively but forcing a specific realm from CLI**
  ```bash
  kc.exe roles create -i --realm myrealm --jira <TICKET>
  # Interactive mode will not re-ask for the realm, only for role names and description.
  ```

#### Flags specific to `roles create`
- `--name <ROLE>` Repeatable. You must provide at least one `--name` (required).
- `--description <TEXT>` Repeatable. Optional. Rules:
  - No `--description` → roles are created without a description.
  - A single `--description` → applied to all `--name`.
  - Multiple `--description` → must be exactly one per `--name`, in the same order.
- `--all-realms` Create the role in all realms
- `--realm <REALM>` Target realm (takes precedence over the global one)
- `-i, --interactive` Prompt for role parameters interactively (realm/all-realms, names, description). Flags already provided on the command line are respected and not re-asked.

#### Target realm resolution
Priority order when you run `roles create` (from highest to lowest):
1. `--realm` flag on the `roles create` command.
2. Global `--realm` flag on the root command.
3. `realm` value in `config.json`.

### Fixed executable for `roles create`

In addition to the main `kc.exe` command, there is a small dedicated entrypoint that always runs a pre-configured `roles create` command:

- **Usage**
  ```bash
  kc.exe-roles-create-fixed
  ```

The exact realm, role names and other arguments executed by `kc.exe-roles-create-fixed` are defined in code inside `src/kc/roles_create_fixed.py`. To change its behavior, edit that file.

#### Edit roles: `roles update`
- **Update the description of multiple roles in a realm**
  ```bash
  kc.exe roles update --realm myrealm \
    --name admin --name operator \
    --description "New description" \
    --jira <TICKET>
  ```

- **Rename roles by order in multiple realms**
  ```bash
  kc.exe roles update \
    --realm myrealm --realm sandbox \
    --name viewer --new-name read_only \
    --name auditor --new-name audit_read \
    --jira <TICKET>
  ```

Flags for `roles update`:
- `--name <ROLE>` Repeatable. Required.
- `--description <TEXT>` Repeatable. Optional; 0, 1 or N (paired by order with `--name`).
- `--new-name <NEW>` Repeatable. Optional; 0, 1 or N (paired by order with `--name`).
- `--realm <REALM>` Target realm. If not provided, uses the default.
- `--all-realms` Applies to all realms.
- `--ignore-missing` If a role does not exist in the realm, skip instead of failing.

#### Delete roles: `roles delete`
- **Delete roles in all realms (skipping non-existent ones)**
  ```bash
  kc.exe roles delete --all-realms \
    --name temp_role --name deprecated_role \
    --ignore-missing \
    --jira <TICKET>
  ```

Flags for `roles delete`:
- `--name <ROLE>` Repeatable. Required.
- `--realm <REALM>` Repeatable. Target realms. If not provided, uses the default.
- `--all-realms` Delete in all realms.
- `--ignore-missing` Skip non-existent roles instead of failing.

### Client Roles
- **Create a client role in a specific client and realm**
  ```bash
  kc.exe client-roles create \
    --client-id my-app \
    --name app-admin \
    --description "Admin role for my-app" \
    --realm myrealm \
    --jira <TICKET>
  ```

- **Create multiple client roles with a single description (applied to all)**
  ```bash
  kc.exe client-roles create \
    --client-id my-app \
    --realm myrealm \
    --name app-admin \
    --name app-user \
    --description "Application roles" \
    --jira <TICKET>
  ```

- **Create multiple client roles in all realms**
  ```bash
  kc.exe client-roles create \
    --client-id my-app \
    --all-realms \
    --name app-admin \
    --name app-user \
    --description "Global app roles" \
    --jira <TICKET>
  ```

#### Flags specific to `client-roles create`
- `--client-id <CLIENT_ID>` Target client-id. Required.
- `--name <ROLE>` Repeatable. You must provide at least one `--name` (required).
- `--description <TEXT>` Repeatable. Optional. Rules (same pattern as `roles create`):
  - No `--description` → roles are created without a description.
  - A single `--description` → applied to all `--name`.
  - Multiple `--description` → must be exactly one per `--name`, in the same order.
- `--all-realms` Create the client role(s) in all realms.
- `--realm <REALM>` Target realm (takes precedence over the global one).

### Users
- **Create multiple users in a realm with a single password**
  ```bash
  kc.exe users create \
    --realm myrealm \
    --username jdoe --username mjane \
    --password Str0ng! \
    --first-name John --first-name Mary \
    --last-name Doe --last-name Jane \
    --email john@acme.com --email mary@acme.com \
    --jira <TICKET>
  ```

- **Create users with per-user passwords and realm roles**
  ```bash
  kc.exe users create \
    --realm myrealm \
    --username a --password Aa!1 --email a@acme.com \
    --username b --password Bb!2 --email b@acme.com \
    --realm-role viewer --realm-role auditor \
    --jira <TICKET>
  ```

- **Create users in all realms, without email (emailVerified=false)**
  ```bash
  kc.exe users create \
    --all-realms \
    --username svc-1 --username svc-2 \
    --enabled=false \
    --jira <TICKET>
  ```

- **Create users in multiple specific realms**
  ```bash
  kc.exe users create \
    --realm myrealm --realm sandbox \
    --username test1 --password Test!123 \
    --jira <TICKET>
  ```

#### Flags specific to `users create`
- `--username <USER>` Repeatable. You must provide at least one `--username` (required).
- `--email <EMAIL>` Repeatable. Optional; 0, 1 or N (paired by order with `--username`). If email is provided, `emailVerified` will be `true`, otherwise `false`.
- `--first-name <FIRST>` Repeatable. Optional; 0, 1 or N.
- `--last-name <LAST>` Repeatable. Optional; 0, 1 or N.
- `--password <PWD>` Repeatable. Optional; 0, 1 or N.
- `--enabled` Boolean. Default `true`. You can disable with `--enabled=false`.
- `--realm <REALM>` Repeatable. Target realms. If omitted and you don't use `--all-realms`, the default realm is used (global flag or `config.json`).
- `--all-realms` Create in all realms.
- `--realm-role <ROLE>` Repeatable. Assign existing realm roles to the created user.
 - `--client-role <ROLE>` Repeatable. Assign existing client roles (from the client given by `--client-id`) to the created user.
 - `--client-id <CLIENT_ID>` Client whose roles will be assigned when using `--client-role`. Required if `--client-role` is provided.

#### Edit users: `users update`
- **Update password and enable multiple users**
  ```bash
  kc.exe users update \
    --realm myrealm \
    --username jdoe --username mjane \
    --password N3wP@ss! \
    --enabled=true \
    --jira <TICKET>
  ```

- **Update fields per user (ordered)**
  ```bash
  kc.exe users update \
    --realm myrealm \
    --username a --email a@acme.com --first-name Ann --last-name A \
    --username b --email b@acme.com --first-name Ben --last-name B \
    --jira <TICKET>
  ```

Flags for `users update`:
- `--username <USER>` Repeatable. Required.
- `--email <EMAIL>` Repeatable. 0, 1 or N (paired by order). If specified, `emailVerified=true`.
- `--first-name <FIRST>` Repeatable. 0, 1 or N.
- `--last-name <LAST>` Repeatable. 0, 1 or N.
- `--password <PWD>` Repeatable. 0, 1 or N.
- `--enabled` Boolean. If the flag is included, apply the value to the target users.
- `--realm <REALM>` Repeatable. Target realms.
- `--all-realms` Applies to all realms.
- `--ignore-missing` Skip non-existent users instead of failing.

#### Delete users: `users delete`
- **Delete users in multiple realms, ignoring non-existent ones**
  ```bash
  kc.exe users delete \
    --realm myrealm --realm sandbox \
    --username olduser1 --username olduser2 \
    --ignore-missing \
    --jira <TICKET>
  ```

Flags for `users delete`:
- `--username <USER>` Repeatable. Required.
- `--realm <REALM>` Repeatable. Target realms.
- `--all-realms` Delete in all realms.
- `--ignore-missing` Skip non-existent users instead of failing.

### Clients
- **Create client(s)**
  ```bash
  kc.exe clients create \
    --realm myrealm \
    --client-id app-frontend \
    --name "App Frontend" \
    --public=true \
    --redirect-uri https://app.example.com/callback \
    --web-origin https://app.example.com \
    --jira <TICKET>
  ```

- **Update client(s)**
  ```bash
  kc.exe clients update \
    --realm myrealm \
    --client-id app-frontend \
    --name "App Frontend v2" \
    --root-url https://app.example.com \
    --base-url / \
    --jira <TICKET>
  ```

- **Delete client(s)**
  ```bash
  kc.exe clients delete --realm myrealm --client-id app-frontend --ignore-missing --jira <TICKET>
  ```

- **List clients**
  ```bash
  kc.exe clients list --realm myrealm --jira <TICKET>
  ```

Flags for `clients` (main):
- `--client-id <ID>` Repeatable in create/update/delete. Required for create/update/delete.
- `--name`, `--public`, `--enabled`, `--protocol`, `--root-url`, `--base-url`.
- `--redirect-uri`, `--web-origin` (list applied to all selected when used in update/create).
- `--standard-flow`, `--direct-access`, `--implicit-flow`, `--service-accounts` (bool 0/1/N).
- `--new-client-id` to rename in `update` (0/1/N).
- `--realm` (0/1/N) or `--all-realms`.
- `--ignore-missing` in `update/delete` to skip non-existent ones.

Note:
- Explicit setting of `--secret` is not supported; the command will emit a warning and omit it.

#### Assign scopes to a client
- **Assign scopes**
  ```bash
  kc.exe clients scopes assign \
    --realm myrealm \
    --client-id app-frontend \
    --type default \
    --scope profile --scope email \
    --jira <TICKET>
  ```

- **Remove scopes**
  ```bash
  kc.exe clients scopes remove \
    --realm myrealm \
    --client-id app-frontend \
    --type optional \
    --scope address --ignore-missing \
    --jira <TICKET>
  ```

Flags:
- `--client-id <ID>` Required.
- `--scope <NAME>` Repeatable. Required.
- `--type default|optional` (default: `default`).
- `--realm` required (or global), or `--all-realms` in assign/remove if you want to apply to multiple realms.
- `--ignore-missing` in remove to skip unassigned scopes.

### Client Scopes
- **Create client scopes**
  ```bash
  kc.exe client-scopes create \
    --realm myrealm \
    --name profile --description "Standard profile" --protocol openid-connect \
    --jira <TICKET>
  ```

- **Update client scopes**
  ```bash
  kc.exe client-scopes update \
    --realm myrealm \
    --name profile --new-name profile_v2 --description "Updated" \
    --jira <TICKET>
  ```

- **Delete client scopes**
  ```bash
  kc.exe client-scopes delete --realm myrealm --name profile --ignore-missing --jira <TICKET>
  ```

- **List client scopes**
  ```bash
  kc.exe client-scopes list --realm myrealm --jira <TICKET>
  ```

Flags for `client-scopes`:
- `--name <NAME>` Repeatable. Required in create/update/delete.
- `--description`, `--protocol` (0/1/N). Default `protocol`: `openid-connect`.
- `--new-name` in update (0/1/N).
- `--realm` or `--all-realms`.
- `--ignore-missing` in update/delete to skip non-existent ones.

## Logging
- All standard output and error are duplicated to `kc.log` (in the execution directory or as per `--log-file`).
- Each command prints `START`/`END` timestamps and errors with their duration.