from __future__ import annotations

import os
import sys
from typing import Optional, TextIO


class Tee:
    def __init__(self, log_file: str):
        self.log_file = log_file or "kc.log"
        self._fh: Optional[TextIO] = None
        self._orig_stdout: Optional[TextIO] = None
        self._orig_stderr: Optional[TextIO] = None

    def install(self) -> None:
        self._fh = open(self.log_file, "a", encoding="utf-8")
        self._orig_stdout = sys.stdout
        self._orig_stderr = sys.stderr
        sys.stdout = _TeeWriter(self._orig_stdout, self._fh)
        sys.stderr = _TeeWriter(self._orig_stderr, self._fh)

    def out(self, s: str) -> None:
        sys.stdout.write(s)

    def err(self, s: str) -> None:
        sys.stderr.write(s)

    def close(self) -> None:
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
        na = self._a.write(s)
        self._b.write(s)
        return na

    def flush(self) -> None:
        self._a.flush()
        self._b.flush()

    def isatty(self) -> bool:
        return False
