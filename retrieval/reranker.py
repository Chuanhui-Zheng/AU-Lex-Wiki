"""
BGE Reranker cross-encoder: re-scores top-k candidates from hybrid search.
"""
from FlagEmbedding import FlagReranker
from config import config

_reranker: FlagReranker | None = None


def get_reranker() -> FlagReranker:
    global _reranker
    if _reranker is None:
        _reranker = FlagReranker(config.reranker_model, use_fp16=True)
    return _reranker


def rerank(query: str, candidates: list[dict], top_n: int = None) -> list[dict]:
    top_n = top_n or config.top_n_rerank
    if not candidates:
        return []

    if not config.enable_local_embeddings:
        results = []
        for candidate in candidates[:top_n]:
            c = candidate.copy()
            c["rerank_score"] = float(c.get("score", 0))
            results.append(c)
        return results

    reranker = get_reranker()
    pairs = [(query, c["body"]) for c in candidates]
    scores = reranker.compute_score(pairs, normalize=True)

    ranked = sorted(
        zip(scores, candidates),
        key=lambda x: -x[0],
    )
    results = []
    for score, candidate in ranked[:top_n]:
        c = candidate.copy()
        c["rerank_score"] = float(score)
        results.append(c)
    return results
