import pandas as pd

from src.retrieval import task_router as tr


def test_run_task_dispatches_bc5cdr(monkeypatch):
    sentinel = (pd.DataFrame([{"pmid": "1"}]), pd.DataFrame([{"pmid": "1"}]))

    def fake_bc5cdr(*args, **kwargs):
        return sentinel

    monkeypatch.setattr(tr, "run_bc5cdr_pipeline", fake_bc5cdr)
    monkeypatch.setattr(tr, "run_jnlpba_pipeline", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("should not call jnlpba")))

    papers_df, entities_df = tr.run_task("bc5cdr", query="BRCA1 breast cancer")
    assert papers_df.equals(sentinel[0])
    assert entities_df.equals(sentinel[1])


def test_run_task_dispatches_jnlpba(monkeypatch):
    sentinel = (pd.DataFrame([{"pmid": "2"}]), pd.DataFrame([{"pmid": "2"}]))

    def fake_jnlpba(*args, **kwargs):
        return sentinel

    monkeypatch.setattr(tr, "run_bc5cdr_pipeline", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("should not call bc5cdr")))
    monkeypatch.setattr(tr, "run_jnlpba_pipeline", fake_jnlpba)

    papers_df, entities_df = tr.run_task("jnlpba", query="IL-2 gene expression")
    assert papers_df.equals(sentinel[0])
    assert entities_df.equals(sentinel[1])
