# Model Context Protocol (MCP) — Endpoint and Transport

## Overview

The Model Context Protocol (MCP) is an open protocol that standardizes how AI applications (hosts/clients, such as an LLM-powered agent) connect to external systems (servers) that expose data, tools, and interaction capabilities. An MCP endpoint is the network-reachable address through which a client establishes a session with an MCP server, distinct from a REST or GraphQL endpoint in that it is designed specifically for agent-oriented, capability-negotiated interaction rather than generic data retrieval.

## Official Definition

MCP is specified and maintained by Anthropic, published as an open specification at `modelcontextprotocol.io`, with governance moving toward broader multi-vendor community stewardship. The specification defines the protocol's message format, lifecycle, transport bindings, and the set of standard primitives (resources, tools, prompts) a server may expose.

## Core Concepts

- **Client-server session model**: an MCP client (embedded in a host application, e.g., an AI agent runtime) initiates a session with an MCP server over a defined transport, beginning with a capability-negotiation handshake.
- **JSON-RPC 2.0 base protocol**: all MCP messages — requests, responses, notifications — are encoded as JSON-RPC 2.0 messages, giving the protocol a well-defined, pre-existing message envelope and error-handling model.
- **Transports**: the specification defines two standard transport bindings — `stdio` (the server is a local subprocess communicating over standard input/output, used for local integrations) and Streamable HTTP (a network-reachable HTTP(S) endpoint, which may use Server-Sent Events for streaming server-to-client messages).
- **Capability negotiation**: during session initialization, client and server each declare which protocol capabilities (resources, tools, prompts, sampling, and others) they support, allowing graceful interoperability between servers and clients of differing feature sets.

## Technical Details

- Initialization handshake: the client sends an `initialize` request declaring its protocol version and capabilities; the server responds with its own supported version and capabilities; the client confirms with an `initialized` notification before normal operation begins.
- HTTP transport: a single HTTP endpoint accepts POST requests carrying JSON-RPC messages and may respond either with a direct JSON response or an `text/event-stream` (SSE) stream for asynchronous/streaming responses; session continuity is managed via an `Mcp-Session-Id` header in the Streamable HTTP transport.
- Protocol versioning: negotiated as a date-stamped version string (e.g., `2025-06-18`) during initialization, allowing servers and clients to detect and handle version mismatches explicitly.
- Message types: Requests (expect a response), Responses (result or error), and Notifications (one-way, no response expected) — the standard JSON-RPC 2.0 taxonomy.

## Detection Characteristics

- An HTTP(S) endpoint accepting POST requests with JSON-RPC 2.0-formatted bodies (`{"jsonrpc": "2.0", "method": ..., "id": ...}`).
- A successful response to an `initialize` request, returning `protocolVersion`, `capabilities`, and `serverInfo` fields.
- Endpoint conventionally exposed at a path such as `/mcp`, though the specification does not mandate a fixed path.
- Response `Content-Type` of `application/json` (single response) or `text/event-stream` (streaming) is characteristic of the Streamable HTTP transport.

## Common Implementations

- Standalone MCP servers exposing a single domain's capabilities (e.g., a database, a SaaS product's API, a file system) over stdio for local desktop AI assistants.
- Remote, multi-tenant MCP servers exposed over Streamable HTTP for cloud-hosted agent platforms.
- Gateway/aggregator servers that expose multiple underlying MCP servers' capabilities through one unified endpoint.

## Limitations

- The protocol does not itself mandate authentication; the specification references OAuth 2.1 as the recommended authorization framework for HTTP-based servers but leaves stdio-based local servers to rely on process-level trust.
- Version negotiation failures (client and server supporting disjoint protocol version ranges) are handled by the specification but still result in a non-functional session if no common version exists.
- As a comparatively new specification, ecosystem tooling and third-party client support are less mature and less standardized than long-established protocols like REST or GraphQL.

## Related Technologies

- JSON-RPC 2.0 (the base message protocol MCP is built on)
- Server-Sent Events (the streaming mechanism used by the Streamable HTTP transport)
- OAuth 2.1 (the recommended authorization framework referenced by the specification for remote servers)

## Official References

- Anthropic, "Model Context Protocol Specification" (modelcontextprotocol.io)
- JSON-RPC Working Group, "JSON-RPC 2.0 Specification"
