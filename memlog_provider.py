"""Storage-provider boundary for engineering-memlog.

The built-in provider is the existing append-only JSONL file. Set
ENGINEERING_MEMLOG_PROVIDER_COMMAND to an executable command to replace storage
without replacing Memlog's validation, ranking, or CLI behavior.
"""

import json
import math
import os
import shlex
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, TextIO

from memlog_schema import entry_validation_errors


PROTOCOL_VERSION = 1
DEFAULT_TIMEOUT_SECONDS = 10.0
DEFAULT_MAX_RESPONSE_BYTES = 5 * 1024 * 1024


class ProviderError(Exception):
    """The configured storage provider could not complete an operation."""


@dataclass
class ScannedRecord:
    position: int
    location: str
    entry: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


def _provider_command() -> Optional[list]:
    raw = os.environ.get("ENGINEERING_MEMLOG_PROVIDER_COMMAND", "").strip()
    if not raw:
        return None
    try:
        command = shlex.split(raw)
    except ValueError as exc:
        raise ProviderError(f"invalid provider command: {exc}") from exc
    if not command:
        raise ProviderError("provider command is empty")
    if not Path(command[0]).is_absolute():
        raise ProviderError("provider executable must use an absolute path")
    return command


def _provider_timeout() -> float:
    raw = os.environ.get(
        "ENGINEERING_MEMLOG_PROVIDER_TIMEOUT_SECONDS",
        str(DEFAULT_TIMEOUT_SECONDS),
    )
    try:
        timeout = float(raw)
    except ValueError as exc:
        raise ProviderError("provider timeout must be a positive number") from exc
    if not math.isfinite(timeout) or timeout <= 0:
        raise ProviderError("provider timeout must be a positive number")
    return timeout


def _provider_max_response_bytes() -> int:
    raw = os.environ.get(
        "ENGINEERING_MEMLOG_PROVIDER_MAX_RESPONSE_BYTES",
        str(DEFAULT_MAX_RESPONSE_BYTES),
    )
    try:
        maximum = int(raw)
    except ValueError as exc:
        raise ProviderError("provider response limit must be a positive integer") from exc
    if maximum <= 0:
        raise ProviderError("provider response limit must be a positive integer")
    return maximum


def _run_provider(
    operation: str,
    data_file: Path,
    entry: Optional[Dict[str, Any]] = None,
) -> str:
    command = _provider_command()
    if command is None:
        raise ProviderError("no external provider is configured")

    request: Dict[str, Any] = {
        "protocol_version": PROTOCOL_VERSION,
        "operation": operation,
        "data_file": str(data_file),
    }
    if entry is not None:
        request["entry"] = entry

    encoded_request = (json.dumps(request, ensure_ascii=False) + "\n").encode("utf-8")
    maximum = _provider_max_response_bytes()
    try:
        with tempfile.TemporaryFile() as stdout_file, tempfile.TemporaryFile() as stderr_file:
            try:
                result = subprocess.run(
                    command,
                    input=encoded_request,
                    stdout=stdout_file,
                    stderr=stderr_file,
                    timeout=_provider_timeout(),
                    check=False,
                )
            except subprocess.TimeoutExpired as exc:
                detail = "provider timed out during " + operation
                if operation == "append":
                    detail += "; write outcome may be unknown"
                raise ProviderError(detail) from exc
            except OSError as exc:
                raise ProviderError(
                    f"could not run provider during {operation}: {exc}"
                ) from exc

            stdout_size = stdout_file.tell()
            stderr_size = stderr_file.tell()
            if stdout_size + stderr_size > maximum:
                raise ProviderError(
                    f"provider {operation} response exceeded {maximum} bytes"
                )
            stdout_file.seek(0)
            stderr_file.seek(0)
            stdout_bytes = stdout_file.read()
            stderr_bytes = stderr_file.read()
    except OSError as exc:
        raise ProviderError(f"could not capture provider {operation} output: {exc}") from exc

    try:
        stdout = stdout_bytes.decode("utf-8")
        stderr = stderr_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ProviderError(f"provider {operation} returned non-UTF-8 output") from exc

    if result.returncode != 0:
        detail = stderr.strip().splitlines()[-1] if stderr.strip() else "no error detail"
        raise ProviderError(
            f"provider {operation} failed with exit {result.returncode}: {detail[:300]}"
        )
    if stderr:
        sys.stderr.write(stderr)
    return stdout


def _parse_records(
    lines: Iterable[str],
    location_prefix: str,
) -> Iterable[ScannedRecord]:
    for position, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line:
            continue
        location = f"{location_prefix} {position}"
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            yield ScannedRecord(position, location, error=f"invalid JSON: {exc.msg}")
            continue
        if not isinstance(value, dict):
            yield ScannedRecord(position, location, error="entry must be a JSON object")
            continue
        yield ScannedRecord(position, location, entry=value)


def scan_records(
    data_file: Path,
    strict_provider: bool = True,
) -> Iterable[ScannedRecord]:
    """Read records from the configured provider without applying schema policy."""
    if _provider_command() is not None:
        output = _run_provider("scan", data_file)
        for record in _parse_records(output.splitlines(), "provider record"):
            if strict_provider and record.error:
                raise ProviderError(
                    f"provider scan returned {record.error} at {record.location}"
                )
            if strict_provider and record.entry is not None:
                errors = entry_validation_errors(record.entry)
                if errors:
                    raise ProviderError(
                        "provider scan returned an invalid entry at "
                        f"{record.location}: {' '.join(errors)}"
                    )
            yield record
        return

    if not data_file.exists():
        return
    try:
        with data_file.open("r", encoding="utf-8") as handle:
            yield from _parse_records(handle, "line")
    except OSError:
        raise


def iter_entries(
    data_file: Path,
    warning_stream: TextIO = sys.stderr,
) -> Iterable[Dict[str, Any]]:
    """Yield object records, preserving the historical skip-and-warn behavior."""
    for record in scan_records(data_file):
        if record.error:
            if record.error.startswith("invalid JSON"):
                message = f"Skipping invalid JSON on {record.location}"
            else:
                message = f"Skipping non-object JSON on {record.location}"
            print(message, file=warning_stream)
            continue
        if record.entry is not None:
            yield record.entry


def append_entry(entry: Dict[str, Any], data_file: Path) -> None:
    """Append through the selected provider; never fall back after provider failure."""
    if _provider_command() is not None:
        output = _run_provider("append", data_file, entry).strip()
        if output:
            try:
                response = json.loads(output)
            except json.JSONDecodeError as exc:
                raise ProviderError("provider append returned invalid JSON") from exc
            if not isinstance(response, dict) or response.get("ok") is not True:
                raise ProviderError("provider append did not return {\"ok\": true}")
        return

    data_file.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(entry, ensure_ascii=False) + "\n").encode("utf-8")
    flags = os.O_APPEND | os.O_CREAT | os.O_WRONLY
    descriptor = os.open(str(data_file), flags, 0o600)
    try:
        written = os.write(descriptor, encoded)
        if written != len(encoded):
            raise OSError(f"Short append: wrote {written} of {len(encoded)} bytes")
    finally:
        os.close(descriptor)
