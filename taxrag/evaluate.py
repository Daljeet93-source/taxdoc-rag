"""Measure the pipeline against a fixed, labelled question set.

Two layers are scored separately, because they fail for different reasons:

Retrieval  - did the right page make it into the top-k chunks?  (hit@k, MRR)
Answering  - given those chunks, did the model answer correctly, or correctly say "not found"?

Answer outcomes:
  correct        answerable, model answered, answer matches
  wrong          answerable, model answered, answer does NOT match
  false_negative answerable, model said "not found"
  false_positive NOT answerable, model answered anyway (a hallucination)
  true_negative  NOT answerable, model said "not found"
  error          model output could not be parsed / validated
"""

import json
import re
import time
from pathlib import Path

import pandas as pd

from .answer import ask
from .config import ROOT, settings
from .index import Index

QUESTIONS = ROOT / "evals" / "questions.jsonl"
RESULTS_DIR = ROOT / "evals" / "results"


def normalise(text: str) -> str:
    text = text.lower().replace("$", "").replace(",", "")
    text = re.sub(r"(\d)\.00\b", r"\1", text)
    return " ".join(text.split())


def is_correct(answer: str, expected: list[str], mode: str = "all") -> bool:
    got = normalise(answer)
    checks = [normalise(e) in got for e in expected]
    return any(checks) if mode == "any" else all(checks)


def load_questions(path: Path = QUESTIONS) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def run(retrieval_only: bool = False, k: int | None = None) -> pd.DataFrame:
    k = k or settings.top_k
    index = Index()
    rows = []
    for q in load_questions():
        hits = index.search(q["question"], k)
        ids = [c.id for c, _ in hits]
        row = {"id": q["id"], "question": q["question"], "answerable": q["answerable"]}

        if q["answerable"]:
            ranks = [i for i, (c, _) in enumerate(hits) if c.source == q["source"] and c.page == q["page"]]
            row["retrieval_hit"] = bool(ranks)
            row["reciprocal_rank"] = 1 / (ranks[0] + 1) if ranks else 0.0
        row["retrieved"] = " ; ".join(ids)

        if not retrieval_only:
            a = ask(index, q["question"], k)
            row.update(
                answer=a.answer, found=a.found, citations=" ; ".join(a.citations), error=a.error,
                input_tokens=a.usage.get("input_tokens", 0), output_tokens=a.usage.get("output_tokens", 0),
                latency_s=a.usage.get("latency_s", 0.0),
            )
            if a.error:
                outcome = "error"
            elif q["answerable"] and a.found:
                outcome = "correct" if is_correct(a.answer, q["expected"], q.get("match", "all")) else "wrong"
            elif q["answerable"]:
                outcome = "false_negative"
            elif a.found:
                outcome = "false_positive"
            else:
                outcome = "true_negative"
            row["outcome"] = outcome
            print(f"{q['id']}: {outcome:15} {a.answer!r}")
        rows.append(row)
    return pd.DataFrame(rows)


def summarise(df: pd.DataFrame) -> dict:
    ans = df[df["answerable"]]
    summary = {
        "questions": len(df),
        "top_k": settings.top_k,
        "retrieval_hit_rate": round(ans["retrieval_hit"].mean(), 3),
        "retrieval_mrr": round(ans["reciprocal_rank"].mean(), 3),
    }
    if "outcome" in df:
        counts = df["outcome"].value_counts().to_dict()
        summary["outcomes"] = counts
        summary["answer_accuracy"] = round(counts.get("correct", 0) / max(len(ans), 1), 3)
        unans = len(df) - len(ans)
        summary["refusal_accuracy"] = round(counts.get("true_negative", 0) / max(unans, 1), 3)
        summary["total_input_tokens"] = int(df["input_tokens"].sum())
        summary["total_output_tokens"] = int(df["output_tokens"].sum())
        summary["avg_latency_s"] = round(df["latency_s"].mean(), 2)
        summary["llm"] = f"{settings.llm_provider}"
    summary["embeddings"] = settings.embed_provider
    return summary


def main(retrieval_only: bool = False, k: int | None = None) -> dict:
    df = run(retrieval_only, k)
    summary = summarise(df)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    df.to_csv(RESULTS_DIR / f"results_{stamp}.csv", index=False)
    (RESULTS_DIR / f"summary_{stamp}.json").write_text(json.dumps(summary, indent=2))

    misses = df[df["answerable"] & ~df["retrieval_hit"].fillna(False).astype(bool)]
    if len(misses):
        print("\nRetrieval misses (right page not in top-k):")
        for _, r in misses.iterrows():
            print(f"  {r['id']}: {r['question']}")
    print("\nSummary:\n" + json.dumps(summary, indent=2))
    print(f"\nSaved to {RESULTS_DIR}")
    return summary
