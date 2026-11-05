<!--
Sync Impact Report
Version change: unfilled scaffold -> 1.0.0
Modified principles:
- Unspecified principle slot 1 -> I. Security and Privacy
- Unspecified principle slot 2 -> II. Maintainable Architecture
- Unspecified principle slot 3 -> III. Verifiable Quality
- Unspecified principle slot 4 -> IV. Reliable Feed Processing
- Unspecified principle slot 5 -> V. Simplicity and Consistency
Added sections: Technology and Data Constraints; Engineering Workflow
Removed sections: None
Follow-up TODO: Confirm the original ratification date.
-->

# RSS Feed Reader Constitution

## Core Principles

### I. Security and Privacy
Treat feed URLs, metadata, and item content as untrusted input. Accept only supported URL
schemes, bound network requests with timeouts and response-size limits, disable DTD and
external-entity processing in XML parsers, and render feed content through context-safe APIs.
Collect, persist, log, and transmit only data needed for documented features; never expose
secrets in source code, logs, or user-facing errors. These controls limit exposure to malicious
feeds and protect user data.

### II. Maintainable Architecture
Keep retrieval, parsing, persistence, and presentation responsibilities clearly separated.
Use focused modules, descriptive names, and established project conventions; document
non-obvious decisions. Prefer changes that are straightforward to test and extend so future
work does not depend on fragile coupling or duplicated behavior.

### III. Verifiable Quality
Every behavior change MUST include or update automated tests at the appropriate level.
Tests for feed handling MUST cover valid input, malformed input, and relevant boundary or
failure cases. Run the applicable test suite and quality checks before delivery, and report
failures rather than hiding or weakening them. This makes regressions visible and supports
safe change.

### IV. Reliable Feed Processing
Feed retrieval and parsing MUST handle network failures, invalid or incomplete documents,
and unusable item data without presenting failures as successful results. A failure in one feed
MUST NOT prevent unrelated feeds from being processed when the architecture allows
independent processing. Surface actionable errors while avoiding disclosure of sensitive
implementation details.

### V. Simplicity and Consistency
Follow the project's documented technology stack and existing patterns. Prefer the smallest
clear implementation that meets requirements; new dependencies and abstractions MUST have
a documented need and a maintenance or security rationale. This keeps the application
understandable and avoids unnecessary operational risk.

## Technology and Data Constraints

Use the project's documented runtime, frameworks, and storage choices; do not silently
introduce a competing stack. When a feature requires a technology decision that the project
has not documented, record and review that decision as part of the feature design. Manage
dependencies through the project's package manager and lockfile where available, and review
new dependencies for maintenance status, security posture, and fit before adoption.

## Engineering Workflow

Define externally observable behavior and acceptance criteria before implementation. Bug fixes
MUST include a regression test when the behavior can be tested automatically. Before delivery,
run relevant automated tests and the project's available lint, type-check, and build checks.
Review changes for security, privacy, maintainability, and compatibility; document any
unavoidable validation gap and obtain maintainer approval before accepting it.

## Governance

This constitution governs project engineering decisions. Amendments MUST be proposed with
their rationale and impact, reviewed and approved by project maintainers, and reflected in the
constitution before the changed practice is treated as standard. Version the constitution using
semantic versioning: MAJOR for incompatible governance changes, MINOR for new principles or
material expansions, and PATCH for clarifications and non-semantic refinements. Every
implementation review MUST check applicable principles; any approved exception MUST state
its scope, rationale, and approver in the change record.

**Version**: 1.0.0 | **Ratified**: TODO(RATIFICATION_DATE): confirm original adoption date | **Last Amended**: 2026-11-05
