# HTTP Strict Transport Security (HSTS)

## Purpose

HTTP Strict Transport Security is a response header, `Strict-Transport-Security`, that instructs a browser to only ever connect to a given domain over HTTPS, for a specified duration, even if the user types `http://` or follows an insecure link. Once a browser has seen the header for a domain, it will automatically upgrade any subsequent request to that domain to HTTPS internally, before the request ever leaves the client, rather than relying on a server-side redirect that could itself be intercepted. This closes a specific but serious gap in transport security: the brief window during an HTTP-to-HTTPS redirect where an attacker on the network path could intercept or downgrade the connection.

## Why it matters

For AI agent readiness, HSTS matters because it guarantees the integrity of the transport channel an agent uses to fetch content and submit data. An agent that resolves a URL and makes its very first request over HTTP, before any redirect happens, is momentarily exposed to interception on that first request unless the browser or HTTP client already has cached HSTS enforcement for the domain. Publishing HSTS with a long `max-age` closes this gap for any client that has previously visited the domain, and combined with HSTS preload lists, it can close the gap even for a client's very first connection. This is foundational trust infrastructure: an agent should be able to assume that once it is talking to a domain over HTTPS, it will never be silently downgraded to plaintext.

## When ARAS recommends it

The Recommendation Agent should retrieve this document when the Security Agent reports:

- Missing `Strict-Transport-Security` header on an HTTPS response.
- The site is served over HTTPS but still resolves and responds on plain HTTP without redirecting or enforcing upgrade.
- HSTS present but with a very short `max-age`, which limits its practical protective duration.

## Implementation Guidelines

Enable HTTPS across the entire domain first, since HSTS only makes sense once HTTPS is fully supported and default. Add the `Strict-Transport-Security` header to every HTTPS response with a `max-age` directive expressed in seconds — a commonly recommended value is one year (`max-age=31536000`) once the domain's HTTPS configuration is confirmed stable. Include the `includeSubDomains` directive if all subdomains also support HTTPS, since this extends the same protection sitewide rather than leaving subdomains exposed. Once the header has been deployed reliably and subdomain coverage is confirmed, consider submitting the domain to the HSTS preload list maintained by major browser vendors, which hardcodes the HTTPS-only requirement into the browser itself, removing even the very first-connection gap. Because preload list inclusion is difficult to reverse quickly, only submit once HTTPS support is fully committed to and stable across the domain and its subdomains.

## Best Practices

- Enforce HTTPS sitewide before enabling HSTS, and ensure any HTTP requests are redirected to HTTPS as a fallback for clients without cached HSTS state.
- Use a long `max-age`, typically one year, once HTTPS stability is confirmed.
- Add `includeSubDomains` only when every subdomain genuinely supports HTTPS.
- Consider HSTS preload submission for maximum protection, but understand its difficulty to reverse.
- Monitor certificate renewal processes closely, since any HTTPS outage becomes more disruptive once HSTS is enforced by browsers.

## Common Mistakes

- Enabling `includeSubDomains` before confirming every subdomain actually supports HTTPS, breaking those subdomains for returning visitors.
- Setting an extremely short `max-age` that provides negligible real-world protection.
- Relying only on a server-side HTTP-to-HTTPS redirect without ever adding the HSTS header, leaving the interception window open indefinitely.
- Submitting to the HSTS preload list without full confidence in long-term HTTPS support, since removal from preload lists takes a long time to propagate.
- Forgetting to renew or monitor HTTPS certificates, which becomes especially disruptive once HSTS prevents any HTTP fallback.

## Expected Benefits

For AI agents and any automated HTTP client, HSTS removes the possibility of a silent downgrade to plaintext for any domain previously visited, and with preload, even for the first visit. For security broadly, it is one of the most effective, low-cost mitigations against man-in-the-middle and SSL-stripping attacks. For machine readability, it has no direct effect on content parsing, but it protects the channel through which that content is retrieved.

## References

- OWASP: HTTP Strict Transport Security Cheat Sheet.
- MDN Web Docs: Strict-Transport-Security header reference.
- The HSTS preload list maintained collaboratively by major browser vendors.
