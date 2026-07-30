# File: src/rag/build_vector_store.py

import json
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

BRONZE_PDF_DIR = Path("data/bronze/pdf")
CHROMA_DB_DIR = Path("data/vector_store")
CHROMA_DB_DIR.mkdir(parents=True, exist_ok=True)

CHUNK_SIZE = 800      # characters per chunk
CHUNK_OVERLAP = 150   # overlap between consecutive chunks, so context isn't cut off


def load_bronze_pdf_records() -> list:
    records = []
    for json_file in BRONZE_PDF_DIR.glob("*.json"):
        with open(json_file, "r", encoding="utf-8") as f:
            records.append(json.load(f))
    return records


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list:
    """
    Splits text into overlapping chunks by character count.
    Simple and effective starting point — no fancy sentence-boundary logic yet.
    """
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += chunk_size - overlap
    return chunks


def build_chunks_from_records(records: list) -> list:
    """
    Returns a list of dicts: {id, text, source_file, page_number}
    One entry per chunk, with metadata tracing it back to its source.
    """
    all_chunks = []
    chunk_counter = 0

    for record in records:
        source_file = record["source_file"]

        for page in record["pages"]:
            page_text = page["text"]
            page_number = page["page_number"]

            if not page_text or not page_text.strip():
                continue

            page_chunks = chunk_text(page_text)

            for chunk in page_chunks:
                all_chunks.append({
                    "id": f"chunk_{chunk_counter}",
                    "text": chunk,
                    "source_file": source_file,
                    "page_number": page_number,
                })
                chunk_counter += 1

    return all_chunks


def build_vector_store(chunks: list):
    """
    Embeds all chunks and stores them in a persistent ChromaDB collection.
    """
    print("Loading embedding model (first run downloads it, may take a minute)...")
    model = SentenceTransformer("all-MiniLM-L6-v2")  # small, fast, free, well-established

    print(f"Embedding {len(chunks)} chunks...")
    texts = [c["text"] for c in chunks]
    embeddings = model.encode(texts, show_progress_bar=True)

    client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))

    # Recreate collection fresh each time (idempotent — avoids duplicate accumulation,
    # same lesson learned from the bronze layer earlier)
    try:
        client.delete_collection("esg_documents")
    except Exception:
        pass  # collection didn't exist yet, that's fine

    collection = client.create_collection("esg_documents")

    collection.add(
        ids=[c["id"] for c in chunks],
        embeddings=embeddings.tolist(),
        documents=texts,
        metadatas=[
            {"source_file": c["source_file"], "page_number": c["page_number"]}
            for c in chunks
        ],
    )

    print(f"[OK] Stored {len(chunks)} chunks in ChromaDB at {CHROMA_DB_DIR}")


if __name__ == "__main__":
    records = load_bronze_pdf_records()
    print(f"Loaded {len(records)} bronze PDF records")

    chunks = build_chunks_from_records(records)
    print(f"Created {len(chunks)} chunks total")

    build_vector_store(chunks)