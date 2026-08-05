# API Availability (Executable Interaction Surfaces)

## Overview

API availability concerns whether a website exposes at least one callable, programmatic interface — REST, GraphQL, or otherwise — that a client can invoke directly to retrieve or manipulate data, as distinct from merely publishing documentation about an API that may or may not have a working, reachable endpoint behind it.

## Official Definition

There is no single specification defining "API availability" as a formal concept; it is an operational/architectural property evaluated against the concrete network-accessible endpoints a service exposes, most commonly conforming to REST architectural constraints (as described by Roy Fielding's dissertation, not a W3C/IETF standard) or the GraphQL specification (GraphQL Foundation).

## Core Concepts

- **Executable vs. descriptive surface**: an available API is one that responds to actual requests (e.g., HTTP GET/POST to a resource endpoint), which is a stronger condition than the mere existence of documentation or a specification file describing an API that may not be live.
- **REST architectural constraints**: statelessness, a uniform interface, resource-based addressing, and client-server separation, as originally described by Fielding — REST is a set of architectural constraints, not a protocol or format with a formal specification document.
- **Endpoint reachability**: a functioning API surface responds with a valid, non-error status code to well-formed requests, as opposed to returning uniformly 404 (not found) or 501 (not implemented).
- **Distinct from documentation availability**: an API can be technically live and callable while being entirely undocumented, and conversely, documentation can exist for endpoints that have since been deprecated or removed.

## Technical Details

- HTTP methods (`GET`, `POST`, `PUT`, `PATCH`, `DELETE`) mapped to resource operations following REST conventions.
- Response status codes (2xx success, 4xx client error, 5xx server error) as defined in RFC 9110 ("HTTP Semantics") indicate whether an endpoint is genuinely implemented versus absent.
- Content negotiation via the `Accept`/`Content-Type` headers, typically `application/json` for modern REST APIs.
- Versioning conventions (URL path versioning `/v1/`, header-based versioning) are common but not standardized by any single specification.

## Detection Characteristics

- A non-404, non-generic-error HTTP response from a candidate endpoint path (e.g., `/api/`, `/api/v1/`), particularly one returning structured (JSON) content rather than an HTML error page.
- Presence of programmatically discoverable API traffic in client-side JavaScript (fetch/XHR calls to same-origin or partner API paths).
- A distinct GraphQL endpoint (commonly `/graphql`) responding to POST requests with a GraphQL-shaped JSON response.

## Common Implementations

- A dedicated API subdomain or path prefix (`api.example.com`, `example.com/api/`) separate from the main web application.
- Backend-for-frontend patterns where the same origin serving HTML also exposes internal API routes consumed by client-side JavaScript.
- Public partner/developer APIs exposed alongside, but architecturally separate from, the consumer-facing website.

## Limitations

- Reachability alone does not imply the API is intended for external/public consumption; internal-only APIs can appear identical to public ones from an external observer's perspective without authentication context.
- No standardized "liveness" signal exists (unlike, for example, a health-check convention); availability must be inferred from response behavior at candidate paths, which is inherently probabilistic.
- Rate limiting, authentication walls, or IP allow-listing can make a technically available API appear unavailable to an unauthenticated or unrecognized client.

## Related Technologies

- OpenAPI Specification (the description format for a REST API, once availability is confirmed)
- GraphQL (an alternative query-based interaction model)
- HTTP semantics (RFC 9110), the transport-and-status-code foundation of REST availability signals

## Official References

- IETF RFC 9110, "HTTP Semantics"
- Roy T. Fielding, "Architectural Styles and the Design of Network-based Software Architectures" (REST, doctoral dissertation, 2000)
- GraphQL Foundation, GraphQL Specification
