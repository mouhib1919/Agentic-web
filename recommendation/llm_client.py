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

# Loads variables from a local `.env` file (e.g. GROQ_API_KEY) into the
# process environment, if one is present. A no-op if `.env` does not
# exist or a variable is already set in the environment.
load_dotenv()

_ISSUE_PATTERN = re.compile(r"Website issue:\s*(.+)")
_CATEGORY_PATTERN = re.compile(r"Category:\s*(.+)")
_PRIORITY_PATTERN = re.compile(r"Priority:\s*(.+)")

_GROQ_API_KEY_ENV_VAR = "GROQ_API_KEY"
_DEFAULT_GROQ_MODEL = "llama-3.1-8b-instant"
_DEFAULT_TEMPERATURE = 0


class LLMClient(ABC):
    """Abstract text-generation backend used by the Recommendation Agent.

    Any implementation only needs to turn a prompt string into a text
    response; how that response is produced (a hosted API call, a
    local model, a template) is entirely up to the implementation.
    """

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Generate a text response for the given prompt.

        Args:
            prompt: The complete prompt string, as built by
                `PromptBuilder.build_recommendation_prompt`.

        Returns:
            The raw text response. `RecommendationAgent` expects it to
            follow the `EXPLANATION:` / `RECOMMENDATION:` /
            `IMPLEMENTATION STEPS:` structure `PromptBuilder` requests,
            but must tolerate deviations gracefully.
        """
        raise NotImplementedError


class GroqLLMClient(LLMClient):
    """Production `LLMClient`, backed by LangChain's `ChatGroq` chat model.

    Uses an open-source model (Llama 3.1 8B Instant) hosted on Groq's
    inference API via LangChain's standard chat model interface. The
    API key is never hardcoded — it is read from the `GROQ_API_KEY`
    environment variable (via a local `.env` file if present).
    """

    def __init__(
        self,
        model: str = _DEFAULT_GROQ_MODEL,
        temperature: float = _DEFAULT_TEMPERATURE,
    ) -> None:
        """Configure the Groq-backed chat model.

        Args:
            model: The Groq-hosted model name to use.
            temperature: Sampling temperature. `0` keeps recommendation
                generation deterministic and consistent across runs.

        Raises:
            ValueError: If the `GROQ_API_KEY` environment variable is
                not set, so the failure is clear and immediate rather
                than surfacing as an opaque authentication error on
                the first `generate()` call.
        """
        if not os.environ.get(_GROQ_API_KEY_ENV_VAR):
            raise ValueError(
                f"{_GROQ_API_KEY_ENV_VAR} environment variable is not set. "
                "Set it in your environment, or in a local .env file, before "
                "using GroqLLMClient."
            )

        self.llm = ChatGroq(model=model, temperature=temperature)

    def generate(self, prompt: str) -> str:
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
    labeled fields already present in the prompt text (`Website
    issue:`, `Category:`, `Priority:`), rather than performing any
    real natural-language generation.

    Not used as the Recommendation Agent's default anymore — that role
    now belongs to `GroqLLMClient` — but kept for tests and for local
    development without a Groq API key.
    """

    def generate(self, prompt: str) -> str:
        """Produce a templated, structured recommendation response.

        Args:
            prompt: The prompt built by `PromptBuilder`.

        Returns:
            A response following the `EXPLANATION:` / `RECOMMENDATION:`
            / `IMPLEMENTATION STEPS:` structure.
        """
        issue = self._extract(_ISSUE_PATTERN, prompt, "the detected issue")
        category = self._extract(_CATEGORY_PATTERN, prompt, "the affected area")
        priority = self._extract(_PRIORITY_PATTERN, prompt, "MEDIUM")

        return (
            "EXPLANATION:\n"
            f"This {category} issue was flagged at {priority} priority because "
            f'"{issue}" directly affects how reliably an AI agent can discover, '
            "understand, interact with, or trust this website.\n\n"
            "RECOMMENDATION:\n"
            f"Address the following issue: {issue}.\n\n"
            "IMPLEMENTATION STEPS:\n"
            "- Review the retrieved technical documentation for this topic.\n"
            "- Apply the corresponding configuration, header, or markup change.\n"
            "- Validate the fix with an appropriate testing or auditing tool.\n"
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
