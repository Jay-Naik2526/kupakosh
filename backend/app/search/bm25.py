"""Memory-light BM25 (Okapi) over every report sentence.

Gives the same scores as rank_bm25.BM25Okapi (k1 = 1.5, b = 0.75, epsilon = 0.25, same idf floor for very common
words), but stores term frequencies as one sparse matrix instead of a Python dict per sentence. On 2,24,016
sentences that is tens of MB instead of more than a gigabyte, so the copilot fits on a 2 GB server.
"""
from __future__ import annotations

import math
from array import array

import numpy as np
from scipy import sparse


class SparseBM25:
    def __init__(self, docs, k1: float = 1.5, b: float = 0.75, epsilon: float = 0.25):
        """docs: any iterable of token lists (a generator keeps peak memory low)."""
        self.k1, self.b = k1, b
        vocab: dict[str, int] = {}
        rows, cols, vals, lens = array("i"), array("i"), array("f"), array("d")
        n = 0
        for i, d in enumerate(docs):
            lens.append(len(d))
            counts: dict[int, int] = {}
            for t in d:
                j = vocab.setdefault(t, len(vocab))
                counts[j] = counts.get(j, 0) + 1
            rows.extend([i] * len(counts))
            cols.extend(counts.keys())
            vals.extend(counts.values())
            n = i + 1
        doc_len = np.frombuffer(lens, dtype=np.float64) if n else np.zeros(0)
        rows, cols, vals = np.frombuffer(rows, dtype=np.int32), np.frombuffer(cols, dtype=np.int32), np.frombuffer(vals, dtype=np.float32)
        # CSC: one column per word, so a query word's postings are a contiguous slice
        self.tf = sparse.csc_matrix((vals, (rows, cols)), shape=(n, len(vocab)))
        self.vocab = vocab
        self.corpus_size = n
        self.avgdl = float(doc_len.sum() / n) if n else 0.0
        self.norm = (k1 * (1 - b + b * doc_len / self.avgdl)).astype(np.float64) if n else doc_len
        # idf exactly as rank_bm25.BM25Okapi._calc_idf
        df = np.diff(self.tf.indptr)
        idf = np.log(n - df + 0.5) - np.log(df + 0.5)
        avg = float(idf.sum() / len(idf)) if len(idf) else 0.0
        idf[idf < 0] = epsilon * avg
        self.idf = idf

    def get_scores(self, query: list[str]) -> np.ndarray:
        score = np.zeros(self.corpus_size, dtype=np.float64)
        for q in query:  # repeated query words count again, as in rank_bm25
            j = self.vocab.get(q)
            if j is None:
                continue
            lo, hi = self.tf.indptr[j], self.tf.indptr[j + 1]
            rows = self.tf.indices[lo:hi]
            f = self.tf.data[lo:hi].astype(np.float64)
            score[rows] += self.idf[j] * (f * (self.k1 + 1) / (f + self.norm[rows]))
        return score


class LazyTokens:
    """docs[i] -> tokens of sentence i, computed on demand (only the few candidates per question need them)."""

    def __init__(self, texts: list[str], tok):
        self._texts, self._tok = texts, tok

    def __getitem__(self, i: int) -> list[str]:
        return self._tok(self._texts[i])

    def __len__(self) -> int:
        return len(self._texts)


def _selfcheck() -> None:
    """Equivalence check against rank_bm25 on a small corpus (run: python -m app.search.bm25)."""
    from rank_bm25 import BM25Okapi
    docs = [s.split() for s in ["stuck pipe at 1200 m", "losses cured with lcm pill", "stuck stuck pipe jarred free",
                                 "tight hole ream", "pipe", "gas kick shut in well", "the well was plugged"]]
    ref, new = BM25Okapi(docs), SparseBM25(docs)
    for q in (["stuck", "pipe"], ["well"], ["pipe", "pipe"], ["nothing"]):
        assert np.allclose(ref.get_scores(q), new.get_scores(q)), q
    assert math.isclose(ref.avgdl, new.avgdl)
    print("SparseBM25 matches rank_bm25.BM25Okapi")


if __name__ == "__main__":
    _selfcheck()
