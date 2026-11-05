# Tasks: MVP RSS Reader

**Input**: Design documents from `specs/001-mvp-rss-reader/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Required by the project constitution; add acceptance-focused tests before each
story's implementation tasks.

**Organization**: Tasks are grouped by user story so each increment can be implemented and
validated against its independent test criteria.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Task can run in parallel with another task in its phase because it edits separate files and has no unfinished prerequisite.
- **[Story]**: User-story label corresponding to spec.md.
- Every task names the exact file or files to create, change, or validate.

## Phase 1: Setup

**Purpose**: Initialize the Python project and its minimal runtime/test dependencies.

- [X] T001 Configure Python 3.11+ project metadata, package discovery, and Flask, feedparser, defusedxml, and pytest dependencies in `pyproject.toml`.
- [X] T002 [P] Ignore the virtual environment, local SQLite database, and Python test/cache artifacts in `.gitignore`.

## Phase 2: Foundational

**Purpose**: Establish durable subscription storage and safe local application startup before
story work begins.

- [X] T003 Create SQLite initialization and subscription storage operations in `src/rss_reader/storage.py`; persist `id` as unique, `feed_url` after trimming surrounding whitespace, a unique `normalized_url` that trims whitespace and normalizes scheme/host case without changing path/query semantics, optional `title` as untrusted display text, and required `created_at` in UTC.
- [X] T004 [P] Create the app factory and configuration for an explicit persistent database path, loopback-only server startup, and package entry point in `src/rss_reader/app.py`, `src/rss_reader/__main__.py`, and `src/rss_reader/__init__.py`.

**Checkpoint**: Project setup and the shared local storage/startup foundation are ready.

## Phase 3: User Story 1 - Add a Feed Subscription (Priority: P1) 🎯 MVP

**Goal**: Let a reader add a valid RSS or Atom URL without an account; reject invalid or
unsafe addresses and duplicates; show an accepted subscription.

**Independent Test**: Submit a valid RSS or Atom feed and verify that it appears once in the
page; invalid, unsafe, unreachable, malformed, or duplicate submissions must not add another
entry and must show a clear result.

### Tests for User Story 1

- [X] T005 [P] [US1] Add feed validation unit tests for allowed schemes/default ports, credentials, DNS results containing private or reserved addresses, pinned destinations, redirects, deadlines, response-size limits, HTTP errors, RSS/Atom parsing, and malformed/non-feed content in `tests/unit/test_feed_validation.py`.
- [X] T006 [P] [US1] Add subscription service unit tests for valid-feed insertion, whitespace and scheme/host-case duplicate normalization, duplicate messaging, and no insert on validation failure in `tests/unit/test_subscriptions.py`.
- [X] T007 [P] [US1] Add web integration tests for submitting valid RSS/Atom and invalid, unavailable, unsafe, malformed, oversized, and duplicate addresses without real external network access in `tests/integration/test_web.py`.
- [X] T008 [US1] Run the new User Story 1 tests in `tests/unit/test_feed_validation.py`, `tests/unit/test_subscriptions.py`, and `tests/integration/test_web.py`; distinguish implementation failures from test setup errors.

### Implementation for User Story 1

- [X] T009 [US1] Implement bounded server-side retrieval and RSS/Atom validation in `src/rss_reader/feed_validation.py`: accept only HTTP(S) default ports without credentials; resolve and reject any non-public destination; connect to a vetted resolved address while preserving the original host for HTTP and TLS verification; disable redirects; enforce a 10-second total deadline and a 1 MiB streamed response cap; reject DTDs and entity declarations; parse response bytes rather than asking feedparser to fetch a URL; reject unsuccessful or malformed/non-feed responses.
- [X] T010 [US1] Implement subscription URL normalization, duplicate lookup before remote retrieval, feed validation, and persistence orchestration in `src/rss_reader/subscriptions.py`, using the storage operations in `src/rss_reader/storage.py`.
- [X] T011 [US1] Implement `POST /subscriptions` and the subscription-list `GET /` route in `src/rss_reader/app.py`; route valid submissions through the service, redirect after submission, and return clear non-sensitive validation or duplicate results without saving rejected feeds.
- [X] T012 [P] [US1] Create the server-rendered add form, visible result messages, and accepted subscription address rows in `src/rss_reader/templates/index.html`.
- [X] T013 [P] [US1] Add accessible, minimal form, list, and result-message styling in `src/rss_reader/static/style.css`.
- [X] T014 [US1] Run the focused User Story 1 unit and web integration tests in `tests/unit/test_feed_validation.py`, `tests/unit/test_subscriptions.py`, and `tests/integration/test_web.py`; correct failures before marking the story complete.

**Checkpoint**: User Story 1 is independently usable and demonstrable as the MVP.

## Phase 4: User Story 2 - Review Saved Subscriptions (Priority: P2)

**Goal**: Make the saved list and empty state clear and prove subscriptions survive an
application restart.

**Independent Test**: With no saved subscriptions, view the empty state; with saved test
subscriptions, verify each address and available title is shown, then restart the app and
verify the list remains.

### Tests for User Story 2

- [X] T015 [US2] Add integration coverage for the empty state, list addresses and optional titles, escaped feed-provided titles, and persistence after app/database reconnection in `tests/integration/test_web.py` and `tests/integration/test_storage.py`.
- [X] T016 [US2] Run the new User Story 2 tests in `tests/integration/test_web.py` and `tests/integration/test_storage.py`; confirm any failures identify missing list behavior rather than test setup errors.

### Implementation for User Story 2

- [X] T017 [US2] Complete saved-list rendering in `src/rss_reader/app.py` and `src/rss_reader/templates/index.html` so the empty state is explicit, each saved address is identifiable, optional titles are rendered only as escaped text, and the rows are loaded from persistent storage.
- [X] T018 [US2] Run the focused list and restart integration tests in `tests/integration/test_web.py` and `tests/integration/test_storage.py`; correct failures before marking the story complete.

**Checkpoint**: User Stories 1 and 2 work, including restart persistence and an explicit
first-run empty state.

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Verify the integrated MVP and keep its run/validation guide accurate.

- [X] T019 [P] Update `specs/001-mvp-rss-reader/quickstart.md` with the implemented local install/run commands, loopback address, and observed outcomes for valid feeds, rejection cases, duplicates, empty state, and restart persistence.
- [X] T020 Run the complete automated suite and the scenarios in `specs/001-mvp-rss-reader/quickstart.md`; verify the service binds only to loopback and that no validation failure creates a subscription.

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies; complete before the foundation.
- **Foundational (Phase 2)**: Depends on Setup; blocks both user stories.
- **User Story 1 (Phase 3)**: Depends on Foundational; delivers the MVP.
- **User Story 2 (Phase 4)**: Depends on Foundational and the basic subscription/list flow in User Story 1; extends the same list with empty-state, title, and restart verification.
- **Polish (Phase 5)**: Depends on the stories selected for delivery; T020 follows T019.

### User Story Dependencies

- **US1 (P1)**: Starts after Phase 2. It establishes accepted subscriptions and the basic list surface.
- **US2 (P2)**: Starts after US1 because it extends the same saved-list flow. Its independent test uses an empty database or pre-seeded subscriptions and does not require the remote feed service.

### Within Each User Story

- Write and run the story tests before implementation.
- Implement dependencies in order: feed validation, subscription service, routes, then view.
- Complete focused story tests before moving to the next story.

### Parallel Opportunities

- **Setup**: T002 can run alongside T001 after project conventions are agreed.
- **Foundational**: T003 and T004 edit separate files and can proceed in parallel after T001.
- **US1 tests**: T005, T006, and T007 cover separate test files and can be authored in parallel after Phase 2.
- **US1 presentation**: T011 and T012 edit separate template/style files and can proceed in parallel; both follow the view's expected data and form contract.
- **US2**: Once T014 is written, its web and storage test files are distinct, but T015 integrates the UI and storage behavior.
- **Polish**: T017 can proceed independently from non-overlapping final review work; T018 depends on the guide being current.

## Parallel Example: User Story 1

```text
After Phase 2:
  T005 -> tests/unit/test_feed_validation.py
  T006 -> tests/unit/test_subscriptions.py
  T007 -> tests/integration/test_web.py

After the tests are written:
  T009 -> src/rss_reader/feed_validation.py
  then T010 -> src/rss_reader/subscriptions.py
  then T011 -> src/rss_reader/app.py
  T012 -> src/rss_reader/templates/index.html (after the view contract is established)
  T013 -> src/rss_reader/static/style.css (can run alongside T012)
  then T014 -> run US1 tests
```

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Setup and Foundational tasks.
2. Complete User Story 1 tests and implementation.
3. Stop and validate with the User Story 1 test task and quickstart add/rejection scenarios.
4. Demonstrate the basic feed-subscription workflow before extending list review.

### Incremental Delivery

1. Setup + Foundational → application starts locally and SQLite is ready.
2. User Story 1 → add, validate, reject, deduplicate, and show a subscription; validate independently.
3. User Story 2 → complete the empty/list/restart experience; validate independently.
4. Polish → update quickstart and run the full suite.
