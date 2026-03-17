# keycloak-cli

## Beschreibung
CLI zur Interaktion mit Keycloak.

## Verwendung
Installieren Sie das Projekt und führen Sie den Befehl `kc.exe` aus, um die allgemeine Hilfe anzuzeigen.

```bash
kc.exe --help
```

## Installation

Vom Root-Verzeichnis des Repositories:

```bash
python -m pip install -e .
```

### Eigenständige ausführbare Dateien erstellen (Windows)
Wenn Sie eine einzelne ausführbare Datei (z. B. `kc.exe`) benötigen, die keine Python-Installation erfordert, verwenden Sie PyInstaller unter Windows.

1. Installieren Sie Python 3.9+ unter Windows (von python.org oder via winget).
2. Klonen Sie das Repo und öffnen Sie ein Terminal (PowerShell/CMD) im Root-Verzeichnis des Repos.
3. Installieren Sie das Projekt im bearbeitbaren Modus:
   ```powershell
   pip install -e .
   ```
4. Installieren Sie PyInstaller:
   ```powershell
   pip install pyinstaller
   ```
5. Erstellen Sie die Hauptdatei:
   ```powershell
   pyinstaller --onefile --console src/kc/cli.py --name kc.exe
   ```
   Die ausführbare Datei wird unter `dist/kc.exe` erstellt.
6. (Optional) Erstellen Sie den festen Einstiegspunkt:
   ```powershell
   pyinstaller --onefile --console src/kc/roles_create_fixed.py --name kc.exe-roles-create-fixed.exe
   ```
   Die ausführbare Datei wird unter `dist/kc.exe-roles-create-fixed.exe` erstellt.
7. Testen:
   ```powershell
   cd dist
   .\kc.exe --help
   .\kc.exe --config ..\config.json realms list
   ```
Sie können `kc.exe` (und optional `kc.exe-roles-create-fixed.exe`) auf jeden Windows-Rechner ohne Python kopieren.

## Globale Flags
- `--config <Pfad>`
  Konfigurationsdatei (Standard: `config.json` neben der ausführbaren Datei (wenn paketiert) oder im aktuellen Verzeichnis).
- `--realm <Name>`
  Standard-Realm, der verwendet werden soll.
- `--jira <Ticket>`
  Jira-Ticket-ID, die nur zur Anzeige im Header der Befehlsausgabe verwendet wird.
- `--log-file <Pfad>`
  Pfad zur Log-Datei (Standard: `kc.log`).
- `--cmd-file <Pfad>`
  Befehle aus einer Textdatei ausführen (eine CLI-Zeile pro Zeile; Zeilen, die mit `#` beginnen, werden ignoriert).
- `--continue-on-error`
  Bei Verwendung mit `--cmd-file`: Fortfahren mit den restlichen Zeilen, auch wenn ein Befehl fehlschlägt (Standard: Stopp beim ersten Fehler).

### Batch-Ausführung aus einer Datei
Die CLI unterstützt das Ausführen mehrerer Befehle aus einer einzelnen Datei im **Klartext-**, **JSON-** oder **YAML-Format**.

#### Klartext-Format (`.txt`)
- Ein CLI-Befehl pro Zeile.
- Zeilen, die mit `#` beginnen, werden ignoriert.
- Beispiel `commands.txt`:
  ```text
  # Realms auflisten
  realms list
  roles create --realm master --name beispiel_rolle --description "Beispielrolle"
  ```

#### JSON-Format (`.json`)
- Kann eine einfache Liste von Zeichenfolgen oder ein Objekt mit dem Schlüssel `commands` sein.
- Beispiel `commands.json`:
  ```json
  {
    "commands": [
      "realms list",
      "users create --realm master --username jdoe --password Str0ng! --email jdoe@acme.com",
      { "cmd": "roles create --realm master --name json_rolle --description 'Erstellt aus JSON'" }
    ]
  }
  ```

#### YAML-Format (`.yaml` / `.yml`)
- Kann eine einfache Liste von Zeichenfolgen oder ein Objekt mit dem Schlüssel `commands` sein.
- Beispiel `commands.yaml`:
  ```yaml
  commands:
    - realms list
    - "users create --realm master --username msmith --password Str0ng! --email msmith@acme.com"
    - cmd: "roles create --realm master --name yaml_rolle --description 'Erstellt aus YAML'"
  ```

#### Ausführen:
```bash
kc.exe --config config.json --cmd-file commands.json
# oder fortfahren, selbst wenn ein Befehl fehlschlägt
kc.exe --config config.json --cmd-file commands.yaml --continue-on-error
```
Globale Flags wie `--realm`, `--log-file`, `--jira` gelten für jeden Befehl in der Datei.

## Befehle und Beispiele

> Hinweis: Alle Befehle akzeptieren auch das globale Flag `--jira <Ticket>`. Dies beeinflusst nur den visuellen Header der Ausgabe; es ändert nicht das Verhalten des Befehls.

### Realms
- **Realms auflisten**
  ```bash
  kc.exe realms list --jira <TICKET>
  ```

### Rollen (Roles)
- **Eine Rolle in einem bestimmten Realm erstellen**
  ```bash
  kc.exe roles create --name <ROLLE> --description "<BESCHREIBUNG>" --realm <REALM> --jira <TICKET>
  ```

- **Eine Rolle im Standard-Realm erstellen**
  ```bash
  kc.exe roles create --name <ROLLE> --description "<BESCHREIBUNG>" --jira <TICKET>
  ```

- **Eine Rolle in allen Realms erstellen**
  ```bash
  kc.exe roles create --name <ROLLE> --description "<BESCHREIBUNG>" --jira <TICKET> --all-realms
  ```

 - **Mehrere Rollen mit einer einzelnen Beschreibung erstellen (für alle angewendet)**
   ```bash
   kc.exe roles create \
     --realm myrealm \
     --name admin \
     --name operator \
     --name auditor \
     --description "Basis-Systemrollen" \
     --jira <TICKET>
   ```

 - **Mehrere Rollen mit individuellen Beschreibungen erstellen (geordnet)**
   ```bash
   kc.exe roles create \
     --realm myrealm \
     --name admin --description "Vollzugriff" \
     --name operator --description "Eingeschränkte Operationen" \
     --name auditor --description "Nur Lesezugriff" \
     --jira <TICKET>
   ```

 - **Mehrere Rollen ohne Beschreibung erstellen**
   ```bash
   kc.exe roles create --realm myrealm --name viewer --name reporter --jira <TICKET>
   ```

 - **Mehrere Rollen in allen Realms erstellen**
   ```bash
   kc.exe roles create --all-realms --name viewer --name auditor --description "Globales Lesen" --jira <TICKET>
   ```

- **Rollen interaktiv erstellen (Realm, Namen, Beschreibung werden abgefragt)**
  ```bash
  kc.exe roles create -i --jira <TICKET>
  ```

- **Rollen interaktiv erstellen, aber einen bestimmten Realm erzwingen**
  ```bash
  kc.exe roles create -i --realm myrealm --jira <TICKET>
  # Der interaktive Modus fragt nicht erneut nach dem Realm, sondern nur nach Rollennamen und Beschreibung.
  ```

#### Spezifische Flags für `roles create`
- `--name <ROLLE>` Wiederholbar. Sie müssen mindestens einen `--name` angeben (erforderlich).
- `--description <TEXT>` Wiederholbar. Optional. Regeln:
  - Kein `--description` → Rollen werden ohne Beschreibung erstellt.
  - Eine einzelne `--description` → wird auf alle `--name` angewendet.
  - Mehrere `--description` → muss genau eine pro `--name` sein, in derselben Reihenfolge.
- `--all-realms` Erstellt die Rolle in allen Realms.
- `--realm <REALM>` Ziel-Realm (hat Vorrang vor dem globalen Realm).
- `-i, --interactive` Parameter interaktiv abfragen (Realm/All-Realms, Namen, Beschreibung). Bereits angegebene Flags werden berücksichtigt und nicht erneut abgefragt.

#### Auflösung des Ziel-Realms
Prioritätsreihenfolge beim Ausführen von `roles create` (von höchster zu niedrigster):
1. `--realm` Flag beim `roles create` Befehl.
2. Globales `--realm` Flag beim Hauptbefehl.
3. `realm` Wert in `config.json`.

### Festgelegte ausführbare Datei für `roles create`

Zusätzlich zum Hauptbefehl `kc.exe` gibt es einen kleinen dedizierten Einstiegspunkt, der immer einen vorkonfigurierten `roles create`-Befehl ausführt:

- **Verwendung**
  ```bash
  kc.exe-roles-create-fixed
  ```

Der genaue Realm, die Rollennamen und andere Argumente, die von `kc.exe-roles-create-fixed` ausgeführt werden, sind im Code in `src/kc/roles_create_fixed.py` definiert. Um das Verhalten zu ändern, bearbeiten Sie diese Datei.

#### Rollen bearbeiten: `roles update`
- **Beschreibung mehrerer Rollen in einem Realm aktualisieren**
  ```bash
  kc.exe roles update --realm myrealm \
    --name admin --name operator \
    --description "Neue Beschreibung" \
    --jira <TICKET>
  ```

- **Rollen nach Reihenfolge in mehreren Realms umbenennen**
  ```bash
  kc.exe roles update \
    --realm myrealm --realm sandbox \
    --name viewer --new-name read_only \
    --name auditor --new-name audit_read \
    --jira <TICKET>
  ```

Flags für `roles update`:
- `--name <ROLLE>` Wiederholbar. Erforderlich.
- `--description <TEXT>` Wiederholbar. Optional; 0, 1 oder N (gepaart nach Reihenfolge mit `--name`).
- `--new-name <NEU>` Wiederholbar. Optional; 0, 1 oder N (gepaart nach Reihenfolge mit `--name`).
- `--realm <REALM>` Ziel-Realm. Wenn nicht angegeben, wird der Standard-Realm verwendet.
- `--all-realms` Gilt für alle Realms.
- `--ignore-missing` Wenn eine Rolle im Realm nicht existiert, überspringen statt fehlschlagen.

#### Rollen löschen: `roles delete`
- **Rollen in allen Realms löschen (nicht existierende überspringen)**
  ```bash
  kc.exe roles delete --all-realms \
    --name temp_role --name deprecated_role \
    --ignore-missing \
    --jira <TICKET>
  ```

Flags für `roles delete`:
- `--name <ROLLE>` Wiederholbar. Erforderlich.
- `--realm <REALM>` Wiederholbar. Ziel-Realms. Wenn nicht angegeben, wird der Standard-Realm verwendet.
- `--all-realms` In allen Realms löschen.
- `--ignore-missing` Nicht existierende Rollen überspringen statt fehlschlagen.

### Client-Rollen
- **Eine Client-Rolle in einem bestimmten Client und Realm erstellen**
  ```bash
  kc.exe client-roles create \
    --client-id my-app \
    --name app-admin \
    --description "Admin-Rolle für my-app" \
    --realm myrealm \
    --jira <TICKET>
  ```

- **Mehrere Client-Rollen mit einer einzelnen Beschreibung erstellen (für alle angewendet)**
  ```bash
  kc.exe client-roles create \
    --client-id my-app \
    --realm myrealm \
    --name app-admin \
    --name app-user \
    --description "Anwendungsrollen" \
    --jira <TICKET>
   ```

- **Mehrere Client-Rollen in allen Realms erstellen**
  ```bash
  kc.exe client-roles create \
    --client-id my-app \
    --all-realms \
    --name app-admin \
    --name app-user \
    --description "Globale App-Rollen" \
    --jira <TICKET>
  ```

#### Spezifische Flags für `client-roles create`
- `--client-id <CLIENT_ID>` Ziel-Client-ID. Erforderlich.
- `--name <ROLLE>` Wiederholbar. Sie müssen mindestens einen `--name` angeben (erforderlich).
- `--description <TEXT>` Wiederholbar. Optional. Regeln (gleiches Muster wie bei `roles create`):
  - Kein `--description` → Rollen werden ohne Beschreibung erstellt.
  - Eine einzelne `--description` → wird auf alle `--name` angewendet.
  - Mehrere `--description` → muss genau eine pro `--name` sein, in derselben Reihenfolge.
- `--all-realms` Erstellt die Client-Rolle(n) in allen Realms.
- `--realm <REALM>` Ziel-Realm (hat Vorrang vor dem globalen Realm).

### Benutzer (Users)
- **Mehrere Benutzer in einem Realm mit einem einzelnen Passwort erstellen**
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

- **Benutzer mit individuellen Passworten und Realm-Rollen erstellen**
  ```bash
  kc.exe users create \
    --realm myrealm \
    --username a --password Aa!1 --email a@acme.com \
    --username b --password Bb!2 --email b@acme.com \
    --realm-role viewer --realm-role auditor \
    --jira <TICKET>
  ```

- **Benutzer in allen Realms erstellen, ohne E-Mail (emailVerified=false)**
  ```bash
  kc.exe users create \
    --all-realms \
    --username svc-1 --username svc-2 \
    --enabled=false \
    --jira <TICKET>
  ```

- **Benutzer in mehreren spezifischen Realms erstellen**
  ```bash
  kc.exe users create \
    --realm myrealm --realm sandbox \
    --username test1 --password Test!123 \
    --jira <TICKET>
  ```

#### Spezifische Flags für `users create`
- `--username <BENUTZER>` Wiederholbar. Sie müssen mindestens einen `--username` angeben (erforderlich).
- `--email <EMAIL>` Wiederholbar. Optional; 0, 1 oder N (gepaart nach Reihenfolge mit `--username`). Wenn eine E-Mail angegeben wird, ist `emailVerified` auf `true` gesetzt, andernfalls auf `false`.
- `--first-name <VORNAME>` Wiederholbar. Optional; 0, 1 oder N.
- `--last-name <NACHNAME>` Wiederholbar. Optional; 0, 1 oder N.
- `--password <PW>` Wiederholbar. Optional; 0, 1 oder N.
- `--enabled` Boolean. Standard `true`. Kann mit `--enabled=false` deaktiviert werden.
- `--realm <REALM>` Wiederholbar. Ziel-Realms. Wenn weggelassen und `--all-realms` nicht verwendet wird, wird der Standard-Realm verwendet (globales Flag oder `config.json`).
- `--all-realms` In allen Realms erstellen.
- `--realm-role <ROLLE>` Wiederholbar. Bestehende Realm-Rollen dem erstellten Benutzer zuweisen.
- `--client-role <ROLLE>` Wiederholbar. Bestehende Client-Rollen (vom Client angegeben durch `--client-id`) dem erstellten Benutzer zuweisen.
- `--client-id <CLIENT_ID>` Client, dessen Rollen bei Verwendung von `--client-role` zugewiesen werden. Erforderlich, wenn `--client-role` angegeben wird.

#### Benutzer bearbeiten: `users update`
- **Passwort aktualisieren und mehrere Benutzer aktivieren**
  ```bash
  kc.exe users update \
    --realm myrealm \
    --username jdoe --username mjane \
    --password N3wP@ss! \
    --enabled=true \
    --jira <TICKET>
  ```

- **Felder pro Benutzer aktualisieren (geordnet)**
  ```bash
  kc.exe users update \
    --realm myrealm \
    --username a --email a@acme.com --first-name Ann --last-name A \
    --username b --email b@acme.com --first-name Ben --last-name B \
    --jira <TICKET>
  ```

Flags für `users update`:
- `--username <BENUTZER>` Wiederholbar. Erforderlich.
- `--email <EMAIL>` Wiederholbar. 0, 1 oder N (gepaart nach Reihenfolge). Wenn angegeben, `emailVerified=true`.
- `--first-name <VORNAME>` Wiederholbar. 0, 1 oder N.
- `--last-name <NACHNAME>` Wiederholbar. 0, 1 oder N.
- `--password <PW>` Wiederholbar. 0, 1 oder N.
- `--enabled` Boolean. Wenn das Flag enthalten ist, wird der Wert auf die Zielbenutzer angewendet.
- `--realm <REALM>` Wiederholbar. Ziel-Realms.
- `--all-realms` Gilt für alle Realms.
- `--ignore-missing` Nicht existierende Benutzer überspringen statt fehlschlagen.

#### Benutzer löschen: `users delete`
- **Benutzer in mehreren Realms löschen, nicht existierende ignorieren**
  ```bash
  kc.exe users delete \
    --realm myrealm --realm sandbox \
    --username olduser1 --username olduser2 \
    --ignore-missing \
    --jira <TICKET>
  ```

Flags für `users delete`:
- `--username <BENUTZER>` Wiederholbar. Erforderlich.
- `--realm <REALM>` Wiederholbar. Ziel-Realms.
- `--all-realms` In allen Realms löschen.
- `--ignore-missing` Nicht existierende Benutzer überspringen statt fehlschlagen.

### Clients
- **Client(s) erstellen**
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

- **Client(s) aktualisieren**
  ```bash
  kc.exe clients update \
    --realm myrealm \
    --client-id app-frontend \
    --name "App Frontend v2" \
    --root-url https://app.example.com \
    --base-url / \
    --jira <TICKET>
  ```

- **Client(s) löschen**
  ```bash
  kc.exe clients delete --realm myrealm --client-id app-frontend --ignore-missing --jira <TICKET>
  ```

- **Clients auflisten**
  ```bash
  kc.exe clients list --realm myrealm --jira <TICKET>
  ```

Hauptflags für `clients`:
- `--client-id <ID>` Wiederholbar bei create/update/delete. Erforderlich für create/update/delete.
- `--name`, `--public`, `--enabled`, `--protocol`, `--root-url`, `--base-url`.
- `--redirect-uri`, `--web-origin` (Liste, die auf alle ausgewählten angewendet wird, wenn in update/create verwendet).
- `--standard-flow`, `--direct-access`, `--implicit-flow`, `--service-accounts` (bool 0/1/N).
- `--new-client-id` zum Umbenennen in `update` (0/1/N).
- `--realm` (0/1/N) oder `--all-realms`.
- `--ignore-missing` in `update/delete`, um nicht existierende zu überspringen.

Hinweis:
- Das explizite Setzen von `--secret` wird nicht unterstützt; der Befehl gibt eine Warnung aus und ignoriert es.

#### Scopes einem Client zuweisen
- **Scopes zuweisen**
  ```bash
  kc.exe clients scopes assign \
    --realm myrealm \
    --client-id app-frontend \
    --type default \
    --scope profile --scope email \
    --jira <TICKET>
  ```

- **Scopes entfernen**
  ```bash
  kc.exe clients scopes remove \
    --realm myrealm \
    --client-id app-frontend \
    --type optional \
    --scope address --ignore-missing \
    --jira <TICKET>
  ```

Flags:
- `--client-id <ID>` Erforderlich.
- `--scope <NAME>` Wiederholbar. Erforderlich.
- `--type default|optional` (Standard: `default`).
- `--realm` erforderlich (oder global), oder `--all-realms` bei assign/remove, wenn auf mehrere Realms angewendet werden soll.
- `--ignore-missing` beim Entfernen, um nicht zugewiesene Scopes zu überspringen.

### Client Scopes
- **Client Scopes erstellen**
  ```bash
  kc.exe client-scopes create \
    --realm myrealm \
    --name profile --description "Standardprofil" --protocol openid-connect \
    --jira <TICKET>
  ```

- **Client Scopes aktualisieren**
  ```bash
  kc.exe client-scopes update \
    --realm myrealm \
    --name profile --new-name profile_v2 --description "Aktualisiert" \
    --jira <TICKET>
  ```

- **Client Scopes löschen**
  ```bash
  kc.exe client-scopes delete --realm myrealm --name profile --ignore-missing --jira <TICKET>
  ```

- **Client Scopes auflisten**
  ```bash
  kc.exe client-scopes list --realm myrealm --jira <TICKET>
  ```

Flags für `client-scopes`:
- `--name <NAME>` Wiederholbar. Erforderlich bei create/update/delete.
- `--description`, `--protocol` (0/1/N). Standard-`protocol`: `openid-connect`.
- `--new-name` bei update (0/1/N).
- `--realm` oder `--all-realms`.
- `--ignore-missing` bei update/delete, um nicht existierende zu überspringen.

## Protokollierung (Logging)
- Die gesamte Standard- und Fehlerausgabe wird in `kc.log` dupliziert (im Ausführungsverzeichnis oder gemäß `--log-file`).
- Jeder Befehl druckt `START`/`END` Zeitstempel und Fehler mit ihrer Dauer.
