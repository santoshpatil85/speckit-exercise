# Implementation Plan: MVP RSS Reader

**Branch**: `001-mvp-rss-reader` | **Date**: 2026-11-05 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/001-mvp-rss-reader/spec.md`

## Summary

Deliver a local, single-user web application for adding RSS or Atom feed subscriptions and
reviewing the saved list. Use server-rendered pages, a small server-side feed validation
component, and local SQLite persistence. The server retrieves and validates a bounded feed
response before saving it; it does not fetch feeds in browser code. Bind only to loopback
because the MVP has no authentication.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: Flask for server-rendered web pages; feedparser for RSS/Atom
parsing; defusedxml for rejecting DTD/entity declarations before feed parsing; pytest for tests

**Storage**: SQLite database on the local filesystem

**Testing**: pytest unit and integration tests, including feed validation, persistence, and
HTTP form flows

**Target Platform**: Local web browser and a single-user application process on the user's
computer

**Project Type**: Server-rendered web application

**Performance Goals**: Render the local subscription list in under 1 second for the MVP's
expected small list. Bound a feed validation request to a 10-second total deadline.

**Constraints**: Bind to loopback only; allow only HTTP and HTTPS feed URLs using default
ports; reject non-public destination addresses; do not follow redirects automatically; enforce
connect/read timeouts and a 1 MiB response-body limit; do not save until a valid RSS or Atom
document is confirmed; preserve subscriptions across process restarts.

**Scale/Scope**: One local reader and a small list of subscriptions. No accounts, feed-item
storage or display, background refresh, subscription editing or removal, public hosting, or
cross-device synchronization.

The referenced `StakeholderDocuments/ProjectGoals.md` and `StakeholderDocuments/TechStack.md`
were not present. The stack and local-only deployment above are explicit planning assumptions,
selected to fit the web target and MVP scope; confirm before implementation if project-specific
technology constraints become available.

## Constitution Check

### Pre-Design Gate

- **Security and Privacy**: Pass. Treat feed URLs and XML as untrusted; keep retrieval on the
  server, restrict destinations, bound requests, avoid redirects, and bind the unauthenticated
  app to loopback.
- **Maintainable Architecture**: Pass. Keep the web routes, feed validation, and subscription
  persistence in focused modules.
- **Verifiable Quality**: Pass. Plan unit and integration coverage for successful, malformed,
  unsafe, duplicate, and persistence cases.
- **Reliable Feed Processing**: Pass. Reject invalid or unavailable feeds before persistence
  and show a useful error without claiming success.
- **Simplicity and Consistency**: Pass with a documented stack assumption. Flask, SQLite, and
  one feed parsing dependency support a small server-rendered application without extra
  services or a client-side framework.

No gate violations identified.

## Project Structure

### Documentation (this feature)

```text
specs/001-mvp-rss-reader/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── subscriptions-web.md
└── tasks.md
```

### Source Code (repository root)

```text
pyproject.toml
src/
└── rss_reader/
    ├── __init__.py
    ├── __main__.py
    ├── app.py
    ├── feed_validation.py
    ├── storage.py
    ├── subscriptions.py
    ├── templates/
    │   └── index.html
    └── static/
        └── style.css
tests/
├── unit/
│   ├── test_feed_validation.py
│   └── test_subscriptions.py
└── integration/
    ├── test_web.py
    └── test_storage.py
```

**Structure Decision**: Use one Python application package with server-rendered pages.
Routes coordinate input/output, feed validation handles remote retrieval and parsing, and
storage owns SQLite persistence. Keep templates and styles with the package. This is sufficient
for one local web application; separate frontend/backend projects or a public API would add
unnecessary complexity.

## Design Decisions

- Validate feeds server-side to avoid dependence on each publisher's browser CORS policy.
- Restrict the app to local use and the fetcher to public HTTP(S) destinations. Resolve and
  validate DNS addresses, pin the vetted address for the connection, and reject unsafe
  redirect destinations by disabling automatic redirects.
- Parse only bounded response bytes; reject DTD and entity declarations before parsing, and
  store a subscription only after HTTP and RSS/Atom validation succeeds.
- Normalize surrounding whitespace and URL scheme/host case for duplicate comparison while
  retaining the submitted address for display. Do not rewrite path or query semantics.
- Store only subscription identity, address, optional feed title, and creation time. Do not
  persist feed item content.

## Post-Design Constitution Check

- **Security and Privacy**: Pass. The fetch contract keeps the unauthenticated server local,
  restricts network destinations, pins validated DNS results, prohibits automatic redirects,
  and bounds time and response size.
- **Maintainable Architecture**: Pass. The design separates routes, fetch/parse validation,
  and persistence with a small set of explicit entities and interfaces.
- **Verifiable Quality**: Pass. Validation scenarios and expected outcomes are defined in
  [quickstart.md](./quickstart.md); unit and integration coverage is included in the proposed
  structure.
- **Reliable Feed Processing**: Pass. Network, status, parsing, and duplicate failures are
  explicit and cannot produce a success-shaped saved subscription.
- **Simplicity and Consistency**: Pass. The design uses a single process, one local database,
  server-rendered HTML, and a focused parsing dependency; no production infrastructure is
  introduced.

No gate violations identified.

## Complexity Tracking

No constitution violations or additional projects require justification.
