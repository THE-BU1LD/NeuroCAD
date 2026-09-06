from __future__ import annotations

import json
import subprocess
import sys
import threading
import urllib.error
import urllib.request
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest

from core.benchmark import BenchmarkTask, benchmark_hash, benchmark_jsonl, generate_benchmark, run_benchmark
from core.demo_server import HTML, DemoHandler, DemoServer, generate_demo_payload, serve_demo


def test_benchmark_generation_is_deterministic_and_split() -> None:
    first = generate_benchmark()
    second = generate_benchmark()
    assert benchmark_jsonl(first) == benchmark_jsonl(second)
    assert benchmark_hash(first) == benchmark_hash(second)
    assert len(first) == 48
    assert {task.split for task in first} == {"train", "validation", "test"}
    assert all(task.task_id == f"NCB-{index:03d}" for index, task in enumerate(first, 1))


def test_benchmark_real_system_beats_trivial_baselines() -> None:
    results = run_benchmark()
    system = results["systems"]["neurocad"]
    fixed = results["systems"]["fixed_box"]
    raw = results["systems"]["raw_numbers_no_unit_normalization"]
    assert system["overall_semantic_exact_rate"] == 1.0
    assert system["intervention_consistency_rate"] == 1.0
    assert system["overall_semantic_exact_rate"] > raw["overall_semantic_exact_rate"] > fixed["overall_semantic_exact_rate"]


def test_benchmark_rejects_empty_duplicate_and_incomplete_task_sets() -> None:
    with pytest.raises(ValueError, match="at least one"):
        run_benchmark([])

    tasks = generate_benchmark()
    with pytest.raises(ValueError, match="IDs must be unique"):
        run_benchmark([*tasks, tasks[0]])

    train_only = [BenchmarkTask("ONE", "train", "box", "a 1 x 1 x 1 mm box", {"kind": "box"})]
    with pytest.raises(ValueError, match="train, validation, and test"):
        run_benchmark(train_only)


def test_demo_uses_real_pipeline() -> None:
    payload = generate_demo_payload("a 100 x 60 x 4 mm plate with two 12 x 4 mm slots")
    assert payload["validation"]["valid"] is True
    assert payload["evaluation"]["exact_round_trip"] is True
    assert payload["evaluation"]["editable_nodes"] == 3
    assert "difference()" in payload["scad"]
    assert "<svg" in payload["preview_svg"]


def test_demo_rejects_unsupported_prompt() -> None:
    with pytest.raises(ValueError, match="unsupported domain"):
        generate_demo_payload("an unsupported warp drive")


def test_demo_exposes_the_typed_enclosure_workflow() -> None:
    payload = generate_demo_payload(
        "80 x 60 x 30 mm electronics enclosure; walls 2 mm; profile fdm standard; "
        "friction lid 2.5 mm thick clearance 0.3 mm lip 2 mm; "
        "rectangular cutout 12 x 7 mm on front at 0 x 8 mm for USB-C; title controller case",
        "enclosure",
    )
    assert payload["mode"] == "enclosure"
    assert payload["parts"] == ["body", "lid"]
    assert payload["spec"]["lid"]["kind"] == "friction"
    assert payload["validation"]["valid"] is True
    assert payload["manufacturing"]["valid"] is True
    assert set(payload["scad"]) == {"body", "lid"}
    assert "<svg" in payload["preview_svg"]


def test_demo_enforces_prompt_limit() -> None:
    with pytest.raises(ValueError, match="limited to 4096"):
        generate_demo_payload("x" * 4097)


def test_demo_marks_edited_and_failed_results_as_unusable() -> None:
    assert "source.addEventListener('input',markDirty)" in HTML
    assert "Input changed; run validation before using any output." in HTML
    assert "No validated output was generated. Correct the input and try again." in HTML
    assert "result.setAttribute('aria-busy','true')" in HTML
    assert 'aria-describedby="status"' in HTML


@contextmanager
def _demo_server() -> Iterator[str]:
    server = DemoServer(("127.0.0.1", 0), DemoHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _request(
    url: str,
    *,
    body: Any = None,
    content_type: str = "application/json",
    host: str | None = None,
) -> tuple[int, dict[str, str], bytes]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {"Content-Type": content_type}
    if host is not None:
        headers["Host"] = host
    request = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, dict(response.headers), response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers), exc.read()


def test_demo_http_security_and_error_contract() -> None:
    with _demo_server() as base:
        status, headers, page = _request(base + "/")
        assert status == 200
        assert headers["X-Frame-Options"] == "DENY"
        assert "unsafe-inline" not in headers["Content-Security-Policy"]
        assert b'nonce="__NONCE__"' not in page
        assert b'nonce="' in page

        status, _, body = _request(base + "/api/generate", body=[])
        assert status == 400
        assert "JSON object" in json.loads(body)["error"]

        status, _, body = _request(base + "/api/generate", body={"source": "a 10 x 10 x 2 mm plate"}, content_type="text/plain")
        assert status == 415
        assert "application/json" in json.loads(body)["error"]

        status, _, body = _request(base + "/api/health", host="attacker.example")
        assert status == 421
        assert json.loads(body) == {"error": "unrecognized Host header"}


def test_demo_refuses_remote_binding_without_explicit_opt_in() -> None:
    with pytest.raises(ValueError, match="explicit.*allow-remote"):
        serve_demo(host="0.0.0.0", port=8765, open_browser=False)


def test_cli_ir_compile_and_evaluate_round_trip(tmp_path: Path) -> None:
    ir_path = tmp_path / "program.ncad.json"
    scad_path = tmp_path / "program.scad"
    generated = subprocess.run(
        [sys.executable, "-m", "neurocad_cli", "ir", "a 40 x 30 x 3 mm plate", "-o", str(ir_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert generated.returncode == 0, generated.stderr
    compiled = subprocess.run(
        [sys.executable, "-m", "neurocad_cli", "compile", str(ir_path), "--format", "scad", "-o", str(scad_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert compiled.returncode == 0, compiled.stderr
    assert "cube(size=[40, 30, 3]" in scad_path.read_text(encoding="utf-8")
    evaluated = subprocess.run(
        [sys.executable, "-m", "neurocad_cli", "evaluate", "--ir", str(ir_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert evaluated.returncode == 0, evaluated.stderr
    assert json.loads(evaluated.stdout)["exact_round_trip"] is True


def test_cli_structured_input_limits_and_io_errors_are_clean(tmp_path: Path) -> None:
    oversized = tmp_path / "oversized.json"
    oversized.write_bytes(b" " * 1_048_577)
    too_large = subprocess.run(
        [sys.executable, "-m", "neurocad_cli", "compile", str(oversized)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert too_large.returncode == 2
    assert "limited to 1 MiB" in too_large.stderr
    assert "Traceback" not in too_large.stderr

    missing = subprocess.run(
        [sys.executable, "-m", "neurocad_cli", "compile", str(tmp_path / "missing.json")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert missing.returncode == 2
    assert "ERROR:" in missing.stderr
    assert "Traceback" not in missing.stderr


def test_cli_rejects_non_positive_openscad_timeout(tmp_path: Path) -> None:
    ir_path = tmp_path / "program.ncad.json"
    generated = subprocess.run(
        [sys.executable, "-m", "neurocad_cli", "ir", "a 40 x 30 x 3 mm plate", "-o", str(ir_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert generated.returncode == 0
    result = subprocess.run(
        [sys.executable, "-m", "neurocad_cli", "compile", str(ir_path), "--format", "stl", "--timeout", "0"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert "timeout must be a positive" in result.stderr
