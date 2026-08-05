# Frontend-Discoverable Interaction Capabilities

## Overview

Frontend interaction capabilities are the API and interactive endpoints a client-side JavaScript application references at runtime — discoverable through static analysis of the shipped JavaScript bundle — even when no formally documented or independently discoverable API surface exists. This represents a fallback interaction signal: evidence that a website is capable of programmatic interaction, inferred indirectly from its own client code rather than from any published specification.

## Official Definition

There is no formal specification for "frontend-discoverable interaction"; it is an analytical technique built on standard, specified web technologies — the JavaScript language (ECMAScript), the Fetch API and XMLHttpRequest (WHATWG/WHATWG-adjacent living standards), and the WebSocket protocol (RFC 6455) — applied through static or dynamic inspection of client-side code rather than any single governing document.

## Core Concepts

- **Network call surfaces in client code**: modern web applications issue data requests from the browser using `fetch()`, `XMLHttpRequest`, or WebSocket connections; the URLs and patterns referenced in these calls reveal backend interaction points even absent formal documentation.
- **Bundled vs. source code**: production JavaScript is typically minified/bundled, so discoverable endpoints appear as string literals or template patterns within compiled bundles rather than clearly named functions.
- **Static vs. dynamic discovery**: static analysis inspects the JavaScript source/bundle text directly for URL-like patterns without executing it; dynamic analysis (not covered by this document) would involve actually executing the page and observing network traffic.
- **Pattern categories**: discoverable references typically fall into categories such as REST-like path patterns (`/api/...`), GraphQL endpoint references (commonly `/graphql`), WebSocket URLs (`ws://`/`wss://`), and references to known third-party service domains.

## Technical Details

- Fetch API: `fetch(url, options)`, a WHATWG-specified, promise-based interface for making HTTP requests from JavaScript, the dominant modern replacement for XMLHttpRequest.
- XMLHttpRequest: the older, still widely present, event-based HTTP request interface, standardized by WHATWG's XMLHttpRequest Living Standard.
- WebSocket: RFC 6455 defines the `ws://`/`wss://` URI schemes and full-duplex communication protocol; client-side usage is exposed via the `WebSocket` constructor.
- String-literal extraction from bundled JavaScript relies on lexical pattern matching (regular expressions for path-like and protocol-like substrings) rather than full JavaScript parsing, since minified/bundled code is not reliably parseable back into meaningful call-site structure.

## Detection Characteristics

- Path-like string literals matching REST conventions (e.g., `/api/`, `/v1/`, `/v2/`) found within downloaded JavaScript file contents.
- String literals matching `/graphql` or similar GraphQL-conventional paths.
- `ws://` or `wss://` prefixed string literals indicating WebSocket usage.
- References to recognized third-party service domains (payment processors, analytics platforms, cloud API providers) as an auxiliary signal of the application's broader integration surface.

## Common Implementations

- Single-page applications (React, Vue, Angular) bundling all API interaction logic into one or more JavaScript files fetched by the browser, with endpoint paths present as literal strings even after minification.
- Server-rendered applications progressively enhanced with client-side JavaScript for specific interactive widgets (search-as-you-type, live chat), each referencing a narrower, more targeted set of endpoints.
- Third-party embedded widgets (chat, analytics, payment) each contributing their own recognizable request patterns to the overall detected surface.

## Limitations

- Purely textual/static analysis cannot distinguish a genuinely functional endpoint from a stale, deprecated, or dead code reference retained in the bundle.
- Obfuscation, code-splitting, and dynamic string construction (e.g., endpoint paths built at runtime via concatenation) can hide interaction surfaces from static string-matching entirely.
- This technique reveals what a website's own frontend can do, not necessarily what is available or permitted for a third-party agent to call — many referenced endpoints require session-specific authentication only obtainable through the site's own login flow.

## Related Technologies

- Fetch API and XMLHttpRequest (the client-side request mechanisms being analyzed)
- WebSocket protocol (RFC 6455)
- REST and GraphQL (the architectural styles the discovered endpoints typically follow)

## Official References

- WHATWG, "Fetch Standard"
- WHATWG, "XMLHttpRequest Standard"
- IETF RFC 6455, "The WebSocket Protocol"
