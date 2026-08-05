# Content Security Policy (CSP)

## Overview

Content Security Policy is a browser-enforced security mechanism, delivered via an HTTP response header, that lets a website declare an allowlist of sources from which it permits content (scripts, styles, images, fonts, frames, and more) to be loaded and executed. It is the primary browser-native defense against content-injection vulnerabilities, most notably cross-site scripting (XSS).

## Official Definition

CSP is specified by the W3C Web Application Security Working Group. The current actively maintained edition is CSP Level 3, a W3C Working Draft that supersedes the W3C Recommendation-status CSP Level 2, extending it with additional directives and refined behaviors while remaining largely backward compatible.

## Core Concepts

- **Directives**: a policy is composed of semicolon-separated directives, each controlling a specific resource category (`script-src`, `style-src`, `img-src`, `connect-src`, `frame-ancestors`, and others) or behavior (`upgrade-insecure-requests`).
- **Source expressions**: each directive's value is a space-separated list of allowed sources, expressed as origins (`https://cdn.example.com`), keywords (`'self'`, `'none'`, `'unsafe-inline'`, `'unsafe-eval'`), or cryptographic values (nonces, hashes).
- **Fallback via `default-src`**: any resource-type directive not explicitly specified falls back to the value of `default-src`, making it the policy's baseline.
- **Enforcement vs. reporting mode**: `Content-Security-Policy` enforces the policy (blocking violations); `Content-Security-Policy-Report-Only` evaluates the same policy without blocking, only reporting violations, commonly used to validate a policy before enforcing it.

## Technical Details

- Header syntax: `Content-Security-Policy: default-src 'self'; script-src 'self' https://cdn.example.com; object-src 'none'`.
- Nonces: a per-response, cryptographically random value (`script-src 'nonce-<random>'`) that must match a corresponding `nonce` attribute on an inline `<script>` tag for that script to execute, allowing specific inline scripts without a blanket `'unsafe-inline'` allowance.
- Hashes: a directive can allowlist a specific inline script/style by its cryptographic hash (`'sha256-<base64hash>'`) rather than requiring it to be moved to an external file.
- `frame-ancestors`: controls which origins may embed the current page in a frame, functionally superseding the older `X-Frame-Options` header with more granular, list-based control.
- Violation reporting: the `report-to` directive (and the deprecated `report-uri`) specifies an endpoint to which the browser sends structured JSON violation reports when a policy (enforced or report-only) is breached.

## Detection Characteristics

- Presence of the `Content-Security-Policy` (or `Content-Security-Policy-Report-Only`) response header.
- Parsed directive set and their source-list contents, particularly whether `script-src`/`default-src` includes weakening keywords such as `'unsafe-inline'` or `'unsafe-eval'`, or an overly permissive wildcard (`*`).
- Presence of `frame-ancestors` as a modern alternative/complement to `X-Frame-Options`.
- Presence of reporting directives (`report-to`/`report-uri`) indicating active violation monitoring.

## Common Implementations

- Strict baseline (`default-src 'self'`) with narrowly scoped additional allowances for specific third-party origins (analytics, payment processors, CDNs).
- Nonce- or hash-based script allowlisting to eliminate `'unsafe-inline'` while still supporting necessary inline scripts (e.g., framework hydration payloads).
- Staged rollout using `Content-Security-Policy-Report-Only` in parallel with an existing enforced (often looser) policy, to validate a stricter policy's real-world impact before switching enforcement.

## Limitations

- A policy is only as strong as its most permissive directive; a single overlooked `'unsafe-inline'` or wildcard source can substantially undermine the protection of an otherwise strict policy.
- CSP mitigates the impact of injection vulnerabilities but does not prevent the underlying vulnerability (e.g., unsanitized user input) from existing in application code.
- Legacy browser support for advanced CSP Level 3 features (strict-dynamic, hash-based allowlisting for specific directive types) is inconsistent, requiring careful fallback design for broad compatibility.

## Related Technologies

- `X-Frame-Options` (an older, single-purpose header for clickjacking protection, partially superseded by CSP's `frame-ancestors`)
- Subresource Integrity (SRI), a complementary mechanism verifying the integrity of allowlisted external resources
- `X-Content-Type-Options` and other browser-enforced security headers, forming a broader defense-in-depth header set alongside CSP

## Official References

- W3C, "Content Security Policy Level 3" (Working Draft)
- W3C Recommendation, "Content Security Policy Level 2"
- OWASP, "Content Security Policy Cheat Sheet"
