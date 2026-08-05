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
    deterministic priority, and everything the RAG Retriever and
    Recommendation Agent need to act on it directly — no re-reading of
    the original analysis results required.

    `category`/`issue`/`priority`/`knowledge_topic`/`reason` are the
    original (unchanged) fields every existing caller already reads.
    `criterion`/`score`/`evidence`/`retrieval_query`/`metadata` are
    additive RAG-oriented fields: none of them affect issue detection
    or priority, they only expose already-computed information in a
    shape the retrieval layer can consume directly.

    Attributes:
        category: The ARAS dimension the issue was reported by
            (`"discoverability"`, `"comprehension"`, `"interaction"`,
            or `"security"`).
        issue: The original issue message, exactly as reported by the
            analysis agent.
        priority: Deterministic severity classification —
            `"HIGH"`, `"MEDIUM"`, or `"LOW"`.
        knowledge_topic: Legacy knowledge-base topic, kept for backward
            compatibility with existing callers. Prefer `criterion`,
            which is guaranteed to match a real
            `knowledge/aras_knowledge/<category>/<criterion>.md`
            document's `criterion` frontmatter field; `knowledge_topic`
            predates that knowledge base and is not always accurate.
        reason: A short, human-readable justification for the assigned
            priority.
        criterion: The exact ARAS criterion this issue was evaluated
            against (e.g. `"csp"`, `"json_ld"`, `"api_documentation"`),
            matching both the analysis agent's `checks` key and the
            ARAS knowledge base's `criterion` frontmatter field for
            this category.
        score: The issue's ARAS dimension's overall score in [0, 100],
            as already computed by the corresponding analysis agent
            (no per-criterion score is computed upstream, so this is
            the most granular already-calculated score available).
        evidence: The raw evaluation evidence behind this issue, e.g.
            `{"csp": False}` — the analysis agent's own pass/fail
            outcome for `criterion`. Empty if the analysis result
            didn't expose a `checks` mapping.
        retrieval_query: `{"category": ..., "criterion": ...}`, ready
            to pass directly to the RAG Retriever as a metadata filter.
        metadata: Optional additional context for future extensions
            (e.g. detected framework/technology), empty unless already
            available — never populated by additional analysis.
    """

    category: str
    issue: str
    priority: str
    knowledge_topic: str
    reason: str
    criterion: str = ""
    score: float = 0.0
    evidence: dict[str, Any] = field(default_factory=dict)
    retrieval_query: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

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
