---
category: security
criterion: http_status
severity: medium
related:
  - https
---

# HTTP Response Status (Homepage Availability)

## Definition

This criterion evaluates whether the assessed website's homepage responds with a successful (HTTP 200) status code, as defined by IETF RFC 9110, confirming the site is genuinely reachable and correctly serving content rather than erroring or being unavailable.

## Technical Background

RFC 9110 organizes status codes into five classes by leading digit; 2xx indicates success, 4xx client error, 5xx server error. A homepage consistently returning 2xx is the baseline availability signal any monitoring or evaluation system relies on.

## Importance for AI Agent Readiness

Every other ARAS evaluation depends on evidence collected from a successfully retrieved homepage. If the homepage itself does not return 200, an agent cannot reliably retrieve any content at all, making this the most foundational availability signal in the entire assessment.

## ARAS Evaluation Context

ARAS checks: `evidence.status_code`.

Passed when: `status_code == 200`.

Failure condition: `status_code` is any value other than 200 (including `None`, if the request failed outright).

Failure message: "The homepage did not respond with HTTP 200."

## Common Issues

- Homepage temporarily or persistently returning a 5xx error (server misconfiguration, upstream failure).
- Homepage returning a 3xx redirect that is not followed to a final 200 response, or that redirects into a loop.
- Homepage returning a 4xx error, often due to misconfigured routing or access rules blocking the evaluated client.
- A "soft 404": a 200 response whose body nonetheless displays an error/not-found message.

## Impact

- **Technical impact**: the site is effectively unreachable or malfunctioning for the request path evaluated.
- **AI agent impact**: no evidence can be collected at all if the homepage does not respond successfully, blocking every downstream ARAS dimension (discoverability, comprehension, interaction, and the rest of security) simultaneously.
- **Security impact**: persistent unavailability can itself indicate an ongoing incident (misconfiguration, overload, or attack) worth investigating.

## Recommendation Strategy

Ensure the homepage responds with a successful HTTP status code: investigate and resolve the underlying cause (server error, misconfigured redirect, access rule) preventing a consistent 200 response.

## Implementation Guidance

- **Monitoring**: implement uptime/health-check monitoring on the homepage to catch regressions before they are discovered externally.
- **Nginx / Apache**: verify routing/rewrite rules do not inadvertently 404 or redirect-loop the root path.
- **Load balancers**: confirm upstream origin health checks are correctly configured to avoid routing traffic to unhealthy instances.

## Validation Checklist

- `GET /` (the homepage) returns HTTP 200 consistently across repeated requests.
- Any redirect chain terminates in a 200 response within a reasonable number of hops.
- The 200 response body reflects genuine page content, not an embedded error message ("soft 404").

## Related ARAS Criteria

- `https` — the scheme under which this status code is evaluated; both must be correct for a fully trustworthy baseline.

## References

Source: official_sources/security/http_status_reference.md
