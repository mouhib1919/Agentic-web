"""Data contracts for the Rule Engine.

This module defines the two output types produced by the Rule Engine:
a single classified issue, and the aggregate result of classifying
every issue reported across all four analysis dimensions. No rule
logic, LLM calls, or retrieval belong here — these are data
containers only.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class ClassifiedIssue:
    """A single analysis-agent issue, classified for recommendation generation.

    This is the Rule Engine's atomic unit of output: one detected
    readiness gap, tagged with the dimension it belongs to, a
    deterministic priority, and the knowledge-base topic the future
    RAG Retriever should search for when generating a recommendation
    for it.

    Attributes:
        category: The ARAS dimension the issue was reported by
            (`"discoverability"`, `"comprehension"`, `"interaction"`,
            or `"security"`).
        issue: The original issue message, exactly as reported by the
            analysis agent.
        priority: Deterministic severity classification —
            `"HIGH"`, `"MEDIUM"`, or `"LOW"`.
        knowledge_topic: The knowledge-base topic (matching a filename
            under `recommendation/knowledge/<category>/`, e.g. `"csp"`,
            `"jsonld"`, `"openapi"`) the Recommendation Agent should
            retrieve documentation for.
        reason: A short, human-readable justification for the assigned
            priority.
    """

    category: str
    issue: str
    priority: str
    knowledge_topic: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        """Convert this issue into a plain JSON-serializable dict.

        Returns:
            A dict representation suitable for `json.dumps`.
        """
        return asdict(self)


@dataclass
class RuleEngineResult:
    """Aggregate output of classifying every issue across all dimensions.

    This dataclass is the sole output of `RuleEngine.evaluate`. It
    contains no evidence, no scores, and no natural-language
    recommendations — only the structured classification that the
    Recommendation Agent and RAG Retriever consume next.

    Attributes:
        issues: Every reported issue, classified into a `ClassifiedIssue`.
        summary: Count of issues per priority level, keyed by
            `"HIGH"`, `"MEDIUM"`, and `"LOW"` (always present, even if
            zero, for a stable, predictable shape).
    """

    issues: list[ClassifiedIssue] = field(default_factory=list)
    summary: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert this result into a plain JSON-serializable dict.

        Returns:
            A dict representation suitable for `json.dumps`.
        """
        return {
            "issues": [issue.to_dict() for issue in self.issues],
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
