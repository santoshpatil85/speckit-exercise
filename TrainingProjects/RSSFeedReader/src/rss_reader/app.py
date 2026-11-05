"""Flask application setup."""

from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, redirect, render_template, request, url_for

from rss_reader.feed_validation import FeedValidationError, validate_feed
from rss_reader.storage import initialize_database, list_subscriptions
from rss_reader.subscriptions import DuplicateSubscriptionError, SubscriptionService


def create_app(test_config: dict[str, object] | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    database_path = Path(
        os.environ.get(
            "RSS_READER_DATABASE",
            str(Path(app.instance_path) / "subscriptions.sqlite3"),
        )
    )
    app.config.from_mapping(DATABASE=str(database_path))
    if test_config:
        app.config.update(test_config)
    initialize_database(app.config["DATABASE"])

    @app.get("/")
    def index():
        status = request.args.get("status")
        message = "Feed subscription added." if status == "added" else None
        return render_template(
            "index.html",
            subscriptions=list_subscriptions(app.config["DATABASE"]),
            message=message,
            error=None,
        )

    @app.post("/subscriptions")
    def add_subscription():
        feed_url = request.form.get("feed_url", "")
        validator = app.config.get("FEED_VALIDATOR", validate_feed)
        service = SubscriptionService(
            app.config["DATABASE"],
            feed_validator=validator,
        )
        try:
            service.add(feed_url)
        except DuplicateSubscriptionError:
            return render_template(
                "index.html",
                subscriptions=list_subscriptions(app.config["DATABASE"]),
                message=None,
                error="This feed is already subscribed.",
            )
        except FeedValidationError as error:
            return render_template(
                "index.html",
                subscriptions=list_subscriptions(app.config["DATABASE"]),
                message=None,
                error=str(error),
            )
        return redirect(url_for("index", status="added"), code=303)

    return app
