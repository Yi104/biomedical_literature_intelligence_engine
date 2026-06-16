from __future__ import annotations

from typing import Any, Dict, List

from src.contracts.evidence_adapters import (
    build_unified_evidence_bundle_from_agent_result,
)


def build_evidence_bundle_from_agent_result(
    question: str,
    agent_result: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Normalize L5 output into a stable L6 input contract.
    """
    return build_unified_evidence_bundle_from_agent_result(question, agent_result)
