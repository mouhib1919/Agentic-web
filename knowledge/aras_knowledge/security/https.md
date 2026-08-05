---
category: security
criterion: https
severity: medium
related:
  - hsts
  - http_status
---

# HTTPS Enforcement

## Definition

HTTPS is HTTP layered over TLS, providing encryption, integrity protection, and server authentication for communication between client and server. ARAS evaluates whether the assessed site is served over the `https://` scheme rather than plain `http://`.

## Technical Background

TLS (currently 1.3, per RFC 8446; TLS 1.0/1.1 formally deprecated by RFC 8996) encrypts the channel via a handshake authenticating the server through an X.509 certificate before any HTTP data is exchanged. The `https` scheme's default port is 443.

## Importance for AI Agent Readiness

An agent retrieving content or submitting data to a site over plain HTTP has no protection against interception or tampering in transit. Any facts, credentials, or instructions exchanged with the site could be altered by a network intermediary before reaching the agent, undermining the reliability of everything downstream in an agent's decision-making.

## ARAS Evaluation Context

ARAS checks: `evidence.url` scheme.

Passed when: the evaluated URL starts with `https://`.

Failure condition: the URL uses `http://`.

Failure message: "HTTPS is not enabled."

## Common Issues

- Site accessible over plain HTTP with no automatic redirect to HTTPS.
- HTTPS available but not the default/enforced scheme for the primary domain.
- Mixed content: HTTPS page loading sub-resources over plain HTTP, undermining the protection even when the primary scheme is correct.

## Impact

- **Technical impact**: any data exchanged is unencrypted and unauthenticated at the transport layer.
- **AI agent impact**: an agent cannot trust that retrieved content, or data it submits, has not been altered or observed in transit — undermining every downstream decision based on that content.
- **Security impact**: high — this is the foundational transport-security control every other browser-enforced protection (HSTS, CSP, secure cookies) assumes is already in place.

## Recommendation Strategy

Redirect all traffic to HTTPS: enforce HTTPS as the sole scheme for the domain, with a permanent (301/308) redirect from any HTTP request, and eliminate mixed-content sub-resource loading.

## Implementation Guidance

- **Nginx**: `return 301 https://$host$request_uri;` in the HTTP server block.
- **Apache**: `RewriteEngine On` + `RewriteCond %{HTTPS} off` + `RewriteRule ^ https://%{HTTP_HOST}%{REQUEST_URI} [L,R=301]`.
- **Cloudflare**: enable "Always Use HTTPS" and set the SSL/TLS mode to "Full (strict)" for end-to-end encryption to origin.
- **Node.js / Express**: terminate TLS at a reverse proxy/load balancer rather than in the application process for production deployments.

## Validation Checklist

- The primary domain resolves and responds over `https://` with a valid, unexpired certificate.
- Any `http://` request to the same host redirects (301/308) to the HTTPS equivalent.
- No mixed-content warnings when loading the page over HTTPS.
- Negotiated TLS version is 1.2 or 1.3 (not 1.0/1.1).

## Related ARAS Criteria

- `hsts` — closes the residual downgrade risk HTTPS alone does not address on unprimed clients.
- `http_status` — confirms the HTTPS endpoint actually responds successfully, not just that the scheme is correct.

## References

Source: official_sources/security/https_reference.md
