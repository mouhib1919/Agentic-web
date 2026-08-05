# HTTPS (HTTP over TLS)

## Overview

HTTPS is HTTP layered over Transport Layer Security (TLS), providing encryption, integrity protection, and server authentication for HTTP communication between a client and server. It is the baseline transport-security expectation for any modern website, protecting data in transit from interception or tampering by network intermediaries.

## Official Definition

HTTPS is formally specified in IETF RFC 9110 ("HTTP Semantics," which defines the `https` URI scheme) in conjunction with RFC 8446 ("The Transport Layer Security (TLS) Protocol Version 1.3"), which defines the encryption protocol HTTPS layers HTTP on top of. Earlier TLS versions (1.2 and below) are defined in their own respective RFCs, with TLS 1.3 being the current recommended version and TLS 1.0/1.1 formally deprecated by RFC 8996.

## Core Concepts

- **Transport-layer encryption**: TLS establishes an encrypted channel between client and server before any HTTP data is exchanged, via a handshake that negotiates protocol version, cipher suite, and authenticates the server (and optionally the client) using X.509 certificates.
- **Server authentication**: a valid TLS certificate, issued by a trusted Certificate Authority (or self-signed with prior trust establishment), cryptographically binds a public key to a domain name, allowing a client to verify it is communicating with the legitimate server.
- **Confidentiality and integrity**: encrypted TLS records prevent passive eavesdropping (confidentiality) and include authenticated encryption or MAC verification preventing undetected tampering (integrity).
- **Distinct URI scheme**: `https://` is a formally separate URI scheme from `http://`, with a default port of 443 (versus 80 for plain HTTP).

## Technical Details

- Handshake: TLS 1.3 reduced the handshake to a single round trip (versus two in TLS 1.2), negotiating the cipher suite and exchanging keys via (EC)DHE for forward secrecy.
- Certificate validation: involves chain-of-trust verification up to a trusted root Certificate Authority, hostname matching against the certificate's Subject Alternative Name (SAN) field, and expiration/revocation checking.
- Deprecated versions: RFC 8996 formally deprecates TLS 1.0 and TLS 1.1 due to known cryptographic weaknesses; TLS 1.2 remains acceptable when TLS 1.3 is unavailable.
- Mixed content: a page served over HTTPS that loads sub-resources (scripts, images, stylesheets) over plain HTTP creates a "mixed content" state that modern browsers actively block or warn against for active content types (e.g., scripts).

## Detection Characteristics

- The requested URL's scheme is `https://` rather than `http://`.
- The TLS handshake completes successfully with a valid, unexpired, hostname-matching certificate chain.
- A plain-HTTP request to the same host either fails, or is redirected (ideally via a 301/308 response) to the HTTPS equivalent.
- Negotiated TLS protocol version (1.3 preferred, 1.2 acceptable, 1.0/1.1 deprecated/non-compliant).

## Common Implementations

- TLS termination at a reverse proxy, load balancer, or CDN edge, with the origin server communicating over plain HTTP internally within a trusted network boundary.
- Automated certificate issuance and renewal via the ACME protocol (RFC 8555), commonly through providers such as Let's Encrypt.
- Sitewide enforcement via unconditional HTTP-to-HTTPS redirection combined with HSTS (see the dedicated HSTS reference) to prevent any plain-HTTP fallback.

## Limitations

- TLS secures data in transit only; it provides no protection for data at rest, nor does it address application-layer vulnerabilities (injection, broken authentication, etc.).
- A valid certificate proves domain control at issuance time, not the legitimacy or trustworthiness of the site's operator or content.
- Without HSTS, the initial request to a domain (before any redirect has been observed by the client) remains vulnerable to interception/downgrade, since the client has no prior instruction to require HTTPS.

## Related Technologies

- HSTS (HTTP Strict Transport Security), which addresses the residual first-connection gap HTTPS alone does not close
- ACME protocol (RFC 8555), automated certificate issuance
- X.509 certificates and the Public Key Infrastructure (PKI) trust model

## Official References

- IETF RFC 9110, "HTTP Semantics"
- IETF RFC 8446, "The Transport Layer Security (TLS) Protocol Version 1.3"
- IETF RFC 8996, "Deprecating TLS 1.0 and TLS 1.1"
