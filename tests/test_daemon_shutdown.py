from __future__ import annotations

import queue
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

from core.config import CONFIG_VERSION, NeuroCADConfig
from core.daemon import DaemonRuntime
from core.generation import GenerationRequest


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


def test_shutdown_reaches_worker_join_even_when_queue_is_full(tmp_path: Path) -> None:
    runtime = DaemonRuntime(_config(tmp_path))
    runtime.queue = queue.Queue(maxsize=1)
    runtime.queue.put_nowait("queued-job")
    joined = threading.Event()
    runtime.workers.append(SimpleNamespace(join=lambda *, timeout: joined.set()))
    stopped = threading.Event()

    def stop() -> None:
        runtime.stop_workers()
        stopped.set()

    stopper = threading.Thread(target=stop, daemon=True)
    stopper.start()
    completed_without_drain = stopped.wait(timeout=1)
    try:
        assert completed_without_drain, "shutdown blocked on the full queue before its worker join deadline"
        assert joined.is_set()
        assert runtime.queue.get_nowait() == "queued-job"
    finally:
        # Release the original implementation's blocking sentinel write so a
        # red regression run also leaves no background stopper behind.
        if not completed_without_drain:
            runtime.queue.get_nowait()
        stopper.join(timeout=1)


def test_shutdown_finishes_inflight_work_and_leaves_queued_work_for_restart(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    entered = threading.Event()
    release = threading.Event()
    resumed = threading.Event()
    generated: list[str] = []

    def delayed_generation(request: GenerationRequest) -> dict[str, object]:
        generated.append(request.output_dir)
        entered.set()
        assert release.wait(timeout=3)
        if len(generated) == 2:
            resumed.set()
        return {"status": "complete", "output_dir": request.output_dir}

    monkeypatch.setattr("core.daemon.generate_artifacts", delayed_generation)
    config = _config(tmp_path)
    runtime = DaemonRuntime(config)
    runtime.start_workers()
    worker = runtime.workers[0]
    join_worker = worker.join
    # Keep this controlled stalled-work case short while exercising the real
    # stop path and real worker. The production join budget stays unchanged.
    monkeypatch.setattr(worker, "join", lambda *, timeout: join_worker(timeout=min(timeout, 0.01)))
    restarted: DaemonRuntime | None = None
    try:
        first = runtime.submit({"prompt": "a 20 x 30 x 4 mm plate"})
        assert entered.wait(timeout=2)
        second = runtime.submit({"prompt": "a 30 x 40 x 4 mm plate"})
        runtime.stop_workers()
        release.set()
        join_worker(timeout=2)
        assert not worker.is_alive()
        assert runtime.store.read(first["job_id"])["status"] == "succeeded"
        assert runtime.store.read(second["job_id"])["status"] == "queued"
        assert generated == [first["output_dir"]]

        restarted = DaemonRuntime(config)
        restarted.start_workers()
        assert resumed.wait(timeout=2)
        restarted.queue.join()
        assert restarted.store.read(second["job_id"])["status"] == "succeeded"
        assert generated == [first["output_dir"], second["output_dir"]]
    finally:
        release.set()
        runtime.stop_workers()
        join_worker(timeout=2)
        if restarted is not None:
            restarted.stop_workers()


def test_idle_workers_stop_without_new_queue_items(tmp_path: Path) -> None:
    runtime = DaemonRuntime(_config(tmp_path))
    runtime.start_workers()
    runtime.stop_workers()
    assert not any(worker.is_alive() for worker in runtime.workers)
    assert runtime.queue.empty()
    assert runtime.queue.unfinished_tasks == 0


def test_worker_joins_share_one_shutdown_deadline(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = DaemonRuntime(_config(tmp_path))
    ticks = iter((10.0, 11.0, 13.0, 18.0))
    monkeypatch.setattr("core.daemon.time", SimpleNamespace(monotonic=lambda: next(ticks)))
    timeouts: list[float] = []
    for _ in range(3):
        runtime.workers.append(SimpleNamespace(join=lambda *, timeout: timeouts.append(timeout)))
    runtime.stop_workers()
    assert timeouts == [4.0, 2.0, 0.0]


def test_stopping_runtime_refuses_new_work_without_persisting_it(tmp_path: Path) -> None:
    runtime = DaemonRuntime(_config(tmp_path))
    runtime.stop_workers()
    with pytest.raises(RuntimeError, match="stopping"):
        runtime.submit({"prompt": "a 20 x 30 x 4 mm plate"})
    assert runtime.store.list_records() == []
