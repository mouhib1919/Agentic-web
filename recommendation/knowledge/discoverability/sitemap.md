# sitemap.xml

## Purpose

`sitemap.xml` is a structured XML document that lists the URLs of a website that the owner considers discoverable, along with optional metadata such as last modification date, change frequency, and relative priority. Unlike relying purely on hyperlink crawling, a sitemap gives crawlers and automated agents a direct, complete inventory of pages without requiring them to traverse the entire link graph of a site. Large sites, sites with sparse internal linking, or sites with content behind JavaScript-rendered navigation particularly benefit from an explicit sitemap, since link-following alone may never surface every page.

## Why it matters

For AI agent readiness, a sitemap is a deterministic index that removes guesswork from content discovery. An agent tasked with answering a question about a website, or with performing a multi-step task across several pages, can consult the sitemap to quickly enumerate candidate pages rather than performing a slow, uncertain crawl. This is especially valuable for agents operating under time or request-count budgets, where every unnecessary request has a cost. A sitemap also communicates freshness signals (via `lastmod`) that help an agent or crawler prioritize recently updated content, which matters for time-sensitive queries.

## When ARAS recommends it

The Recommendation Agent should retrieve this document when the Discoverability Agent reports:

- Missing `sitemap.xml` (no file found, or a non-200/non-XML response).
- A `robots.txt` file that does not reference the sitemap's location.
- A sitemap that exists but appears stale or incomplete relative to the site's actual page count.

## Implementation Guidelines

Generate the sitemap programmatically from the site's routing or content management system rather than maintaining it by hand, so it stays synchronized with actual site structure. Each `<url>` entry should contain a `<loc>` with the absolute URL, and ideally a `<lastmod>` date in ISO 8601 format. Avoid including URLs that return non-200 status codes, redirect chains, or are blocked by `robots.txt`, since these create inconsistent signals for crawlers. If the site has more than 50,000 URLs or the file exceeds roughly 50MB uncompressed, split the content into multiple sitemap files and reference them from a sitemap index file. Reference the sitemap's absolute URL from `robots.txt` using a `Sitemap:` directive so crawlers that check `robots.txt` first can find it immediately, and consider also submitting it directly through search engine webmaster tools for faster initial discovery.

## Best Practices

- Keep the sitemap automatically generated and regenerated on content changes, not manually curated.
- Use accurate `lastmod` timestamps reflecting real content changes, not deployment timestamps.
- Exclude non-canonical, paginated duplicate, or noindex-marked pages to avoid diluting crawl signals.
- Compress large sitemaps with gzip (`sitemap.xml.gz`) to reduce transfer size.
- Validate the XML against the sitemap protocol schema before publishing.
- Reference it from `robots.txt` and keep both files consistent with each other.

## Common Mistakes

- Publishing a sitemap that includes URLs blocked by `robots.txt`, creating contradictory signals.
- Letting the sitemap go stale after a site redesign, so it references pages that no longer exist (broken links).
- Including low-value or duplicate URLs (faceted search results, session-tracked URLs) that dilute the usefulness of the index.
- Forgetting to update `lastmod` values, making freshness signals meaningless.
- Omitting the `Sitemap:` reference from `robots.txt`, forcing crawlers to discover it only through manual submission.

## Expected Benefits

For AI agents, a sitemap provides a fast, low-cost way to enumerate a site's content without exhaustive crawling, which is particularly valuable when an agent needs to reason about "what exists on this site" before deciding where to look for an answer. For search engines, it improves indexing completeness and crawl efficiency, especially for pages with weak internal linking. For machine readability, it standardizes how site structure is exposed in a way every crawler and agent already knows how to parse, since the sitemap protocol is universally supported.

## References

- sitemaps.org: the sitemap protocol specification.
- Google Search Central: guidance on building and submitting sitemaps.
- MDN Web Docs: crawling and indexing fundamentals related to sitemap usage.
