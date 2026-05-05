import pytest

from src.extraction.jnlpba_pipeline import run_jnlpba_pipeline


def test_run_jnlpba_pipeline_is_not_implemented_yet():
    with pytest.raises(NotImplementedError):
        run_jnlpba_pipeline(query="IL-2 gene expression")
