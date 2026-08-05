---
category: security
criterion: infrastructure_security
severity: medium
related:
  - https
---

# Infrastructure Security (Reverse Proxy, CDN, WAF Detection)

## Definition

Infrastructure security evaluates whether a website is fronted by a recognized reverse proxy, content delivery network (CDN), or web application firewall (WAF) — infrastructure layers providing caching, DDoS mitigation, and attack-pattern filtering before requests reach the origin server.

## Technical Background

Detection relies on vendor-specific response header fingerprints: the `Server` header value (e.g., containing "cloudflare"), or provider-specific headers independent of `Server` (e.g., `cf-ray` for Cloudflare, `x-amz-cf-id` for CloudFront, `x-served-by` for Fastly). No shared cross-vendor specification governs these headers.

## Importance for AI Agent Readiness

Infrastructure hardening improves the operational resilience an agent can rely on when interacting with a site repeatedly or at scale — a site behind a CDN/WAF is less likely to become unreachable under load or targeted disruption, and typically benefits from centrally managed baseline protections (rate limiting, malicious-pattern filtering) that reduce risk for both the site and its automated consumers.

## ARAS Evaluation Context

ARAS checks: `evidence.headers["server"]` against known provider keywords (`cloudflare`, `cloudfront`, `fastly`, `akamai`, `sucuri`, `incapsula`, `imperva`), OR presence of any provider-specific indicator header (`cf-ray`, `cf-cache-status`, `x-amz-cf-id`, `x-amz-cf-pop`, `x-served-by`, `x-akamai-transformed`, `x-akamaighost`, `x-sucuri-id`, `x-iinfo`).

Passed when: either the `Server` header matches a known provider, or any indicator header is present.

Failure condition: neither signal is present.

Failure message: "No recognized reverse proxy, CDN, or WAF detected."

## Common Issues

- Origin server exposed directly with no fronting CDN/WAF layer at all.
- Fronting infrastructure present but deliberately configured to suppress all identifying headers (a legitimate hardening choice that nonetheless produces a false-negative for this specific detection method).
- `Server` header masked or replaced with a generic value while genuinely using unprotected direct-to-origin hosting.

## Impact

- **Technical impact**: the origin bears full exposure to traffic spikes, scraping load, and volumetric attacks without an intermediary absorbing them.
- **AI agent impact**: repeated or higher-volume agent interaction is more likely to be perceived as abusive load on an unprotected origin, and the site itself is more likely to experience availability issues under any concurrent load.
- **Security impact**: medium — presence indicates infrastructure exists, not that it is correctly configured; absence indicates a weaker baseline posture, not an active vulnerability.

## Recommendation Strategy

Consider using a trusted reverse proxy or CDN to improve security, availability, and resilience, particularly one bundling WAF capabilities for baseline attack-pattern filtering ahead of the origin.

## Implementation Guidance

- **Cloudflare**: a common combined CDN+WAF offering, deployable by changing DNS to route traffic through Cloudflare's edge network.
- **AWS CloudFront + AWS WAF**: a combined offering for infrastructure already hosted on AWS.
- **Fastly**: a CDN offering with configurable edge logic and WAF add-ons.
- **Origin hardening**: once fronted, restrict direct origin access (IP allow-listing or shared-secret headers) so the fronting layer cannot be trivially bypassed.

## Validation Checklist

- `Server` header or a provider-specific indicator header confirms fronting infrastructure is in place.
- Origin server rejects direct traffic that bypasses the fronting layer.
- WAF rules (if included) are in enforcing, not merely monitoring, mode.

## Related ARAS Criteria

- `https` — TLS termination is commonly co-located with the same fronting infrastructure layer.

## References

Source: official_sources/security/infrastructure_security_reference.md
