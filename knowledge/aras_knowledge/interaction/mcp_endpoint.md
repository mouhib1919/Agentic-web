---
category: interaction
criterion: mcp_endpoint
severity: medium
related:
  - mcp_tools
---

# Model Context Protocol (MCP) Endpoint Availability

## Definition

MCP endpoint availability evaluates whether a website exposes a Model Context Protocol endpoint — a JSON-RPC 2.0-based, network-reachable address (per the Anthropic-maintained MCP Specification) through which an AI agent host/client can establish a capability-negotiated session, distinct from generic REST/GraphQL interfaces.

## Technical Background

MCP sessions begin with an `initialize` handshake exchanging protocol version and capabilities before any tool/resource interaction. The Streamable HTTP transport exposes a single endpoint accepting POST requests carrying JSON-RPC messages, conventionally at a path such as `/mcp`, though the specification does not mandate a fixed path.

## Importance for AI Agent Readiness

MCP is a protocol designed specifically for agent-native interaction rather than adapted from general-purpose web APIs. Its presence is the clearest possible signal that a site has invested in first-class AI agent interoperability, offering structured, self-describing tools and resources rather than requiring an agent to reverse-engineer a REST/GraphQL surface.

## ARAS Evaluation Context

ARAS checks: `evidence.api_analysis["mcp_endpoints"]`.

Passed when: `mcp_endpoints` is non-empty.

Failure condition: `mcp_endpoints` is empty.

Failure message: "No MCP endpoint detected."

## Common Issues

- No MCP endpoint at all — still the most common state, since the specification and its ecosystem are comparatively recent.
- Endpoint present at a non-conventional path with no discovery reference elsewhere on the site.
- Endpoint present but the `initialize` handshake fails or returns an unsupported protocol version with no graceful negotiation.

## Impact

- **Technical impact**: no agent-native protocol surface exists; any AI-driven interaction must go through generic REST/GraphQL adaptation.
- **AI agent impact**: agents built around MCP-native tooling cannot connect at all, forcing a fallback to slower, less structured interaction methods.
- **Security impact**: minimal directly; the specification references OAuth 2.1 as the recommended authorization framework for remote servers, so absence is not itself a vulnerability.

## Recommendation Strategy

Provide MCP interfaces to expose agent-native capabilities, starting with a minimal Streamable HTTP endpoint implementing the standard initialization handshake before adding tools/resources.

## Implementation Guidance

- **Official SDKs**: use the language-specific MCP SDKs (Python, TypeScript) maintained alongside the specification to implement handshake and transport handling correctly.
- **Node.js / Express**: expose the MCP endpoint as a dedicated route accepting JSON-RPC POST bodies, with SSE support for streaming responses where needed.
- **Authentication**: pair with OAuth 2.1 for remote, multi-tenant deployments per the specification's recommendation.

## Validation Checklist

- The endpoint accepts POST requests with JSON-RPC 2.0-formatted bodies.
- An `initialize` request returns a valid response with `protocolVersion`, `capabilities`, and `serverInfo`.
- The negotiated protocol version is current and documented.

## Related ARAS Criteria

- `mcp_tools` — the capabilities (tools/resources) exposed once a session with this endpoint is established.

## References

Source: official_sources/interaction/mcp_endpoint_reference.md
