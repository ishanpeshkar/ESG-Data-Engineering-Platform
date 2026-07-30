# File: src/rag/ask_esg.py

import os
from dotenv import load_dotenv
from groq import Groq
import chromadb
from sentence_transformers import SentenceTransformer

load_dotenv()

CHROMA_DB_DIR = "data/vector_store"
TOP_K = 5  # how many chunks to retrieve per question

# ---- Setup (loaded once) ----
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
chroma_client = chromadb.PersistentClient(path=CHROMA_DB_DIR)
collection = chroma_client.get_collection("esg_documents")

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def retrieve_relevant_chunks(question: str, top_k: int = TOP_K) -> list:
    """
    Embeds the question and retrieves the most similar chunks from ChromaDB.
    """
    question_embedding = embedding_model.encode([question]).tolist()

    results = collection.query(
        query_embeddings=question_embedding,
        n_results=top_k,
    )

    chunks = []
    for i in range(len(results["documents"][0])):
        chunks.append({
            "text": results["documents"][0][i],
            "source_file": results["metadatas"][0][i]["source_file"],
            "page_number": results["metadatas"][0][i]["page_number"],
        })
    return chunks


def build_prompt(question: str, chunks: list) -> str:
    """
    Builds a grounded prompt: instructs the LLM to answer ONLY using the
    provided context, and to cite which document/page it came from.
    """
    context_blocks = []
    for i, chunk in enumerate(chunks, start=1):
        context_blocks.append(
            f"[Source {i}: {chunk['source_file']}, page {chunk['page_number']}]\n{chunk['text']}"
        )
    context = "\n\n---\n\n".join(context_blocks)

    prompt = f"""You are an ESG/EPD document assistant. Answer the question using ONLY
the context provided below. If the answer is not present in the context, say so clearly
instead of guessing. Always cite which source(s) you used (e.g. "Source 2").

Context:
{context}

Question: {question}

Answer:"""
    return prompt


def ask(question: str):
    chunks = retrieve_relevant_chunks(question)
    prompt = build_prompt(question, chunks)

    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
    )

    answer = response.choices[0].message.content

    print("\n" + "=" * 60)
    print("QUESTION:", question)
    print("=" * 60)
    print("\nANSWER:\n", answer)
    print("\n" + "-" * 60)
    print("Retrieved sources:")
    for c in chunks:
        print(f"  - {c['source_file']} (page {c['page_number']})")


if __name__ == "__main__":
    # ---- Quick test question ----
    ask("What standards are referenced in these EPD documents?")