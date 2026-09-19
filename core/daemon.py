"""Local durable NeuroCAD generation daemon and Unix-socket client."""

from __future__ import annotations

import argparse
import json
import os
import queue
import re
import shutil
import signal
import socket
import socketserver
import stat
import subprocess  # nosec B404
import sys
import threading
import time
import traceback
import uuid
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .artifacts import write_text_atomic
from .config import NeuroCADConfig, ensure_runtime_directories, load_config
from .generation import GenerationRequest, generate_artifacts
from .json_io import read_bounded_utf8, strict_json_loads

PROTOCOL_VERSION = "neurocad-daemon-v1"
MAX_REQUEST_BYTES = 1_048_576
MAX_LOG_BYTES = 10 * 1024 * 1024
LOG_BACKUPS = 3
MAX_JOB_RECORD_BYTES = 4 * 1024 * 1024
JOB_ID_PATTERN = re.compile(r"^NCJ-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{8}$")
TERMINAL_STATES = frozenset({"succeeded", "failed", "cancelled"})


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def new_job_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"NCJ-{stamp}-{uuid.uuid4().hex[:8]}"


def log_event(event: str, **fields: Any) -> None:
    """Write one bounded, machine-readable daemon event without prompt contents."""

    print(json.dumps({"at": utc_now(), "event": event, **fields}, separators=(",", ":"), sort_keys=True), flush=True)


def remove_stale_socket(path: Path) -> None:
    """Remove only an owned Unix socket; never replace a regular file or symlink."""

    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return
    if path.is_symlink() or not stat.S_ISSOCK(metadata.st_mode):
        raise RuntimeError(f"refusing to replace non-socket path: {path}")
    if hasattr(os, "getuid") and metadata.st_uid != os.getuid():
        raise PermissionError(f"refusing to replace socket owned by another user: {path}")
    path.unlink()


def rotate_log(path: Path, *, max_bytes: int = MAX_LOG_BYTES, backups: int = LOG_BACKUPS) -> bool:
    """Rotate a bounded daemon log before a directly managed daemon starts."""

    if isinstance(max_bytes, bool) or not isinstance(max_bytes, int) or max_bytes < 1:
        raise ValueError("max_bytes must be a positive integer")
    if isinstance(backups, bool) or not isinstance(backups, int) or backups < 1:
        raise ValueError("backups must be a positive integer")
    if not path.exists():
        return False
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"daemon log must be a regular file: {path}")
    if path.stat().st_size <= max_bytes:
        return False
    oldest = path.with_name(f"{path.name}.{backups}")
    oldest.unlink(missing_ok=True)
    for index in range(backups - 1, 0, -1):
        source = path.with_name(f"{path.name}.{index}")
        if source.exists():
            os.replace(source, path.with_name(f"{path.name}.{index + 1}"))
    os.replace(path, path.with_name(f"{path.name}.1"))
    return True


class JobStore:
    def __init__(self, config: NeuroCADConfig) -> None:
        self.config = config
        self.root = Path(config.state_root) / "jobs"
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._lock = threading.RLock()

    def _path(self, job_id: str) -> Path:
        if not JOB_ID_PATTERN.fullmatch(job_id):
            raise ValueError("invalid job ID")
        return self.root / f"{job_id}.json"

    def write(self, record: dict[str, Any]) -> dict[str, Any]:
        job_id = record.get("job_id")
        if not isinstance(job_id, str):
            raise TypeError("job record requires a string job_id")
        with self._lock:
            write_text_atomic(self._path(job_id), json.dumps(record, indent=2, sort_keys=True) + "\n")
        return record

    def read(self, job_id: str) -> dict[str, Any]:
        with self._lock:
            path = self._path(job_id)
            if not path.is_file():
                raise FileNotFoundError(f"unknown job: {job_id}")
            value = strict_json_loads(read_bounded_utf8(path, max_bytes=MAX_JOB_RECORD_BYTES, label="job record"))
        if not isinstance(value, dict) or value.get("job_id") != job_id:
            raise ValueError(f"invalid persisted job record: {job_id}")
        return value

    def transition(self, job_id: str, allowed_states: set[str], **updates: Any) -> dict[str, Any] | None:
        """Apply a compare-and-set state transition under the store lock."""

        with self._lock:
            record = self.read(job_id)
            if record.get("status") not in allowed_states:
                return None
            record.update(updates)
            return self.write(record)

    def list_records(self, limit: int = 50) -> list[dict[str, Any]]:
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 500:
            raise ValueError("job list limit must be from 1 through 500")
        records: list[dict[str, Any]] = []
        for path in sorted(self.root.glob("NCJ-*.json"), reverse=True):
            if len(records) == limit:
                break
            records.append(self.read(path.stem))
        return records

    def _all_records(self) -> list[dict[str, Any]]:
        return [self.read(path.stem) for path in sorted(self.root.glob("NCJ-*.json"), reverse=True)]

    def recover(self) -> list[str]:
        queued: list[str] = []
        for record in self._all_records():
            if record.get("status") == "running":
                record.update(
                    status="failed",
                    finished_at=utc_now(),
                    error={"type": "DaemonInterrupted", "message": "daemon stopped while this job was running"},
                )
                self.write(record)
            elif record.get("status") == "cancellation_requested":
                record.update(status="cancelled", finished_at=utc_now())
                self.write(record)
            elif record.get("status") == "queued":
                queued.append(record["job_id"])
        return list(reversed(queued))

    def status_counts(self) -> dict[str, int]:
        counts = {"queued": 0, "running": 0, "cancellation_requested": 0, "succeeded": 0, "failed": 0, "cancelled": 0}
        for record in self._all_records():
            status = record.get("status")
            if isinstance(status, str) and status in counts:
                counts[status] += 1
        return counts


class DaemonRuntime:
    def __init__(self, config: NeuroCADConfig) -> None:
        self.config = config
        self.store = JobStore(config)
        self.queue: queue.Queue[str | None] = queue.Queue(maxsize=1000)
        self.started_at = utc_now()
        self.started_monotonic = time.monotonic()
        self.workers: list[threading.Thread] = []
        self.server: NeuroCADUnixServer | None = None

    def start_workers(self) -> None:
        for index in range(self.config.worker_count):
            worker = threading.Thread(target=self._worker, name=f"neurocad-worker-{index + 1}", daemon=True)
            worker.start()
            self.workers.append(worker)
        for job_id in self.store.recover():
            self.queue.put_nowait(job_id)

    def stop_workers(self) -> None:
        for _ in self.workers:
            self.queue.put(None)
        for worker in self.workers:
            worker.join(timeout=5)

    def submit(self, payload: dict[str, Any], *, retried_from: str | None = None) -> dict[str, Any]:
        allowed = {"prompt", "formats", "fn", "timeout_seconds"}
        unknown = set(payload) - allowed
        if unknown:
            raise ValueError(f"submit has unknown fields: {sorted(unknown)}")
        prompt = payload.get("prompt")
        formats = payload.get("formats", list(self.config.default_formats))
        fn = payload.get("fn", self.config.default_fn)
        timeout = payload.get("timeout_seconds", self.config.default_timeout_seconds)
        if not isinstance(formats, list) or any(not isinstance(item, str) for item in formats):
            raise TypeError("formats must be a list of strings")
        if not isinstance(prompt, str):
            raise TypeError("prompt must be a string")
        job_id = new_job_id()
        output_dir = Path(self.config.output_root) / job_id
        request = GenerationRequest(
            prompt=prompt,
            output_dir=str(output_dir),
            formats=tuple(formats),
            fn=fn,
            timeout_seconds=timeout,
        )
        request.validate()
        record = {
            "job_id": job_id,
            "protocol_version": PROTOCOL_VERSION,
            "status": "queued",
            "created_at": utc_now(),
            "started_at": None,
            "finished_at": None,
            "request": {
                "prompt": request.prompt,
                "formats": list(request.formats),
                "fn": request.fn,
                "timeout_seconds": request.timeout_seconds,
            },
            "output_dir": str(output_dir),
            "result": None,
            "error": None,
        }
        if retried_from is not None:
            record["retried_from"] = retried_from
        self.store.write(record)
        try:
            self.queue.put_nowait(job_id)
        except queue.Full:
            record.update(
                status="failed",
                finished_at=utc_now(),
                error={"type": "QueueFull", "message": "daemon job queue is full"},
            )
            self.store.write(record)
            raise RuntimeError("daemon job queue is full") from None
        log_event("job.queued", job_id=job_id, formats=list(request.formats))
        return record

    def cancel(self, job_id: str) -> dict[str, Any]:
        record = self.store.read(job_id)
        status = record.get("status")
        if status == "queued":
            updated = self.store.transition(job_id, {"queued"}, status="cancelled", finished_at=utc_now())
            if updated is None:
                return self.cancel(job_id)
            log_event("job.cancelled", job_id=job_id)
            return updated
        if status == "running":
            updated = self.store.transition(job_id, {"running"}, status="cancellation_requested")
            if updated is None:
                return self.cancel(job_id)
            log_event("job.cancellation_requested", job_id=job_id)
            return updated
        if status == "cancellation_requested":
            return record
        raise RuntimeError(f"only queued or running jobs can be cancelled; {job_id} is {status}")

    def retry(self, job_id: str) -> dict[str, Any]:
        previous = self.store.read(job_id)
        if previous.get("status") not in TERMINAL_STATES:
            raise RuntimeError(f"only finished jobs can be retried; {job_id} is {previous.get('status')}")
        request = previous.get("request")
        if not isinstance(request, dict):
            raise TypeError(f"job {job_id} has no valid request")
        record = self.submit(request, retried_from=job_id)
        log_event("job.retried", job_id=record["job_id"], retried_from=job_id)
        return record

    def _worker(self) -> None:
        while True:
            job_id = self.queue.get()
            try:
                if job_id is None:
                    return
                record = self.store.transition(job_id, {"queued"}, status="running", started_at=utc_now())
                if record is None:
                    continue
                log_event("job.started", job_id=job_id)
                request_data = record["request"]
                request = GenerationRequest(
                    prompt=request_data["prompt"],
                    output_dir=record["output_dir"],
                    formats=tuple(request_data["formats"]),
                    fn=request_data["fn"],
                    timeout_seconds=request_data["timeout_seconds"],
                )
                try:
                    started = time.monotonic()
                    result = generate_artifacts(request)
                    elapsed = time.monotonic() - started
                    updated = self.store.transition(
                        job_id,
                        {"running"},
                        status="succeeded",
                        result=result,
                        finished_at=utc_now(),
                        elapsed_seconds=elapsed,
                    )
                    if updated is None:
                        latest = self.store.read(job_id)
                        if latest.get("status") != "cancellation_requested":
                            raise RuntimeError(f"job entered unexpected state during generation: {latest.get('status')}")
                        shutil.rmtree(request.output_dir, ignore_errors=True)
                        self.store.transition(
                            job_id,
                            {"cancellation_requested"},
                            status="cancelled",
                            finished_at=utc_now(),
                            elapsed_seconds=elapsed,
                        )
                        log_event("job.cancelled", job_id=job_id)
                    else:
                        log_event("job.succeeded", job_id=job_id, elapsed_seconds=elapsed)
                except Exception as exc:  # noqa: BLE001 - durable job boundary records a classified failure
                    cancelled = self.store.transition(
                        job_id,
                        {"cancellation_requested"},
                        status="cancelled",
                        finished_at=utc_now(),
                    )
                    if cancelled is not None:
                        shutil.rmtree(request.output_dir, ignore_errors=True)
                        log_event("job.cancelled", job_id=job_id)
                    else:
                        self.store.transition(
                            job_id,
                            {"running"},
                            status="failed",
                            error={"type": type(exc).__name__, "message": str(exc)},
                            finished_at=utc_now(),
                        )
                        log_event("job.failed", job_id=job_id, error_type=type(exc).__name__)
            finally:
                self.queue.task_done()

    def dispatch(self, request: dict[str, Any]) -> dict[str, Any]:
        if request.get("protocol_version") != PROTOCOL_VERSION:
            raise ValueError(f"protocol_version must be {PROTOCOL_VERSION!r}")
        command = request.get("command")
        if command == "ping":
            return {
                "protocol_version": PROTOCOL_VERSION,
                "status": "ready",
                "pid": os.getpid(),
                "started_at": self.started_at,
                "workers": self.config.worker_count,
                "workers_alive": sum(worker.is_alive() for worker in self.workers),
                "queue_depth": self.queue.qsize(),
                "queue_capacity": self.queue.maxsize,
                "uptime_seconds": time.monotonic() - self.started_monotonic,
                "jobs": self.store.status_counts(),
            }
        if command == "submit":
            payload = request.get("payload")
            if not isinstance(payload, dict):
                raise TypeError("submit payload must be an object")
            return self.submit(payload)
        if command == "show":
            job_id = request.get("job_id")
            if not isinstance(job_id, str):
                raise TypeError("job_id must be a string")
            return self.store.read(job_id)
        if command == "list":
            return {"jobs": self.store.list_records(request.get("limit", 50))}
        if command == "cancel":
            job_id = request.get("job_id")
            if not isinstance(job_id, str):
                raise TypeError("job_id must be a string")
            return self.cancel(job_id)
        if command == "retry":
            job_id = request.get("job_id")
            if not isinstance(job_id, str):
                raise TypeError("job_id must be a string")
            return self.retry(job_id)
        if command == "shutdown":
            if self.server is None:
                raise RuntimeError("daemon server is unavailable")
            return {"status": "stopping"}
        raise ValueError(f"unsupported daemon command: {command!r}")


class NeuroCADRequestHandler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        raw = self.rfile.readline(MAX_REQUEST_BYTES + 1)
        if len(raw) > MAX_REQUEST_BYTES:
            self._respond(False, error={"type": "RequestTooLarge", "message": "request exceeds 1 MiB"})
            return
        if not raw or not raw.endswith(b"\n"):
            self._respond(False, error={"type": "InvalidFrame", "message": "request must be one newline-terminated JSON object"})
            return
        try:
            value = strict_json_loads(raw.decode("utf-8"))
            if not isinstance(value, dict):
                raise TypeError("request must be a JSON object")
            runtime: DaemonRuntime = self.server.runtime  # type: ignore[attr-defined]
            result = runtime.dispatch(value)
            self._respond(True, result=result)
            if value.get("command") == "shutdown":
                server = runtime.server
                if server is None:
                    raise RuntimeError("daemon server is unavailable")
                threading.Thread(target=server.shutdown, name="neurocad-shutdown", daemon=True).start()
        except Exception as exc:  # noqa: BLE001 - protocol boundary returns a bounded error
            self._respond(False, error={"type": type(exc).__name__, "message": str(exc)})

    def _respond(self, ok: bool, **payload: Any) -> None:
        response = {"ok": ok, "protocol_version": PROTOCOL_VERSION, **payload}
        self.wfile.write(json.dumps(response, sort_keys=True).encode("utf-8") + b"\n")
        self.wfile.flush()


class NeuroCADUnixServer(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True
    allow_reuse_address = False

    def __init__(self, socket_path: str, runtime: DaemonRuntime) -> None:
        self.runtime = runtime
        super().__init__(socket_path, NeuroCADRequestHandler)


def daemon_request(
    config: NeuroCADConfig,
    command: str,
    *,
    socket_timeout_seconds: float = 5.0,
    **payload: Any,
) -> dict[str, Any]:
    if not 0 < socket_timeout_seconds <= 60:
        raise ValueError("socket timeout must be greater than zero and at most 60 seconds")
    request = {"protocol_version": PROTOCOL_VERSION, "command": command, **payload}
    encoded = json.dumps(request, separators=(",", ":"), sort_keys=True).encode("utf-8") + b"\n"
    if len(encoded) > MAX_REQUEST_BYTES:
        raise ValueError("daemon request exceeds 1 MiB")
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(socket_timeout_seconds)
        client.connect(config.socket_path)
        client.sendall(encoded)
        chunks = bytearray()
        while not chunks.endswith(b"\n"):
            chunk = client.recv(65_536)
            if not chunk:
                break
            chunks.extend(chunk)
            if len(chunks) > MAX_REQUEST_BYTES:
                raise RuntimeError("daemon response exceeds 1 MiB")
    response = strict_json_loads(bytes(chunks).decode("utf-8"))
    if not isinstance(response, dict) or response.get("protocol_version") != PROTOCOL_VERSION:
        raise RuntimeError("invalid daemon response")
    if not response.get("ok"):
        error = response.get("error", {})
        raise RuntimeError(f"{error.get('type', 'DaemonError')}: {error.get('message', 'unknown error')}")
    result = response.get("result")
    if not isinstance(result, dict):
        raise TypeError("daemon response has no result object")
    return result


def daemon_is_ready(config: NeuroCADConfig) -> bool:
    try:
        return daemon_request(config, "ping", socket_timeout_seconds=0.2).get("status") == "ready"
    except (OSError, RuntimeError, ValueError):
        return False


def start_daemon(config_path: Path, config: NeuroCADConfig) -> dict[str, Any]:
    ensure_runtime_directories(config)
    if daemon_is_ready(config):
        return daemon_request(config, "ping")
    socket_path = Path(config.socket_path)
    remove_stale_socket(socket_path)
    log_path = Path(config.log_path)
    rotate_log(log_path)
    with log_path.open("ab", buffering=0) as log:
        process = subprocess.Popen(  # nosec B603
            [sys.executable, "-m", "core.daemon", "serve", "--config", str(config_path)],
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=log,
            start_new_session=True,
            close_fds=True,
        )
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if daemon_is_ready(config):
            return daemon_request(config, "ping")
        if process.poll() is not None:
            break
        time.sleep(0.05)
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        remove_stale_socket(socket_path)
    detail = log_path.read_text(encoding="utf-8", errors="replace")[-4096:].strip()
    suffix = f": {detail}" if detail else ""
    raise RuntimeError(f"daemon did not become ready; inspect {config.log_path}{suffix}")


def serve(config: NeuroCADConfig) -> None:
    ensure_runtime_directories(config)
    socket_path = Path(config.socket_path)
    if daemon_is_ready(config):
        raise RuntimeError("a NeuroCAD daemon is already running")
    remove_stale_socket(socket_path)
    runtime = DaemonRuntime(config)
    server = NeuroCADUnixServer(config.socket_path, runtime)
    runtime.server = server
    os.chmod(socket_path, 0o600)
    pid_path = Path(config.state_root) / "daemon.pid"
    write_text_atomic(pid_path, f"{os.getpid()}\n")
    runtime.start_workers()
    log_event("daemon.started", pid=os.getpid(), socket=config.socket_path, workers=config.worker_count)

    def request_shutdown(_signum: int, _frame: Any) -> None:
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, request_shutdown)
    signal.signal(signal.SIGINT, request_shutdown)
    try:
        server.serve_forever(poll_interval=0.2)
    finally:
        log_event("daemon.stopping", pid=os.getpid())
        server.server_close()
        runtime.stop_workers()
        for path in (socket_path, pid_path):
            try:
                path.unlink()
            except FileNotFoundError:
                pass


def wait_for_job(
    config: NeuroCADConfig,
    job_id: str,
    *,
    timeout_seconds: int | None = None,
    on_update: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    deadline = None if timeout_seconds is None else time.monotonic() + timeout_seconds
    previous_status: object = None
    while True:
        record = daemon_request(config, "show", job_id=job_id)
        status = record.get("status")
        if on_update is not None and status != previous_status:
            on_update(record)
            previous_status = status
        if status in TERMINAL_STATES:
            return record
        if deadline is not None and time.monotonic() >= deadline:
            raise TimeoutError(f"timed out waiting for {job_id}; it continues in the daemon")
        time.sleep(0.1)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="NeuroCAD local generation daemon")
    sub = parser.add_subparsers(dest="command", required=True)
    serve_parser = sub.add_parser("serve")
    serve_parser.add_argument("--config", required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    try:
        if args.command == "serve":
            serve(load_config(Path(args.config), require_exists=True))
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        traceback.print_exc(file=sys.stderr)
        raise SystemExit(f"ERROR: {exc}") from None


if __name__ == "__main__":
    main()
