"""BM25 keyword search, written out in ~40 lines so it's easy to explain.

Why keyword search at all when we have embeddings? Financial documents are full of
exact tokens (invoice numbers, ABNs, dollar amounts, dates) that embeddings often
blur together. BM25 matches those exactly. We combine both in index.py.
"""

import math
import re
from collections import Counter

TOKEN = re.compile(r"[a-z0-9]+(?:[.\-/][a-z0-9]+)*")
STOPWORDS = set("a an and are as at be by for from has have how in is it of on or that the this to was what when which who will with does did".split())


def tokenize(text: str) -> list[str]:
    return [t for t in TOKEN.findall(text.lower()) if t not in STOPWORDS]


class BM25:
    def __init__(self, docs: list[str], k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self.docs = [tokenize(d) for d in docs]
        self.lengths = [len(d) for d in self.docs]
        self.avg_len = sum(self.lengths) / max(len(self.docs), 1)
        self.tf = [Counter(d) for d in self.docs]
        df = Counter(term for d in self.docs for term in set(d))
        n = len(self.docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def scores(self, query: str) -> list[float]:
        terms = tokenize(query)
        out = []
        for tf, length in zip(self.tf, self.lengths):
            s = 0.0
            for t in terms:
                if t not in tf:
                    continue
                f = tf[t]
                s += self.idf[t] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * length / self.avg_len))
            out.append(s)
        return out
