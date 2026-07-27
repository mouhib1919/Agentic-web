"""Full end-to-end test of the complete ARAS pipeline.

Runs `ARASOrchestrator.run()` against a real website
(`https://www.mytek.tn`) through every stage of the extended LangGraph
workflow:

    Evidence Collector
        -> [Discoverability, Comprehension, Interaction, Security] (parallel)
        -> Scoring Agent
        -> Rule Engine
        -> Recommendation Agent (RAG retrieval + Groq LLM generation)
        -> Reporter Agent (PDF rendering)

This test adds no logic of its own — it only exercises the already-built
orchestrator and asserts on its output, mirroring the real-site scenarios
already used for the individual agents and the pre-Reporter orchestrator.

Requires network access and a valid GROQ_API_KEY (loaded from `.env`).
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running this file directly (e.g. from an IDE "Run" button) by
# ensuring the project root is importable, not just the `tests/` folder.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orchestrator.agent import ARASOrchestrator
from orchestrator.state import ARASState

TARGET_URL = "https://www.mytek.tn"


def _print_full_pipeline_report(url: str, result: ARASState) -> None:
    """Print the debug summary requested for the full end-to-end pipeline run."""
    print("=" * 30)
    print("ARAS FULL PIPELINE TEST")
    print("=" * 30)
    print()
    print(f"Website:\n{url}")
    print()
    print(f"Evidence:\n{'OK' if result['evidence'] is not None else 'FAILED'}")
    print()
    print("Analysis scores:")
    print(f"Discoverability: {result['discoverability_result'].score}")
    print(f"Comprehension: {result['comprehension_result'].score}")
    print(f"Interaction: {result['interaction_result'].score}")
    print(f"Security: {result['security_result'].score}")
    print()
    print(f"Global Score:\n{result['global_result'].global_score} / 100")
    print()
    summary = result["rule_engine_result"].summary
    print("Detected Issues:")
    print(f"HIGH: {summary.get('HIGH', 0)}")
    print(f"MEDIUM: {summary.get('MEDIUM', 0)}")
    print(f"LOW: {summary.get('LOW', 0)}")
    print()
    print(f"Recommendations:\n{len(result['recommendation_result'].recommendations)} generated")
    print()
    print(f"PDF Report:\n{result['report_result'].output_path}")
    print()
    print("=" * 30)


def test_aras_full_pipeline_on_mytek() -> None:
    """Run the complete ARAS MVP pipeline end-to-end against mytek.tn."""
    orchestrator = ARASOrchestrator()
    result = orchestrator.run(TARGET_URL)

    _print_full_pipeline_report(TARGET_URL, result)

    # 1. Evidence exists.
    assert result["evidence"] is not None

    # 2. Analysis results exist.
    assert result["discoverability_result"] is not None
    assert result["comprehension_result"] is not None
    assert result["interaction_result"] is not None
    assert result["security_result"] is not None

    # 3. Score exists. The Scoring Agent's output is stored under
    # `global_result` (its pre-existing field name in ARASState, kept
    # unchanged rather than duplicated as a separate `scoring_result` key).
    assert result["global_result"] is not None
    assert 0.0 <= result["global_result"].global_score <= 100.0
    assert set(result["global_result"].dimension_scores.keys()) == {
        "discoverability",
        "comprehension",
        "interaction",
        "security",
    }

    # 4. Rule Engine exists.
    assert result["rule_engine_result"] is not None
    summary = result["rule_engine_result"].summary
    assert set(summary.keys()) == {"HIGH", "MEDIUM", "LOW"}
    assert len(result["rule_engine_result"].issues) == sum(summary.values())

    # 5. Recommendation Agent: recommendations generated, grounded in the
    #    knowledge base where retrieval succeeded.
    assert result["recommendation_result"] is not None
    recommendations = result["recommendation_result"].recommendations
    assert len(recommendations) == len(result["rule_engine_result"].issues)
    assert any(recommendation.references for recommendation in recommendations), (
        "expected at least one recommendation grounded in retrieved knowledge-base references"
    )
    for recommendation in recommendations:
        assert recommendation.explanation.strip()
        assert recommendation.recommendation.strip()

    # 6. PDF Report: file created, exists, non-empty.
    assert result["report_result"] is not None
    assert result["report_result"].generated is True
    report_path = Path(result["report_result"].output_path)
    assert report_path.exists()
    assert report_path.stat().st_size > 0

    # The workflow completed without unrecoverable node-level failures.
    print(f"Workflow errors: {result['errors']}")


if __name__ == "__main__":
    test_aras_full_pipeline_on_mytek()
    print("All tests passed.")
