# API Documentation (OpenAPI, Swagger, ReDoc)

## Overview

API documentation, in a machine-readable interaction context, refers specifically to a formal specification document — most commonly conforming to the OpenAPI Specification — that fully describes an API's available operations, parameters, request/response schemas, and authentication requirements, as distinct from prose-only human-facing documentation that cannot be parsed programmatically.

## Official Definition

The OpenAPI Specification (OAS) is maintained by the OpenAPI Initiative under the Linux Foundation. It defines a language-agnostic, JSON- or YAML-formatted schema for describing REST APIs, evolved from the originally proprietary Swagger Specification (donated to the OpenAPI Initiative in 2015). Swagger UI and ReDoc are open-source rendering tools, not specifications themselves, that consume an OpenAPI document to produce interactive or static human-readable documentation.

## Core Concepts

- **Specification vs. rendering tool**: the OpenAPI document is the authoritative machine-readable artifact; Swagger UI and ReDoc are two of several possible renderers that transform that document into a browsable interface — the same OpenAPI file can be rendered by either tool interchangeably.
- **Paths and operations**: the OpenAPI document's `paths` object enumerates every endpoint and, per endpoint, every supported HTTP method, forming the complete operational surface of the API.
- **Schema objects**: request and response bodies are described using a JSON Schema-derived format embedded in the `components/schemas` section, enabling full type validation without executing any request.
- **Security schemes**: the `components/securitySchemes` section formally declares supported authentication mechanisms (API key, OAuth2, HTTP bearer, etc.), referenced per-operation via `security` requirements.

## Technical Details

- Root document fields: `openapi` (version string, e.g., `3.1.0`), `info` (title, version, description), `paths`, `components`, `servers`.
- Format: JSON or YAML; both are formally equivalent serializations of the same schema.
- Current major version: OpenAPI 3.1, which aligned its schema dialect with JSON Schema 2020-12 (earlier 3.0.x used a JSON-Schema-like but non-conformant subset).
- Swagger UI conventionally serves at a `/docs` or `/swagger` path and fetches the underlying OpenAPI JSON/YAML file via a configured URL.
- ReDoc similarly consumes an OpenAPI document but renders a static, three-panel documentation layout rather than Swagger UI's interactive "try it out" console.

## Detection Characteristics

- A JSON or YAML document containing a top-level `openapi` (3.x) or `swagger` (2.0, legacy) version field, located at a conventional path.
- An HTML page embedding the Swagger UI JavaScript bundle, typically identifiable by characteristic script/style references and a `SwaggerUIBundle` initialization call.
- An HTML page embedding ReDoc's `<redoc>` custom element or its bundled JavaScript.
- Presence of an interactive "Try it out" execution panel is specific to Swagger UI; ReDoc is documentation-only without built-in request execution.

## Common Implementations

- Framework-native auto-generation (FastAPI, NestJS with `@nestjs/swagger`, Spring with springdoc) producing both the OpenAPI document and a bundled UI from route/type annotations.
- Manually authored OpenAPI YAML files maintained in a repository, rendered via a standalone Swagger UI or ReDoc deployment, decoupled from the API's own runtime.
- API gateway platforms that aggregate and republish OpenAPI documents from multiple backend services under one documentation portal.

## Limitations

- An OpenAPI document can drift out of sync with the actual deployed API behavior if not generated directly from the implementation (manually maintained specifications are especially prone to this).
- OpenAPI 3.0.x's schema dialect has known incompatibilities with standard JSON Schema tooling, requiring 3.1 for full JSON Schema alignment — many still-deployed APIs use 3.0.x.
- Neither Swagger UI nor ReDoc validates that example values or the live API's actual responses conform to the declared schemas; documentation accuracy is not self-verifying.

## Related Technologies

- JSON Schema (the type-description language OpenAPI 3.1 aligns with)
- GraphQL introspection (an analogous but protocol-native self-description mechanism, requiring no separate specification file)
- REST architectural constraints (the style OpenAPI-described APIs typically, though not universally, follow)

## Official References

- The OpenAPI Initiative, OpenAPI Specification 3.1
- Swagger UI, official project documentation
- ReDoc, official project documentation
