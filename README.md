# taxdoc-rag

A small, local RAG (retrieval-augmented generation) system for answering questions about
accounting documents (invoices, payslips, bank statements and internal policies), with a
labelled evaluation set that measures accuracy, false positives and false negatives.

All documents are **synthetic**. The firm, clients, people and figures are invented.

## Why this project

Most RAG demos stop at "it answers questions". In practice the hard part is knowing *how often*
it's right, and *why* it's wrong when it isn't. This project is built around that:

- **Table-aware PDF extraction.** Tables are extracted separately with pdfplumber and each row is
  written as `Header: value` pairs, so a row like a bank transaction still makes sense on its own
  after chunking. Pages with no extractable text are flagged (likely scanned) instead of skipped.
- **Hybrid retrieval.** BM25 keyword search (exact matches on invoice numbers, amounts, dates) plus
  embedding search (meaning), merged with Reciprocal Rank Fusion.
- **Grounded, validated answers.** The model must answer from the provided chunks only, cite chunk
  ids, and is allowed to say "not found". Output is parsed strictly: broken JSON or citations to
  chunks it was never given are reported as errors, not passed through.
- **Evaluation harness.** 28 labelled questions, including 6 that look answerable but aren't
  (wrong month, invoice that doesn't exist, information not in any document). Retrieval and
  answering are scored separately.
- **Runs fully local** with Ollama, or on **AWS Bedrock** (Claude + Titan embeddings, default
  region `ap-southeast-2`) by changing one setting.

## How it works

```
PDFs ──> extract.py ──> chunk.py ──> index.py ──────────────> answer.py ──> JSON answer + citations
        (text + tables)  (page-safe   (BM25 + embeddings,      (prompt, LLM call,
                          chunks)      saved to data/index)     strict validation)
                                                                      │
                                               evaluate.py <──────────┘  (questions.jsonl -> metrics)
```

| File | What it does |
|---|---|
| `scripts/make_synthetic_docs.py` | Generates the 6 synthetic PDFs (one statement spans 2 pages on purpose) |
| `taxrag/extract.py` | pdfplumber extraction; tables become `Header: value` lines |
| `taxrag/chunk.py` | Line-safe chunking, never mixes pages, adds a document header to each chunk |
| `taxrag/bm25.py` | BM25 keyword search, written out in full |
| `taxrag/providers.py` | Ollama and Bedrock behind the same `embed()` / `chat()` interface |
| `taxrag/index.py` | Builds and loads the index; hybrid search with RRF |
| `taxrag/answer.py` | Prompt, LLM call, strict output validation with one retry |
| `taxrag/evaluate.py` | Runs the question set and writes CSV + summary JSON |
| `tests/` | Unit tests that need no model |

## Setup

Requires Python 3.10+.

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                 # Windows: copy .env.example .env
python scripts/make_synthetic_docs.py
```

### Option A: fully local with Ollama (free)

Install [Ollama](https://ollama.com), then:

```bash
ollama pull llama3.1:8b
ollama pull nomic-embed-text
```

Keep `LLM_PROVIDER=ollama` and `EMBED_PROVIDER=ollama` in `.env`.

### Option B: AWS Bedrock

Enable model access in the Bedrock console for region `ap-southeast-2`, configure AWS credentials
(`aws configure`), then set in `.env`:

```
LLM_PROVIDER=bedrock
EMBED_PROVIDER=bedrock
AWS_REGION=ap-southeast-2
BEDROCK_CHAT_MODEL=<model or inference profile ID from the Bedrock console>
```

### Option C: no model at all

`EMBED_PROVIDER=none` and `LLM_PROVIDER=none` lets you run ingestion, keyword search and the
retrieval part of the evaluation without installing anything else.

## Usage

```bash
python -m taxrag ingest                                   # build the index
python -m taxrag search "closing balance Bluegum July"    # inspect what retrieval returns
python -m taxrag ask "What is the total payable on invoice INV-1042?"
python -m taxrag eval                                     # full evaluation
python -m taxrag eval --retrieval-only -k 1               # retrieval only, top-1
python -m pytest -q                                       # unit tests
```

Example `ask` output:

```json
{
  "question": "What is the total payable on invoice INV-1042?",
  "found": true,
  "answer": "$3,135.00",
  "citations": ["invoice_INV-1042.pdf#p1#c0"],
  ...
}
```

## Results

Retrieval with BM25 only (no embeddings), 22 answerable questions:

| Setting | Hit rate (right page in top-k) | MRR |
|---|---|---|
| top-5 | 1.00 | 0.955 |
| top-1 | 0.909 | 0.909 |

At top-1 there are two misses, and both are bank statement rows that lose to a "louder" chunk:

- *"On what date did Bluegum Cafe pay Harbourline invoice INV-1042?"* — the invoice itself ranks
  first because it repeats "INV-1042" and "Harbourline"; the bank row that records the payment is second.
- *"How much was the bank fee on the Bluegum Cafe July statement?"* — the boilerplate text block at
  the top of the statement ranks first because it repeats the word "statement"; the row is second.

Both are fixed at top-3, which is why the default is top-5. Embeddings or a re-ranker are the
next things to test against these two cases.

<!-- After running `python -m taxrag eval` with a model, paste your summary here:
| Model | Embeddings | Answer accuracy | Refusal accuracy | False positives | False negatives | Avg latency |
-->

## Ideas for next steps

- Add OCR (e.g. Tesseract) for scanned pages that are currently only flagged
- A re-ranking step after retrieval
- Compare models and chunk sizes on the same question set and track cost per question
- Field extraction mode: return a fixed JSON schema per document type (invoice, payslip)
