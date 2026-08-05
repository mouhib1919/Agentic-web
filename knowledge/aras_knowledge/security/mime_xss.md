---
category: security
criterion: mime_xss
severity: high
related:
  - csp
---

# MIME and XSS Protection Headers (X-Content-Type-Options, X-XSS-Protection)

## Definition

This criterion covers two browser-security headers: `X-Content-Type-Options`, which disables MIME-type sniffing, and `X-XSS-Protection`, a now largely deprecated header that formerly controlled browsers' built-in reflected-XSS filters.

## Technical Background

`X-Content-Type-Options: nosniff` (WHATWG Fetch Standard) instructs the browser to strictly honor the declared `Content-Type` rather than guessing via content inspection. `X-XSS-Protection` (never formally standardized) is now functionally inert in current Chromium, Firefox, and Safari, since the underlying filter has been removed from these engines; current guidance is to set it to `0` or omit it, relying on CSP instead for XSS mitigation.

## Importance for AI Agent Readiness

MIME-sniffing protection prevents a browser from reinterpreting an attacker-controlled upload as executable script or HTML, protecting the integrity of content an agent might retrieve or that flows through the site's upload/serving paths. This is one of the lowest-cost, no-downside security headers available.

## ARAS Evaluation Context

ARAS checks: `X-Content-Type-Options` and `X-XSS-Protection` header presence in `evidence.headers` (case-insensitive lookup), evaluated independently of `X-Frame-Options`.

Passed when: at least one of the two headers is present.

Failure condition: both are absent.

Failure message: "Missing MIME/XSS protection headers."

## Common Issues

- `X-Content-Type-Options: nosniff` entirely absent, leaving default browser MIME-sniffing behavior active.
- `X-XSS-Protection` set to a legacy-enabling value (`1; mode=block`) rather than the currently recommended `0`, reflecting outdated guidance without functional benefit.
- Neither header present at all, relying entirely on CSP (if present) for related protections.

## Impact

- **Technical impact**: the browser may reinterpret a resource's content type contrary to the server's declared `Content-Type`, under specific circumstances enabling content-type confusion issues.
- **AI agent impact**: reduces confidence that resources served by the site are interpreted exactly as declared, a narrow but real integrity concern for any automated content consumer.
- **Security impact**: high per ARAS's classification of this header pair as a low-effort, no-downside hardening measure, though `X-XSS-Protection` specifically no longer provides meaningful protection in modern browsers.

## Recommendation Strategy

Enable browser-side MIME type and XSS protections: add `X-Content-Type-Options: nosniff` universally, and set `X-XSS-Protection: 0` explicitly (relying on CSP for actual XSS mitigation) rather than leaving the legacy header unset or misconfigured.

## Implementation Guidance

- **Nginx**: `add_header X-Content-Type-Options "nosniff" always;`
- **Apache**: `Header always set X-Content-Type-Options "nosniff"`
- **Express / Node.js**: `helmet` sets `X-Content-Type-Options: nosniff` by default via its `noSniff` module.
- **Cloudflare**: can be added via Transform Rules if not set at the origin.

## Validation Checklist

- `X-Content-Type-Options: nosniff` present on all responses.
- `X-XSS-Protection`, if present, set to `0` per current guidance (not relied upon as a primary XSS defense).
- CSP present and treated as the primary XSS mitigation mechanism.

## Related ARAS Criteria

- `csp` — the comprehensive, modern replacement for browser-side XSS mitigation that `X-XSS-Protection` historically attempted.

## References

Source: official_sources/security/mime_xss_reference.md
