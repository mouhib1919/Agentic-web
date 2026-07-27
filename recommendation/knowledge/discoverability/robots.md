# robots.txt

## Purpose

`robots.txt` is a plain-text file published at the root of a website (e.g. `https://example.com/robots.txt`) that tells web crawlers and automated agents which parts of a site they are allowed or disallowed to access. It follows the Robots Exclusion Protocol, a de facto web standard supported by search engine crawlers, scraping tools, and increasingly by AI agents that browse the web on behalf of users. The file uses simple directives — `User-agent`, `Allow`, `Disallow`, and optionally `Sitemap` — grouped into blocks that target specific crawlers or apply to all of them via the `*` wildcard.

## Why it matters

For AI agent readiness specifically, `robots.txt` is the first artifact an autonomous agent should check before crawling a site. It establishes a machine-readable contract about which paths are safe, intended, or forbidden for automated access. A website without a `robots.txt` file forces an agent to guess at boundaries, which increases the risk of the agent wasting time on irrelevant paths (admin panels, checkout flows, internal search results) or, worse, being blocked entirely by defensive infrastructure that treats undeclared crawlers as suspicious. Publishing a clear `robots.txt` signals that the site owner has thought about automated access and is willing to guide it, which is a foundational trust signal for both search engine discovery and AI agent interaction.

## When ARAS recommends it

The Recommendation Agent should retrieve this document when the Discoverability Agent reports:

- Missing `robots.txt` (no file found at the site root, or a non-200 response).
- A `robots.txt` file that blocks all crawlers (`Disallow: /` under `User-agent: *`) without justification.
- A `robots.txt` file present but without a `Sitemap:` directive pointing to `sitemap.xml`.

## Implementation Guidelines

Place `robots.txt` at the domain root, not in a subdirectory — crawlers only look for it at `/robots.txt`. Start with a permissive default (`User-agent: *` followed by `Allow: /`) unless there are specific paths that genuinely should not be crawled, such as authenticated areas, internal APIs not meant for public consumption, or duplicate content paths. Use `Disallow` sparingly and precisely; overly broad disallow rules (e.g. blocking an entire `/products/` tree) can inadvertently hide the exact content an AI agent or search engine needs to answer user queries. Always include a `Sitemap:` line pointing to the absolute URL of the sitemap, since this gives crawlers a direct path to a structured list of pages rather than relying purely on link discovery. If different crawlers need different treatment (for example, allowing general search bots but restricting an aggressive scraper), use separate `User-agent` blocks rather than trying to encode conditional logic that the format does not support.

## Best Practices

- Serve the file with a `text/plain` content type and ensure it returns HTTP 200.
- Keep the file small and human-readable; avoid deeply nested or redundant rules.
- Always include a `Sitemap:` directive with the full absolute URL.
- Review `robots.txt` whenever site structure changes to avoid stale disallow rules blocking new, relevant content.
- Test the file with crawler simulation tools before deploying changes, since a misconfigured `Disallow: /` can deindex an entire site.
- Treat `robots.txt` as a courtesy signal, not a security control — it does not prevent access, it only requests that well-behaved crawlers respect the stated boundaries.

## Common Mistakes

- Forgetting to publish the file at all, leaving crawlers and agents without any explicit guidance.
- Blocking `/` entirely by mistake, often left over from a staging environment configuration that was never updated for production.
- Blocking CSS/JS assets needed for rendering, which can prevent search engines and agents from correctly interpreting page content.
- Omitting the `Sitemap:` directive even when a sitemap exists.
- Using `robots.txt` as if it were an access-control mechanism, when it provides no actual enforcement against non-compliant crawlers.

## Expected Benefits

For AI agents, a well-formed `robots.txt` clarifies which parts of the site are safe and intended for automated interaction, reducing wasted requests and the risk of triggering anti-bot defenses. For search engines, it improves crawl efficiency by directing crawl budget toward valuable content. For machine readability generally, it acts as the entry point of a predictable discovery chain (`robots.txt` → `sitemap.xml` → individual pages), which is exactly the pattern automated systems are built to follow. It also reduces server load from crawlers repeatedly hitting irrelevant or infinite-parameter URLs.

## References

- Google Search Central: Robots.txt introduction and specifications.
- The Internet Engineering Task Force (IETF) RFC 9309, which formalizes the Robots Exclusion Protocol.
- MDN Web Docs: guidance on robots.txt and its relationship to crawling and indexing.
