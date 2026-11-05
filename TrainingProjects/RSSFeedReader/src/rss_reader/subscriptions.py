"""Subscription validation and persistence orchestration."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from rss_reader.feed_validation import (
    FeedValidationError,
    ValidatedFeed,
    validate_feed,
)
from rss_reader.storage import (
    FeedSubscription,
    create_subscription,
    get_subscription,
)


class DuplicateSubscriptionError(Exception):
    """Raised when a normalized feed URL is already subscribed."""


class SubscriptionService:
    def __init__(self, database_path: str | Path, feed_validator=validate_feed):
        self.database_path = database_path
        self.feed_validator = feed_validator

    def add(self, feed_url: str) -> FeedSubscription:
        normalized_url = normalize_feed_url(feed_url)
        trimmed_url = feed_url.strip()
        if get_subscription(self.database_path, normalized_url) is not None:
            raise DuplicateSubscriptionError("This feed is already subscribed.")

        validated_feed: ValidatedFeed = self.feed_validator(trimmed_url)
        try:
            return create_subscription(
                self.database_path,
                trimmed_url,
                normalized_url,
                validated_feed.title,
            )
        except sqlite3.IntegrityError:
            if get_subscription(self.database_path, normalized_url) is not None:
                raise DuplicateSubscriptionError(
                    "This feed is already subscribed."
                ) from None
            raise


def normalize_feed_url(feed_url: str) -> str:
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
    scheme = parsed_url.scheme.lower()
    if (
        scheme not in ("http", "https")
        or not hostname
        or "%" in hostname
        or parsed_url.username is not None
        or parsed_url.password is not None
        or (port is not None and port != (443 if scheme == "https" else 80))
    ):
        raise FeedValidationError("The feed address is invalid.")
    try:
        normalized_host = hostname.encode("idna").decode("ascii").lower()
    except UnicodeError:
        raise FeedValidationError("The feed address is invalid.") from None
    if ":" in normalized_host:
        normalized_host = f"[{normalized_host}]"
    netloc = normalized_host
    path = parsed_url.path or "/"
    return urlunsplit(
        (scheme, netloc, path, parsed_url.query, "")
    )
