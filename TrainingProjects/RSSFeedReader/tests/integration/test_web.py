from __future__ import annotations

import pytest

from rss_reader.app import create_app
from rss_reader.feed_validation import FeedValidationError, ValidatedFeed
from rss_reader.storage import list_subscriptions


@pytest.fixture
def app(tmp_path):
    application = create_app(
        {
            "TESTING": True,
            "DATABASE": str(tmp_path / "subscriptions.sqlite3"),
        }
    )
    return application


def test_accepts_rss_atom_and_shows_subscription(app):
    app.config["FEED_VALIDATOR"] = lambda url: ValidatedFeed(title="Example feed")
    client = app.test_client()

    response = client.post(
        "/subscriptions", data={"feed_url": "https://example.com/rss"}
    )

    assert response.status_code == 303
    page = client.get(response.headers["Location"])
    assert b"https://example.com/rss" in page.data
    assert b"Example feed" in page.data
    assert len(list_subscriptions(app.config["DATABASE"])) == 1


@pytest.mark.parametrize(
    "url",
    [
        "",
        "not a url",
        "http://127.0.0.1/private",
        "https://example.com/unavailable",
        "https://example.com/malformed",
        "https://example.com/oversized",
    ],
)
def test_rejected_feed_is_not_saved_and_returns_clear_result(app, url):
    def validator(value):
        raise FeedValidationError("The feed address could not be added.")

    app.config["FEED_VALIDATOR"] = validator
    client = app.test_client()

    response = client.post("/subscriptions", data={"feed_url": url})

    assert response.status_code == 200
    assert b'role="alert"' in response.data
    assert list_subscriptions(app.config["DATABASE"]) == []


def test_duplicate_is_reported_without_second_row(app):
    app.config["FEED_VALIDATOR"] = lambda url: ValidatedFeed(title="Feed")
    client = app.test_client()
    client.post("/subscriptions", data={"feed_url": "https://example.com/rss"})

    response = client.post(
        "/subscriptions", data={"feed_url": " HTTPS://EXAMPLE.COM/rss "}
    )

    assert response.status_code == 200
    assert b"already subscribed" in response.data
    assert len(list_subscriptions(app.config["DATABASE"])) == 1


def test_empty_state_is_clear_and_remains_after_app_reopen(app, tmp_path):
    first_client = app.test_client()
    empty_page = first_client.get("/")
    assert b"No feeds have been added yet." in empty_page.data

    app.config["FEED_VALIDATOR"] = lambda url: ValidatedFeed(title="Reopened")
    first_client.post(
        "/subscriptions", data={"feed_url": "https://example.com/feed"}
    )

    reopened_app = create_app(
        {
            "TESTING": True,
            "DATABASE": app.config["DATABASE"],
        }
    )
    reopened_page = reopened_app.test_client().get("/")
    assert b"https://example.com/feed" in reopened_page.data
    assert b"Reopened" in reopened_page.data


def test_feed_title_is_rendered_as_text(app):
    app.config["FEED_VALIDATOR"] = lambda url: ValidatedFeed(
        title="<script>alert(1)</script>"
    )
    client = app.test_client()
    client.post("/subscriptions", data={"feed_url": "https://example.com/feed"})

    page = client.get("/")

    assert b"&lt;script&gt;alert(1)&lt;/script&gt;" in page.data
    assert b"<script>alert(1)</script>" not in page.data
