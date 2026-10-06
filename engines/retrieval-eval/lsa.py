#!/usr/bin/env python3
"""lsa — local, deterministic semantic channel (LSA / truncated SVD over the vault).

Why it exists: retrieval queries are natural-language tasks ("improve this
screen, the X at the bottom looks odd") and notes are abstract claims ("Button
design combines affordance hierarchy size and copy"). Lexical overlap between
the two is close to zero, so BM25 alone scores very low recall against recorded
use — not because the vault is bad, but because the query->note jump is
semantic.

No network and no new dependencies (numpy always; scipy only to build the
index): the vault's own TF-IDF matrix is factorised with truncated SVD and
compared in the latent space. It captures real corpus co-occurrence ("screen"
appears next to design vocabulary IN YOUR OWN NOTES), which is exactly the
missing bridge. It is not a trained embedding: it is weaker, but local,
reproducible, and it never sends the vault anywhere.

numpy is imported lazily-tolerant: if it is missing, the channel is simply
unavailable (eval_retrieval.py skips it) instead of breaking the whole engine.
"""

from __future__ import annotations

import json
import os

try:
    import numpy as np
except ImportError:  # pragma: no cover
    np = None

import rlib

DIM = 300
MIN_DF = 2


def _np():
    if np is None:
        raise RuntimeError("the LSA channel needs numpy (pip install numpy).")
    return np


def build(ix, path):
    np = _np()
    # scipy is only needed to BUILD the index (truncated SVD). The LSA class
    # below, which runs on every query, only uses numpy: importing scipy at the
    # top made `retrieve` abort in any shell without scipy even when the .npz
    # was already built.
    try:
        from scipy.sparse import csr_matrix
        from scipy.sparse.linalg import svds
    except ImportError as e:
        raise RuntimeError(
            "lsa.build needs scipy (only for indexing; querying does not use it). "
            "Install scipy in this python3 or run `eval_retrieval.py index` "
            "where you have it. Detail: %s" % e)
    vocab = {t: j for j, t in enumerate(sorted(t for t, d in ix.df.items() if d >= MIN_DF))}
    N = len(ix.docs)
    idf = np.zeros(len(vocab), dtype=np.float32)
    for t, j in vocab.items():
        idf[j] = np.log((1.0 + N) / (1.0 + ix.df[t])) + 1.0
    rows, cols, vals = [], [], []
    for i, tf in enumerate(ix.tf):
        for t, f in tf.items():
            j = vocab.get(t)
            if j is None:
                continue
            rows.append(i); cols.append(j); vals.append(1.0 + np.log(f))
    X = csr_matrix((np.array(vals, dtype=np.float32), (rows, cols)),
                   shape=(N, len(vocab)))
    X = X.multiply(idf[None, :]).tocsr()
    norms = np.sqrt(X.multiply(X).sum(axis=1)).A.ravel()
    norms[norms == 0] = 1.0
    X = csr_matrix(X.multiply((1.0 / norms)[:, None]))
    k = min(DIM, min(X.shape) - 1)
    U, S, Vt = svds(X, k=k, random_state=0)
    order = np.argsort(-S)
    U, S, Vt = U[:, order], S[order], Vt[order, :]
    D = U * S                        # document vectors
    dn = np.linalg.norm(D, axis=1); dn[dn == 0] = 1.0
    D = D / dn[:, None]
    np.savez_compressed(path, D=D.astype(np.float32), Vt=Vt.astype(np.float32),
                        idf=idf, S=S.astype(np.float32))
    json.dump({"vocab": vocab, "fingerprint": ix.fingerprint()},
              open(path + ".vocab.json", "w"), ensure_ascii=False)
    return {"docs": N, "vocab": len(vocab), "dim": int(k),
            "fingerprint": ix.fingerprint(),
            "energy_top50": float(S[:50].sum() / S.sum())}


class LSA(object):
    def __init__(self, path, ix):
        np = _np()
        z = np.load(path)
        self.D, self.Vt, self.idf = z["D"], z["Vt"], z["idf"]
        meta = json.load(open(path + ".vocab.json"))
        self.vocab = meta["vocab"]
        if meta.get("fingerprint") != ix.fingerprint():
            raise RuntimeError(
                "lsa.npz is out of sync with the index (fingerprint %s != %s). "
                "Rebuild: python3 eval_retrieval.py index" %
                (meta.get("fingerprint"), ix.fingerprint()))
        self.ix = ix

    def query_vec(self, text):
        np = _np()
        v = np.zeros(len(self.vocab), dtype=np.float32)
        toks = rlib.tokenize(text)
        if not toks:
            return None
        from collections import Counter
        for t, f in Counter(toks).items():
            j = self.vocab.get(t)
            if j is not None:
                v[j] = (1.0 + np.log(f)) * self.idf[j]
        n = np.linalg.norm(v)
        if n == 0:
            return None
        q = self.Vt.dot(v / n)
        qn = np.linalg.norm(q)
        return None if qn == 0 else q / qn

    def search(self, text, k=100):
        np = _np()
        q = self.query_vec(text)
        if q is None:
            return []
        sims = self.D.dot(q)
        top = np.argpartition(-sims, min(k, len(sims) - 1))[:k]
        top = top[np.argsort(-sims[top], kind="stable")]
        return [(self.ix.docs[int(i)]["rel"], round(float(sims[i]), 4)) for i in top]
