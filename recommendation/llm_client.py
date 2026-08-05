"""LLM abstraction for the ARAS Recommendation Agent.

This module defines the `LLMClient` interface the Recommendation Agent
depends on, its production implementation (`GroqLLMClient`, backed by
LangChain + Groq), and a deterministic, offline test double
(`TemplateLLMClient`). No prompt-building, retrieval, or issue
classification logic belongs here — this module only turns a prompt
string into a text response.

Keeping this behind an abstract interface means the Recommendation
Agent never hardcodes a specific model or provider: swapping the LLM
backend (Groq, another LangChain chat model, a local model, a test
double) requires no change to `RecommendationAgent` or `PromptBuilder`,
only a new `LLMClient` subclass.
"""

from __future__ import annotations

import os
import re
from abc import ABC, abstractmethod

from dotenv import load_dotenv
from langchain_groq import ChatGroq

# Loads variables from a local `.env` file (e.g. GROQ_API_KEY,
# MODEL_NAME) into the process environment, if one is present. A no-op
# if `.env` does not exist or a variable is already set in the
# environment.
load_dotenv()

_CATEGORY_PATTERN = re.compile(r"Category:\s*(.+)")
_CRITERION_PATTERN = re.compile(r"Criterion:\s*(.+)")
_PRIORITY_PATTERN = re.compile(r"Priority:\s*(.+)")
_ISSUE_PATTERN = re.compile(r"Issue:\s*(.+)")

_GROQ_API_KEY_ENV_VAR = "GROQ_API_KEY"
_MODEL_NAME_ENV_VAR = "MODEL_NAME"
_DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"
_DEFAULT_TEMPERATURE = 0


class LLMClient(ABC):
    """Abstract text-generation backend used by the Recommendation Agent.

    Any implementation only needs to turn a prompt string into a text
    response; how that response is produced (a hosted API call, a
    local model, a template) is entirely up to the implementation. No
    ARAS logic depends on which provider or model backs this interface
    — swapping Groq for another LangChain chat model, a different
    Groq-hosted model (`llama-3.3-70b-versatile`, `qwen`, ...), or a
    fully different provider requires only a new `LLMClient`
    implementation, never a change to `RecommendationAgent` or
    `PromptBuilder`.
    """

    @abstractmethod
    def invoke(self, prompt: str) -> str:
        """Generate a text response for the given prompt.

        Args:
            prompt: The complete prompt string, as built by
                `PromptBuilder.build`.

        Returns:
            The raw text response. `RecommendationAgent` expects it to
            follow the `PromptBuilder.RESPONSE_HEADERS` structure the
            prompt requests, but must tolerate deviations gracefully.
        """
        raise NotImplementedError


class GroqLLMClient(LLMClient):
    """Production `LLMClient`, backed by LangChain's `ChatGroq` chat model.

    Uses a Groq-hosted open-source model via LangChain's standard chat
    model interface (`invoke()`, not the deprecated batch `generate()`
    API). Neither the API key nor the model name is ever hardcoded —
    both are read from environment variables (`GROQ_API_KEY`,
    `MODEL_NAME`), via a local `.env` file if present, so the backing
    model can be swapped (e.g. to another Groq-hosted Llama or Qwen
    model) without a code change.
    """

    def __init__(
        self,
        model: str = "",
        temperature: float = _DEFAULT_TEMPERATURE,
    ) -> None:
        """Configure the Groq-backed chat model.

        Args:
            model: The Groq-hosted model name to use. Defaults to the
                `MODEL_NAME` environment variable, falling back to
                `_DEFAULT_GROQ_MODEL` if that variable is unset.
            temperature: Sampling temperature. `0` keeps recommendation
                generation deterministic and consistent across runs.

        Raises:
            ValueError: If the `GROQ_API_KEY` environment variable is
                not set, so the failure is clear and immediate rather
                than surfacing as an opaque authentication error on
                the first `invoke()` call.
        """
        if not os.environ.get(_GROQ_API_KEY_ENV_VAR):
            raise ValueError(
                f"{_GROQ_API_KEY_ENV_VAR} environment variable is not set. "
                "Set it in your environment, or in a local .env file, before "
                "using GroqLLMClient."
            )

        resolved_model = model or os.environ.get(_MODEL_NAME_ENV_VAR) or _DEFAULT_GROQ_MODEL
        self.llm = ChatGroq(model=resolved_model, temperature=temperature)

    def invoke(self, prompt: str) -> str:
        """Generate a text response by invoking the Groq chat model.

        Args:
            prompt: The prompt built by `PromptBuilder`.

        Returns:
            The model's response text.
        """
        response = self.llm.invoke(prompt)
        return response.content


class TemplateLLMClient(LLMClient):
    """Deterministic, offline test double for `LLMClient`.

    Makes no network call and requires no API key, so the
    Recommendation Agent's orchestration logic (retrieval, prompt
    building, response parsing, fallback handling) can be exercised in
    tests without depending on Groq API access. It reconstructs the
    structured response format the prompt requests directly from the
    labeled fields already present in the prompt's ISSUE CONTEXT
    section (`Category:`, `Criterion:`, `Priority:`, `Issue:`), rather
    than performing any real natural-language generation.

    Not used as the Recommendation Agent's default anymore — that role
    now belongs to `GroqLLMClient` — but kept for tests and for local
    development without a Groq API key.
    """

    def invoke(self, prompt: str) -> str:
        """Produce a templated, structured recommendation response.

        Args:
            prompt: The prompt built by `PromptBuilder`.

        Returns:
            A response following `PromptBuilder.RESPONSE_HEADERS`.
        """
        category = self._extract(_CATEGORY_PATTERN, prompt, "the affected area")
        criterion = self._extract(_CRITERION_PATTERN, prompt, "this criterion")
        priority = self._extract(_PRIORITY_PATTERN, prompt, "MEDIUM")
        issue = self._extract(_ISSUE_PATTERN, prompt, "the detected issue")

        return (
            "EXPLANATION:\n"
            f"This {category} issue was flagged at {priority} priority because "
            f'"{issue}" directly affects how reliably an AI agent can discover, '
            "understand, interact with, or trust this website.\n\n"
            "IMPACT:\n"
            f"Leaving this {criterion} gap unaddressed reduces the site's "
            "overall Agentic Readiness and may cause AI agents to skip, "
            "misinterpret, or distrust the affected content.\n\n"
            "RECOMMENDATION:\n"
            f"Address the following issue: {issue}.\n\n"
            "IMPLEMENTATION STEPS:\n"
            "- Review the retrieved technical documentation for this topic.\n"
            "- Apply the corresponding configuration, header, or markup change.\n"
            "- Validate the fix with an appropriate testing or auditing tool.\n\n"
            "BEST PRACTICES:\n"
            f"- Follow the official specification or standard for {criterion}.\n"
            "- Re-run this check after deploying the fix.\n\n"
            "EXPECTED BENEFITS:\n"
            f"Improves the {category} dimension's score and this website's "
            "overall readiness for AI agent interaction.\n\n"
            "REFERENCES:\n"
            f"- {criterion} documentation\n"
        )

    @staticmethod
    def _extract(pattern: re.Pattern[str], text: str, default: str) -> str:
        """Extract a labeled field's value from the prompt text.

        Args:
            pattern: Compiled regex capturing the field's value.
            text: The prompt text to search.
            default: Value to return if the pattern is not found.

        Returns:
            The matched value, stripped, or `default` if not found.
        """
        match = pattern.search(text)
        return match.group(1).strip() if match else default
