from rss_reader.storage import (
    create_subscription,
    initialize_database,
    list_subscriptions,
)


def test_subscriptions_survive_database_reinitialization(tmp_path):
    database = tmp_path / "subscriptions.sqlite3"
    initialize_database(database)
    create_subscription(
        database,
        "https://example.com/feed",
        "https://example.com/feed",
        "Example",
    )

    initialize_database(database)

    subscriptions = list_subscriptions(database)
    assert len(subscriptions) == 1
    assert subscriptions[0].feed_url == "https://example.com/feed"
    assert subscriptions[0].title == "Example"
