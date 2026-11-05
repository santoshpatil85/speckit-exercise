# Quickstart: MVP RSS Reader

This guide describes validation to run after implementation. The app is a local-only web
application; do not expose it on a public interface.

## Prerequisites

- Python 3.11 or newer
- A writable local directory for the SQLite database
- Network access to a valid public RSS or Atom feed for the success scenario

## Install and run

From the repository root:

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m rss_reader
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in a browser. The application binds only
to `127.0.0.1`; do not expose it on a public or all-interface address.

## End-to-end scenarios

1. **Add an RSS feed**: Submit a reachable public RSS feed URL. Expect a success result and one
   listed subscription.
2. **Add an Atom feed**: Submit a reachable public Atom feed URL. Expect the same successful
   behavior.
3. **Reject invalid content**: Submit a reachable URL returning HTML or malformed XML. Expect
   a clear error and no new list entry.
4. **Reject unsafe/unavailable addresses**: Try a malformed URL, loopback/private address,
   unreachable host, redirect response, and oversized response. Expect rejection and no entry.
5. **Prevent duplicates**: Submit the same feed again with surrounding whitespace and
   different host letter case. Expect a duplicate message and one list entry.
6. **Persist subscriptions**: Restart the app and reopen the page. Expect the accepted
   subscriptions to remain listed.
7. **Show the empty state**: Start with an empty database. Expect a message that no feeds have
   been added and a visible way to add one.

## Automated validation

```sh
python -m pytest
```

The automated suite covers the URL and response safety boundaries with mocked network
responses, so it does not require external network access. The complete user-facing contract is in
[contracts/subscriptions-web.md](./contracts/subscriptions-web.md); data validation is
described in [data-model.md](./data-model.md).
