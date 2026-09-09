import socket
import threading
from collections.abc import Iterator

import pytest

from core.demo_server import DemoHandler, DemoServer
from core.mesh_preview import _COMPILER_SLOT


@pytest.fixture
def server() -> Iterator[DemoServer]:
    class BoundedTestServer(DemoServer):
        request_timeout_seconds = 0.2
        maximum_workers = 1

    instance = BoundedTestServer(("127.0.0.1", 0), DemoHandler)
    thread = threading.Thread(target=instance.serve_forever, daemon=True)
    thread.start()
    try:
        yield instance
    finally:
        instance.shutdown()
        instance.server_close()
        thread.join(timeout=2)


def send(server: DemoServer, headers: str, body: bytes = b"", *, eof: bool = False) -> bytes:
    with socket.create_connection(server.server_address, timeout=2) as client:
        client.sendall((f"POST /api/generate HTTP/1.1\r\nHost: 127.0.0.1:{server.server_port}\r\n"
                        f"Content-Type: application/json\r\n{headers}\r\n").encode() + body)
        if eof:
            client.shutdown(socket.SHUT_WR)
        chunks = []
        while chunk := client.recv(4096):
            chunks.append(chunk)
        return b"".join(chunks)


def test_stalled_body_times_out_and_worker_can_be_reused(server: DemoServer) -> None:
    assert b"408 Request Timeout" in send(server, "Content-Length: 100\r\n", b"{")
    assert b"400 Bad Request" in send(server, "Content-Length: 2\r\n", b"{}")


@pytest.mark.parametrize("headers,body", [
    ("Content-Length: 2\r\nContent-Length: 3\r\n", b"{}"),
    ("Content-Length: 2\r\nTransfer-Encoding: chunked\r\n", b"{}"),
    ("Content-Length: 100\r\n", b"{}"),
])
def test_ambiguous_and_truncated_frames_fail_closed(server: DemoServer, headers: str, body: bytes) -> None:
    assert b"400 Bad Request" in send(server, headers, body, eof=True)


def test_overload_does_not_create_an_extra_worker(server: DemoServer) -> None:
    assert server._worker_slots.acquire(blocking=False)
    try:
        with socket.create_connection(server.server_address, timeout=2) as client:
            assert client.recv(1) == b""
    finally:
        server._worker_slots.release()


def test_duplicate_host_and_foreign_origin_are_rejected(server: DemoServer) -> None:
    assert b"421 Misdirected Request" in send(server, "Host: evil.example\r\nContent-Length: 2\r\n", b"{}")
    assert b"403 Forbidden" in send(server, "Origin: https://evil.example\r\nContent-Length: 2\r\n", b"{}")
    assert b"403 Forbidden" in send(server, "Origin: null\r\nContent-Length: 2\r\n", b"{}")
    origin = f"Origin: http://127.0.0.1:{server.server_port}\r\n"
    assert b"403 Forbidden" in send(server, origin + origin + "Content-Length: 2\r\n", b"{}")
    # Same-origin requests reach normal input validation; CLI clients may omit Origin.
    assert b"400 Bad Request" in send(server, origin + "Content-Length: 2\r\n", b"{}")


def test_invalid_request_flags_fail_before_pipeline(server: DemoServer, monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*args: object, **kwargs: object) -> None:
        pytest.fail("invalid request reached the CAD pipeline")

    monkeypatch.setattr("core.demo_server.generate_demo_payload", forbidden)
    for body in (
        b'{"source":"x","compile_mesh":"yes"}', b'{"source":"x","unknown":true}',
        b'{"source":"x","timeout_seconds":true}', b'{"source":"x","timeout_seconds":121}',
        b'{"source":"x","timeout_seconds":"30"}',
    ):
        assert b"400 Bad Request" in send(server, f"Content-Length: {len(body)}\r\n", body)


def test_busy_compiler_is_retryable_not_invalid_input(server: DemoServer) -> None:
    body = b'{"source":"a 40 x 30 x 3 mm box","compile_mesh":true}'
    with _COMPILER_SLOT:
        response = send(server, f"Content-Length: {len(body)}\r\n", body)
    assert b"503 Service Unavailable" in response
    assert b"Retry-After: 5" in response
    assert b"compiler is busy" in response


@pytest.mark.parametrize("kind,status,code", [
    ("timeout", b"504 Gateway Timeout", b"compiler_timeout"),
    ("missing", b"503 Service Unavailable", b"compiler_unavailable"),
])
def test_kernel_failure_categories_are_actionable_and_redacted(
    server: DemoServer, monkeypatch: pytest.MonkeyPatch, kind: str, status: bytes, code: bytes,
) -> None:
    from core.artifacts import CompilerTimeoutError, CompilerUnavailableError

    def failed(*args: object, **kwargs: object) -> None:
        exception = CompilerTimeoutError if kind == "timeout" else CompilerUnavailableError
        raise exception("private diagnostic path must not be returned")

    monkeypatch.setattr("core.demo_server.compile_payload_meshes", failed)
    body = b'{"source":"a 40 x 30 x 3 mm box","compile_mesh":true}'
    response = send(server, f"Content-Length: {len(body)}\r\n", body)
    assert status in response and code in response
    assert b"private diagnostic" not in response
