"""Command line entry point.

    python -m taxrag ingest                  # read PDFs, chunk, embed, save index
    python -m taxrag search "question"       # show which chunks retrieval returns
    python -m taxrag ask "question"          # full RAG answer with citations
    python -m taxrag eval                    # run the labelled test set
    python -m taxrag eval --retrieval-only   # score retrieval without calling the LLM
"""

import argparse
import json
from dataclasses import asdict

from . import evaluate
from .answer import ask
from .index import Index, build_index


def main() -> None:
    parser = argparse.ArgumentParser(prog="taxrag")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("ingest")
    s = sub.add_parser("search")
    s.add_argument("question")
    s.add_argument("-k", type=int, default=None)
    a = sub.add_parser("ask")
    a.add_argument("question")
    a.add_argument("-k", type=int, default=None)
    e = sub.add_parser("eval")
    e.add_argument("--retrieval-only", action="store_true")
    e.add_argument("-k", type=int, default=None)
    args = parser.parse_args()

    if args.cmd == "ingest":
        build_index()
    elif args.cmd == "search":
        index = Index()
        hits = index.search(args.question, args.k) if args.k else index.search(args.question)
        for chunk, score in hits:
            print(f"\n--- {chunk.id}  (score {score:.4f})\n{chunk.text[:400]}")
    elif args.cmd == "ask":
        result = ask(Index(), args.question, args.k)
        print(json.dumps(asdict(result), indent=2))
    elif args.cmd == "eval":
        evaluate.main(args.retrieval_only, args.k)


if __name__ == "__main__":
    main()
