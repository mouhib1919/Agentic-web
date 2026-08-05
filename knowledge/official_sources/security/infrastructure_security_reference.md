# Infrastructure Security (Reverse Proxies, CDNs, and Web Application Firewalls)

## Overview

Infrastructure security, in the context of externally observable signals, concerns whether a website is fronted by a recognized reverse proxy, content delivery network (CDN), or web application firewall (WAF) — infrastructure layers that sit between the client and the origin server to provide caching, DDoS mitigation, traffic filtering, and attack-pattern blocking before requests ever reach the origin.

## Official Definition

No single specification defines "infrastructure security" as a formal category; it is an architectural pattern combining several independently specified or vendor-defined mechanisms — reverse proxying (an HTTP intermediary role described generally in RFC 9110's HTTP terminology), CDN edge delivery (a commercial/operational pattern, not a standardized protocol), and WAF filtering (a security control category defined by industry bodies such as OWASP rather than a formal IETF/W3C specification).

## Core Concepts

- **Reverse proxy**: an intermediary that receives client requests on behalf of one or more origin servers, forwarding them internally and returning the origin's response to the client — as opposed to a forward proxy, which acts on behalf of the client toward arbitrary destinations.
- **CDN**: a globally distributed network of edge servers caching and serving content geographically closer to the requesting client, typically also absorbing traffic spikes and volumetric attacks before they reach the origin.
- **WAF**: a filtering layer that inspects incoming HTTP requests against known attack signatures (SQL injection, XSS payloads, malicious bot patterns) and blocks or challenges requests matching those patterns, independent of the origin application's own input handling.
- **Observable fronting signals**: because these layers intermediate all traffic, they typically leave characteristic, vendor-specific fingerprints in response headers, even though their presence is an infrastructural choice rather than a standardized, self-declaring protocol.

## Technical Details

- `Server` header: some (not all) reverse proxies/CDNs identify themselves via the `Server` response header (e.g., a value containing `cloudflare`), though many deliberately omit or obscure this for security-through-obscurity reasons.
- Vendor-specific headers: providers commonly inject their own identifying headers or values independent of `Server` — for example, Cloudflare's `cf-ray` and `cf-cache-status`, or Amazon CloudFront's `x-amz-cf-id` and `x-amz-cf-pop` — which persist even when the generic `Server` header is masked.
- Fastly and other CDNs similarly use headers such as `x-served-by` or `x-cache` to expose caching/routing metadata.
- None of these headers are governed by a shared cross-vendor specification; each provider defines and documents its own header set independently.

## Detection Characteristics

- `Server` header value containing a recognized provider name (Cloudflare, Akamai, Fastly, Sucuri, Imperva/Incapsula, among others).
- Presence of any provider-specific identifying header (e.g., `cf-ray`, `x-amz-cf-id`, `x-served-by`, `x-akamai-transformed`) independent of whether the `Server` header itself is populated or masked.
- Absence of both generic and vendor-specific indicators suggests either a direct-to-origin deployment or a fronting layer configured to fully suppress identifying signals.

## Common Implementations

- CDN-fronted static and dynamic content delivery combined with edge-level caching rules.
- WAF rule sets applied at the same edge layer as CDN/reverse-proxy functionality (commonly bundled as a single commercial offering, e.g., Cloudflare's combined CDN+WAF product).
- Origin servers configured to reject direct traffic that bypasses the fronting layer, enforced via IP allow-listing or shared-secret headers, ensuring the fronting layer cannot be trivially circumvented.

## Limitations

- Absence of detectable fronting-layer signals does not prove the absence of such infrastructure — deliberate header suppression is itself a recognized hardening practice, meaning a well-configured deployment can appear indistinguishable from an unprotected one via header inspection alone.
- Presence of a CDN/WAF signal indicates the existence of that infrastructure layer, not the correctness or strength of its actual configuration (e.g., a WAF can be present but running in permissive/monitoring-only mode).
- Header-based detection is inherently a fingerprinting technique, not a specification-driven guarantee; providers can and do change header behavior between product tiers or configurations.

## Related Technologies

- Reverse proxy software (general architectural role, e.g., as commonly implemented by nginx, Envoy, HAProxy)
- DDoS mitigation services, frequently bundled with CDN/WAF offerings
- TLS termination, commonly co-located with the same fronting infrastructure layer

## Official References

- IETF RFC 9110, "HTTP Semantics" — intermediary (proxy) terminology
- OWASP, "Web Application Firewall" definition and guidance
- IANA, "Message Headers" registry (context for vendor-specific header registration practices)
