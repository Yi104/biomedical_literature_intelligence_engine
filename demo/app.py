import os
import sys
import streamlit as st
import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.retrieval.structured_query import run_search_ner_pipeline
from src.extraction.ner_infer import get_label_mapping


st.title("PubMed Biomarker Search + NER")
model_path = st.text_input("Model checkpoint path", "outputs/best_model")
query = st.text_input("Search keyword (chemical or disease)", "cisplatin kidney diseases")
retmax = st.slider("Number of papers", min_value=5, max_value=100, value=20, step=5)
max_length = st.slider("NER max token length", min_value=64, max_value=512, value=256, step=32)
col1, col2 = st.columns(2)
with col1:
    year_from = st.number_input("Year from", min_value=1900, max_value=2100, value=2015, step=1)
with col2:
    year_to = st.number_input("Year to", min_value=1900, max_value=2100, value=2026, step=1)
journal_filter = st.text_input("Journal filter (optional, exact journal name)", "")

with st.expander("How to read labels (B/I/O, Disease, Chemical, label_id)", expanded=False):
    st.markdown(
        """
`label_id` is the model's numeric class index. It must be mapped to `label_name`.

- `B-XXX`: beginning token of an entity
- `I-XXX`: continuation token of the same entity
- `O`: not an entity

For this model, common entity types:
- `Disease`: disease mention
- `Chemical`: chemical/drug mention

Examples:
- `B-Disease I-Disease` -> one disease span
- `B-Chemical I-Chemical` -> one chemical span
"""
    )

st.subheader("Label Mapping (`label_id` ↔ `label_name`)")
try:
    label_map = get_label_mapping(model_path.strip())
    if label_map:
        mapping_df = pd.DataFrame(
            [{"label_id": k, "label_name": v} for k, v in label_map.items()]
        )
        st.dataframe(mapping_df, use_container_width=True)
    else:
        st.info("No label mapping found in model config.")
except Exception as e:
    st.warning(f"Cannot load label mapping from model path: {e}")

if st.button("Search and Extract"):
    if not query.strip():
        st.warning("Please enter a search query.")
    elif int(year_from) > int(year_to):
        st.warning("`Year from` cannot be greater than `Year to`.")
    else:
        with st.spinner("Searching PubMed and running NER..."):
            papers_df, entities_df = run_search_ner_pipeline(
                query=query.strip(),
                model_path=model_path.strip(),
                retmax=retmax,
                max_length=max_length,
                year_from=int(year_from),
                year_to=int(year_to),
                journal=journal_filter.strip() or None,
                expected_entity_types={"Chemical", "Disease"},
            )

        if len(entities_df) > 0:
            st.subheader("Entity Filters")
            all_types = sorted(entities_df["entity_type"].dropna().unique().tolist())
            selected_types = st.multiselect(
                "Entity types",
                options=all_types,
                default=all_types,
            )
            min_entities = st.number_input(
                "Min entities per paper",
                min_value=0,
                max_value=1000,
                value=0,
                step=1,
            )

            if selected_types:
                entities_df = entities_df[entities_df["entity_type"].isin(selected_types)]
            else:
                entities_df = entities_df.iloc[0:0]

            if len(papers_df) > 0:
                counts = entities_df.groupby("pmid").size().rename("filtered_entity_count")
                papers_df = papers_df.merge(counts, on="pmid", how="left")
                papers_df["filtered_entity_count"] = papers_df["filtered_entity_count"].fillna(0).astype(int)
                papers_df = papers_df[papers_df["filtered_entity_count"] >= int(min_entities)]
                valid_pmids = set(papers_df["pmid"].tolist())
                entities_df = entities_df[entities_df["pmid"].isin(valid_pmids)]
            else:
                papers_df["filtered_entity_count"] = 0

        st.subheader("Papers")
        st.write(f"Matched papers with abstract + NER output: {len(papers_df)}")
        if len(papers_df) > 0:
            display_cols = ["pmid", "year", "journal", "title", "entity_count", "entity_types"]
            if "filtered_entity_count" in papers_df.columns:
                display_cols.append("filtered_entity_count")
            st.dataframe(papers_df[display_cols], use_container_width=True)
            st.download_button(
                "Download papers CSV",
                papers_df.to_csv(index=False).encode("utf-8"),
                file_name="papers_with_entities.csv",
                mime="text/csv",
            )
        else:
            st.info("No papers with usable abstract were found for this query.")

        st.subheader("Extracted Entities")
        if len(entities_df) > 0:
            st.dataframe(entities_df, use_container_width=True)
            st.download_button(
                "Download entities CSV",
                entities_df.to_csv(index=False).encode("utf-8"),
                file_name="extracted_entities.csv",
                mime="text/csv",
            )
        else:
            st.info("No entities extracted.")
