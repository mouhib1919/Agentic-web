# llms.txt

## Purpose

`llms.txt` is an emerging convention, analogous to `robots.txt`, that gives large language models and AI agents a concise, curated entry point into a website's most important content. Published at the root of a domain (`/llms.txt`), it is a plain Markdown file that typically summarizes what the site or product does and links to the pages an AI agent should read first to understand the site — documentation, API references, key product pages, or FAQs. Unlike a sitemap, which lists every URL indiscriminately, `llms.txt` is intentionally curated and human-authored, prioritizing the handful of resources that best explain the site to a model with limited context.

## Why it matters

Large language models and AI agents operate under strict context-window constraints: they cannot read an entire website before answering a question. `llms.txt` solves this by giving the agent a pre-summarized, high-signal starting point instead of forcing it to infer importance from raw HTML or a full crawl. This is directly aligned with the goals of Agentic Readiness: a site that publishes `llms.txt` is explicitly optimizing for AI consumption rather than only for human browsers or traditional search crawlers. Because the convention is still emerging, adopting it early is also a low-cost way to signal that a site takes AI-agent interaction seriously.

## When ARAS recommends it

The Recommendation Agent should retrieve this document when the Discoverability Agent reports:

- Missing `llms.txt` at the site root.
- A site with substantial documentation or API surface but no consolidated, agent-friendly summary.
- A site otherwise well-structured for search engines but not yet adapted for AI agent consumption.

## Implementation Guidelines

Write `llms.txt` in Markdown, starting with an H1 title naming the site or product, followed by a short paragraph (a few sentences) describing its purpose. Follow this with one or more H2 sections grouping links by category — for example "Documentation", "API Reference", "Guides" — each containing a Markdown list of links with a brief one-line description of what each linked page covers. Keep the file concise: it should be readable in a single pass and prioritize the pages that most efficiently explain the site's core value and functionality, rather than attempting to be exhaustive like a sitemap. If the site changes significantly (new major features, restructured documentation), update `llms.txt` alongside those changes so it does not drift out of sync with reality. Some sites also publish an extended version (`llms-full.txt`) containing the full concatenated content of key pages for models that can consume larger contexts, but the root `llms.txt` should remain a lightweight index.

## Best Practices

- Keep the file short and curated — a few dozen links at most, not an exhaustive listing.
- Group links logically (product overview, docs, API, pricing, support) with brief descriptions.
- Prioritize canonical, stable URLs rather than deep links likely to change.
- Update the file whenever major content or product changes occur.
- Write descriptions that explain *why* a link matters, not just *what* it is.
- Keep the tone factual and information-dense rather than promotional.

## Common Mistakes

- Treating `llms.txt` as a marketing page instead of a navigational aid, filling it with promotional copy rather than useful links.
- Listing too many links without prioritization, defeating the purpose of a curated entry point.
- Letting the file go stale after site restructuring, leading agents to broken or outdated links.
- Duplicating the entire sitemap instead of providing a genuinely curated subset.
- Omitting a clear description of what the site or product actually does.

## Expected Benefits

For AI agents, `llms.txt` dramatically reduces the effort needed to understand a site's purpose and locate authoritative content, improving both the speed and accuracy of agent-generated answers about the site. For machine readability, it complements `robots.txt` and `sitemap.xml` by adding a semantic, human-curated layer on top of purely structural discovery mechanisms. While it has limited direct effect on traditional search engine ranking, it positions a site favorably as AI-driven search and agentic browsing become more prevalent alongside conventional search engines.

## References

- llmstxt.org: the community specification and rationale for the `llms.txt` convention.
- Public examples from early-adopting developer tools and documentation platforms.
- General Markdown authoring guidance from the CommonMark specification, which `llms.txt` builds on.
