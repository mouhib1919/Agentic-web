"""Security Agent.

This module is the fourth analysis ("judgment") layer of ARAS. It
evaluates the security readiness of a website for AI agent
interaction: transport security (HTTPS, HSTS), response availability,
browser-enforced protections (CSP, clickjacking, MIME/XSS), and
whether the website sits behind a recognized reverse proxy, CDN, or
web application firewall.

This agent MUST NOT:
    - perform HTTP requests
    - crawl websites
    - parse HTML
    - inspect JavaScript
    - scan for vulnerabilities
    - perform penetration testing
    - discover security headers
    - use BeautifulSoup, HttpClient, or any extraction tool

It only reads an already-collected `WebsiteEvidence` snapshot and
turns it into a scored `SecurityResult`. Evidence collection belongs
to the Evidence Collector, a separate, earlier layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from models.evidence import WebsiteEvidence
from models.security import SecurityResult

_CRITERIA_COUNT = 7
_CRITERION_WEIGHT = 100.0 / _CRITERIA_COUNT

_HSTS_HEADER = "strict-transport-security"
_CSP_HEADER = "content-security-policy"
_X_FRAME_OPTIONS_HEADER = "x-frame-options"
_X_CONTENT_TYPE_OPTIONS_HEADER = "x-content-type-options"
_X_XSS_PROTECTION_HEADER = "x-xss-protection"
_SERVER_HEADER = "server"

# Header names whose mere presence signals a recognized reverse proxy,
# CDN, or web application firewall, independent of the `Server` value.
_INFRASTRUCTURE_INDICATOR_HEADERS = (
    "cf-ray",
    "cf-cache-status",
    "x-amz-cf-id",
    "x-amz-cf-pop",
    "x-served-by",
    "x-akamai-transformed",
    "x-akamaighost",
    "x-sucuri-id",
    "x-iinfo",
)

# Substrings recognized in the `Server` header as known infrastructure
# providers.
_INFRASTRUCTURE_SERVER_KEYWORDS = (
    "cloudflare",
    "cloudfront",
    "fastly",
    "akamai",
    "sucuri",
    "incapsula",
    "imperva",
)


@dataclass(frozen=True)
class _CriterionOutcome:
    """The result of evaluating a single security criterion.

    Attributes:
        passed: Whether the criterion was satisfied.
        details: Evidence to merge into `SecurityResult.details`.
        issue: Message to record if the criterion failed.
        recommendation: Fix to record if the criterion failed.
    """

    passed: bool
    details: dict[str, object]
    issue: str
    recommendation: str


class SecurityAgent:
    """Evaluates a website's security readiness for AI agents.

    This class holds no evidence-collection logic. It is a pure
    judgment step: it reads a `WebsiteEvidence` snapshot and scores it
    against a fixed set of equally-weighted security criteria.
    """

    def evaluate(self, evidence: WebsiteEvidence) -> SecurityResult:
        """Evaluate security readiness from already-collected evidence.

        Args:
            evidence: The `WebsiteEvidence` snapshot to evaluate.

        Returns:
            A `SecurityResult` with a score in [0, 100], a pass/fail
            breakdown, supporting details, and recommendations for
            every failed criterion.
        """
        result = SecurityResult()
        headers = self._normalize_headers(evidence.headers)

        criteria: list[tuple[str, Callable[[WebsiteEvidence, dict[str, str]], _CriterionOutcome]]] = [
            ("https", self._evaluate_https),
            ("http_status", self._evaluate_http_status),
            ("hsts", self._evaluate_hsts),
            ("csp", self._evaluate_csp),
            ("x_frame_options", self._evaluate_x_frame_options),
            ("mime_xss", self._evaluate_mime_xss),
            ("infrastructure_security", self._evaluate_infrastructure_security),
        ]

        for name, evaluator in criteria:
            self._apply(name, evaluator(evidence, headers), result)

        result.score = self._compute_score(result.checks)
        return result

    # ------------------------------------------------------------------
    # Result assembly
    # ------------------------------------------------------------------

    @staticmethod
    def _apply(name: str, outcome: _CriterionOutcome, result: SecurityResult) -> None:
        """Merge a single criterion's outcome into the aggregate result.

        Args:
            name: The criterion's key in `result.checks`.
            outcome: The evaluated outcome for this criterion.
            result: The in-progress result to update.
        """
        result.checks[name] = outcome.passed
        result.details.update(outcome.details)
        if not outcome.passed:
            result.issues.append(outcome.issue)
            result.recommendations.append(outcome.recommendation)

    @staticmethod
    def _compute_score(checks: dict[str, bool]) -> float:
        """Compute the overall score from equally-weighted criteria.

        Args:
            checks: Pass/fail outcome of every evaluated criterion.

        Returns:
            The percentage of passed criteria, in [0, 100].
        """
        if not checks:
            return 0.0
        passed = sum(1 for outcome in checks.values() if outcome)
        return round(passed * _CRITERION_WEIGHT, 2)

    # ------------------------------------------------------------------
    # Header normalization
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_headers(headers: dict[str, Any]) -> dict[str, str]:
        """Build a lowercase-keyed view of the collected response headers.

        The Evidence Collector may store headers with any casing
        (`Strict-Transport-Security`, `strict-transport-security`, ...).
        Every criterion looks up headers through this normalized view
        so casing never affects the outcome.

        Args:
            headers: The raw `WebsiteEvidence.headers` mapping.

        Returns:
            A dict keyed by lowercase header name, values coerced to `str`.
        """
        return {str(key).lower(): str(value) for key, value in headers.items()}

    # ------------------------------------------------------------------
    # 1. HTTPS
    # ------------------------------------------------------------------

    @staticmethod
    def _evaluate_https(evidence: WebsiteEvidence, headers: dict[str, str]) -> _CriterionOutcome:
        """Check that the website URL uses the HTTPS scheme.

        Args:
            evidence: The evidence snapshot to evaluate.
            headers: The normalized (lowercase-keyed) response headers.

        Returns:
            The outcome of this criterion.
        """
        found = evidence.url.strip().lower().startswith("https://")
        return _CriterionOutcome(
            passed=found,
            details={"url": evidence.url},
            issue="HTTPS is not enabled.",
            recommendation="Redirect all traffic to HTTPS.",
        )

    # ------------------------------------------------------------------
    # 2. HTTP response status
    # ------------------------------------------------------------------

    @staticmethod
    def _evaluate_http_status(
        evidence: WebsiteEvidence, headers: dict[str, str]
    ) -> _CriterionOutcome:
        """Check that the homepage responded with a successful status code.

        Args:
            evidence: The evidence snapshot to evaluate.
            headers: The normalized (lowercase-keyed) response headers.

        Returns:
            The outcome of this criterion.
        """
        found = evidence.status_code == 200
        return _CriterionOutcome(
            passed=found,
            details={"status_code": evidence.status_code},
            issue="The homepage did not respond with HTTP 200.",
            recommendation="Ensure the homepage responds with a successful HTTP status code.",
        )

    # ------------------------------------------------------------------
    # 3. Transport security (HSTS)
    # ------------------------------------------------------------------

    @staticmethod
    def _evaluate_hsts(evidence: WebsiteEvidence, headers: dict[str, str]) -> _CriterionOutcome:
        """Check that the `Strict-Transport-Security` header is present.

        Args:
            evidence: The evidence snapshot to evaluate.
            headers: The normalized (lowercase-keyed) response headers.

        Returns:
            The outcome of this criterion.
        """
        found = _HSTS_HEADER in headers
        return _CriterionOutcome(
            passed=found,
            details={"hsts": found},
            issue="No HSTS header detected.",
            recommendation="Enable Strict-Transport-Security.",
        )

    # ------------------------------------------------------------------
    # 4. Content Security Policy
    # ------------------------------------------------------------------

    @staticmethod
    def _evaluate_csp(evidence: WebsiteEvidence, headers: dict[str, str]) -> _CriterionOutcome:
        """Check that the `Content-Security-Policy` header is present.

        Args:
            evidence: The evidence snapshot to evaluate.
            headers: The normalized (lowercase-keyed) response headers.

        Returns:
            The outcome of this criterion.
        """
        found = _CSP_HEADER in headers
        return _CriterionOutcome(
            passed=found,
            details={"content_security_policy": found},
            issue="Missing Content-Security-Policy header.",
            recommendation="Configure a Content Security Policy.",
        )

    # ------------------------------------------------------------------
    # 5. Clickjacking protection
    # ------------------------------------------------------------------

    @staticmethod
    def _evaluate_x_frame_options(
        evidence: WebsiteEvidence, headers: dict[str, str]
    ) -> _CriterionOutcome:
        """Check that the `X-Frame-Options` header is present.

        Args:
            evidence: The evidence snapshot to evaluate.
            headers: The normalized (lowercase-keyed) response headers.

        Returns:
            The outcome of this criterion.
        """
        value = headers.get(_X_FRAME_OPTIONS_HEADER)
        found = value is not None
        return _CriterionOutcome(
            passed=found,
            details={"x_frame_options": value},
            issue="Missing X-Frame-Options header.",
            recommendation="Protect against clickjacking by adding the X-Frame-Options header.",
        )

    # ------------------------------------------------------------------
    # 6. MIME and XSS protection
    # ------------------------------------------------------------------

    @staticmethod
    def _evaluate_mime_xss(
        evidence: WebsiteEvidence, headers: dict[str, str]
    ) -> _CriterionOutcome:
        """Check that at least one browser-side MIME/XSS protection is present.

        Considers `X-Content-Type-Options` and `X-XSS-Protection`
        independently of `X-Frame-Options` (clickjacking protection),
        which is evaluated by its own dedicated criterion.

        Args:
            evidence: The evidence snapshot to evaluate.
            headers: The normalized (lowercase-keyed) response headers.

        Returns:
            The outcome of this criterion.
        """
        content_type_options = headers.get(_X_CONTENT_TYPE_OPTIONS_HEADER)
        xss_protection = headers.get(_X_XSS_PROTECTION_HEADER)
        found = content_type_options is not None or xss_protection is not None

        return _CriterionOutcome(
            passed=found,
            details={
                "x_content_type_options": content_type_options,
                "x_xss_protection": xss_protection,
            },
            issue="Missing MIME/XSS protection headers.",
            recommendation="Enable browser-side MIME type and XSS protections.",
        )

    # ------------------------------------------------------------------
    # 7. Infrastructure security
    # ------------------------------------------------------------------

    @staticmethod
    def _evaluate_infrastructure_security(
        evidence: WebsiteEvidence, headers: dict[str, str]
    ) -> _CriterionOutcome:
        """Check that a recognized reverse proxy, CDN, or WAF protects the site.

        Considers the `Server` header value against a list of known
        provider names, and the presence of any provider-specific
        header (e.g. `cf-ray` for Cloudflare, `x-amz-cf-id` for
        CloudFront) as an independent signal for providers that mask
        their `Server` header.

        Args:
            evidence: The evidence snapshot to evaluate.
            headers: The normalized (lowercase-keyed) response headers.

        Returns:
            The outcome of this criterion.
        """
        server = headers.get(_SERVER_HEADER)
        server_matches = bool(server) and any(
            keyword in server.lower() for keyword in _INFRASTRUCTURE_SERVER_KEYWORDS
        )
        indicator_matches = any(
            header in headers for header in _INFRASTRUCTURE_INDICATOR_HEADERS
        )
        found = server_matches or indicator_matches

        return _CriterionOutcome(
            passed=found,
            details={"server": server},
            issue="No recognized reverse proxy, CDN, or WAF detected.",
            recommendation="Consider using a trusted reverse proxy or CDN to improve security, availability, and resilience.",
        )
