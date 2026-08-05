---
category: interaction
criterion: api_documentation
severity: medium
related:
  - api_availability
  - graphql
---

# API Documentation (OpenAPI, Swagger, ReDoc)

## Definition

API documentation, in a machine-readable interaction context, refers to a formal specification document — most commonly conforming to the OpenAPI Specification — that fully describes an API's operations, parameters, schemas, and authentication requirements, reachable via a documentation UI (Swagger UI, ReDoc) or the raw specification file.

## Technical Background

The OpenAPI Specification (OpenAPI Initiative) defines paths, operations, and request/response schemas in JSON or YAML. Swagger UI and ReDoc are rendering tools consuming that document, not specifications themselves — the same file can be rendered by either interchangeably.

## Importance for AI Agent Readiness

Documentation is what lets an agent learn how to construct valid requests against an already-available API surface, without trial-and-error probing. Without it, even a technically reachable API remains effectively unusable by an automated client that has no prior knowledge of its parameters and schemas.

## ARAS Evaluation Context

ARAS checks: `evidence.api_analysis["openapi_urls"]`, `["swagger_urls"]`, `["redoc_urls"]`, `["api_documentation_urls"]`.

Passed when: at least one of these is non-empty.

Failure condition: all are empty.

Failure message: "No API documentation available."

## Common Issues

- API is live and callable but no OpenAPI/Swagger document exists at any conventional path.
- Specification file exists but is significantly out of sync with the actual deployed API behavior.
- Documentation UI reachable but the underlying specification file it fetches returns an error.
- Only OpenAPI 2.0 (Swagger) published without migration to the more capable, JSON-Schema-aligned 3.1.

## Impact

- **Technical impact**: integration work for any consumer requires manual reverse-engineering of the API's behavior.
- **AI agent impact**: an agent cannot programmatically learn the API's operations and schemas, blocking reliable automated request construction even when the API itself is reachable.
- **Security impact**: minimal directly, though undocumented parameter/schema requirements increase the risk of malformed or unintentionally unsafe client requests.

## Recommendation Strategy

Publish OpenAPI, Swagger, or API documentation, ideally auto-generated directly from the implementation (route/type annotations) so it cannot drift out of sync with actual behavior.

## Implementation Guidance

- **FastAPI**: OpenAPI document and Swagger UI are generated automatically by default; ensure they remain enabled in production if the API is meant to be externally discoverable.
- **NestJS**: `@nestjs/swagger` generates the specification from existing decorators.
- **Express / Node.js**: `swagger-jsdoc` + `swagger-ui-express` generate and serve documentation from route annotations.
- **Manually maintained specs**: schedule periodic verification against the live API to catch drift.

## Validation Checklist

- A specification document (JSON/YAML) is reachable and contains a valid `openapi`/`swagger` version field.
- A documentation UI renders the specification without errors.
- Documented endpoints and schemas match the API's actual current behavior.
- Authentication/security requirements are explicitly declared in the specification.

## Related ARAS Criteria

- `api_availability` — confirms the API this documentation describes is actually reachable.
- `graphql` — an alternative interaction style with its own self-description mechanism (introspection) rather than a separate specification file.

## References

Source: official_sources/interaction/api_documentation_reference.md
