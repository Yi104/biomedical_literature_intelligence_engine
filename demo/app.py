import streamlit as st
from src.infer import ner


st.title("BioBERT Biomarker NER Demo")
model_path = st.text_input("Model checkpoint path", "outputs/checkpoints")
text = st.text_area("Paste a PubMed abstract (tokenized by space)", "BRCA1 is associated with ...")

if st.button("Extract Entities"):
    tokens = text.split()
    preds = ner(model_path, tokens)
    st.write(preds)
