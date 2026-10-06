#!/usr/bin/env python3
"""embed — semantic channel with a real, local, multilingual embedding model.

OPTIONAL and OFF by default: eval_retrieval.py only uses it when OB_EMBED=1.
Everything else in retrieval-eval works without it, and this module imports
its heavy dependencies (numpy, onnxruntime, tokenizers) lazily, only when the
channel is actually built or queried.

Why it exists, and why `lsa.py` is not enough: truncated SVD only learns
co-occurrence within the corpus itself. If two notes never appear together,
LSA does not see them as similar, however much they say the same thing in
other words. A model trained multilingually already knows that "expert blind
spot" and "the teacher skips the steps they no longer see" are the same idea.
That is exactly the missing jump: log queries are natural-language tasks and
notes are abstract claims.

Real cost: no torch, no transformers, no API key. Only `onnxruntime`, the
`tokenizers` wheel and an ONNX model on disk. The vault never leaves the
machine.

Setup (only if you want to try the channel):
  pip install numpy onnxruntime tokenizers
  put the int8-quantized ONNX export of `multilingual-e5-small` in
  retrieval-eval/models/multilingual-e5-small/ as `model_quantized.onnx`
  plus its `tokenizer.json`, then run `OB_EMBED=1 python3 eval_retrieval.py index`.

The artifact is N x 384 in float16. It carries the index fingerprint, like the
other artifacts: an out-of-sync channel does not fail, it silently returns
noise — which is how a misaligned lsa.npz once dropped known-item retrieval
to zero without raising any error.
"""

from __future__ import annotations

import json
import os
import re

try:  # lazy/optional: the rest of the engine must work without numpy here
    import numpy as np
except ImportError:  # pragma: no cover
    np = None

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(HERE, "models", "multilingual-e5-small")
MAXLEN = 192          # title + head of the body; the title is the claim
BATCH = 32
DIM = 384

# e5 is trained with these prefixes and needs them: without them the query
# space and the document space are not aligned.
Q_PREFIX = "query: "
D_PREFIX = "passage: "

FM = re.compile(r"\A---\n.*?\n---\n", re.S)
WS = re.compile(r"\s+")


def _np():
    if np is None:
        raise RuntimeError("the embed channel needs numpy (pip install numpy). "
                           "It is optional: leave OB_EMBED=0 to skip it.")
    return np


def _session():
    """CPU on purpose, not CoreML. Measured on this same model: CoreML ~4
    notes/s, CPU with 10 threads ~52 notes/s — about 13x faster. The cause is in
    the onnxruntime log: the multilingual model's embedding table has ~250k rows
    and CoreML does not support dim > 16,384, so it splits the graph into dozens
    of pieces and pays the round trip on each. A small int8 model on CPU does
    not need it. If the float model is ever used, measure again."""
    import onnxruntime as ort
    so = ort.SessionOptions()
    so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    so.intra_op_num_threads = os.cpu_count() or 4
    return ort.InferenceSession(os.path.join(MODEL_DIR, "model_quantized.onnx"),
                                sess_options=so, providers=["CPUExecutionProvider"])


def _tokenizer():
    from tokenizers import Tokenizer
    tk = Tokenizer.from_file(os.path.join(MODEL_DIR, "tokenizer.json"))
    tk.enable_truncation(max_length=MAXLEN)
    tk.enable_padding(length=None)
    return tk


def _encode(sess, tk, texts):
    np = _np()
    enc = tk.encode_batch(texts)
    ids = np.array([e.ids for e in enc], dtype=np.int64)
    att = np.array([e.attention_mask for e in enc], dtype=np.int64)
    tt = np.zeros_like(ids)
    h = sess.run(["last_hidden_state"], {"input_ids": ids, "attention_mask": att,
                                         "token_type_ids": tt})[0]
    # Masked mean pooling: averaging over padding adds zeros and shifts the vector.
    m = att[:, :, None].astype(np.float32)
    v = (h * m).sum(axis=1) / np.maximum(m.sum(axis=1), 1e-9)
    n = np.linalg.norm(v, axis=1, keepdims=True)
    return (v / np.maximum(n, 1e-9)).astype(np.float32)


def note_text(root, rel, title):
    """Title + head of the body. In a Zettelkasten of claims the title IS the
    assertion, so it goes first and weighs what it should."""
    try:
        raw = open(os.path.join(root, rel), encoding="utf-8", errors="ignore").read()
    except OSError:
        raw = ""
    body = FM.sub("", raw)
    body = WS.sub(" ", body).strip()
    return D_PREFIX + title + ". " + body[:1200]


def build(root, ix, path, progress=None):
    np = _np()
    sess, tk = _session(), _tokenizer()
    N = len(ix.docs)
    E = np.zeros((N, DIM), dtype=np.float32)
    for s in range(0, N, BATCH):
        chunk = ix.docs[s:s + BATCH]
        E[s:s + len(chunk)] = _encode(
            sess, tk, [note_text(root, d["rel"], d["title"]) for d in chunk])
        if progress and (s // BATCH) % 20 == 0:
            progress(s + len(chunk), N)
    np.savez_compressed(path, E=E.astype(np.float16))
    json.dump({"fingerprint": ix.fingerprint(), "model": "multilingual-e5-small (onnx int8)",
               "dim": DIM, "maxlen": MAXLEN, "docs": N},
              open(path + ".meta.json", "w"), ensure_ascii=False)
    return {"docs": N, "dim": DIM, "fingerprint": ix.fingerprint(),
            "mb": round(os.path.getsize(path) / 1e6, 1)}


class Embed(object):
    def __init__(self, path, ix):
        np = _np()
        meta = json.load(open(path + ".meta.json"))
        if meta.get("fingerprint") != ix.fingerprint():
            raise RuntimeError(
                "embed.npz is out of sync with the index (fingerprint %s != %s). "
                "Rebuild: python3 eval_retrieval.py index" %
                (meta.get("fingerprint"), ix.fingerprint()))
        self.E = np.load(path)["E"].astype(np.float32)
        self.ix = ix
        self._sess = self._tk = None

    def _lazy(self):
        if self._sess is None:
            self._sess, self._tk = _session(), _tokenizer()
        return self._sess, self._tk

    def search(self, text, k=100):
        np = _np()
        if not text or not text.strip():
            return []
        sess, tk = self._lazy()
        q = _encode(sess, tk, [Q_PREFIX + text.strip()])[0]
        sims = self.E.dot(q)
        kk = min(k, len(sims) - 1)
        top = np.argpartition(-sims, kk)[:k]
        top = top[np.argsort(-sims[top], kind="stable")]
        return [(self.ix.docs[int(i)]["rel"], round(float(sims[i]), 4)) for i in top]
