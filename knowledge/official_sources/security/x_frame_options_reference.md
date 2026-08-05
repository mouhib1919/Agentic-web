# X-Frame-Options

## Overview

`X-Frame-Options` is an HTTP response header that allows a page to control whether it may be rendered inside a `<frame>`, `<iframe>`, `<embed>`, or `<object>` on another page, providing a browser-enforced defense against clickjacking attacks, in which a malicious page overlays or disguises a framed target page to trick users into interacting with it unintentionally.

## Official Definition

`X-Frame-Options` originated as a de facto industry convention (introduced by Microsoft in Internet Explorer 8, 2009) later documented as an informational specification in IETF RFC 7034, "HTTP Header Field X-Frame-Options." It was never advanced to full IETF Standards Track status; the specification itself explicitly notes the header is considered obsolete in favor of the Content Security Policy `frame-ancestors` directive, though it remains widely deployed for backward compatibility.

## Core Concepts

- **Framing control**: the header instructs the browser whether the current response is permitted to be displayed within a framing context at all, evaluated by the browser before rendering the framed content.
- **Directive values**: RFC 7034 defines three values — `DENY` (never permit framing, by any page including the same origin), `SAMEORIGIN` (permit framing only by pages of the same origin), and `ALLOW-FROM <origin>` (permit framing only by the named origin) — though `ALLOW-FROM` was never consistently implemented across major browsers and is considered non-functional in practice.
- **Single-value limitation**: unlike CSP's `frame-ancestors`, which accepts a list of allowed origins, `X-Frame-Options` supports only a single directive value per response, precluding "allow multiple specific origins" policies without CSP.
- **Per-response scope**: the header applies independently to each HTTP response; there is no site-wide default unless applied consistently to every response.

## Technical Details

- Header syntax: `X-Frame-Options: DENY` or `X-Frame-Options: SAMEORIGIN`.
- Browser processing occurs prior to rendering the framed document; a disallowed framing attempt results in a blank or blocked frame rather than a rendered but inert page.
- `ALLOW-FROM` is formally defined by RFC 7034 but is not reliably implemented in modern browser engines, which either ignore it (falling back to permissive behavior) or treat it inconsistently — CSP's `frame-ancestors` is the recommended replacement whenever multi-origin allowance is required.

## Detection Characteristics

- Presence of the `X-Frame-Options` response header and its declared value (`DENY`, `SAMEORIGIN`, or the effectively non-functional `ALLOW-FROM`).
- Absence of the header (and absence of a CSP `frame-ancestors` directive as a substitute) indicates no clickjacking protection via either mechanism.
- When both `X-Frame-Options` and CSP `frame-ancestors` are present, modern browsers give precedence to `frame-ancestors`, making the CSP directive the operative control in that case.

## Common Implementations

- Applied uniformly across an entire site via a reverse proxy, CDN, or framework-level default middleware, typically set to `SAMEORIGIN` or `DENY`.
- `SAMEORIGIN` chosen when legitimate same-origin framing is required (e.g., internal preview or embed tooling); `DENY` chosen when no framing use case exists at all.
- Increasingly superseded by, or paired redundantly with, a CSP `frame-ancestors` directive for browsers that support it, retaining `X-Frame-Options` only as a fallback for older clients.

## Limitations

- Cannot express "allow framing from these specific N origins" reliably, due to `ALLOW-FROM`'s lack of consistent implementation — CSP is required for that use case.
- Provides no protection against clickjacking techniques that do not rely on iframe embedding (though iframe-based embedding is the dominant classic clickjacking vector the header was designed to address).
- As a single, unlisted-value header, it cannot be combined with per-origin nuance the way a full source list can.

## Related Technologies

- Content Security Policy `frame-ancestors` directive (the modern, more capable, browser-preferred replacement)
- Clickjacking as an attack category, and JavaScript-based "frame-busting" scripts, an older, less reliable mitigation predating both header-based approaches

## Official References

- IETF RFC 7034, "HTTP Header Field X-Frame-Options" (Informational)
- W3C, "Content Security Policy Level 3" — `frame-ancestors` directive
- MDN Web Docs, "X-Frame-Options"
