# OpenAPI

## Purpose

OpenAPI (formerly Swagger) is a standardized specification format for describing REST APIs in a machine-readable document, typically JSON or YAML, published at a predictable location such as `/openapi.json` or surfaced through interactive documentation tools like Swagger UI or ReDoc. An OpenAPI document formally describes every available endpoint, its HTTP methods, expected request parameters, request and response schemas, authentication requirements, and possible error responses. It turns an API from something a developer must learn by reading prose documentation or trial and error into something a program can parse and act on directly.

## Why it matters

For AI agent readiness, an OpenAPI specification is the difference between an agent that can reliably call an API and one that cannot use it at all. Without a machine-readable contract, an agent has no dependable way to know which endpoints exist, what parameters they expect, or what shape the response will take — it would have to guess from documentation prose, which is fragile and error-prone. With OpenAPI, an agent (or a code-generation tool acting on its behalf) can programmatically enumerate every available operation and construct valid requests with correct parameter types, headers, and authentication, turning the API into a directly executable interaction surface rather than a black box that requires human-authored integration code.

## When ARAS recommends it

The Recommendation Agent should retrieve this document when the Interaction Agent reports:

- No OpenAPI, Swagger, or ReDoc documentation found at any standard location.
- Raw API endpoints detected (e.g. via frontend JavaScript analysis) but no accompanying specification describing them.
- API documentation present in prose/HTML form only, with no machine-readable equivalent.

## Implementation Guidelines

Generate the OpenAPI document from the API's actual route definitions and validation schemas wherever possible, using framework integrations that keep the specification synchronized with the implementation automatically, rather than maintaining a separate hand-written document that can drift out of date. Publish the resulting JSON or YAML file at a conventional, discoverable path (`/openapi.json`, `/api/openapi.json`, or referenced from `/swagger` or `/docs`), and expose an interactive documentation UI (Swagger UI or ReDoc) at a well-known path so both humans and automated discovery tools can find it easily. Describe every endpoint's request parameters, request body schema, response schema for each status code, and authentication requirements (API key, OAuth, bearer token) using the `securitySchemes` section. Include realistic examples for request and response bodies, since examples significantly improve an agent's ability to construct correct calls without trial and error.

## Best Practices

- Auto-generate the specification from code (route decorators, validation schemas) instead of hand-authoring it separately.
- Publish it at a predictable, well-known path and reference it from other discovery mechanisms (`llms.txt`, API landing pages).
- Keep descriptions and examples accurate and complete for every operation, not just the most commonly used ones.
- Version the API and reflect versioning clearly in the specification (path versioning or the `info.version` field).
- Document authentication and rate-limiting requirements explicitly, since these are essential for an agent to use the API correctly.
- Validate the specification against the OpenAPI schema before publishing to catch structural errors.

## Common Mistakes

- Publishing an outdated specification that no longer matches the live API's actual behavior.
- Omitting authentication requirements, leaving an agent unable to determine how to authenticate calls.
- Providing only minimal endpoint descriptions without example requests or responses.
- Hiding the specification behind a path that is not referenced anywhere else, making it effectively undiscoverable.
- Describing error responses inconsistently or not at all, leaving agents unable to handle failure cases gracefully.

## Expected Benefits

For AI agents, a published OpenAPI specification enables direct, reliable programmatic use of an API — agents (and the tools that generate clients for them) can construct valid requests without human intervention. For search engines, this has limited direct effect, but for machine readability broadly, it is the clearest possible signal that an API is intended for automated, third-party consumption rather than internal use only. It also reduces integration friction for any automated system, human developer or AI agent alike.

## References

- The OpenAPI Initiative: the OpenAPI Specification (current and prior versions).
- Swagger: tooling built around the OpenAPI specification, including Swagger UI.
- ReDoc: an alternative interactive documentation renderer for OpenAPI documents.
