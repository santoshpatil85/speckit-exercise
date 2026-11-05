# Web Contract: Feed Subscriptions

The application is a local, server-rendered web interface. All pages are same-origin. The
server listens on loopback only; it has no public API or account endpoints.

## `GET /`

Return the subscription page containing:

- A form with a required feed address field and an action to add the subscription.
- The saved subscriptions, each identified by its submitted feed address and optional title.
- An explicit empty state when there are no saved subscriptions.
- A user-readable validation result after an add attempt.

## `POST /subscriptions`

Accept a form submission with one feed address.

### Successful addition

- Validate and retrieve the feed before persistence.
- Save the subscription and redirect to `GET /` with a success result.
- Do not display or execute feed-provided markup; titles are escaped as text.

### Rejected addition

For blank/malformed/unsupported URLs, unsafe destinations, network errors, unsuccessful HTTP
responses, oversized responses, non-feed content, malformed RSS/Atom, or duplicate addresses:

- Do not create a subscription.
- Return to the subscription page with an actionable, non-sensitive message.
- For a duplicate, explain that the feed is already subscribed.

## Feed retrieval contract

- Only `http` and `https` schemes and default ports are accepted; URL credentials are rejected.
- Resolve the hostname and reject the destination if any resolved address is not globally
  reachable. Connect to a vetted resolved address while preserving the original host for the
  HTTP host header and TLS verification.
- Do not automatically follow redirects. Reject redirect responses.
- Use bounded connection/read timeouts and a 10-second overall deadline.
- Stream and cap the response at 1 MiB regardless of `Content-Length`; reject compressed
  responses that cannot be bounded safely.
- Parse the bounded response as RSS or Atom; only a valid parsed feed may be stored.

## Persistence and duplicate behavior

- Save subscriptions in local durable storage so they survive process restarts.
- Compare URLs after trimming surrounding whitespace and normalizing scheme and host case.
- Preserve the submitted address for display. Do not rewrite path or query semantics.
- A duplicate normalized address does not create a second entry.
