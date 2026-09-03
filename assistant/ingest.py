"""
ingest.py
---------
This script builds the vector database used for retrieval.

What it does, step by step:
  1. Reads each source document (plain Markdown files in data/).
  2. Splits each document into chunks along its section headings.
  3. Converts each chunk into a vector embedding (sentence-transformers).
  4. Stores the chunk text + embedding + metadata (document name, section)
     in a local ChromaDB collection saved to disk.

Run this once before using the assistant, and again any time the source
documents change:

    python ingest.py
"""

import os
import re

os.environ.setdefault("HF_HOME", os.path.abspath(".cache/huggingface"))
os.environ.setdefault("TRANSFORMERS_CACHE", os.path.abspath(".cache/huggingface/transformers"))
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

import chromadb
from sentence_transformers import SentenceTransformer

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
DATA_DIR = "data"
CHROMA_DIR = "chroma_db"                    # where the vector DB is saved on disk
COLLECTION_NAME = "mgc_docs"
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"   # small + fast + good enough for this size of corpus

# Map each real filename to a human-readable name we show in "Sources".
DOCUMENT_NAMES = {
    "01_mgc_aurora_heights_brochure.md": "MGC Brochure",
    "02_price_list_payment_plan.md": "MGC Price List",
    "03_booking_policy_faq.md": "MGC Booking Policy & FAQ",
}


def read_markdown_file(filepath):
    """Read a source file and return its raw text.

    Note: these documents are plain Markdown, not PDFs, so no PDF library
    (e.g. PyMuPDF) is needed here. If real PDFs were used instead, this is
    the only function that would need to change (swap in a PDF text
    extractor and keep everything downstream the same).
    """
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def split_into_sections(text):
    """Split a Markdown document into chunks along its '## ' headings.

    WHY split by heading instead of, say, every 500 characters?
    Each '## ' section in these documents is a self-contained topic
    (e.g. "Location Premiums", "Cancellations and Refunds"). Splitting on
    headings keeps related numbers and table rows together in a single
    chunk - which matters a lot here, because pricing questions need a
    whole table row (unit type + area + price) to stay intact.

    Returns a list of (section_title, section_text) tuples.
    """
    # Split right before every '## ' heading. Whatever comes before the
    # first '## ' (the title + intro line) becomes an "Overview" chunk.
    parts = re.split(r"\n(?=## )", text)
    sections = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        first_line = part.splitlines()[0]
        if first_line.startswith("## "):
            title = first_line.replace("## ", "").strip()
        else:
            title = "Overview"
        sections.append((title, part))
    return sections


def build_chunks():
    """Read every document and turn it into a flat list of chunk dicts.

    Each chunk dict carries the metadata we need later to cite a source:
        - chunk_id: unique id (used as the ChromaDB primary key)
        - text: the chunk content itself
        - document_name: human-readable source document name
        - section: which section of the document this chunk came from
    """
    chunks = []
    for filename, doc_name in DOCUMENT_NAMES.items():
        filepath = os.path.join(DATA_DIR, filename)
        raw_text = read_markdown_file(filepath)
        for i, (section_title, section_text) in enumerate(split_into_sections(raw_text)):
            chunks.append({
                "chunk_id": f"{filename}::{i}",
                "text": section_text,
                "document_name": doc_name,
                "section": section_title,
            })
    return chunks


def main():
    print("Reading and chunking documents...")
    chunks = build_chunks()
    print(f"Created {len(chunks)} chunks from {len(DOCUMENT_NAMES)} documents.")

    # -----------------------------------------------------------------
    # EMBEDDINGS
    # An embedding turns a piece of text into a list of numbers (a
    # vector) that represents its *meaning*. Text with similar meaning
    # ends up as vectors that sit close together in that number-space.
    # We embed both the document chunks (here) and, later, the user's
    # question, so we can find which chunks are semantically closest to
    # what the user asked - even if they don't use the exact same words
    # as the document.
    # -----------------------------------------------------------------
    print(f"Loading embedding model '{EMBEDDING_MODEL_NAME}'...")
    model = SentenceTransformer(EMBEDDING_MODEL_NAME)

    texts = [c["text"] for c in chunks]
    print("Creating embeddings for all chunks...")
    embeddings = model.encode(texts).tolist()

    # -----------------------------------------------------------------
    # VECTOR DATABASE
    # ChromaDB stores each chunk's text, embedding, and metadata, and
    # lets us later ask "which stored chunks are closest in meaning to
    # this new embedding?". PersistentClient saves everything to disk so
    # we only need to run this ingestion step once.
    # -----------------------------------------------------------------
    print("Saving chunks + embeddings to ChromaDB...")
    client = chromadb.PersistentClient(path=CHROMA_DIR)

    # Drop any previous collection first, so re-running ingest.py never
    # creates duplicate chunks.
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    collection = client.create_collection(COLLECTION_NAME)

    collection.add(
        ids=[c["chunk_id"] for c in chunks],
        embeddings=embeddings,
        documents=texts,
        metadatas=[
            {"document_name": c["document_name"], "section": c["section"]}
            for c in chunks
        ],
    )

    print(f"Done. Stored {len(chunks)} chunks in '{CHROMA_DIR}/'.")


if __name__ == "__main__":
    main()
