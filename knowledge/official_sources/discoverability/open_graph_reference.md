# Open Graph Protocol

## Overview

The Open Graph protocol defines a set of HTML `<meta>` tags that let any web page describe itself as a structured "object" — with a title, type, image, and URL — so that external platforms (social networks, chat applications, search engines) can render a consistent, rich representation of the page without parsing its full content.

## Official Definition

Open Graph is specified by The Open Graph Protocol project (originally released by Facebook in 2010, at `ogp.me`), which defines the required and optional properties, their RDFa-based markup syntax, and a registry of structured object types (article, product, video, and others), each with type-specific properties.

## Core Concepts

- **Basic metadata**: four properties are required by the base specification for any object: `og:title`, `og:type`, `og:image`, `og:url`.
- **Object types**: `og:type` selects a semantic category (e.g., `website`, `article`, `product`, `video.movie`), which in turn defines additional type-specific properties (e.g., `article:published_time`).
- **Structured properties**: complex properties like `og:image` can carry sub-properties (`og:image:width`, `og:image:height`, `og:image:alt`) expressed as sibling `<meta>` tags.
- **Namespace via RDFa**: the specification is technically an RDFa vocabulary, though in practice nearly all implementations use plain `<meta property="..." content="...">` tags rather than full RDFa attribute syntax.

## Technical Details

- Syntax: `<meta property="og:title" content="...">` placed in `<head>`.
- Namespace declaration: historically required `<html prefix="og: https://ogp.me/ns#">` on the root element for strict RDFa parsers; most modern consumers no longer require this.
- Required properties per the base spec: `og:title`, `og:type`, `og:image`, `og:url`.
- Common optional properties: `og:description`, `og:site_name`, `og:locale`.
- `og:image` may be repeated to provide multiple image candidates; consuming platforms typically select the first valid one or apply their own heuristics.

## Detection Characteristics

- One or more `<meta property="og:...">` tags present in the document `<head>`.
- Minimal valid implementation includes at least `og:title` and `og:image`.
- Absence of any `og:` prefixed meta tag indicates no Open Graph support.
- Malformed implementations (missing `content` attribute, relative URLs where absolute are required) are a detectable partial-compliance state.

## Common Implementations

- CMS platforms and site builders auto-populate Open Graph tags from existing title/featured-image/excerpt fields.
- E-commerce platforms use `og:type="product"` with associated price and availability properties.
- Social sharing plugins/libraries generate the tag set from a page's existing metadata at build or render time.

## Limitations

- No formal validation or enforcement; consuming platforms apply their own fallback heuristics when tags are missing or malformed, leading to inconsistent rendering across platforms.
- The specification does not define a machine-readable schema/type system as rigorous as Schema.org's; the object-type registry is comparatively small and social-sharing-oriented.
- Overlaps but does not integrate directly with Schema.org/JSON-LD; sites often must maintain both independently.

## Related Technologies

- Twitter Card meta tags (`twitter:*`), a parallel, partially overlapping convention for a single platform
- Schema.org / JSON-LD structured data, a broader and more formally typed alternative
- RDFa, the underlying markup model Open Graph is technically specified against

## Official References

- The Open Graph Protocol, ogp.me specification
