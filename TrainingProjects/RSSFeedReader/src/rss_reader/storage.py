"""SQLite persistence for feed subscriptions."""

from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class FeedSubscription:
    id: str
    feed_url: str
    normalized_url: str
    title: str | None
    created_at: str


def initialize_database(database_path: str | Path) -> None:
    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS feed_subscriptions (
                id TEXT PRIMARY KEY,
                feed_url TEXT NOT NULL,
                normalized_url TEXT NOT NULL UNIQUE,
                title TEXT,
                created_at TEXT NOT NULL
            )
            """
        )


def get_subscription(database_path: str | Path, normalized_url: str) -> FeedSubscription | None:
    with sqlite3.connect(database_path) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            """
            SELECT id, feed_url, normalized_url, title, created_at
            FROM feed_subscriptions
            WHERE normalized_url = ?
            """,
            (normalized_url,),
        ).fetchone()
    return _subscription_from_row(row) if row is not None else None


def create_subscription(
    database_path: str | Path,
    feed_url: str,
    normalized_url: str,
    title: str | None,
) -> FeedSubscription:
    trimmed_url = feed_url.strip()
    created_at = datetime.now(timezone.utc).isoformat()
    subscription = FeedSubscription(
        id=str(uuid.uuid4()),
        feed_url=trimmed_url,
        normalized_url=normalized_url,
        title=title,
        created_at=created_at,
    )
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            INSERT INTO feed_subscriptions
                (id, feed_url, normalized_url, title, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                subscription.id,
                subscription.feed_url,
                subscription.normalized_url,
                subscription.title,
                subscription.created_at,
            ),
        )
    return subscription


def list_subscriptions(database_path: str | Path) -> list[FeedSubscription]:
    with sqlite3.connect(database_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT id, feed_url, normalized_url, title, created_at
            FROM feed_subscriptions
            ORDER BY created_at, id
            """
        ).fetchall()
    return [_subscription_from_row(row) for row in rows]


def _subscription_from_row(row: sqlite3.Row) -> FeedSubscription:
    return FeedSubscription(
        id=row["id"],
        feed_url=row["feed_url"],
        normalized_url=row["normalized_url"],
        title=row["title"],
        created_at=row["created_at"],
    )
