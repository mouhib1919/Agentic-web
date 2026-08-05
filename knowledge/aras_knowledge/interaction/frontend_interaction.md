---
category: interaction
criterion: frontend_interaction
severity: low
related:
  - api_availability
---

# Frontend-Discoverable Interaction Capabilities

## Definition

Frontend interaction capabilities are API and interactive endpoints a client-side JavaScript application references at runtime, discoverable through static analysis of the shipped JavaScript bundle even when no formally documented or independently reachable API surface exists — a fallback interaction signal.

## Technical Background

Static analysis inspects downloaded JavaScript file contents for path-like string literals matching REST conventions (`/api/`), GraphQL paths (`/graphql`), or WebSocket URLs (`ws://`/`wss://`), without executing the code. This reveals what the site's own frontend can call, even absent formal documentation.

## Importance for AI Agent Readiness

When no formal API documentation or MCP interface exists, evidence of frontend-referenced endpoints is the last remaining signal that a site has any programmatic interaction surface at all — a weaker, indirect signal compared to a documented API, but still meaningfully better than none.

## ARAS Evaluation Context

ARAS checks: `evidence.frontend_analysis["discovered_api_urls"]`, `["graphql_references"]`, `["websocket_references"]`.

Passed when: the combined list of frontend-discovered actions is non-empty.

Failure condition: all three lists are empty.

Failure message: "No actionable frontend interaction detected."

## Common Issues

- Frontend built as a fully server-rendered application with no client-side API calls at all (not necessarily a defect, but yields no signal for this criterion).
- Endpoint paths constructed dynamically at runtime (string concatenation) rather than as static literals, hiding them from static analysis.
- Heavily obfuscated/minified bundles that fragment recognizable path patterns across variables.

## Impact

- **Technical impact**: none on the site's actual functionality; this criterion measures external observability, not correctness.
- **AI agent impact**: without any discoverable frontend interaction evidence — and no formal API — an agent has essentially no path to programmatic interaction with the site at all.
- **Security impact**: none directly, though the discovered patterns can indicate an unintentionally exposed internal API surface worth reviewing separately.

## Recommendation Strategy

Expose structured actions or machine-readable interaction surfaces — ideally a formally documented API or MCP interface rather than relying on frontend-inferred signals, which are inherently indirect and incomplete.

## Implementation Guidance

- **Primary fix**: treat this as a symptom, not the target — the real remediation is publishing a documented API (`api_documentation`) or MCP interface (`mcp_endpoint`), which supersedes reliance on frontend inference entirely.
- **If frontend-only interaction is intentional**: ensure at least the core interaction endpoints remain as static, non-obfuscated string literals in the shipped bundle, or, better, publish them formally.

## Validation Checklist

- A published API or MCP endpoint exists, making this fallback criterion unnecessary to rely on.
- If no formal API exists, verify whether frontend-referenced endpoints could be reasonably formalized into a documented surface.

## Related ARAS Criteria

- `api_availability` — the criterion this frontend-inferred signal substitutes for when no formal API is confirmed.

## References

Source: official_sources/interaction/frontend_interaction_reference.md
