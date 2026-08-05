---
category: interaction
criterion: mcp_tools
severity: medium
related:
  - mcp_endpoint
---

# MCP Tools and Resources

## Definition

MCP Tools and Resources are the two core server-side primitives defined by the Model Context Protocol: Tools expose discrete, schema-validated, invocable actions; Resources expose readable, URI-addressable data — together forming the explicit, structured capability surface an MCP server offers beyond mere endpoint reachability.

## Technical Background

Each tool is described by a `name`, `description`, and JSON Schema `inputSchema`, discoverable via a `tools/list` request and invoked via `tools/call`. Each resource is identified by a URI, discoverable via `resources/list` and retrieved via `resources/read`. Both are only exposed if the server declared the corresponding capability during initialization.

## Importance for AI Agent Readiness

Tools and Resources are what actually make an MCP endpoint useful to an agent: the endpoint alone only establishes a session, while tools/resources define the concrete, schema-validated actions and data the connected AI model can take or retrieve. Their absence means an MCP session, even if established, has nothing meaningful to offer.

## ARAS Evaluation Context

ARAS checks: `evidence.api_analysis["mcp_tools"]` and `evidence.api_analysis["mcp_resources"]`.

Passed when: `mcp_tools` OR `mcp_resources` is non-empty.

Failure condition: both are empty.

Failure message: "No MCP tools or resources available."

## Common Issues

- An MCP endpoint exists and the handshake succeeds, but no tools or resources are registered, offering an empty capability surface.
- Tools registered without a well-formed `inputSchema`, leaving arguments unvalidated and ambiguous to the calling model.
- Overly broad tool definitions that bundle multiple unrelated actions into a single tool, reducing the model's ability to select the correct one.

## Impact

- **Technical impact**: a technically reachable MCP server provides no actionable capability, functionally equivalent to no MCP support at all.
- **AI agent impact**: the connected AI model has nothing explicit and structured to act on or retrieve, defeating the primary purpose of implementing MCP in the first place.
- **Security impact**: minimal directly, though poorly scoped tools (when they do exist) carry an operational risk of unintended actions — a design concern for whoever implements the tool set, not evaluated by this criterion.

## Recommendation Strategy

Expose MCP tools and resources describing available actions, starting with a small number of well-scoped, clearly named tools wrapping existing core operations, and resources exposing the most useful read-only context.

## Implementation Guidance

- **Official MCP SDKs**: register tools with an explicit JSON Schema for `inputSchema` and a clear, specific `description` the model can use to decide when to invoke it.
- **Wrapping existing systems**: expose tools as thin wrappers around already-existing REST/CLI operations rather than building new business logic specifically for MCP.
- **Resources**: expose read-only context (documentation, records) that would otherwise require a separate API call to retrieve.

## Validation Checklist

- `tools/list` returns one or more entries with valid `name` and `inputSchema`.
- `resources/list` returns one or more URI-addressable entries, if resources are the chosen primitive.
- Tool invocation (`tools/call`) with valid arguments returns a well-formed result.
- The `capabilities` object returned at `initialize` correctly declares `tools`/`resources` support.

## Related ARAS Criteria

- `mcp_endpoint` — the underlying session-establishing endpoint these primitives are exposed through.

## References

Source: official_sources/interaction/mcp_tools_reference.md
