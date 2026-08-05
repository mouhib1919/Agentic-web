---
category: security
criterion: x_frame_options
severity: high
related:
  - csp
---

# X-Frame-Options (Clickjacking Protection)

## Definition

`X-Frame-Options` is an HTTP response header (IETF RFC 7034, Informational) controlling whether a page may be rendered inside a frame/iframe on another page, providing browser-enforced defense against clickjacking attacks.

## Technical Background

The header supports `DENY` (never permit framing) or `SAMEORIGIN` (permit only same-origin framing); `ALLOW-FROM <origin>` exists in the specification but is not reliably implemented across modern browsers. The specification itself notes the header is considered obsolete in favor of CSP's `frame-ancestors` directive, though it remains widely deployed for backward compatibility.

## Importance for AI Agent Readiness

An agent operating on a user's behalf, or rendering a page for a human user through an embedded view, should be able to trust that the page is not designed to be invisibly framed and hijacked. This is a low-effort, high-impact control whose absence signals a basic gap in browser-security hardening.

## ARAS Evaluation Context

ARAS checks: `X-Frame-Options` header presence in `evidence.headers` (case-insensitive lookup).

Passed when: the header is present (any value).

Failure condition: the header is absent.

Failure message: "Missing X-Frame-Options header."

## Common Issues

- Header entirely absent, leaving no clickjacking protection via this mechanism.
- `ALLOW-FROM` used for multi-origin allowance, which is not reliably honored by modern browsers.
- Header present but CSP's `frame-ancestors` absent, meaning protection relies entirely on this single, less flexible header.

## Impact

- **Technical impact**: the page can be embedded in an attacker-controlled frame with no browser-level restriction.
- **AI agent impact**: reduces confidence that a page is not designed to be overlaid or disguised for clickjacking, a factor relevant when an agent renders or interacts with the page on a user's behalf.
- **Security impact**: high — this is a low-effort, well-understood control against a well-understood attack class.

## Recommendation Strategy

Protect against clickjacking by adding the X-Frame-Options header, set to `DENY` unless legitimate same-origin framing is required, in which case use `SAMEORIGIN`; pair with CSP's `frame-ancestors` for more flexible multi-origin control where needed.

## Implementation Guidance

- **Nginx**: `add_header X-Frame-Options "SAMEORIGIN" always;`
- **Apache**: `Header always set X-Frame-Options "SAMEORIGIN"`
- **Express / Node.js**: `helmet` sets a sensible default automatically (`frameguard` module).
- **Cloudflare**: can be injected at the edge via Transform Rules if not set at the origin.

## Validation Checklist

- `X-Frame-Options` header present with `DENY` or `SAMEORIGIN`.
- If multi-origin framing is legitimately required, CSP `frame-ancestors` is used instead of/alongside this header.
- No reliance on the non-functional `ALLOW-FROM` value.

## Related ARAS Criteria

- `csp` — `frame-ancestors` is the modern, more capable superset of this header's protection.

## References

Source: official_sources/security/x_frame_options_reference.md
