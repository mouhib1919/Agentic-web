---
category: discoverability
criterion: robots_txt
severity: medium
related:
  - sitemap
  - llms_txt
---

# robots.txt

## Definition

`robots.txt` is the Robots Exclusion Protocol file (IETF RFC 9309), published at the root of a website, that tells crawlers and automated agents which paths they may or may not request, and optionally where to find a sitemap.

## Technical Background

The file must be served at `/robots.txt` with a 200 status. It is organized into `User-agent` groups containing `Allow`/`Disallow` path rules, and may include a `Sitemap:` directive pointing to one or more sitemap URLs. A missing file, or a non-200 response, leaves crawlers without any explicit crawling guidance for the site.

## Importance for AI Agent Readiness

`robots.txt` is the first artifact an AI agent or crawler checks before interacting with a site. Its absence forces the agent to guess at access boundaries, increasing the risk of wasted requests, unintended access to non-public paths, or the site's own defenses flagging the agent as an unrecognized, untrusted client.

## ARAS Evaluation Context

ARAS checks: `evidence.robots_txt` (populated by the Evidence Collector only when `/robots.txt` returns HTTP 200).

Passed when: `robots_txt` is non-empty.

Failure condition: `robots_txt` is empty or `None`.

Failure message: "No robots.txt found"

## Common Issues

- File entirely absent from the site root.
- File present but returning a non-200 status (e.g., 404, redirected away from root).
- File present but with no `Sitemap:` directive, leaving crawlers to discover the sitemap through other means only.
- Overly broad `Disallow: /` left over from a staging environment configuration.

## Impact

- **Technical impact**: crawlers fall back to undirected link-following, increasing crawl time and load on the server.
- **AI agent impact**: an agent has no explicit signal of which paths are intended for automated access, increasing uncertainty and the chance of the agent avoiding the site entirely or hitting disallowed/irrelevant paths.
- **Security impact**: minimal directly, though the absence of any declared boundary can indicate a broader lack of attention to machine-facing site configuration.

## Recommendation Strategy

Add a robots.txt file at the site root. At minimum, publish a permissive `User-agent: *` group with `Allow: /` unless specific paths genuinely need to be excluded, and include a `Sitemap:` directive referencing the site's sitemap.xml.

## Implementation Guidance

- **Static hosting / Nginx**: place a `robots.txt` file in the web root; Nginx will serve it automatically as a static file.
- **Node.js / Express**: `app.get('/robots.txt', (req, res) => res.type('text/plain').send('User-agent: *\nAllow: /\nSitemap: https://example.com/sitemap.xml'))`.
- **FastAPI**: serve via a `StaticFiles` mount or a dedicated route returning `PlainTextResponse`.
- **Cloudflare**: can serve a static `robots.txt` directly from Cloudflare Pages/Workers without touching the origin.

## Validation Checklist

- `GET /robots.txt` returns HTTP 200.
- Response `Content-Type` is `text/plain`.
- At least one `User-agent` group with valid `Allow`/`Disallow` syntax is present.
- A `Sitemap:` line references the correct, absolute sitemap URL.

## Related ARAS Criteria

- `sitemap` — referenced from within `robots.txt` via the `Sitemap:` directive.
- `llms_txt` — a complementary, AI-agent-specific discovery file following the same root-file convention.

## References

Source: official_sources/discoverability/robots_reference.md
