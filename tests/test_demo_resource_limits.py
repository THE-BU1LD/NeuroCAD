import socket
import threading
from collections.abc import Iterator

import pytest

from core.demo_server import DemoHandler, DemoServer


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
