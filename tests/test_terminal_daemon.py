from __future__ import annotations

import json
import os
import shutil
import socket
import tempfile
import threading
import time
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

import neurocad_cli
from core.config import CONFIG_VERSION, NeuroCADConfig, load_config, load_or_create_config, write_config
from core.daemon import (
    DaemonRuntime,
    JobStore,
    NeuroCADUnixServer,
    daemon_is_ready,
    daemon_request,
    remove_stale_socket,
    rotate_log,
    start_daemon,
    wait_for_job,
)
from core.generation import GenerationRequest, generate_artifacts, verify_artifact_bundle
from core.performance import profile_generation
from core.service import SERVICE_LABEL, install_user_service, uninstall_user_service

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def runtime_root() -> Path:
    configured_root = os.environ.get("NEUROCAD_TEST_TMPDIR")
    if configured_root:
        temporary_root = Path(configured_root).expanduser().resolve()
        temporary_root.mkdir(parents=True, exist_ok=True)
        root = Path(tempfile.mkdtemp(prefix="nc-", dir=temporary_root))
    else:
        root = Path(tempfile.mkdtemp(prefix="nc-"))
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _config(root: Path) -> NeuroCADConfig:
    return NeuroCADConfig(
        version=CONFIG_VERSION,
        data_root=str(root / "data"),
        state_root=str(root / "state"),
        output_root=str(root / "outputs"),
        socket_path=str(root / "state" / "daemon.sock"),
        log_path=str(root / "state" / "daemon.log"),
        default_formats=("ir", "scad"),
    )


def test_config_round_trip_is_strict(runtime_root: Path) -> None:
    path = runtime_root / "config.json"
    expected = _config(runtime_root)
    write_config(expected, path)
    assert load_config(path, require_exists=True) == expected

    value = json.loads(path.read_text(encoding="utf-8"))
    value["unknown"] = True
    path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError, match="unknown fields"):
        load_config(path, require_exists=True)


def test_first_use_creates_strict_configuration(runtime_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NEUROCAD_DATA_DIR", str(runtime_root / "data"))
    monkeypatch.setenv("NEUROCAD_STATE_DIR", str(runtime_root / "state"))
    path = runtime_root / "config.json"

    config, destination, created = load_or_create_config(path)
    assert created is True
    assert destination == path.resolve()
    assert load_config(path, require_exists=True) == config
    assert load_or_create_config(path)[2] is False


def test_generation_is_atomic_and_records_artifacts(runtime_root: Path) -> None:
    output = runtime_root / "valid"
    result = generate_artifacts(
        GenerationRequest(
            prompt="a 20 x 30 x 4 mm plate",
            output_dir=str(output),
            formats=("ir", "scad"),
        )
    )
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert result["status"] == "complete"
    assert set(manifest["artifacts"]) == {"ir", "request", "scad", "validation"}
    assert all(len(entry["sha256"]) == 64 for entry in manifest["artifacts"].values())

    failed = runtime_root / "failed"
    with pytest.raises(ValueError):
        generate_artifacts(GenerationRequest(prompt="make an unspecified object", output_dir=str(failed), formats=("ir",)))
    assert not failed.exists()


def test_artifact_verification_rejects_tampering_and_undeclared_files(runtime_root: Path) -> None:
    output = runtime_root / "bundle"
    generate_artifacts(GenerationRequest(prompt="a 20 x 30 x 4 mm plate", output_dir=str(output), formats=("ir", "scad")))
    report = verify_artifact_bundle(output)
    assert report["status"] == "verified"
    assert report["artifact_count"] == 4

    (output / "design.scad").write_text("tampered", encoding="utf-8")
    with pytest.raises(ValueError, match="does not match"):
        verify_artifact_bundle(output)

    shutil.rmtree(output)
    generate_artifacts(GenerationRequest(prompt="a 20 x 30 x 4 mm plate", output_dir=str(output), formats=("ir", "scad")))
    (output / "undeclared.txt").write_text("unexpected", encoding="utf-8")
    with pytest.raises(ValueError, match="differs from manifest"):
        verify_artifact_bundle(output)


def test_artifact_verify_and_open_cli(runtime_root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    output = runtime_root / "bundle"
    generate_artifacts(GenerationRequest(prompt="a 20 x 30 x 4 mm plate", output_dir=str(output), formats=("ir", "scad")))
    for arguments in ["artlés"] if False else [["artifacts", "verify", str(output)], ["open", str(output), "--print-only"]]:
        with pytest.raises(SystemExit) as exit_info:
            neurocad_cli.main(arguments)
        assert exit_info.value.code == 0
    rendered = capsys.readouterr().out
    assert "verified 4 artifacts" in rendered
    assert str(output.resolve()) in rendered


def test_scad_is_retained_as_a_reproducibility_dependency(runtime_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output = runtime_root / "mesh"

    def fake_compile(source: Path, destination: Path, **_: object) -> tuple[Path, dict[str, object]]:
        destination.write_text("solid fake\nendsolid fake\n", encoding="utf-8")
        return destination, {"valid": True}

    monkeypatch.setattr("core.generation.compile_scad_verified", fake_compile)
    generate_artifacts(GenerationRequest(prompt="a sphere with radius 10 mm", output_dir=str(output), formats=("stl",)))
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["artifacts"]["scad"]["role"] == "reproducibility_dependency"
    assert (output / "design.scad").is_file()


@pytest.mark.skipif(not hasattr(os, "getuid"), reason="Unix-domain daemon")
def test_daemon_runs_durable_generation_job(runtime_root: Path) -> None:
    config = _config(runtime_root)
    config_path = write_config(config, runtime_root / "config.json")
    probe_path = runtime_root / "probe.sock"
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as probe:
        try:
            probe.bind(str(probe_path))
        except PermissionError:
            pytest.skip("test filesystem does not support Unix-domain sockets")
    probe_path.unlink()
    try:
        status = start_daemon(config_path, config)
        assert status["status"] == "ready"
        submitted = daemon_request(
            config,
            "submit",
            payload={"prompt": "a 12 x 12 x 12 mm plate", "formats": ["ir", "scad"], "fn": 32, "timeout_seconds": 30},
        )
        record = wait_for_job(config, submitted["job_id"], timeout_seconds=20)
        assert record["status"] == "succeeded", record
        assert Path(record["output_dir"], "manifest.json").is_file()
        assert any(job["job_id"] == record["job_id"] for job in daemon_request(config, "list")["jobs"])
    finally:
        if daemon_is_ready(config):
            daemon_request(config, "shutdown")
            deadline = time.monotonic() + 10
            while daemon_is_ready(config) and time.monotonic() < deadline:
                time.sleep(0.05)


@pytest.mark.skipif(not hasattr(os, "getuid"), reason="Unix-domain daemon")
def test_shutdown_acknowledgement_is_flushed_before_server_stops(runtime_root: Path) -> None:
    for index in range(10):
        config = replace(_config(runtime_root), socket_path=str(runtime_root / f"shutdown-{index}.sock"))
        runtime = DaemonRuntime(config)
        server = NeuroCADUnixServer(config.socket_path, runtime)
        runtime.server = server
        thread = threading.Thread(target=lambda current=server: current.serve_forever(poll_interval=0.001))
        thread.start()
        try:
            assert daemon_request(config, "shutdown") == {"status": "stopping"}
            thread.join(timeout=2)
            assert not thread.is_alive()
        finally:
            server.shutdown()
            server.server_close()


def test_daemon_startup_timeout_terminates_spawned_process(runtime_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = _config(runtime_root)
    config_path = write_config(config, runtime_root / "config.json")

    class FakeProcess:
        terminated = False

        def poll(self) -> None:
            return None

        def terminate(self) -> None:
            self.terminated = True

        def wait(self, *, timeout: int) -> int:
            assert timeout == 5
            return 0

    process = FakeProcess()
    ticks = iter((0.0, 31.0))
    monkeypatch.setattr("core.daemon.daemon_is_ready", lambda _config: False)
    monkeypatch.setattr("core.daemon.subprocess.Popen", lambda *args, **kwargs: process)
    monkeypatch.setattr("core.daemon.time.monotonic", lambda: next(ticks))

    with pytest.raises(RuntimeError, match="daemon did not become ready"):
        start_daemon(config_path, config)
    assert process.terminated


def test_daemon_runtime_executes_and_persists_jobs_without_transport(runtime_root: Path) -> None:
    runtime = DaemonRuntime(_config(runtime_root))
    runtime.start_workers()
    try:
        submitted = runtime.submit({"prompt": "a 12 x 12 x 12 mm plate", "formats": ["ir", "scad"], "fn": 32, "timeout_seconds": 30})
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            record = runtime.store.read(submitted["job_id"])
            if record["status"] in {"succeeded", "failed", "cancelled"}:
                break
            time.sleep(0.05)
        assert record["status"] == "succeeded", record
        assert Path(record["output_dir"], "manifest.json").is_file()
        status = runtime.dispatch({"protocol_version": "neurocad-daemon-v1", "command": "ping"})
        assert status["workers_alive"] == 1
        assert status["jobs"]["succeeded"] == 1
        assert status["uptime_seconds"] >= 0

        retried = runtime.retry(record["job_id"])
        assert retried["retried_from"] == record["job_id"]
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            retry_record = runtime.store.read(retried["job_id"])
            if retry_record["status"] in {"succeeded", "failed", "cancelled"}:
                break
            time.sleep(0.05)
        assert retry_record["status"] == "succeeded", retry_record
    finally:
        runtime.stop_workers()


def test_running_job_can_be_cancelled_at_atomic_publication_boundary(runtime_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    entered = threading.Event()
    release = threading.Event()

    def delayed_generation(request: GenerationRequest) -> dict[str, object]:
        entered.set()
        assert release.wait(timeout=10)
        Path(request.output_dir).mkdir(parents=True)
        return {"status": "complete", "output_dir": request.output_dir}

    monkeypatch.setattr("core.daemon.generate_artifacts", delayed_generation)
    runtime = DaemonRuntime(_config(runtime_root))
    runtime.start_workers()
    try:
        submitted = runtime.submit({"prompt": "a 12 x 12 x 12 mm plate", "formats": ["ir"], "fn": 32, "timeout_seconds": 30})
        assert entered.wait(timeout=10)
        requested = runtime.cancel(submitted["job_id"])
        assert requested["status"] == "cancellation_requested"
        release.set()
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            record = runtime.store.read(submitted["job_id"])
            if record["status"] == "cancelled":
                break
            time.sleep(0.05)
        assert record["status"] == "cancelled"
        assert not Path(record["output_dir"]).exists()
    finally:
        release.set()
        runtime.stop_workers()


def test_direct_prompt_is_primary_cli(runtime_root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    config_path = write_config(_config(runtime_root), runtime_root / "config.json")
    output = runtime_root / "direct"
    with pytest.raises(SystemExit) as exit_info:
        neurocad_cli.main(
            [
                "a",
                "20",
                "x",
                "30",
                "x",
                "4",
                "mm",
                "plate",
                "--config",
                str(config_path),
                "--local",
                "--format",
                "scad",
                "--output",
                str(output),
            ]
        )
    assert exit_info.value.code == 0
    assert capsys.readouterr().out.strip() == str(output.resolve())
    assert (output / "design.scad").is_file()


def test_direct_prompt_bootstraps_first_use_without_setup(
    runtime_root: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("NEUROCAD_CONFIG_DIR", str(runtime_root / "config"))
    monkeypatch.setenv("NEUROCAD_DATA_DIR", str(runtime_root / "data"))
    monkeypatch.setenv("NEUROCAD_STATE_DIR", str(runtime_root / "state"))
    output = runtime_root / "first-use"

    with pytest.raises(SystemExit) as exit_info:
        neurocad_cli.main(["a", "20", "x", "30", "x", "4", "mm", "plate", "--local", "--format", "scad", "-o", str(output)])

    assert exit_info.value.code == 0
    assert capsys.readouterr().out.strip() == str(output.resolve())
    assert (runtime_root / "config" / "config.json").is_file()
    assert (output / "manifest.json").is_file()


def test_auto_format_uses_independently_probed_openscad_capabilities(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        neurocad_cli,
        "probe_openscad_capabilities",
        lambda: SimpleNamespace(mesh=False, preview=False),
    )
    assert neurocad_cli._requested_formats("auto") == ("ir", "scad")
    monkeypatch.setattr(
        neurocad_cli,
        "probe_openscad_capabilities",
        lambda: SimpleNamespace(mesh=True, preview=False),
    )
    assert neurocad_cli._requested_formats("auto") == ("ir", "scad", "stl")
    monkeypatch.setattr(
        neurocad_cli,
        "probe_openscad_capabilities",
        lambda: SimpleNamespace(mesh=True, preview=True),
    )
    assert neurocad_cli._requested_formats("auto") == ("ir", "scad", "stl", "preview")


def test_daemon_recovery_and_counts_cover_records_older_than_display_limit(runtime_root: Path) -> None:
    store = JobStore(_config(runtime_root))
    queued_id = "NCJ-20200101T000000Z-00000000"
    store.write({"job_id": queued_id, "status": "queued"})
    for index in range(500):
        job_id = f"NCJ-20210101T000000Z-{index:08x}"
        store.write({"job_id": job_id, "status": "succeeded"})

    assert store.recover() == [queued_id]
    assert store.status_counts() == {
        "queued": 1,
        "running": 0,
        "cancellation_requested": 0,
        "succeeded": 500,
        "failed": 0,
        "cancelled": 0,
    }


def test_human_job_list_is_compact(capsys: pytest.CaptureFixture[str]) -> None:
    neurocad_cli._print_jobs(
        [
            {
                "job_id": "NCJ-20260912T010203Z-deadbeef",
                "status": "succeeded",
                "created_at": "2026-09-12T01:02:03Z",
                "request": {"prompt": "a 20 x 30 x 4 mm plate"},
            }
        ]
    )
    rendered = capsys.readouterr().out
    assert "NeuroCAD jobs (1)" in rendered
    assert "succeeded" in rendered
    assert "a 20 x 30 x 4 mm plate" in rendered


def test_config_set_preserves_typed_fields(runtime_root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    config_path = write_config(_config(runtime_root), runtime_root / "config.json")
    updated_output = runtime_root / "custom-outputs"

    for key, value in (
        ("worker_count", "3"),
        ("default_formats", "ir, preview"),
        ("output_root", str(updated_output)),
    ):
        with pytest.raises(SystemExit) as exit_info:
            neurocad_cli.main(["config", "set", key, value, "--config", str(config_path)])
        assert exit_info.value.code == 0

    capsys.readouterr()
    config = load_config(config_path, require_exists=True)
    assert config.worker_count == 3
    assert config.default_formats == ("ir", "preview")
    assert config.output_root == str(updated_output.resolve())


@pytest.mark.parametrize("system", ["Darwin", "Linux"])
def test_user_service_definition(system: str, runtime_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = _config(runtime_root)
    config_path = write_config(config, runtime_root / "config.json")
    monkeypatch.setattr("core.service.platform.system", lambda: system)
    if system == "Darwin":
        service_root = runtime_root / "launch-agents"
        monkeypatch.setenv("NEUROCAD_LAUNCH_AGENTS_DIR", str(service_root))
        expected = service_root / f"{SERVICE_LABEL}.plist"
    else:
        service_root = runtime_root / "systemd"
        monkeypatch.setenv("NEUROCAD_SYSTEMD_USER_DIR", str(service_root))
        expected = service_root / "neurocad.service"
    result = install_user_service(config_path, config, activate=False)
    assert result["activated"] is False
    assert Path(result["path"]) == expected
    assert expected.is_file()


@pytest.mark.parametrize("system", ["Darwin", "Linux"])
def test_user_service_uninstall_removes_only_owned_definition(system: str, runtime_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    class Completed:
        returncode = 0
        stdout = ""
        stderr = ""

    monkeypatch.setattr("core.service.platform.system", lambda: system)
    monkeypatch.setattr("core.service.subprocess.run", lambda *args, **kwargs: Completed())
    if system == "Darwin":
        service_root = runtime_root / "launch-agents"
        monkeypatch.setenv("NEUROCAD_LAUNCH_AGENTS_DIR", str(service_root))
        definition = service_root / f"{SERVICE_LABEL}.plist"
    else:
        service_root = runtime_root / "systemd"
        monkeypatch.setenv("NEUROCAD_SYSTEMD_USER_DIR", str(service_root))
        definition = service_root / "neurocad.service"
    definition.parent.mkdir(parents=True)
    definition.write_text("owned definition", encoding="utf-8")
    unrelated = definition.parent / "unrelated.service"
    unrelated.write_text("preserve", encoding="utf-8")

    result = uninstall_user_service()

    assert result["stopped"] is True
    assert not definition.exists()
    assert unrelated.read_text(encoding="utf-8") == "preserve"


def test_socket_must_be_inside_state_root(runtime_root: Path) -> None:
    config = replace(_config(runtime_root), socket_path=str(runtime_root / "outside.sock"))
    with pytest.raises(ValueError, match="below state_root"):
        config.validate()


def test_daemon_refuses_to_replace_non_socket_path(runtime_root: Path) -> None:
    occupied = runtime_root / "daemon.sock"
    occupied.write_text("user data", encoding="utf-8")
    with pytest.raises(RuntimeError, match="non-socket"):
        remove_stale_socket(occupied)
    assert occupied.read_text(encoding="utf-8") == "user data"


def test_daemon_log_rotation_is_bounded(runtime_root: Path) -> None:
    log = runtime_root / "daemon.log"
    log.write_text("first", encoding="utf-8")
    assert rotate_log(log, max_bytes=4, backups=2) is True
    assert not log.exists()
    assert log.with_name("daemon.log.1").read_text(encoding="utf-8") == "first"
    log.write_text("second", encoding="utf-8")
    assert rotate_log(log, max_bytes=4, backups=2) is True
    assert log.with_name("daemon.log.1").read_text(encoding="utf-8") == "second"
    assert log.with_name("daemon.log.2").read_text(encoding="utf-8") == "first"


def test_performance_profile_records_scope_and_determinism() -> None:
    profile = profile_generation("a 20 x 30 x 4 mm plate", iterations=3, fn=32, warmup_iterations=2)
    assert profile["iterations"] == 3
    assert profile["warmup_iterations"] == 2
    assert profile["deterministic_output"] is True
    assert profile["latency_seconds"]["max"] >= profile["latency_seconds"]["min"] >= 0
    assert set(profile["stage_latency_seconds"]) == {
        "parse_and_generate",
        "validate_design",
        "lower_to_ir",
        "validate_ir",
        "emit_scad",
    }
    assert all(len(samples) == 3 for samples in profile["raw_samples_seconds"].values())
    assert profile["workload"]["ir_nodes"] > 0
    assert profile["workload"]["scad_bytes"] > 0
    assert profile["tracemalloc_peak_bytes"] > 0


@pytest.mark.parametrize("warmups", [0, 101, True])
def test_performance_profile_rejects_invalid_warmup_counts(warmups: object) -> None:
    with pytest.raises(ValueError, match="warmup_iterations"):
        profile_generation("a 20 x 30 x 4 mm plate", warmup_iterations=warmups)  # type: ignore[arg-type]
