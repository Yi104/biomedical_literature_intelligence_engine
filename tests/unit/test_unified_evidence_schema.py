from __future__ import annotations

from src.contracts.unified_evidence_schema import SCHEMA_VERSION


def test_schema_version_constant_is_stable():
    assert SCHEMA_VERSION == "evidence-v1"
