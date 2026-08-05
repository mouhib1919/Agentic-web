---
category: security
criterion: hsts
severity: high
related:
  - https
---

# HTTP Strict Transport Security (HSTS)

## Definition

HSTS is a response header (IETF RFC 6797) instructing browsers to interact with a host only over HTTPS for a specified duration, eliminating the possibility of the browser making a subsequent plain-HTTP request to that host once the policy has been received.

## Technical Background

The `Strict-Transport-Security` header carries a required `max-age` (seconds), and optional `includeSubDomains` and `preload` directives. It is only meaningful, and must only be honored, when received over an already-secure HTTPS connection — it has no effect if sent over plain HTTP.

## Importance for AI Agent Readiness

HTTPS alone leaves a residual gap: the very first connection a client makes to a host (before it has ever seen the HSTS header) can still be intercepted or downgraded. HSTS closes this gap for any client that has previously connected, ensuring an agent's repeated interactions with a site remain protected even if a single request were to attempt a plain-HTTP fallback.

## ARAS Evaluation Context

ARAS checks: `Strict-Transport-Security` header presence in `evidence.headers` (case-insensitive lookup).

Passed when: the header is present.

Failure condition: the header is absent.

Failure message: "No HSTS header detected."

## Common Issues

- Header entirely absent despite the site being served correctly over HTTPS.
- `max-age` set too low to provide meaningful protection duration.
- `includeSubDomains` omitted, leaving subdomains outside the policy's protection.
- Header present but the site itself still allows an unredirected plain-HTTP fallback.

## Impact

- **Technical impact**: browsers have no cached instruction to require HTTPS for this host, other than what a same-session redirect provides.
- **AI agent impact**: an automated client's first (or any subsequent, unprimed) request to the domain remains exposed to interception/downgrade risk that HSTS specifically exists to close.
- **Security impact**: high — this is one of the most effective, lowest-cost mitigations against man-in-the-middle and SSL-stripping attacks.

## Recommendation Strategy

Enable Strict-Transport-Security: add the header on every HTTPS response with a long `max-age` (commonly one year), `includeSubDomains` once subdomain HTTPS coverage is confirmed, and consider preload submission once the configuration is stable.

## Implementation Guidance

- **Nginx**: `add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;`
- **Apache**: `Header always set Strict-Transport-Security "max-age=31536000; includeSubDomains"`
- **Express / Node.js**: use the `helmet` middleware's `hsts()` module, or set the header directly.
- **Cloudflare**: enable HSTS in the SSL/TLS > Edge Certificates dashboard section, which sets the header at the edge.

## Validation Checklist

- `Strict-Transport-Security` header present on HTTPS responses with a parseable `max-age`.
- `max-age` value is at least several months (commonly one year: `31536000`).
- `includeSubDomains` present only if every subdomain genuinely supports HTTPS.
- Preload submission considered only after long-term HTTPS commitment is confirmed, given its slow reversibility.

## Related ARAS Criteria

- `https` — the prerequisite this header enforces exclusive use of.

## References

Source: official_sources/security/hsts_reference.md
