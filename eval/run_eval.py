"""
Run DeepEval evaluation against the auto-generated QA set.
Uses LLM-as-a-Judge for faithfulness, relevance, and refusal detection.
"""
import json
import psycopg2
import anthropic
from pathlib import Path
from tqdm import tqdm
from deepeval import evaluate
from deepeval.metrics import (
    FaithfulnessMetric,
    AnswerRelevancyMetric,
    ContextualPrecisionMetric,
    ContextualRecallMetric,
)
from deepeval.test_case import LLMTestCase
from pipeline.rag_pipeline import answer, build_context
from retrieval.hybrid_retriever import hybrid_search
from retrieval.reranker import rerank
from eval.judge_prompt import REFUSAL_JUDGE, SECTION_CITATION_JUDGE
from config import config

OUT = Path(config.data_dir) / "eval_set"


def judge_call(prompt: str) -> dict:
    client = anthropic.Anthropic(api_key=config.anthropic_api_key)
    # Use a different model from generation to avoid self-preference
    msg = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=256,
        messages=[{"role": "user", "content": prompt}],
    )
    try:
        return json.loads(msg.content[0].text)
    except json.JSONDecodeError:
        return {}


def run_refusal_check(questions: list[dict], conn) -> dict:
    correct = 0
    total = 0
    for q in tqdm(questions, desc="Refusal check"):
        result = answer(q["question"], conn)
        prompt = REFUSAL_JUDGE.format(
            question=q["question"], answer=result["answer"]
        )
        verdict = judge_call(prompt)
        if verdict.get("correct_refusal"):
            correct += 1
        total += 1
    return {"refusal_accuracy": correct / total if total else 0, "n": total}


def run_deepeval(questions: list[dict], conn) -> None:
    test_cases = []
    for q in tqdm(questions[:50], desc="Building DeepEval cases"):
        candidates = hybrid_search(q["question"], conn)
        top = rerank(q["question"], candidates)
        ctx = [s["body"] for s in top]
        result = answer(q["question"], conn)

        tc = LLMTestCase(
            input=q["question"],
            actual_output=result["answer"],
            expected_output=q["expected_answer"],
            retrieval_context=ctx,
        )
        test_cases.append(tc)

    metrics = [
        FaithfulnessMetric(threshold=0.8, model="claude-haiku-4-5"),
        AnswerRelevancyMetric(threshold=0.7, model="claude-haiku-4-5"),
        ContextualPrecisionMetric(threshold=0.7, model="claude-haiku-4-5"),
        ContextualRecallMetric(threshold=0.7, model="claude-haiku-4-5"),
    ]
    results = evaluate(test_cases, metrics)
    print(results)


def main():
    questions_path = OUT / "eval_questions.jsonl"
    if not questions_path.exists():
        print("Run generate_eval_set.py first.")
        return

    questions = [json.loads(l) for l in questions_path.read_text().splitlines() if l.strip()]
    conn = psycopg2.connect(config.db_url)

    by_type: dict[str, list] = {}
    for q in questions:
        by_type.setdefault(q["question_type"], []).append(q)

    print(f"Loaded {len(questions)} questions: {[(k, len(v)) for k,v in by_type.items()]}")

    # refusal check (most important for legal RAG)
    print("\n── Refusal check ──")
    refusal_stats = run_refusal_check(by_type.get("refusal", []), conn)
    print(f"Refusal accuracy: {refusal_stats['refusal_accuracy']:.2%} ({refusal_stats['n']} questions)")

    # DeepEval on locate + cross_ref questions
    print("\n── DeepEval metrics ──")
    locate_qs = by_type.get("locate", []) + by_type.get("cross_ref", [])
    run_deepeval(locate_qs, conn)

    conn.close()


if __name__ == "__main__":
    main()
