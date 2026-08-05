---
category: discoverability
criterion: sitemap
severity: medium
related:
  - robots_txt
  - internal_links
---

# sitemap.xml

## Definition

`sitemap.xml` is an XML file, conforming to the Sitemaps protocol (sitemaps.org), that explicitly lists a website's discoverable URLs, optionally with last-modified dates, giving crawlers a direct index of content independent of internal link structure.

## Technical Background

The file's root element is `<urlset>`, with one `<url>` entry per page containing at minimum a `<loc>` (absolute URL). Large sites use a `<sitemapindex>` referencing multiple individual sitemap files (a single file is capped at 50,000 URLs / 50 MiB). Discovery happens via a `Sitemap:` directive in `robots.txt` or direct submission to search engine tools.

## Importance for AI Agent Readiness

A sitemap lets an AI agent enumerate a site's content deterministically and quickly, without performing an exhaustive crawl of every internal link. This matters most for agents operating under a limited request budget, or for sites whose navigation is sparse, JavaScript-driven, or otherwise not fully traversable through link-following alone.

## ARAS Evaluation Context

ARAS checks: `evidence.sitemap_xml` (populated by the Evidence Collector only when `/sitemap.xml` returns HTTP 200).

Passed when: `sitemap_xml` is non-empty.

Failure condition: `sitemap_xml` is empty or `None`.

Failure message: "No sitemap.xml found"

## Common Issues

- File absent entirely, or served at a non-conventional path never referenced from `robots.txt`.
- Sitemap present but stale, listing pages that 404 or redirect.
- Sitemap omits large sections of the site (e.g., paginated or dynamically generated content).
- No sitemap index used despite exceeding the 50,000 URL / 50 MiB single-file limit.

## Impact

- **Technical impact**: crawlers must rely entirely on link-graph traversal, which is slower and can miss orphan or weakly linked pages.
- **AI agent impact**: an agent cannot quickly enumerate "what exists on this site," increasing latency and request count for any content-discovery task.
- **Security impact**: none directly; this is a discoverability, not a protective, mechanism.

## Recommendation Strategy

Publish a sitemap.xml listing the site's discoverable pages, generated programmatically from the site's routing or content database so it stays synchronized with actual content, and reference it from `robots.txt`.

## Implementation Guidance

- **Static site generators**: most (Next.js, Hugo, Jekyll, Astro) provide a built-in or plugin-based sitemap generator run at build time.
- **Express / Node.js**: libraries such as `sitemap` can generate and stream a sitemap from a list of routes.
- **FastAPI**: generate the XML dynamically from the application's route/content registry and serve via a dedicated endpoint with `Content-Type: application/xml`.
- **Large sites**: split into a `sitemap_index.xml` referencing per-section sitemap files (e.g., `sitemap-products.xml`, `sitemap-articles.xml`).

## Validation Checklist

- `GET /sitemap.xml` returns HTTP 200 with `Content-Type` `application/xml` or `text/xml`.
- Root element is `<urlset>` or `<sitemapindex>`.
- Sampled `<loc>` URLs resolve with HTTP 200 (no broken or redirected entries).
- `robots.txt` contains a `Sitemap:` line pointing to this file's absolute URL.

## Related ARAS Criteria

- `robots_txt` — the primary discovery pointer to the sitemap.
- `internal_links` — a complementary, link-graph-based discovery mechanism.

## References

Source: official_sources/discoverability/sitemap_reference.md
