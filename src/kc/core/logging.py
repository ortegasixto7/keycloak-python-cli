from __future__ import annotations

import os
import sys
from typing import Optional, TextIO


def _is_frozen() -> bool:
    return getattr(sys, "frozen", False)


class Tee:
    def __init__(self, log_file: str):
        self.log_file = log_file or "kc.log"
        self._fh: Optional[TextIO] = None
        self._orig_stdout: Optional[TextIO] = None
        self._orig_stderr: Optional[TextIO] = None

    def install(self) -> None:
        self._fh = open(self.log_file, "a", encoding="utf-8")
        if _is_frozen():
            # Do not replace stdout/stderr when frozen (PyInstaller exe), so console
            # output is visible. Log file is still written via err()/out().
            return
        self._orig_stdout = sys.stdout
        self._orig_stderr = sys.stderr
        sys.stdout = _TeeWriter(self._orig_stdout, self._fh)
        sys.stderr = _TeeWriter(self._orig_stderr, self._fh)

    def out(self, s: str) -> None:
        if _is_frozen() and self._fh:
            self._fh.write(s)
            self._fh.flush()
        else:
            sys.stdout.write(s)

    def err(self, s: str) -> None:
        if _is_frozen() and self._fh:
            self._fh.write(s)
            self._fh.flush()
        else:
            sys.stderr.write(s)

    def close(self) -> None:
        if not _is_frozen():
            try:
                sys.stdout.flush()
                sys.stderr.flush()
            except Exception:
                pass
            if self._orig_stdout is not None:
                sys.stdout = self._orig_stdout
            if self._orig_stderr is not None:
                sys.stderr = self._orig_stderr
        if self._fh is not None:
            try:
                self._fh.close()
            finally:
                self._fh = None


class _TeeWriter:
    def __init__(self, a: TextIO, b: TextIO):
        self._a = a
        self._b = b

    def write(self, s: str) -> int:
        try:
            na = self._a.write(s)
        except UnicodeEncodeError:
            enc = getattr(self._a, "encoding", None) or "cp1252"
            s_safe = s.encode(enc, errors="replace").decode(enc, errors="replace")
            na = self._a.write(s_safe)
        self._b.write(s)
        return na

    def flush(self) -> None:
        self._a.flush()
        self._b.flush()

    def isatty(self) -> bool:
        return False
