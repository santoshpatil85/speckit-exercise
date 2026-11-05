"""Safe, bounded RSS and Atom retrieval and parsing."""

from __future__ import annotations

import http.client
import ipaddress
import socket
import ssl
import threading
import time
from dataclasses import dataclass
from typing import Callable
from urllib.parse import SplitResult, quote, urlsplit, urlunsplit
from xml.etree.ElementTree import ParseError

from defusedxml import ElementTree as SafeElementTree
from defusedxml.common import DefusedXmlException
import feedparser

MAX_RESPONSE_BYTES = 1024 * 1024
REQUEST_DEADLINE_SECONDS = 10.0
READ_CHUNK_SIZE = 64 * 1024
_DNS_LOOKUP_SLOTS = threading.BoundedSemaphore(4)


class FeedValidationError(Exception):
    """A safe, user-presentable feed validation failure."""


@dataclass(frozen=True)
class ValidatedFeed:
    title: str | None


Resolver = Callable[..., list[tuple]]
Requester = Callable[[SplitResult, tuple, float], tuple[http.client.HTTPResponse, object]]


def validate_feed(
    feed_url: str,
    *,
    resolver: Resolver | None = None,
    requester: Requester | None = None,
    clock: Callable[[], float] | None = None,
) -> ValidatedFeed:
    """Retrieve and parse a public RSS/Atom URL without following redirects."""
    resolve = resolver or socket.getaddrinfo
    open_request = requester or _open_pinned_response
    now = clock or time.monotonic
    started_at = now()
    deadline = started_at + REQUEST_DEADLINE_SECONDS
    parsed_url = _parse_feed_url(feed_url)

    try:
        addresses = _resolve_with_deadline(
            resolve,
            parsed_url.hostname,
            parsed_url.port or (443 if parsed_url.scheme == "https" else 80),
            deadline,
            now,
        )
    except TimeoutError:
        raise FeedValidationError("The feed request timed out.") from None
    except (OSError, UnicodeError):
        raise FeedValidationError("The feed address could not be reached.") from None

    if not addresses:
        raise FeedValidationError("The feed address could not be reached.")
    if now() >= deadline:
        raise FeedValidationError("The feed request timed out.")
    if any(not _is_public_address(info) for info in addresses):
        raise FeedValidationError("The feed address must point to a public network host.")

    response = None
    connection = None
    last_network_error: OSError | None = None
    for address_info in addresses:
        if now() >= deadline:
            raise FeedValidationError("The feed request timed out.")
        try:
            response, connection = open_request(parsed_url, address_info, deadline)
            break
        except (OSError, ssl.SSLError, http.client.HTTPException) as error:
            last_network_error = error
    if response is None:
        if isinstance(last_network_error, (socket.timeout, TimeoutError)) or now() >= deadline:
            raise FeedValidationError("The feed request timed out.") from None
        raise FeedValidationError("The feed address could not be reached.") from None

    try:
        if 300 <= response.status < 400:
            raise FeedValidationError("Feed redirects are not supported.")
        if not 200 <= response.status < 300:
            raise FeedValidationError("The feed server returned an unsuccessful response.")

        content_encoding = response.getheader("content-encoding", "identity")
        if content_encoding and content_encoding.lower() != "identity":
            raise FeedValidationError("Compressed feed responses are not supported.")

        content_length = response.getheader("content-length")
        if content_length is not None:
            try:
                if int(content_length) > MAX_RESPONSE_BYTES:
                    raise FeedValidationError("The feed response exceeds the size limit.")
            except ValueError:
                raise FeedValidationError("The feed server returned an invalid response.") from None

        body = bytearray()
        while True:
            remaining_time = deadline - now()
            if remaining_time <= 0:
                raise FeedValidationError("The feed request timed out.")
            if connection is not None and getattr(connection, "sock", None) is not None:
                connection.sock.settimeout(remaining_time)
            chunk = response.read(min(READ_CHUNK_SIZE, MAX_RESPONSE_BYTES + 1 - len(body)))
            if not chunk:
                break
            body.extend(chunk)
            if len(body) > MAX_RESPONSE_BYTES:
                raise FeedValidationError("The feed response exceeds the size limit.")

        if now() >= deadline:
            raise FeedValidationError("The feed request timed out.")
        try:
            SafeElementTree.fromstring(
                bytes(body),
                forbid_dtd=True,
                forbid_entities=True,
                forbid_external=True,
            )
        except (DefusedXmlException, ParseError, ValueError):
            raise FeedValidationError(
                "The address does not contain a valid RSS or Atom feed."
            ) from None
        parsed_feed = feedparser.parse(bytes(body))
        if (
            getattr(parsed_feed, "bozo", False)
            or not parsed_feed.version
            or not parsed_feed.version.startswith(("rss", "atom"))
        ):
            raise FeedValidationError("The address does not contain a valid RSS or Atom feed.")

        title = parsed_feed.feed.get("title")
        if not isinstance(title, str):
            title = None
        return ValidatedFeed(title=title[:300] if title else None)
    except (OSError, socket.timeout, TimeoutError):
        raise FeedValidationError("The feed request timed out.") from None
    except http.client.HTTPException:
        raise FeedValidationError("The feed server returned an invalid response.") from None
    finally:
        if connection is not None:
            connection.close()


def _parse_feed_url(feed_url: str) -> SplitResult:
    if not isinstance(feed_url, str) or not feed_url.strip():
        raise FeedValidationError("Enter a feed address.")
    trimmed_url = feed_url.strip()
    if any(
        character.isspace() or ord(character) < 32 or ord(character) == 127
        for character in trimmed_url
    ):
        raise FeedValidationError("The feed address is invalid.")
    try:
        parsed_url = urlsplit(trimmed_url)
        hostname = parsed_url.hostname
        port = parsed_url.port
    except ValueError:
        raise FeedValidationError("The feed address is invalid.") from None

    if (
        parsed_url.scheme.lower() not in ("http", "https")
        or not hostname
        or "%" in hostname
        or parsed_url.username is not None
        or parsed_url.password is not None
        or (port is not None and port != (443 if parsed_url.scheme.lower() == "https" else 80))
    ):
        raise FeedValidationError(
            "Use an HTTP or HTTPS feed address on its default port, without credentials."
        )
    try:
        ascii_hostname = hostname.encode("idna").decode("ascii").lower()
    except UnicodeError:
        raise FeedValidationError("The feed address is invalid.") from None
    if not ascii_hostname:
        raise FeedValidationError("The feed address is invalid.")

    netloc = f"[{ascii_hostname}]" if ":" in ascii_hostname else ascii_hostname
    path = parsed_url.path or "/"
    return SplitResult(
        scheme=parsed_url.scheme.lower(),
        netloc=netloc,
        path=path,
        query=parsed_url.query,
        fragment="",
    )


def _resolve_with_deadline(
    resolver: Resolver,
    hostname: str,
    port: int,
    deadline: float,
    clock: Callable[[], float],
) -> list[tuple]:
    remaining = deadline - clock()
    if remaining <= 0:
        raise TimeoutError
    if not _DNS_LOOKUP_SLOTS.acquire(blocking=False):
        raise TimeoutError

    completed = threading.Event()
    result: list[tuple] = []
    errors: list[Exception] = []

    def resolve_in_background() -> None:
        try:
            result.extend(
                resolver(hostname, port, type=socket.SOCK_STREAM)
            )
        except Exception as error:
            errors.append(error)
        finally:
            _DNS_LOOKUP_SLOTS.release()
            completed.set()

    threading.Thread(target=resolve_in_background, daemon=True).start()
    if not completed.wait(remaining):
        raise TimeoutError
    if errors:
        raise errors[0]
    return result


def _is_public_address(address_info: tuple) -> bool:
    family, _, _, _, sockaddr = address_info
    try:
        address = ipaddress.ip_address(sockaddr[0].split("%", 1)[0])
    except (ValueError, AttributeError, IndexError):
        return False
    if family == socket.AF_INET6 and len(sockaddr) > 3 and sockaddr[3] != 0:
        return False
    if family == socket.AF_INET and address.version != 4:
        return False
    if family == socket.AF_INET6 and address.version != 6:
        return False
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped is not None:
        address = address.ipv4_mapped
    return address.is_global and not address.is_multicast and family in (
        socket.AF_INET,
        socket.AF_INET6,
    )


def _open_pinned_response(
    parsed_url: SplitResult,
    address_info: tuple,
    deadline: float,
) -> tuple[http.client.HTTPResponse, object]:
    family, socktype, proto, _, sockaddr = address_info
    host = parsed_url.hostname
    port = parsed_url.port or (443 if parsed_url.scheme == "https" else 80)
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise socket.timeout("request deadline exceeded")

    raw_socket = socket.socket(family, socktype, proto)
    raw_socket.settimeout(remaining)
    connection = None
    try:
        raw_socket.connect(sockaddr)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise socket.timeout("request deadline exceeded")
        raw_socket.settimeout(remaining)
        if parsed_url.scheme == "https":
            tls_socket = ssl.create_default_context().wrap_socket(
                raw_socket,
                server_hostname=host,
            )
            raw_socket = tls_socket
        if parsed_url.scheme == "https":
            connection = http.client.HTTPSConnection(host, port, timeout=remaining)
        else:
            connection = http.client.HTTPConnection(host, port, timeout=remaining)
        connection.sock = raw_socket
        raw_socket = None
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            connection.close()
            raise socket.timeout("request deadline exceeded")
        if connection.sock is not None:
            connection.sock.settimeout(remaining)
        path = urlunsplit(
            (
                "",
                "",
                quote(parsed_url.path or "/", safe="/%:@!$&'()*+,;=-._~"),
                quote(parsed_url.query, safe="/?%:@!$&'()*+,;=-._~"),
                "",
            )
        )
        connection.request(
            "GET",
            path,
            headers={
                "Host": parsed_url.netloc,
                "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml",
                "Accept-Encoding": "identity",
                "Connection": "close",
                "User-Agent": "MVP-RSS-Reader/0.1",
            },
        )
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            connection.close()
            raise socket.timeout("request deadline exceeded")
        if connection.sock is not None:
            connection.sock.settimeout(remaining)
        return connection.getresponse(), connection
    except Exception:
        if connection is not None:
            connection.close()
        elif raw_socket is not None:
            raw_socket.close()
        raise
