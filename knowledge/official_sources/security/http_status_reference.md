# HTTP Response Status Codes

## Overview

HTTP status codes are three-digit numeric codes returned in every HTTP response, indicating the outcome of a request at a standardized level of granularity. In a security- and availability-assessment context, the status code returned by a website's homepage or a given endpoint is the primary signal of whether the resource is genuinely reachable and correctly served, as opposed to erroring, redirecting unexpectedly, or being entirely unavailable.

## Official Definition

HTTP status codes are defined in IETF RFC 9110, "HTTP Semantics," which supersedes the status-code definitions previously spread across RFC 7231 and related documents. RFC 9110 organizes status codes into five classes, each identified by its leading digit, and maintains the canonical registry of standard codes and their defined semantics.

## Core Concepts

- **Status code classes**: 1xx (Informational, provisional), 2xx (Successful), 3xx (Redirection, further action needed), 4xx (Client Error), 5xx (Server Error) — the leading digit alone conveys the general outcome category even for codes a client does not specifically recognize.
- **Canonical vs. extension codes**: RFC 9110 and companion RFCs define a core set of registered codes (200, 301, 404, 500, etc.); additional codes are defined by other specifications (e.g., WebDAV's 207 Multi-Status) and registered in the IANA HTTP Status Code Registry.
- **Reason phrases**: the human-readable text historically accompanying a status code (e.g., "OK" for 200) is defined as advisory only; RFC 9110 explicitly notes clients should not depend on the reason phrase's exact wording.
- **Idempotent interpretation**: unrecognized codes within a known class must be treated according to that class's general semantics (e.g., an unrecognized 4xx code should be treated as a generic client error) per RFC 9110's forward-compatibility guidance.

## Technical Details

- 200 OK: the request succeeded and the response body contains the representation of the requested resource.
- 3xx codes: 301 (Moved Permanently), 302 (Found/temporary redirect), 307/308 (temporary/permanent redirect preserving the original HTTP method) each carry a `Location` header indicating the new resource URL.
- 404 Not Found: the origin server did not find a current representation for the target resource; distinct from 410 Gone, which indicates the absence is known to be permanent.
- 5xx codes: indicate the server recognized the request but failed to fulfill it due to an internal condition (500 Internal Server Error, 502 Bad Gateway, 503 Service Unavailable, 504 Gateway Timeout being the most common in practice).

## Detection Characteristics

- The numeric status line of the HTTP response (`HTTP/1.1 200 OK`, etc.) is present in every response by protocol requirement and directly observable without further parsing.
- A homepage or key endpoint consistently returning 2xx indicates baseline availability; persistent 4xx/5xx indicates a broken or misconfigured resource.
- Redirect chains (successive 3xx responses) can be followed and counted; excessive redirect hops are a detectable inefficiency or misconfiguration.
- Distinction between a "soft 404" (a 200 response whose body nonetheless displays an error/not-found message) and a genuine HTTP-level 404 requires content inspection beyond the status code alone.

## Common Implementations

- Health-check and monitoring systems polling a fixed endpoint expecting a consistent 200 response as a liveness signal.
- Load balancers and reverse proxies returning 502/503/504 when an upstream origin server is unreachable, overloaded, or timing out.
- Content-management systems returning 410 Gone for intentionally and permanently removed content, as distinct from merely missing (404) content.

## Limitations

- A 200 status code alone does not guarantee correct or complete content — an application-level error can still be rendered within a 200 response (a "soft error").
- Status codes reflect the immediate response to a single request; transient failures may not manifest consistently across repeated requests to the same resource.
- Custom or non-standard status code usage by an origin server (returning an unconventional code for a routine condition) can defeat generic classification logic that assumes conventional usage.

## Related Technologies

- HTTP redirection (`Location` header, 3xx class codes)
- Health-check/liveness-probe conventions used by monitoring and orchestration systems
- IANA HTTP Status Code Registry, the authoritative registry of all defined codes

## Official References

- IETF RFC 9110, "HTTP Semantics" — Status Codes
- IANA, "Hypertext Transfer Protocol (HTTP) Status Code Registry"
