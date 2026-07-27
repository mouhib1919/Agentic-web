# Security Headers (X-Frame-Options, X-Content-Type-Options, X-XSS-Protection)

## Purpose

Beyond Content Security Policy and HSTS, a small set of additional HTTP response headers provide targeted, browser-enforced protections against specific classes of attack. `X-Frame-Options` controls whether a page can be embedded inside a `<frame>` or `<iframe>` on another site, mitigating clickjacking, where an attacker overlays a legitimate page inside an invisible frame to trick users into interacting with it unintentionally. `X-Content-Type-Options: nosniff` instructs the browser not to guess (MIME-sniff) a resource's content type based on its content, forcing it to respect the declared `Content-Type` header, which prevents certain attacks where a file is served with a benign extension but sniffed and executed as a different, dangerous type. `X-XSS-Protection` is an older header that enabled a browser's built-in reflected-XSS filter; it is now largely superseded by CSP in modern browsers but is still checked by some auditing tools and legacy clients.

## Why it matters

For AI agent readiness, these headers collectively signal that a site follows baseline browser-security hardening practices, which correlates with a more predictable and trustworthy interaction surface overall. Clickjacking protection in particular matters for any automated or assisted interaction: an agent operating on a user's behalf, or rendering a page for a human user through an embedded view, should be able to trust that the page is not designed to be invisibly framed and hijacked. MIME-sniffing protection reduces the risk that content an agent retrieves and expects to be one type (e.g. plain text or JSON) gets reinterpreted by a browser as executable content due to sniffing behavior.

## When ARAS recommends it

The Recommendation Agent should retrieve this document when the Security Agent reports:

- Missing `X-Frame-Options` header (clickjacking protection check failed).
- Missing both `X-Content-Type-Options` and `X-XSS-Protection` headers (MIME/XSS protection check failed).
- A generally weak security header posture where CSP is also absent, since `frame-ancestors` in CSP can substitute for `X-Frame-Options` but only if CSP is actually deployed.

## Implementation Guidelines

Add `X-Frame-Options: DENY` if the page should never be framed by any site, or `X-Frame-Options: SAMEORIGIN` if framing is only acceptable from the same origin (for example, for internal preview tools). Where a Content Security Policy is already in place, prefer expressing frame control through the CSP `frame-ancestors` directive, which is more flexible and is the modern standard, while keeping `X-Frame-Options` as a fallback for older browsers that do not support `frame-ancestors`. Add `X-Content-Type-Options: nosniff` to every response, since this header has no meaningful downside and closes an entire class of MIME-confusion attacks with a single line of server configuration. `X-XSS-Protection` can be set to `0` to explicitly disable the legacy filter (recommended in modern deployments that rely on CSP instead, since the legacy filter itself has been a source of vulnerabilities in some browsers), or omitted entirely if the target browser support matrix no longer includes browsers that honor it.

## Best Practices

- Set `X-Content-Type-Options: nosniff` on every response as a low-cost, high-value default.
- Choose `X-Frame-Options: DENY` unless legitimate same-origin framing is required, in which case use `SAMEORIGIN`.
- Prefer CSP's `frame-ancestors` directive when CSP is deployed, keeping `X-Frame-Options` as a compatibility fallback.
- Apply these headers globally through server or edge/CDN configuration rather than per-route, to avoid accidental omissions.
- Periodically audit header configuration using automated security header scanners.

## Common Mistakes

- Omitting these headers entirely, leaving no baseline protection against clickjacking or MIME-sniffing attacks.
- Setting `X-Frame-Options: ALLOWALL` or omitting it where broad third-party framing was never actually intended.
- Relying solely on the legacy `X-XSS-Protection` filter instead of adopting CSP, which offers substantially stronger protection.
- Applying headers inconsistently across different routes or subdomains due to fragmented configuration.
- Assuming these headers alone constitute a complete security posture without complementary measures like CSP and HSTS.

## Expected Benefits

For AI agents and human users alike, these headers close well-understood, low-effort attack vectors that could otherwise compromise the integrity of a page's rendering or embedding context. For security broadly, they represent some of the highest return-on-effort hardening measures available, since they require only configuration changes with no impact on legitimate functionality in the vast majority of cases. For machine readability, `X-Content-Type-Options` in particular ensures that automated clients and browsers alike interpret a resource's type exactly as declared, avoiding ambiguity.

## References

- OWASP: Secure Headers Project and related cheat sheets.
- MDN Web Docs: reference pages for X-Frame-Options, X-Content-Type-Options, and X-XSS-Protection.
- W3C: Content Security Policy specification, covering the modern `frame-ancestors` alternative to X-Frame-Options.
