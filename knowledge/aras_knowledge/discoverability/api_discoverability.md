---
category: discoverability
criterion: api_discoverability
severity: medium
related:
  - api_availability
  - api_documentation
---

# API Discoverability

## Definition

API discoverability concerns whether a website exposes machine-readable API documentation or specification files (OpenAPI, Swagger, GraphQL, generic API docs) reachable at conventional, predictable paths, independent of whether the API itself is separately confirmed reachable.

## Technical Background

No single specification governs discovery; the ecosystem relies on convention. Common specification file locations include `/openapi.json`, `/swagger.json`; common documentation UI paths include `/docs`, `/swagger`, `/redoc`. RFC 8615's `.well-known` URI convention offers a more standardized (but not universally adopted) alternative for machine metadata discovery.

## Importance for AI Agent Readiness

Discoverable API documentation lets an agent learn how to call a site's API programmatically without prior out-of-band knowledge. Its absence forces reliance on undocumented, error-prone guessing of endpoints and parameters, or on the frontend-interaction fallback (indirect discovery via client-side JavaScript).

## ARAS Evaluation Context

ARAS checks: `evidence.api_analysis` — specifically the combined presence of `openapi_urls`, `swagger_urls`, `graphql_endpoints`, `api_endpoints`, or `api_documentation_urls`.

Passed when: at least one of these lists is non-empty.

Failure condition: all are empty.

Failure message: "No API documentation found"

## Common Issues

- API exists and is callable, but no specification document or documentation UI is published at any conventional path.
- Specification file exists but is not linked from any documentation UI or discoverable index.
- Documentation is prose-only (a written guide) with no machine-parseable specification file behind it.
- Specification published at a non-conventional, undocumented path known only internally.

## Impact

- **Technical impact**: integration effort for any consumer (human or automated) increases substantially without a formal specification.
- **AI agent impact**: an agent cannot reliably construct valid API calls without a specification to parse, blocking a significant class of automated interaction entirely.
- **Security impact**: minimal directly, though undocumented APIs are more prone to inconsistent or unreviewed security practices.

## Recommendation Strategy

Publish OpenAPI or Swagger documentation for any exposed API, at a conventional, discoverable path, and reference it from the site's other discovery artifacts (e.g., `llms.txt`) where applicable.

## Implementation Guidance

- **FastAPI**: auto-generates and serves an OpenAPI document and interactive docs UI by default at `/openapi.json` and `/docs`.
- **Express / Node.js**: use `swagger-jsdoc` + `swagger-ui-express` to generate and serve a specification from route annotations.
- **NestJS**: `@nestjs/swagger` auto-generates the OpenAPI document from decorators.
- **Nginx / Cloudflare**: ensure the documentation path is not accidentally blocked by `robots.txt` or edge-layer access rules.

## Validation Checklist

- At least one conventional specification path (`/openapi.json`, `/swagger.json`) returns HTTP 200 with a valid `openapi`/`swagger` version field.
- A documentation UI (Swagger UI, ReDoc) is reachable and correctly renders the specification.
- The specification reflects the currently deployed API surface (not a stale prior version).

## Related ARAS Criteria

- `api_availability` — confirms the API is actually callable, distinct from documentation existing.
- `api_documentation` — the Interaction-dimension counterpart evaluating the same signal for interaction readiness.

## References

Source: official_sources/discoverability/api_discoverability_reference.md
