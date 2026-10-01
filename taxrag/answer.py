"""Ask the model a question using only the retrieved chunks, and validate what comes back.

Two things matter more than the prompt wording:
1. The model must be allowed to say "not found". Most false positives in RAG come from
   a model that is forced to answer and fills the gap with a plausible guess.
2. The output is parsed strictly. If the JSON is broken, or it cites a chunk we never
   gave it, we report that as an error instead of quietly passing it through.
"""

import json
import re
from dataclasses import dataclass, field

from . import providers
from .chunk import Chunk
from .index import Index

SYSTEM_PROMPT = """You answer questions about accounting documents using ONLY the context provided.

Rules:
- Use only facts that appear in the context. Do not use outside knowledge.
- If the context does not contain the answer, set "found" to false and "answer" to null.
  Do not guess, and do not answer from a similar but different document (for example a different month, invoice or person).
- Quote numbers exactly as written in the context, including $ and commas.
- Cite the chunk ids you used.

Reply with JSON only, in exactly this shape:
{"found": true, "answer": "short answer", "citations": ["chunk id", "..."]}"""


@dataclass
class Answer:
    question: str
    found: bool
    answer: str | None
    citations: list[str]
    retrieved: list[str]
    usage: dict = field(default_factory=dict)
    error: str | None = None


def build_context(chunks: list[Chunk]) -> str:
    return "\n\n".join(f"<chunk id=\"{c.id}\">\n{c.text}\n</chunk>" for c in chunks)


def parse_response(raw: str, allowed_ids: set[str]) -> tuple[bool, str | None, list[str]]:
    """Strictly parse the model output. Raises ValueError on anything malformed."""
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise ValueError("no JSON object in model output")
    data = json.loads(match.group(0))
    if not isinstance(data.get("found"), bool):
        raise ValueError("'found' must be true/false")
    answer = data.get("answer")
    citations = data.get("citations") or []
    if data["found"]:
        if not answer or not isinstance(answer, str):
            raise ValueError("found=true but no answer")
        unknown = [c for c in citations if c not in allowed_ids]
        if unknown:
            raise ValueError(f"cited chunks that were not provided: {unknown}")
        if not citations:
            raise ValueError("found=true but no citations")
    else:
        answer, citations = None, []
    return data["found"], answer, citations


def ask(index: Index, question: str, k: int | None = None, retries: int = 1) -> Answer:
    hits = index.search(question, k) if k else index.search(question)
    chunks = [c for c, _ in hits]
    retrieved = [c.id for c in chunks]
    user = f"Context:\n{build_context(chunks)}\n\nQuestion: {question}"

    usage_total = {"input_tokens": 0, "output_tokens": 0, "latency_s": 0.0}
    last_error = None
    for _ in range(retries + 1):
        raw, usage = providers.chat(SYSTEM_PROMPT, user)
        for key in usage_total:
            usage_total[key] += usage.get(key, 0)
        try:
            found, answer, citations = parse_response(raw, set(retrieved))
            return Answer(question, found, answer, citations, retrieved, usage_total)
        except (ValueError, json.JSONDecodeError) as e:
            last_error = f"{e} | raw: {raw[:200]}"
    return Answer(question, False, None, [], retrieved, usage_total, error=last_error)
