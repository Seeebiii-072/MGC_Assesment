# Assistant Module

## Overview

This folder contains the document-question answering part of the MGC AI Sales Assistant. It answers known assessment questions with deterministic code first, then falls back to retrieval from the local Chroma vector database for more general questions.

The main entry point is:

```python
from assistant import answer_question
```

## Folder Structure

```text
assistant/
  __init__.py
  assistant.py
  ingest.py
  data/
  chroma_db/
```

## Flow

```text
Markdown source documents
  -> ingest.py chunks documents by section
  -> sentence-transformers creates embeddings
  -> ChromaDB stores chunk text, embeddings, and source metadata

User question
  -> answer_question()
  -> deterministic handler if it matches a known assessment question
  -> otherwise retrieve() gets relevant chunks from ChromaDB
  -> optional LLM fallback answers only from retrieved context
  -> response includes answer, status, sources, and optional calculation
```

## Files

### `__init__.py`

Exports the package-level `answer_question` function from `assistant.py`.

This lets other parts of the app import the assistant cleanly:

```python
from assistant import answer_question
```

### `assistant.py`

Contains the runtime question-answering logic. This is the assistant brain used by `app.py` and `tests/test_questions.py`.

Main responsibilities:

- route each user question to the right answer path
- answer the five required assessment questions deterministically
- retrieve relevant document chunks for general questions
- optionally call an LLM with strict document-grounding rules
- return a consistent response dictionary

Important constants:

- `DATA_DIR`: source document directory
- `CHROMA_DIR`: local ChromaDB directory
- `COLLECTION_NAME`: Chroma collection name
- `EMBEDDING_MODEL_NAME`: sentence-transformers model used for embeddings
- `TOP_K`: number of chunks retrieved for generic RAG answers
- `RAW_FILES`: mapping of document keys to Markdown file paths and display names
- `STRICT_SYSTEM_PROMPT`: grounding rules used when an LLM is called
- `NOT_FOUND_MSG`: standard message for missing document evidence

Important functions:

- `answer_question(question)`: main public function. It checks deterministic handlers first, then uses the generic RAG fallback.
- `handle_base_price_lookup(question_lower)`: answers base price questions by reading the price table directly.
- `handle_price_calculation(question_lower)`: calculates total price using base price plus applicable location premiums.
- `handle_transfer_fee(question_lower)`: compares transfer fee values across documents and reports conflicts.
- `handle_rental_yield(question_lower)`: handles rental yield questions where the documents do not provide a reliable value.
- `handle_anchor_tenant(question_lower)`: answers whether an anchor tenant is confirmed.
- `generic_rag_answer(question)`: fallback path for questions outside the deterministic patterns.
- `retrieve(question, k=TOP_K)`: embeds the question and retrieves the most relevant chunks from ChromaDB.
- `_call_llm(question, context_chunks)`: calls OpenRouter, Gemini, or OpenAI if an API key is configured.
- `_classify_llm_answer(llm_text)`: maps LLM text to `FOUND IN DOCUMENT`, `NOT FOUND`, or `CONFLICTING INFORMATION`.
- `_get_embedding_model()`: lazily loads the sentence-transformers model.
- `_get_collection()`: lazily opens the ChromaDB collection.
- `_read_raw(key)`: reads a full source Markdown file for deterministic parsing.
- `_source(doc_key, section)`: formats source names for display.

Return format:

```python
{
    "answer": "text shown to the user",
    "status": "FOUND IN DOCUMENT | NOT FOUND | CONFLICTING INFORMATION | CALCULATED FROM DOCUMENT",
    "sources": ["Document Name - Section"],
    "calculation": "optional calculation text or None",
}
```

### `ingest.py`

Builds or refreshes the local vector database used by the RAG fallback.

Main responsibilities:

- read Markdown source documents
- split each document into section-based chunks
- create embeddings with `all-MiniLM-L6-v2`
- store chunks, embeddings, and metadata in ChromaDB
- replace the old Chroma collection when ingestion is rerun

Important functions:

- `read_markdown_file(filepath)`: reads one Markdown source file.
- `split_into_sections(text)`: splits a document by `##` headings so each chunk keeps related facts together.
- `build_chunks()`: creates chunk dictionaries with `chunk_id`, `text`, `document_name`, and `section`.
- `main()`: runs the full ingestion process and writes the collection to `chroma_db/`.

Run ingestion when documents change:

```bash
python -m assistant.ingest
```

### `data/`

Contains the Markdown source documents used by this assistant package:

```text
01_mgc_aurora_heights_brochure.md
02_price_list_payment_plan.md
03_booking_policy_faq.md
```

These files are used in two ways:

- deterministic handlers read them directly for exact prices, policies, and conflict checks
- `ingest.py` chunks and embeds them for semantic retrieval

### `chroma_db/`

Local persisted ChromaDB storage for the `mgc_docs` collection.

This directory is generated by `ingest.py`. If the source documents change, rerun ingestion so the vector database matches the latest Markdown content.

## LLM Provider Fallback

The assistant can answer generic questions without an LLM by returning the most relevant retrieved excerpt. If an API key is available, `_call_llm()` checks providers in this order:

```text
OPENROUTER_API_KEY
GEMINI_API_KEY
OPENAI_API_KEY
```

The LLM is instructed to answer only from retrieved document context, report conflicts, and say when information is not available.

## Testing

From the project root, run:

```bash
python tests/test_questions.py
```

The test script exercises the five required assessment questions through `answer_question()`.
