# API Discoverability

## Overview

API discoverability refers to the mechanisms by which an automated client can locate machine-readable API documentation or specification files for a website's backend services, without prior out-of-band knowledge of their existence. Unlike page-level discovery (robots.txt, sitemaps), this concerns the discovery of programmatic interfaces rather than human-readable content.

## Official Definition

There is no single formal standard governing API discovery; instead, several conventions and specifications address related aspects: the OpenAPI Initiative's OpenAPI Specification defines the format of the description document itself; RFC 8615 defines the `.well-known` URI path convention that many discovery mechanisms build on; and individual API documentation tools (Swagger UI, ReDoc) establish de facto conventional paths.

## Core Concepts

- **Well-known URIs**: RFC 8615 reserves the `/.well-known/` path prefix at any origin for registered, standardized metadata resources, providing a predictable location for machine discovery without requiring prior coordination.
- **Specification documents**: a machine-readable file (commonly OpenAPI JSON/YAML) that fully describes an API's available operations, independent of any human-facing documentation UI.
- **Documentation UIs**: interactive tools (Swagger UI, ReDoc, Stoplight) that render a specification document at a conventional, human-browsable path.
- **Conventional paths**: absent a universal standard, the ecosystem has converged on a set of commonly probed locations by convention rather than specification.

## Technical Details

- Common specification file locations include `/openapi.json`, `/openapi.yaml`, `/swagger.json`, and versioned variants such as `/api/v1/openapi.json`.
- Common documentation UI paths include `/docs`, `/swagger`, `/swagger-ui`, `/redoc`, and `/api-docs`.
- The `.well-known` convention (RFC 8615) is used by some standardized discovery mechanisms (e.g., OAuth 2.0 Authorization Server Metadata, RFC 8414) but is not yet universally adopted for general REST API specification discovery.
- A specification document, once located, is typically itself in OpenAPI format (see the dedicated OpenAPI reference document) and can be parsed to enumerate every available operation.

## Detection Characteristics

- HTTP 200 response (rather than 404) at one or more conventional specification or documentation paths.
- Response `Content-Type` of `application/json`, `application/yaml`, or `text/html` (for interactive UIs) at a matching path.
- For JSON/YAML responses, presence of a root `openapi` or `swagger` version field confirms a genuine specification document rather than a coincidental 200 response.
- Absence of any response across the full set of conventional paths indicates no discoverable API surface via this mechanism (though an API may still exist without published discovery metadata).

## Common Implementations

- Framework-integrated auto-generation (e.g., FastAPI, NestJS, Spring) that serves both the specification JSON and an interactive UI from fixed, framework-default paths.
- API gateways that centralize and republish specification documents aggregated from multiple backend services.
- Manually maintained specification files committed to a repository and served statically.

## Limitations

- Discovery by convention is inherently probabilistic: a client must guess among known common paths, and a false negative (no response at any probed path) does not prove the absence of an API.
- No authentication-aware discovery standard exists; private or partner-only APIs may be technically discoverable but functionally unusable without credentials.
- Conventions vary by ecosystem/framework, so coverage requires maintaining an evolving list of candidate paths.

## Related Technologies

- OpenAPI Specification (the description format most commonly found via this discovery process)
- GraphQL introspection (an analogous but protocol-specific discovery mechanism)
- RFC 8615 `.well-known` URIs
- RFC 8414, OAuth 2.0 Authorization Server Metadata (a standardized example of `.well-known`-based discovery)

## Official References

- IETF RFC 8615, "Well-Known Uniform Resource Identifiers (URIs)"
- The OpenAPI Initiative, OpenAPI Specification
- IETF RFC 8414, "OAuth 2.0 Authorization Server Metadata"
