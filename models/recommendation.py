"""Data contracts for the Recommendation Agent.

This module defines the two output types produced by the
Recommendation Agent: a single generated recommendation, and the
aggregate result of generating one for every classified issue. No
retrieval, prompt-building, or LLM-calling logic belongs here — these
are data containers only.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class Recommendation:
    """A single, professional recommendation generated for one classified issue.

    This is the Recommendation Agent's atomic unit of output: one
    `ClassifiedIssue` (from the Rule Engine), expanded into an
    explanation, an actionable recommendation, concrete implementation
    steps, and the knowledge-base sources it was grounded in.

    Attributes:
        category: The ARAS dimension the underlying issue belongs to
            (`"discoverability"`, `"comprehension"`, `"interaction"`,
            or `"security"`), carried over unchanged from the
            `ClassifiedIssue` that produced this recommendation.
        issue: The original issue message, carried over unchanged.
        priority: The deterministic priority assigned by the Rule
            Engine, carried over unchanged — the Recommendation Agent
            never re-classifies or overrides it.
        explanation: A short explanation of why this issue matters.
        recommendation: A concise, actionable recommendation statement.
        implementation_steps: Concrete steps to implement the fix.
        references: Knowledge-base source paths (e.g.
            `"knowledge/security/csp.md"`) the recommendation was
            grounded in, empty if no relevant documentation was found.
    """

    category: str
    issue: str
    priority: str
    explanation: str
    recommendation: str
    implementation_steps: list[str] = field(default_factory=list)
    references: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert this recommendation into a plain JSON-serializable dict.

        Returns:
            A dict representation suitable for `json.dumps`.
        """
        return asdict(self)


@dataclass
class RecommendationResult:
    """Aggregate output of generating a recommendation for every classified issue.

    This dataclass is the sole output of `RecommendationAgent.generate`.

    Attributes:
        recommendations: One `Recommendation` per input `ClassifiedIssue`.
        summary: Count of recommendations per priority level, keyed by
            `"HIGH"`, `"MEDIUM"`, and `"LOW"` (always present, even if
            zero, for a stable, predictable shape).
    """

    recommendations: list[Recommendation] = field(default_factory=list)
    summary: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert this result into a plain JSON-serializable dict.

        Returns:
            A dict representation suitable for `json.dumps`.
        """
        return {
            "recommendations": [recommendation.to_dict() for recommendation in self.recommendations],
            "summary": self.summary,
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialize this result to a JSON string.

        Args:
            indent: Number of spaces to indent nested JSON structures.

        Returns:
            A JSON string representation of the result.
        """
        import json

        return json.dumps(self.to_dict(), indent=indent, default=str)
