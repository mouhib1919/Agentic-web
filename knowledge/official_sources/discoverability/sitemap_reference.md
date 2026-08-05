# Sitemaps Protocol

## Overview

The Sitemaps protocol defines an XML-based file format that lets a website publisher provide crawlers with an explicit, structured list of URLs on the site, optionally annotated with metadata such as last modification time. It is a complementary discovery mechanism to hyperlink-based crawling, useful when a site's internal link structure does not expose every page.

## Official Definition

The protocol is maintained collaboratively at sitemaps.org (originally introduced by Google in 2005 and later adopted jointly by Google, Microsoft, and Yahoo). It defines the `<urlset>` XML schema, the sitemap index format for large sites, and the discovery mechanisms (robots.txt reference and direct submission) crawlers use to locate sitemap files.

## Core Concepts

- **URL set**: The root element `<urlset>` contains one `<url>` entry per page, each requiring a `<loc>` (absolute URL) and optionally `<lastmod>`, `<changefreq>`, and `<priority>`.
- **Sitemap index**: A `<sitemapindex>` document lists multiple individual sitemap files via `<sitemap>` entries, used when the URL count or file size exceeds single-file limits.
- **Extensions**: The base schema is extended by specialized namespaces for images, video, and news content, each adding domain-specific child elements under `<url>`.
- **Discovery**: Crawlers locate sitemaps either through a `Sitemap:` directive in `robots.txt` or through direct submission to a search engine's webmaster tools.

## Technical Details

- Format: XML, UTF-8 encoded, conforming to the schema published at `https://www.sitemaps.org/schemas/sitemap/0.9`.
- Limits: a single sitemap file is limited to 50,000 URLs and 50 MiB uncompressed; larger sets require a sitemap index referencing multiple sitemap files.
- Compression: individual sitemap files may be served gzip-compressed with a `.xml.gz` extension.
- `<lastmod>` uses W3C Datetime format (a profile of ISO 8601).
- `<changefreq>` and `<priority>` are hints, not guarantees; major search engines have stated they may be disregarded.
- An alternative plain-text format is also permitted: one absolute URL per line, UTF-8, no other markup.

## Detection Characteristics

- A file, typically at `/sitemap.xml`, with `Content-Type` `application/xml` or `text/xml`, root element `<urlset>` or `<sitemapindex>`.
- Referenced via a `Sitemap:` line in `robots.txt`.
- May be one of several conventional filenames (`sitemap.xml`, `sitemap_index.xml`, `sitemap-index.xml`) or a custom path declared only in `robots.txt`.

## Common Implementations

- Auto-generated at build or deploy time from a CMS's content database or a static site generator's route list.
- Segmented sitemap indexes for large e-commerce or publishing sites (e.g., separate sitemaps per content type: products, categories, articles).
- Dynamically served by the application server, regenerated on a schedule or on content change.

## Limitations

- No enforcement mechanism: a sitemap is informational; crawlers are free to ignore entries, crawl unlisted URLs, or crawl at a different rate than any hinted priority.
- Including a URL in a sitemap does not guarantee indexing; it does not override `robots.txt` disallow rules or `noindex` directives.
- Stale sitemaps (URLs that 404, redirect, or are blocked) create ambiguous or contradictory signals for crawlers.

## Related Technologies

- Robots Exclusion Protocol (`robots.txt`), the primary discovery pointer to a sitemap
- RSS/Atom feeds, an alternative content-discovery mechanism for frequently updated content
- `llms.txt`, a curated (non-exhaustive) alternative index aimed at AI agents rather than crawlers

## Official References

- Sitemaps.org, Sitemaps XML format specification (protocol version 0.90)
- Google Search Central, "Build and submit a sitemap"
