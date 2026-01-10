from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from kc.core.audit import append_audit
from kc.core.config import load_config
from kc.core.logging import Tee


CURRENT_RUNTIME: "Runtime | None" = None


@dataclass
class Runtime:
    config_path: str
    default_realm: str
    log_file: str
    jira_ticket: str

    started_at: Optional[datetime] = None
    ended: bool = False
    tee: Optional[Tee] = None
    audit_details: str = ""

    def start(self) -> None:
        global CURRENT_RUNTIME
        load_config(self.config_path)
        self.tee = Tee(self.log_file)
        self.tee.install()
        self.started_at = datetime.now(timezone.utc)
        self.ended = False
        CURRENT_RUNTIME = self
        raw = self._build_raw_command()
        self.tee.err(f"[{self.started_at.isoformat()}] START: {raw}\n")

    def finish_ok(self) -> None:
        global CURRENT_RUNTIME
        if self.ended:
            return
        self.ended = True
        start = self.started_at or datetime.now(timezone.utc)
        end = datetime.now(timezone.utc)
        dur = end - start
        self.tee.err(f"[{end.isoformat()}] END: status=ok dur={dur}\n\n")
        append_audit(
            status="ok",
            command_path=self._build_command_path(),
            raw_command=self._build_raw_command(),
            jira=self.jira_ticket,
            target_realms=self._resolve_target_realms(),
            duration=str(dur),
            details=self.audit_details,
        )
        if self.tee is not None:
            self.tee.close()
        if CURRENT_RUNTIME is self:
            CURRENT_RUNTIME = None

    def finish_error(self, err: Exception) -> None:
        global CURRENT_RUNTIME
        if self.ended:
            return
        self.ended = True
        start = self.started_at or datetime.now(timezone.utc)
        end = datetime.now(timezone.utc)
        dur = end - start
        self.tee.err(f"[{end.isoformat()}] ERROR: {err}\n")
        self.tee.err(f"[{end.isoformat()}] END: status=error dur={dur}\n\n")
        append_audit(
            status="error",
            command_path=self._build_command_path(),
            raw_command=self._build_raw_command(),
            jira=self.jira_ticket,
            target_realms=self._resolve_target_realms(),
            duration=str(dur),
            details=self.audit_details,
        )
        if self.tee is not None:
            self.tee.close()
        if CURRENT_RUNTIME is self:
            CURRENT_RUNTIME = None

    def _build_raw_command(self) -> str:
        import sys

        if len(sys.argv) <= 1:
            return "./kc.exe"
        return "./kc.exe " + " ".join(sys.argv[1:])

    def _build_command_path(self) -> str:
        import sys

        if len(sys.argv) <= 1:
            return "kc"
        # mimic cobra CommandPath-like output by joining tokens excluding flags
        parts: list[str] = ["kc"]
        for a in sys.argv[1:]:
            if a.startswith("-"):
                continue
            parts.append(a)
        return " ".join(parts[:3]) if len(parts) > 3 else " ".join(parts)

    def _resolve_target_realms(self) -> str:
        from kc.core.config import GLOBAL

        if self.default_realm:
            return self.default_realm
        if GLOBAL.realm:
            return GLOBAL.realm
        return ""
