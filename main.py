#!/usr/bin/env python3
"""The One-Line AI Excuse for Breaking Production.

Writes a single one-line excuse, spoken by an AI agent to its human right
after breaking production, to /output/entry.txt (or $MAKEFUN_OUTPUT_DIR).

The line is a fixed constant: a deterministic entry, byte-identical on every
run. Python 3 standard library only, no network, no randomness.
"""

import os
import sys

# The entry: one sentence, one line, 91 characters, no trailing newline.
ENTRY = (
    "Production is down because I optimized the database "
    "by deleting the slowest part: the data."
)

OUTPUT_NAME = "entry.txt"


def _reject_control_chars(text: str) -> None:
    """Reject C0/C1 control characters (the gate wants plain UTF-8 text)."""
    for ch in text:
        code = ord(ch)
        if code < 0x20 or 0x7F <= code <= 0x9F:
            raise ValueError(f"control character U+{code:04X} in entry")


def _validate(text: str) -> None:
    """Enforce the competition gate: 1-180 chars, not whitespace-only."""
    _reject_control_chars(text)
    if not (1 <= len(text) <= 180):
        raise ValueError(f"entry length {len(text)} outside 1..180")
    if not text.strip():
        raise ValueError("entry is whitespace-only")
    if text.endswith("\n") or text.endswith("\r"):
        raise ValueError("entry must not end with a newline")


def _output_dir() -> str:
    """$MAKEFUN_OUTPUT_DIR, falling back to /output when unset or empty."""
    out = os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output"
    return out


def _fsync_dir(path: str) -> None:
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _write_atomic(target: str, data: bytes) -> None:
    """Write data to target via an exclusively-created temp file.

    A temp file left behind by a killed earlier run must not poison the
    next run: on FileExistsError the stale temp is removed and the
    exclusive create is retried once. A failed write removes the temp
    so it never lingers for the next run either.
    """
    tmp_path = target + ".tmp"
    try:
        fd = os.open(tmp_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except FileExistsError:
        os.unlink(tmp_path)
        fd = os.open(tmp_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        os.write(fd, data)
        os.fsync(fd)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
    finally:
        os.close(fd)
    os.chmod(tmp_path, 0o644)
    os.replace(tmp_path, target)


def main() -> int:
    _validate(ENTRY)
    data = ENTRY.encode("utf-8")

    out_dir = _output_dir()
    # Never delete the output directory itself: the grader mounts it.
    os.makedirs(out_dir, exist_ok=True)

    target = os.path.join(out_dir, OUTPUT_NAME)
    _write_atomic(target, data)
    _fsync_dir(out_dir)

    # Read-back verification: the file must match the constant exactly.
    with open(target, "rb") as fh:
        written = fh.read()
    if written != data:
        raise ValueError("read-back mismatch: entry.txt != ENTRY")
    os.chmod(target, 0o644)
    return 0


if __name__ == "__main__":
    sys.exit(main())
