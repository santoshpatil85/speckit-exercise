# Research: MVP RSS Reader

## Decision: Use a server-rendered local web application

**Decision**: Use a single-process Python web app with Flask-rendered HTML pages, a local
SQLite database, and a feed validation module. The app binds to loopback and is intended for
one local reader.

**Rationale**: The product is a small form-and-list workflow. Server-rendered pages avoid a
separate frontend and API. SQLite persists data on disk without a database service. A local-only
deployment is appropriate because accounts and access controls are outside the MVP.

**Alternatives considered**:

- A browser-only app would keep the UI simple but cannot reliably retrieve arbitrary feeds
  across origins because browser cross-origin reads depend on publisher CORS permissions.
- A public multi-user web service would require authentication, abuse controls, and stronger
  operational protections that exceed the specified MVP.

## Decision: Retrieve feeds on the server and validate before saving

**Decision**: Fetch the submitted URL in a narrowly scoped server-side component, pass a bounded
response body through a DTD/entity-rejecting XML preflight and feed parser, and save only after
a successful HTTP response and valid RSS/Atom parse.

**Rationale**: Browser CORS restrictions make direct client fetching unreliable. Keeping
retrieval separate from parsing and persistence gives the app a clear validation boundary.
`feedparser` supports RSS/Atom and reports malformed documents through its `bozo` indicator.
`defusedxml` provides a separate preflight that rejects DTDs and entity declarations before
feed parsing. The parser's URL fetching and redirect behavior must not be used because the
application needs to apply network safety checks to every connection.

**Alternatives considered**:

- Trusting the feed URL without fetching would not meet FR-002.
- Hand-parsing XML would add complexity and risk around the RSS and Atom formats.
- Allowing the parser library to retrieve URLs would prevent reliable application control over
  redirect handling and destination checks.

## Decision: Apply strict network and parser bounds

**Decision**: Permit only HTTP and HTTPS on default ports; reject credentials and non-public
  destination addresses; validate all resolved addresses and pin a vetted address for the
  connection; disable automatic redirects; enforce a 10-second overall deadline and 1 MiB
  response-body limit; reject malformed/non-feed responses before saving.

**Rationale**: A user-provided feed address is an untrusted network input. These controls limit
  access to local/private services and bound resource use. If redirects are ever required, each
  hop would need the same URL and address validation; redirects are not needed for this MVP.
  XML parser safety depends on its runtime/parser version, so use a maintained parser and
  retain response-size limits.

**Alternatives considered**:

- Default HTTP client redirect and DNS behavior risks bypassing destination checks.
- Allowing arbitrary IP ranges or ports increases exposure without contributing to the stated
  subscription use case.
- Unbounded download or parser input risks unnecessary resource consumption.

## Decision: Store minimal subscription metadata in SQLite

**Decision**: Persist subscription ID, submitted feed URL, normalized comparison URL,
optional title, and creation timestamp in a local SQLite database. Enforce uniqueness on the
normalized comparison value.

**Rationale**: Local durable storage meets restart persistence without accounts or external
services. A normalized comparison key handles surrounding whitespace and URL host/scheme case
while preserving the user-entered address for display.

**Alternatives considered**:

- In-memory storage fails the restart requirement.
- A remote database adds deployment and account complexity outside MVP scope.
- Storing feed items is unnecessary because the MVP only adds and reviews subscriptions.

## Decision: Use Python, Flask, and feedparser as the assumed stack

**Decision**: Plan for Python 3.11+, Flask, feedparser, SQLite via Python's standard library,
and pytest.

**Rationale**: This stack supports a small server-rendered app and established RSS/Atom parsing
without a separate frontend or database service. Python's standard library provides SQLite
access and IP address classification utilities. This is a planning choice, not a repository
constraint: the referenced TechStack document and application source were not present.

**Alternatives considered**:

- Go with `net/http`, an RSS/Atom parser, and a SQLite driver is reasonable but not simpler in
  the absence of an existing Go codebase.
- Node with a web framework, XML/feed parser, and SQLite package is also viable but has no
  established project convention to favor it.

## Sources

- [Flask Quickstart](https://flask.palletsprojects.com/en/stable/quickstart/)
- [Python sqlite3](https://docs.python.org/3/library/sqlite3.html)
- [Python ipaddress](https://docs.python.org/3/library/ipaddress.html)
- [Python XML vulnerabilities](https://docs.python.org/3/library/xml.html#xml-vulnerabilities)
- [feedparser documentation](https://feedparser.readthedocs.io/en/latest/)
- [feedparser bozo detection](https://feedparser.readthedocs.io/en/latest/bozo/)
- [feedparser HTTP redirects](https://feedparser.readthedocs.io/en/latest/http-redirect/)
- [MDN CORS guide](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/CORS)
- [OWASP SSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html)
