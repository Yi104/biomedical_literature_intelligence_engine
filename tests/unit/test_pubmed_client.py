from src.ingestion import pubmed_client as pc


def test_search_pubmed_parses_id_list(monkeypatch):
    xml = b"""
    <eSearchResult>
      <IdList>
        <Id>111</Id>
        <Id>222</Id>
      </IdList>
    </eSearchResult>
    """

    monkeypatch.setattr(pc, "_http_get", lambda url, timeout=30: xml)
    ids = pc.search_pubmed("BRCA1", retmax=2)
    assert ids == ["111", "222"]


def test_fetch_pubmed_details_parses_article_fields(monkeypatch):
    xml = b"""
    <PubmedArticleSet>
      <PubmedArticle>
        <MedlineCitation>
          <PMID>12345</PMID>
          <Article>
            <ArticleTitle>Example title</ArticleTitle>
            <Journal><Title>Nature</Title><JournalIssue><PubDate><Year>2020</Year></PubDate></JournalIssue></Journal>
            <Abstract>
              <AbstractText Label="BACKGROUND">A text.</AbstractText>
              <AbstractText>B text.</AbstractText>
            </Abstract>
          </Article>
        </MedlineCitation>
      </PubmedArticle>
    </PubmedArticleSet>
    """
    monkeypatch.setattr(pc, "_http_get", lambda url, timeout=30: xml)
    records = pc.fetch_pubmed_details(["12345"])
    assert len(records) == 1
    rec = records[0]
    assert rec.pmid == "12345"
    assert rec.title == "Example title"
    assert rec.journal == "Nature"
    assert rec.year == "2020"
    assert "BACKGROUND: A text." in rec.abstract
