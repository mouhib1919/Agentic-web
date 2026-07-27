"""Data contract for the Reporter Agent.

This module defines the single output type produced by the Reporter
Agent: a record of whether a PDF report was successfully rendered, and
where. No evidence analysis, scoring, classification, or recommendation
logic belongs here — this is a data container only.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Optional


@dataclass
class ReportResult:
    """Outcome of rendering the final ARAS report for a single website.

    This dataclass is the sole output of :class:`ReporterAgent`. It
    describes only whether rendering succeeded and where the file was
    written — the report's content is derived entirely from the
    already-computed results passed into the Reporter Agent, not
    recomputed here.

    Attributes:
        output_path: Filesystem path the PDF was (or was meant to be)
            written to.
        generated: Whether the PDF was successfully written to disk.
        error: A human-readable description of why rendering failed,
            or `None` if `generated` is `True`.
    """

    output_path: str
    generated: bool
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert this result into a plain JSON-serializable dict.

        Returns:
            A dict representation suitable for `json.dumps`.
        """
        return asdict(self)
