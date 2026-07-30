# File: src/dashboard/app.py

import duckdb
import pandas as pd
import streamlit as st
from pathlib import Path
import os
from dotenv import load_dotenv
from groq import Groq
from sentence_transformers import SentenceTransformer
import chromadb

load_dotenv()

GOLD_DB_PATH = Path("data/gold/esg_gold.duckdb")

st.set_page_config(
    page_title="ESG Data Platform — Assessment Dashboard",
    layout="wide",
)


@st.cache_data(ttl=30)  # cache for 30s so repeated reruns don't hammer DuckDB
def load_gold_data():
    con = duckdb.connect(str(GOLD_DB_PATH), read_only=True)
    valid_df = con.execute("SELECT * FROM gold_valid_records").fetchdf()
    flagged_df = con.execute("SELECT * FROM gold_flagged_records").fetchdf()
    con.close()
    return valid_df, flagged_df

@st.cache_resource  # cache_resource, not cache_data — these are models/clients, not data
def load_rag_components():
    embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
    chroma_client = chromadb.PersistentClient(path="data/vector_store")
    collection = chroma_client.get_collection("esg_documents")
    groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    return embedding_model, chroma_client, collection, groq_client


def retrieve_relevant_chunks(question, embedding_model, collection, top_k=5):
    question_embedding = embedding_model.encode([question]).tolist()
    results = collection.query(query_embeddings=question_embedding, n_results=top_k)

    chunks = []
    for i in range(len(results["documents"][0])):
        chunks.append({
            "text": results["documents"][0][i],
            "source_file": results["metadatas"][0][i]["source_file"],
            "page_number": results["metadatas"][0][i]["page_number"],
        })
    return chunks


def build_prompt(question, chunks):
    context_blocks = []
    for i, chunk in enumerate(chunks, start=1):
        context_blocks.append(
            f"[Source {i}: {chunk['source_file']}, page {chunk['page_number']}]\n{chunk['text']}"
        )
    context = "\n\n---\n\n".join(context_blocks)

    return f"""You are an ESG/EPD document assistant. Answer the question using ONLY
the context provided below. If the answer is not present in the context, say so clearly
instead of guessing. Always cite which source(s) you used (e.g. "Source 2").

Context:
{context}

Question: {question}

Answer:"""


st.title("🌱 ESG Data Platform — Assessment Dashboard")
st.caption("Bronze → Silver → Gold pipeline output, orchestrated via Airflow")

valid_df, flagged_df = load_gold_data()

total_docs = len(valid_df) + len(flagged_df)
valid_count = len(valid_df)
flagged_count = len(flagged_df)
pass_rate = (valid_count / total_docs * 100) if total_docs > 0 else 0

# ---- Summary metrics ----
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Documents Processed", total_docs)
col2.metric("Valid Records", valid_count)
col3.metric("Flagged Records", flagged_count)
col4.metric("Pass Rate", f"{pass_rate:.1f}%")

st.divider()

# ---- Tabs for valid vs flagged ----
tab1, tab2, tab3 = st.tabs(["🚩 Flagged Records", "✅ Valid Records", "💬 Ask a Question"])

with tab1:
    st.subheader("Documents flagged for review")
    if flagged_count == 0:
        st.success("No flagged records.")
    else:
        st.warning(f"{flagged_count} document(s) require manual review.")

        # Let user filter by flag reason type
        all_reasons = flagged_df["_flags"].str.split("; ").explode().unique()
        selected_reason = st.selectbox(
            "Filter by flag reason",
            options=["All"] + sorted(all_reasons.tolist())
        )

        display_df = flagged_df
        if selected_reason != "All":
            display_df = flagged_df[flagged_df["_flags"].str.contains(selected_reason, na=False)]

        st.dataframe(
            display_df[["_source_file", "product_name", "gwp_total", "standard_reference", "_flags"]],
            use_container_width=True,
            hide_index=True,
        )

with tab2:
    st.subheader("Validated documents")
    if valid_count == 0:
        st.info("No valid records yet — all current documents are flagged for review.")
    else:
        st.dataframe(
            valid_df[["_source_file", "product_name", "gwp_total", "standard_reference"]],
            use_container_width=True,
            hide_index=True,
        )
with tab3:
    st.subheader("Ask a question about your ESG/EPD documents")
    st.caption("Answers are generated only from the content of your ingested documents (RAG-grounded).")

    embedding_model, chroma_client, collection, groq_client = load_rag_components()

    question = st.text_input("Your question:", placeholder="e.g. What standards are referenced in these EPD documents?")

    if st.button("Ask") and question.strip():
        with st.spinner("Retrieving relevant document sections and generating answer..."):
            chunks = retrieve_relevant_chunks(question, embedding_model, collection)
            prompt = build_prompt(question, chunks)

            response = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
            )
            answer = response.choices[0].message.content

        st.markdown("### Answer")
        st.write(answer)

        st.markdown("### Sources retrieved")
        for c in chunks:
            st.caption(f"📄 {c['source_file']} — page {c['page_number']}")
st.divider()
st.caption(f"Data source: `{GOLD_DB_PATH}` | Refresh the page to reload latest pipeline output")