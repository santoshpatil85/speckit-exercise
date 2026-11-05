from __future__ import annotations

import pytest

from rss_reader.feed_validation import ValidatedFeed
from rss_reader.storage import initialize_database, list_subscriptions
from rss_reader.subscriptions import (
    DuplicateSubscriptionError,
    SubscriptionService,
)


def test_adds_and_persists_valid_subscription(tmp_path):
    database = tmp_path / "subscriptions.sqlite3"
    initialize_database(database)
    service = SubscriptionService(
        database,
        feed_validator=lambda url: ValidatedFeed(title="Test feed"),
    )

    saved = service.add("  https://Example.com/RSS  ")

    assert saved.feed_url == "https://Example.com/RSS"
    assert saved.normalized_url == "https://example.com/RSS"
    assert saved.title == "Test feed"
    assert len(list_subscriptions(database)) == 1


def test_normalized_duplicate_is_rejected_without_second_validation(tmp_path):
    database = tmp_path / "subscriptions.sqlite3"
    initialize_database(database)
    validations = []

    def validator(url):
        validations.append(url)
        return ValidatedFeed(title=None)

    service = SubscriptionService(database, feed_validator=validator)
    service.add("https://Example.com/rss")

    with pytest.raises(DuplicateSubscriptionError):
        service.add("  HTTPS://example.COM/rss  ")

    assert validations == ["https://Example.com/rss"]
    assert len(list_subscriptions(database)) == 1


def test_does_not_save_when_validation_fails(tmp_path):
    database = tmp_path / "subscriptions.sqlite3"
    initialize_database(database)

    def reject(url):
        raise ValueError("unavailable")

    service = SubscriptionService(database, feed_validator=reject)
    with pytest.raises(ValueError):
        service.add("https://example.com/rss")
    assert list_subscriptions(database) == []
