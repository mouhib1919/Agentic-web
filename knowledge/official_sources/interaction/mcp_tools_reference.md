# Model Context Protocol (MCP) — Tools and Resources

## Overview

Tools and Resources are two of the core server-side primitives defined by the Model Context Protocol: Tools expose discrete, invocable actions a client (typically an AI model acting through an agent) can execute with defined inputs and outputs, while Resources expose readable, addressable data a client can retrieve as context — together forming the primary means by which an MCP server offers explicit, structured capabilities rather than free-form access.

## Official Definition

Both primitives are formally defined in the Model Context Protocol Specification maintained by Anthropic. Tools are defined as model-controlled functions the client (and, through it, the connected AI model) can invoke; Resources are defined as application-controlled data sources the client can read, distinct from Tools in that they represent state to be retrieved rather than actions to be performed.

## Core Concepts

- **Tools**: each tool is described by a unique `name`, a human/model-readable `description`, and an `inputSchema` expressed in JSON Schema, formally defining the arguments the tool accepts before it is ever invoked.
- **Tool invocation**: a client calls a tool via a `tools/call` request naming the tool and supplying arguments conforming to its schema; the server executes the corresponding action and returns a structured result (text, image, or embedded resource content).
- **Resources**: each resource is identified by a URI, with an optional MIME type, and can be read via a `resources/read` request; resources may be static or templated (parameterized URIs enumerable via `resources/templates/list`).
- **Discovery**: both primitives are enumerable before use — `tools/list` returns every available tool and its schema; `resources/list` returns every available resource — allowing a client (or the AI model behind it) to learn what is available without prior hardcoded knowledge.
- **Capability declaration**: a server only exposes `tools/*` or `resources/*` methods if it declared the corresponding capability (`tools`, `resources`) during the initialization handshake.

## Technical Details

- Tool listing response: an array of objects, each with `name`, `description`, and `inputSchema` (a JSON Schema object describing expected parameters).
- Tool call request: `{"method": "tools/call", "params": {"name": "...", "arguments": {...}}}`; the result contains a `content` array (text, image, or resource blocks) and an `isError` flag for execution failures distinct from protocol-level errors.
- Resource listing response: an array of objects with `uri`, `name`, and optional `mimeType` and `description` fields.
- Resource read request: `{"method": "resources/read", "params": {"uri": "..."}}`; the result contains the resource's content, either as text or base64-encoded binary data.
- Change notifications: servers may declare support for `listChanged` notifications, informing clients when the available set of tools or resources has changed dynamically.

## Detection Characteristics

- A successful `tools/list` response returning one or more entries with valid `name`/`inputSchema` fields indicates tool availability.
- A successful `resources/list` response returning one or more URI-addressable entries indicates resource availability.
- The `capabilities` object returned during `initialize` explicitly declares whether `tools` and/or `resources` are supported before any listing call is attempted.
- Absence of both capabilities in the initialization response indicates a server offering neither primitive (e.g., a prompts-only or sampling-only server).

## Common Implementations

- Tools wrapping existing REST/CLI operations (e.g., "create_ticket," "run_query") to give an AI model an explicit, schema-validated action surface instead of raw API access.
- Resources exposing read-only context such as file contents, database records, or documentation, intended to be retrieved and inserted into an AI model's context window.
- Combined servers exposing both: resources for grounding context and tools for taking action on the same underlying system.

## Limitations

- Tool and resource sets are server-defined and can vary arbitrarily between implementations; no universal registry of standard tool/resource names exists across the MCP ecosystem.
- Input/output validation relies on JSON Schema conformance for tool arguments; the specification does not mandate runtime enforcement beyond what the server chooses to implement.
- Because tools are model-invocable, poorly scoped or overly broad tool definitions carry a real operational risk (unintended or unsafe actions), which the specification addresses only through general human-in-the-loop guidance, not an enforced technical control.

## Related Technologies

- JSON Schema (the format used to describe tool input parameters)
- MCP Prompts (a third primitive, user-controlled reusable prompt templates, distinct from Tools and Resources)
- REST/GraphQL APIs (frequently the underlying systems that MCP tools and resources wrap)

## Official References

- Anthropic, "Model Context Protocol Specification" — Tools and Resources sections (modelcontextprotocol.io)
