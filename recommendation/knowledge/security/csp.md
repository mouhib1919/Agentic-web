# Content Security Policy (CSP)

## Purpose

Content Security Policy is an HTTP response header, `Content-Security-Policy`, that lets a website declare which sources of content — scripts, stylesheets, images, fonts, frames, and connections — the browser is allowed to load and execute for that page. Instead of trusting every script that ends up in the page's HTML, the browser enforces an allowlist defined by the server, blocking anything that falls outside the declared policy. CSP is one of the most effective browser-enforced defenses against content injection attacks, particularly cross-site scripting (XSS), because even if an attacker manages to inject a malicious script tag into a page, a correctly configured CSP will prevent the browser from executing it.

## Why it matters

For AI agent readiness and security more broadly, CSP matters because an agent (or any automated system) interacting with a website implicitly trusts that the page it retrieves has not been tampered with by a third party. A site without CSP is more vulnerable to script injection, which could alter the content an agent reads, redirect it to malicious endpoints, or exfiltrate data submitted through forms the agent interacts with on a user's behalf. A published, well-scoped CSP is a strong signal that a site takes content integrity seriously, which matters both for human users and for automated agents that need to trust the fidelity of what they retrieve.

## When ARAS recommends it

The Recommendation Agent should retrieve this document when the Security Agent reports:

- Missing `Content-Security-Policy` header on the homepage response.
- A CSP present but configured with an overly permissive policy (e.g. `default-src *` or broad use of `unsafe-inline`/`unsafe-eval`).
- Other security headers present but CSP absent, indicating partial but incomplete adoption of browser-enforced protections.

## Implementation Guidelines

Start by defining a `default-src` directive as a restrictive baseline (commonly `'self'`), then add more specific directives (`script-src`, `style-src`, `img-src`, `connect-src`, `frame-ancestors`) to allow only the specific external origins the site actually depends on, such as a CDN, analytics provider, or payment processor. Avoid `unsafe-inline` and `unsafe-eval` wherever possible; instead, move inline scripts and styles into external files, or use nonces or hashes generated per-request to allow specific inline blocks without opening the door to arbitrary injected scripts. Roll out CSP incrementally using the `Content-Security-Policy-Report-Only` header first, paired with a `report-uri` or `report-to` endpoint, to observe what the policy would block in production before enforcing it, avoiding accidental breakage of legitimate functionality. Review and tighten the policy over time as the site's actual dependency on third-party origins becomes clearer through report data.

## Best Practices

- Start from a restrictive `default-src 'self'` baseline and expand only as needed.
- Avoid `unsafe-inline` and `unsafe-eval`; use nonces, hashes, or externalized scripts instead.
- Use `Content-Security-Policy-Report-Only` during rollout to catch breakage before enforcing.
- Set `frame-ancestors` to control which sites can embed the page, complementing clickjacking protections.
- Regularly review and tighten the policy as third-party dependencies change.
- Monitor CSP violation reports to detect both misconfigurations and active injection attempts.

## Common Mistakes

- Omitting CSP entirely, leaving no browser-enforced defense against script injection.
- Deploying an overly permissive policy (`default-src *`) that provides little real protection.
- Relying heavily on `unsafe-inline`, which defeats much of CSP's protective value against XSS.
- Enforcing a policy directly in production without first testing in report-only mode, causing broken functionality.
- Letting the policy go stale as new third-party scripts are added without updating the allowlist.

## Expected Benefits

For AI agents, a strong CSP increases confidence that the content retrieved from a page has not been altered by injected, unauthorized scripts, which matters for any agent relying on page content to make decisions or take actions. For security broadly, CSP substantially reduces the practical impact of XSS vulnerabilities, even when other input-sanitization defenses fail. For machine readability, it has no direct effect on parsing, but it protects the integrity of the content being parsed in the first place.

## References

- OWASP: Content Security Policy Cheat Sheet.
- MDN Web Docs: Content-Security-Policy header reference and directive guide.
- W3C: the Content Security Policy specification.
