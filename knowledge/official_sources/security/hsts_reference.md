# HTTP Strict Transport Security (HSTS)

## Overview

HTTP Strict Transport Security is a response header mechanism that allows a website to instruct browsers to interact with it only over HTTPS, for a specified duration, eliminating the possibility of the browser ever making a plain-HTTP request to that host once the policy has been received and cached.

## Official Definition

HSTS is defined in IETF RFC 6797, "HTTP Strict Transport Security (HSTS)," which specifies the `Strict-Transport-Security` response header syntax, the browser-side processing model (the "HSTS Policy" a user agent must maintain per host), and the preload-list mechanism referenced (though not itself standardized) as a complementary trust-on-first-use mitigation.

## Core Concepts

- **Trust-on-first-use with caching**: a browser only learns of a host's HSTS policy after receiving the header at least once over a genuinely secure (HTTPS) connection; RFC 6797 explicitly disallows honoring the header over plain HTTP.
- **Known HSTS Host**: once a policy is received, the browser records the host (and, if specified, its subdomains) as a "Known HSTS Host" for the duration specified by `max-age`, automatically upgrading any subsequent `http://` request to that host to `https://` before the request is sent.
- **includeSubDomains**: an optional directive extending the policy to every subdomain of the declaring host, not merely the exact host that sent the header.
- **Preload list**: a browser-vendor-maintained, hardcoded list of domains (submitted voluntarily by site operators) that ship with HSTS enforcement built into the browser itself, closing the residual "first connection" gap that header-based HSTS cannot address on its own.

## Technical Details

- Header syntax: `Strict-Transport-Security: max-age=<seconds>; includeSubDomains; preload`.
- `max-age` is a required directive specifying, in seconds, how long the policy remains valid from receipt; a value of `0` immediately expires/removes a previously cached policy for that host.
- The header is only meaningful, and per RFC 6797 must only be honored by the client, when delivered over a connection already secured by HTTPS — the header has no effect if sent over plain HTTP.
- `preload` is not part of RFC 6797 itself; it is a convention recognized by browser vendors as a prerequisite for submission to their independently maintained preload lists (eligibility additionally requires `includeSubDomains` and a sufficiently long `max-age`, per each vendor's submission criteria).

## Detection Characteristics

- Presence of the `Strict-Transport-Security` response header on an HTTPS response, with a parseable `max-age` directive.
- `max-age` value magnitude (a very short duration provides materially weaker protection than the commonly recommended one-year value).
- Presence or absence of `includeSubDomains` and `preload` directives as additional policy-strength indicators.
- Cross-referencing the host against a known browser preload list dataset indicates whether first-connection protection is already achieved independent of the header itself.

## Common Implementations

- Applied uniformly at a reverse proxy, CDN, or edge layer across an entire site, rather than per-application-route.
- Rolled out incrementally: a shorter `max-age` during initial verification, increased to the long-lived, `includeSubDomains`, `preload`-eligible configuration once HTTPS coverage across the domain and subdomains is confirmed stable.
- Combined with an unconditional HTTP-to-HTTPS redirect as a defense-in-depth pairing (the redirect handles unprimed clients; HSTS prevents any subsequent downgrade for primed ones).

## Limitations

- Provides no protection on a client's genuinely first-ever connection to a host, unless that host is already on the browser's preload list — this is an inherent trust-on-first-use limitation of the header-based mechanism.
- `includeSubDomains` misconfiguration can break legitimately HTTP-only subdomains, since the policy is not selectively scoped once declared.
- Preload list inclusion is slow to reverse: removal from major browsers' shipped lists can take months to fully propagate through release cycles, making it a high-commitment, difficult-to-undo action.

## Related Technologies

- HTTPS / TLS (the underlying secure transport HSTS enforces exclusive use of)
- HTTP redirects (301/308), the complementary mechanism for unprimed clients
- Content Security Policy's `upgrade-insecure-requests` directive, a related but distinct resource-level HTTPS-upgrade mechanism

## Official References

- IETF RFC 6797, "HTTP Strict Transport Security (HSTS)"
