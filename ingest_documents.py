"""
ingest_documents.py — Load company documents into the knowledge_base table.
Splits each file into paragraph-sized chunks for retrieval.
Run: py ingest_documents.py
"""

import os
from lib.db import execute, query

DOCS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "company_docs")


def chunk_text(text, min_chunk_size=100):
    """Split text into chunks by double newline (paragraphs), merging small ones."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    chunks = []
    current = ""
    for p in paragraphs:
        current += p + "\n\n"
        if len(current) >= min_chunk_size:
            chunks.append(current.strip())
            current = ""
    if current.strip():
        chunks.append(current.strip())

    return chunks


def ingest_all_documents():
    if not os.path.exists(DOCS_DIR):
        print(f"No {DOCS_DIR} folder found.")
        return

    # Clear existing knowledge base to avoid duplicates on re-run
    execute("DELETE FROM knowledge_base")

    total_chunks = 0
    for filename in os.listdir(DOCS_DIR):
        if not filename.endswith(".txt"):
            continue

        filepath = os.path.join(DOCS_DIR, filename)
        with open(filepath, encoding="utf-8") as f:
            text = f.read()

        chunks = chunk_text(text)
        for i, chunk in enumerate(chunks):
            execute(
                "INSERT INTO knowledge_base (source_file, chunk_text, chunk_index) VALUES (%s, %s, %s)",
                [filename, chunk, i],
            )
            total_chunks += 1

        print(f"Ingested {len(chunks)} chunks from {filename}")

    print(f"\nTotal chunks in knowledge base: {total_chunks}")


if __name__ == "__main__":
    ingest_all_documents()