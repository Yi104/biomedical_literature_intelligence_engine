import pandas as pd

from src.retrieval import task_router as tr


def test_run_task_dispatches_bc5cdr(monkeypatch):
    sentinel = (pd.DataFrame([{"pmid": "1"}]), pd.DataFrame([{"pmid": "1"}]))

    def fake_bc5cdr(*args, **kwargs):
        return sentinel

    monkeypatch.setattr(tr, "run_bc5cdr_pipeline", fake_bc5cdr)
    monkeypatch.setattr(tr, "run_jnlpba_pipeline", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("should not call jnlpba")))

    papers_df, entities_df = tr.run_task("bc5cdr", query="cisplatin kidney diseases")
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


def test_run_task_dispatches_biored(monkeypatch):
    sentinel = (
        pd.DataFrame([{"pmid": "3"}]),
        pd.DataFrame([{"pmid": "3"}]),
        pd.DataFrame([{"pmid": "3"}]),
    )

    def fake_biored(*args, **kwargs):
        return sentinel

    monkeypatch.setattr(tr, "run_bc5cdr_pipeline", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("should not call bc5cdr")))
    monkeypatch.setattr(tr, "run_jnlpba_pipeline", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("should not call jnlpba")))
    monkeypatch.setattr(tr, "run_biored_pipeline", fake_biored)

    papers_df, entities_df, relations_df = tr.run_task("biored", query="BRCA1 breast cancer", smoke=True)
    assert papers_df.equals(sentinel[0])
    assert entities_df.equals(sentinel[1])
    assert relations_df.equals(sentinel[2])
