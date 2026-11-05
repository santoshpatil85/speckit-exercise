from __future__ import annotations

from io import BytesIO
import socket
from dataclasses import dataclass
import time

import pytest

from rss_reader.feed_validation import FeedValidationError, validate_feed


RSS = b"""<?xml version="1.0"?>
<rss version="2.0"><channel><title>Example RSS</title><link>https://example.com</link>
<description>Example</description><item><title>Entry</title></item></channel></rss>"""
ATOM = b"""<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom"><title>Example Atom</title>
<id>https://example.com/</id><updated>2025-01-01T00:00:00Z</updated></feed>"""
PUBLIC_INFO = (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("8.8.8.8", 443))


@dataclass
class FakeResponse:
    status: int
    body: bytes
    headers: dict[str, str] | None = None

    def __post_init__(self):
        self.remaining = self.body

    def getheader(self, name: str, default: str | None = None) -> str | None:
        return (self.headers or {}).get(name.lower(), default)

    def read(self, size: int = -1) -> bytes:
        if size < 0:
            size = len(self.remaining)
        chunk, self.remaining = self.remaining[:size], self.remaining[size:]
        return chunk


def _requester(response: FakeResponse, seen: list[tuple] | None = None):
    def request(parsed_url, address_info, deadline):
        if seen is not None:
            seen.append((parsed_url, address_info, deadline))
        return response, None

    return request


def test_rejects_malformed_unsupported_credentials_and_non_default_ports():
    for url in (
        "",
        "ftp://example.com/feed",
        "http://user:pass@example.com/feed",
        "https://example.com:8443/feed",
        "https:///feed",
        "https://example.com/a raw path",
    ):
        with pytest.raises(FeedValidationError):
            validate_feed(url)


def test_rejects_any_non_public_dns_answer_before_request():
    unsafe_answers = [
        PUBLIC_INFO,
        (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("127.0.0.1", 443)),
    ]
    requested = []
    with pytest.raises(FeedValidationError, match="public"):
        validate_feed(
            "https://feeds.example/feed",
            resolver=lambda *args, **kwargs: unsafe_answers,
            requester=_requester(FakeResponse(200, RSS), requested),
        )
    assert requested == []


def test_connects_only_to_a_validated_dns_answer():
    seen = []
    result = validate_feed(
        "https://Feeds.Example/rss",
        resolver=lambda *args, **kwargs: [PUBLIC_INFO],
        requester=_requester(FakeResponse(200, RSS), seen),
    )
    assert result.title == "Example RSS"
    assert seen[0][1] == PUBLIC_INFO
    assert seen[0][0].hostname == "feeds.example"


def test_real_transport_connects_to_pinned_address_and_sends_host_header(monkeypatch):
    class FakeSocket:
        def __init__(self):
            self.connected_to = None
            self.sent = bytearray()

        def settimeout(self, timeout):
            pass

        def connect(self, address):
            self.connected_to = address

        def sendall(self, data):
            self.sent.extend(data)

        def makefile(self, mode):
            return BytesIO(
                b"HTTP/1.1 200 OK\r\n"
                + f"Content-Length: {len(RSS)}\r\nConnection: close\r\n\r\n".encode()
                + RSS
            )

        def close(self):
            pass

    connected_sockets = []

    def create_socket(*args):
        created = FakeSocket()
        connected_sockets.append(created)
        return created

    monkeypatch.setattr(socket, "socket", create_socket)
    address_info = (
        socket.AF_INET,
        socket.SOCK_STREAM,
        socket.IPPROTO_TCP,
        "",
        ("8.8.8.8", 80),
    )
    result = validate_feed(
        "http://Feeds.Example/rss",
        resolver=lambda *args, **kwargs: [address_info],
    )

    assert result.title == "Example RSS"
    assert connected_sockets[0].connected_to == ("8.8.8.8", 80)
    assert b"Host: feeds.example\r\n" in connected_sockets[0].sent


def test_rejects_redirects_without_following_them():
    requested = []
    with pytest.raises(FeedValidationError, match="redirect"):
        validate_feed(
            "https://feeds.example/feed",
            resolver=lambda *args, **kwargs: [PUBLIC_INFO],
            requester=_requester(
                FakeResponse(302, b"", {"location": "http://127.0.0.1/"}),
                requested,
            ),
        )
    assert len(requested) == 1


def test_rejects_oversized_and_compressed_responses():
    with pytest.raises(FeedValidationError, match="size"):
        validate_feed(
            "https://feeds.example/feed",
            resolver=lambda *args, **kwargs: [PUBLIC_INFO],
            requester=_requester(FakeResponse(200, b"x" * (1024 * 1024 + 1))),
        )

    with pytest.raises(FeedValidationError, match="(?i)compressed"):
        validate_feed(
            "https://feeds.example/feed",
            resolver=lambda *args, **kwargs: [PUBLIC_INFO],
            requester=_requester(
                FakeResponse(200, RSS, {"content-encoding": "gzip"})
            ),
        )


@pytest.mark.parametrize(
    ("status", "body"),
    [
        (503, RSS),
        (200, b"<html>not a feed</html>"),
        (200, b"<rss><channel>"),
        (
            200,
            b'<!DOCTYPE rss SYSTEM "http://127.0.0.1/private"><rss version="2.0"/>',
        ),
        (
            200,
            b'<!DOCTYPE rss [<!ENTITY x "expanded">]><rss version="2.0"/>',
        ),
    ],
)
def test_rejects_http_errors_malformed_and_non_feed(status, body):
    with pytest.raises(FeedValidationError):
        validate_feed(
            "https://feeds.example/feed",
            resolver=lambda *args, **kwargs: [PUBLIC_INFO],
            requester=_requester(FakeResponse(status, body)),
        )


@pytest.mark.parametrize(("document", "title"), [(RSS, "Example RSS"), (ATOM, "Example Atom")])
def test_accepts_rss_and_atom(document, title):
    result = validate_feed(
        "https://feeds.example/feed",
        resolver=lambda *args, **kwargs: [PUBLIC_INFO],
        requester=_requester(FakeResponse(200, document)),
    )
    assert result.title == title


def test_enforces_overall_deadline_during_body_read():
    class SlowResponse(FakeResponse):
        def read(self, size=-1):
            nonlocal current_time
            current_time += 11
            return super().read(size)

    current_time = 0.0
    with pytest.raises(FeedValidationError, match="timed out"):
        validate_feed(
            "https://feeds.example/feed",
            resolver=lambda *args, **kwargs: [PUBLIC_INFO],
            requester=_requester(SlowResponse(200, RSS)),
            clock=lambda: current_time,
        )


def test_enforces_deadline_during_dns_resolution(monkeypatch):
    import rss_reader.feed_validation as validation

    monkeypatch.setattr(validation, "REQUEST_DEADLINE_SECONDS", 0.01)

    def slow_resolver(*args, **kwargs):
        time.sleep(0.1)
        return [PUBLIC_INFO]

    with pytest.raises(FeedValidationError, match="timed out"):
        validate_feed("https://feeds.example/feed", resolver=slow_resolver)
