"""Data contract for the Scoring Agent.

This module defines the single output type produced by the Scoring
Agent: a global, JSON-serializable Agentic Readiness score aggregated
from the four analysis dimensions. No evidence inspection, criteria
evaluation, or reporting logic belongs here — this is a data container
only.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class GlobalReadinessResult:
    """Aggregated Agentic Readiness assessment for a single website.

    This dataclass is the sole output of :class:`ScoringAgent`. It is
    derived entirely from the four already-computed analysis results
    (`DiscoverabilityResult`, `ComprehensionResult`,
    `InteractionResult`, `SecurityResult`) — no new evidence is
    inspected and no criteria are evaluated while producing it.

    Attributes:
        global_score: The weighted aggregate of the four dimension
            scores, in the range [0, 100].
        dimension_scores: Each dimension's own score, keyed by
            dimension name (`"discoverability"`, `"comprehension"`,
            `"interaction"`, `"security"`).
        details: Supporting evidence carried over from each analysis
            agent (its `checks` mapping), keyed by
            `"{dimension}_checks"`, so a future Reporter Agent can
            explain the global score without re-running any analysis.
        critical_issues: Every failed criterion's issue message,
            collected across all four dimensions, without duplicates.
        recommendations: Every failed criterion's recommendation,
            collected across all four dimensions, without duplicates.
    """

    global_score: float = 0.0
    dimension_scores: dict[str, float] = field(default_factory=dict)
    details: dict[str, Any] = field(default_factory=dict)
    critical_issues: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert this result into a plain JSON-serializable dict.

        Returns:
            A dict representation suitable for `json.dumps`.
        """
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        """Serialize this result to a JSON string.

        Args:
            indent: Number of spaces to indent nested JSON structures.

        Returns:
            A JSON string representation of the result.
        """
        import json

        return json.dumps(self.to_dict(), indent=indent, default=str)
