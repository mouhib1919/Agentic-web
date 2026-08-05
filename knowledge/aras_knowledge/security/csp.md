---
category: security
criterion: csp
severity: high
related:
  - x_frame_options
  - mime_xss
---

# Content Security Policy (CSP)

## Definition

Content Security Policy is a browser-enforced HTTP response header (W3C CSP Level 3) letting a site declare an allowlist of sources from which scripts, styles, images, and other resources may load and execute, providing the primary browser-native defense against content-injection attacks, most notably cross-site scripting (XSS).

## Technical Background

A policy is composed of directives (`default-src`, `script-src`, `frame-ancestors`, etc.), each with a source-list value using origins, keywords (`'self'`, `'unsafe-inline'`), or nonces/hashes. `Content-Security-Policy` enforces; `Content-Security-Policy-Report-Only` evaluates without blocking, commonly used during rollout.

## Importance for AI Agent Readiness

CSP protects the integrity of the content an agent retrieves and acts upon. Without it, a page is more vulnerable to script injection, which could alter the content an agent reads, redirect it to malicious endpoints, or exfiltrate data submitted through any forms the agent interacts with on a user's behalf.

## ARAS Evaluation Context

ARAS checks: `Content-Security-Policy` header presence in `evidence.headers` (case-insensitive lookup).

Passed when: the header is present.

Failure condition: the header is absent.

Failure message: "Missing Content-Security-Policy header."

## Common Issues

- Header entirely absent, leaving no browser-enforced defense against injection.
- Present but overly permissive (`default-src *`, or heavy reliance on `'unsafe-inline'`), providing little real protection.
- Deployed directly in enforcing mode without first validating via `Content-Security-Policy-Report-Only`, risking breakage of legitimate functionality.
- Missing `frame-ancestors`, leaving clickjacking protection dependent solely on the separate `X-Frame-Options` header.

## Impact

- **Technical impact**: no browser-enforced barrier exists between an injected script and full page/DOM access.
- **AI agent impact**: content integrity cannot be assumed; an agent's understanding of the page, or actions it takes based on page content, could be manipulated by injected content the site itself did not intend to serve.
- **Security impact**: high — CSP substantially reduces the practical impact of XSS vulnerabilities even when input-sanitization defenses elsewhere fail.

## Recommendation Strategy

Configure a Content Security Policy: start from a restrictive `default-src 'self'` baseline, add narrowly scoped allowances for required third-party origins, and roll out via report-only mode before enforcing.

## Implementation Guidance

- **Nginx**: `add_header Content-Security-Policy "default-src 'self'; script-src 'self'; object-src 'none';" always;`
- **Express / Node.js**: use the `helmet` middleware's `contentSecurityPolicy()` module for structured directive configuration.
- **FastAPI**: set the header via middleware on every response.
- **Cloudflare**: can inject or modify response headers at the edge via Transform Rules if origin-level changes are constrained.

## Validation Checklist

- `Content-Security-Policy` header present with a restrictive `default-src`.
- No unnecessary `'unsafe-inline'`/`'unsafe-eval'` in `script-src`.
- `frame-ancestors` set to control embedding, complementing or replacing `X-Frame-Options`.
- Policy validated in report-only mode before full enforcement; violation reports monitored via `report-to`.

## Related ARAS Criteria

- `x_frame_options` — CSP's `frame-ancestors` directive is the modern superset of this older header's protection.
- `mime_xss` — a complementary, narrower browser-security header evaluated separately.

## References

Source: official_sources/security/csp_reference.md
