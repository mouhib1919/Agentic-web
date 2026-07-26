"""Scoring Agent.

This module is the aggregation layer of ARAS. It combines the four
already-computed dimension results (Discoverability, Comprehension,
Interaction, Security) into a single global Agentic Readiness score.

This agent MUST NOT:
    - inspect WebsiteEvidence
    - inspect HTML
    - evaluate discoverability, comprehension, interaction, or security
      criteria
    - call the Evidence Collector or any extraction tool
    - modify any analysis agent's logic

It only reads the `score`, `checks`, `issues`, and `recommendations`
already produced by the four analysis agents and combines them.
Criteria evaluation belongs exclusively to those agents.
"""

from __future__ import annotations

from typing import Any, Optional

from models.comprehension import ComprehensionResult
from models.discoverability import DiscoverabilityResult
from models.interaction import InteractionResult
from models.scoring import GlobalReadinessResult
from models.security import SecurityResult

# Equal weighting across all four dimensions, summing to 1.0.
_DISCOVERABILITY_WEIGHT = 0.25
_COMPREHENSION_WEIGHT = 0.25
_INTERACTION_WEIGHT = 0.25
_SECURITY_WEIGHT = 0.25

_SCORE_DECIMALS = 2


class ScoringAgent:
    """Aggregates the four ARAS dimension results into a global score.

    This class holds no criteria-evaluation logic. It is a pure
    aggregation step: it reads four already-computed results and
    combines their scores, checks, issues, and recommendations.
    """

    def calculate(
        self,
        discoverability_result: Optional[DiscoverabilityResult],
        comprehension_result: Optional[ComprehensionResult],
        interaction_result: Optional[InteractionResult],
        security_result: Optional[SecurityResult],
    ) -> GlobalReadinessResult:
        """Aggregate the four analysis results into a global readiness score.

        A dimension whose result is `None` (its analysis agent did not
        run or failed) contributes a score of 0.0 to the weighted
        average and no checks, issues, or recommendations — it is not
        excluded from the weighting, since a missing analysis is
        itself a readiness gap.

        Args:
            discoverability_result: Output of `DiscoverabilityAgent`.
            comprehension_result: Output of `ComprehensionAgent`.
            interaction_result: Output of `InteractionAgent`.
            security_result: Output of `SecurityAgent`.

        Returns:
            A `GlobalReadinessResult` with a weighted global score in
            [0, 100], per-dimension scores, carried-over checks, and
            deduplicated issues/recommendations across all dimensions.
        """
        dimension_scores = {
            "discoverability": self._score_of(discoverability_result),
            "comprehension": self._score_of(comprehension_result),
            "interaction": self._score_of(interaction_result),
            "security": self._score_of(security_result),
        }

        global_score = round(
            dimension_scores["discoverability"] * _DISCOVERABILITY_WEIGHT
            + dimension_scores["comprehension"] * _COMPREHENSION_WEIGHT
            + dimension_scores["interaction"] * _INTERACTION_WEIGHT
            + dimension_scores["security"] * _SECURITY_WEIGHT,
            _SCORE_DECIMALS,
        )

        details: dict[str, Any] = {
            "discoverability_checks": self._checks_of(discoverability_result),
            "comprehension_checks": self._checks_of(comprehension_result),
            "interaction_checks": self._checks_of(interaction_result),
            "security_checks": self._checks_of(security_result),
        }

        results = (
            discoverability_result,
            comprehension_result,
            interaction_result,
            security_result,
        )

        return GlobalReadinessResult(
            global_score=global_score,
            dimension_scores=dimension_scores,
            details=details,
            critical_issues=self._deduplicate(
                issue for result in results for issue in self._issues_of(result)
            ),
            recommendations=self._deduplicate(
                recommendation
                for result in results
                for recommendation in self._recommendations_of(result)
            ),
        )

    # ------------------------------------------------------------------
    # Result field accessors
    #
    # Every analysis result shares the same `score`/`checks`/`issues`/
    # `recommendations` shape, but as unrelated dataclasses rather than
    # a common base type, so these helpers centralize the `None`
    # handling in one place instead of repeating it per dimension.
    # ------------------------------------------------------------------

    @staticmethod
    def _score_of(result: Optional[Any]) -> float:
        """Read a dimension result's score, defaulting to 0.0 if absent.

        Args:
            result: The analysis result to read, or `None`.

        Returns:
            The result's `score`, or `0.0` if `result` is `None`.
        """
        return result.score if result is not None else 0.0

    @staticmethod
    def _checks_of(result: Optional[Any]) -> dict[str, bool]:
        """Read a dimension result's checks, defaulting to empty if absent.

        Args:
            result: The analysis result to read, or `None`.

        Returns:
            The result's `checks` mapping, or `{}` if `result` is `None`.
        """
        return result.checks if result is not None else {}

    @staticmethod
    def _issues_of(result: Optional[Any]) -> list[str]:
        """Read a dimension result's issues, defaulting to empty if absent.

        Args:
            result: The analysis result to read, or `None`.

        Returns:
            The result's `issues` list, or `[]` if `result` is `None`.
        """
        return result.issues if result is not None else []

    @staticmethod
    def _recommendations_of(result: Optional[Any]) -> list[str]:
        """Read a dimension result's recommendations, defaulting to empty if absent.

        Args:
            result: The analysis result to read, or `None`.

        Returns:
            The result's `recommendations` list, or `[]` if `result` is `None`.
        """
        return result.recommendations if result is not None else []

    @staticmethod
    def _deduplicate(items: Any) -> list[str]:
        """Deduplicate a sequence of strings while preserving first-seen order.

        Args:
            items: An iterable of strings, possibly containing repeats
                across dimensions (e.g. the same missing-metadata issue
                reported by more than one agent).

        Returns:
            The unique items, in the order they were first encountered.
        """
        seen: set[str] = set()
        unique: list[str] = []
        for item in items:
            if item and item not in seen:
                seen.add(item)
                unique.append(item)
        return unique
