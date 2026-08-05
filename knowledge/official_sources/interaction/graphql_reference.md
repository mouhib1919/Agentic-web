# GraphQL

## Overview

GraphQL is a query language for APIs and a server-side runtime for executing those queries against a strongly typed schema. Unlike REST's multiple fixed endpoints, a GraphQL API exposes a single endpoint capable of answering arbitrarily shaped queries, letting a client request exactly the fields it needs across related entities in one round trip.

## Official Definition

GraphQL is specified by the GraphQL Foundation (part of the Linux Foundation, following Facebook's 2015 open-sourcing of the technology) through the GraphQL Specification, which formally defines the query language grammar, the type system, validation rules, and execution semantics.

## Core Concepts

- **Schema and type system**: every GraphQL API is described by a schema composed of object types, each with typed fields; the schema is itself introspectable at runtime.
- **Operations**: three root operation types — `Query` (read), `Mutation` (write), and `Subscription` (real-time updates over a persistent connection) — define the entry points into the schema.
- **Introspection**: the specification mandates a standard introspection system (queryable via the `__schema` and `__type` meta-fields) allowing any client to retrieve the complete schema — every type, field, and argument — without external documentation.
- **Resolvers**: server-side functions bound to schema fields that produce the field's value at execution time; the specification defines execution semantics but leaves resolver implementation to the server.

## Technical Details

- Transport: commonly HTTP POST to a single endpoint (conventionally `/graphql`) with a JSON body containing a `query` string and optional `variables`; the specification itself is transport-agnostic and does not mandate HTTP.
- Query document syntax: a typed selection-set language distinct from JSON, using curly-brace-delimited field selections, e.g., `{ user(id: "1") { name email } }`.
- Type system primitives: Scalar, Object, Interface, Union, Enum, Input Object, List, Non-Null — the full set of building blocks from which any schema is composed.
- Introspection query root fields: `__schema` (entire schema metadata) and `__type(name: String!)` (a single named type's metadata).

## Detection Characteristics

- An HTTP endpoint (commonly `/graphql`) accepting POST requests with a GraphQL query body and returning a JSON response shaped as `{"data": ..., "errors": ...}`.
- A successful response to an introspection query (`{ __schema { types { name } } }`) confirms both the endpoint's identity and that introspection is enabled.
- Presence of a GraphiQL or Apollo Sandbox/Explorer interactive interface at or near the endpoint path.
- GraphQL-specific error response shape (an `errors` array with `message`/`locations`/`path` fields) distinguishes it from a generic REST error response.

## Common Implementations

- A single unified endpoint aggregating data from multiple internal services or databases behind one GraphQL layer (a common "backend for frontend" pattern).
- Public, introspectable APIs paired with an interactive explorer (GraphiQL, Apollo Sandbox) for developer discovery.
- Introspection deliberately disabled in production for some APIs as a defensive measure, requiring an out-of-band schema document (SDL file) for discovery instead.

## Limitations

- No built-in specification for pagination, filtering, or authorization — these are addressed by widely adopted conventions (e.g., Relay's cursor-based connection pattern) rather than the core specification itself.
- Query complexity is client-determined; without server-side safeguards (depth limiting, cost analysis), deeply nested queries can impose disproportionate server load — the specification does not mandate any such protection.
- Introspection, while specified, is commonly disabled in production environments for security reasons, meaning its absence does not necessarily indicate the absence of a GraphQL API, only that self-description is unavailable.

## Related Technologies

- REST (the architectural style GraphQL is most commonly contrasted with)
- JSON (the typical response serialization format, though not mandated by the specification)
- Schema Definition Language (SDL), GraphQL's own IDL for expressing schemas outside of runtime introspection

## Official References

- GraphQL Foundation, "GraphQL Specification" (current edition)
- GraphQL.org, official documentation
