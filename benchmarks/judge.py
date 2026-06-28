#!/usr/bin/env python3
"""LLM-as-judge rubric scoring for subjective skill evaluation axes.

Validated by selftest before any real run — see --selftest flag.
Judges communication clarity, reasoning quality, and adherence to skill philosophy.

  python benchmarks/judge.py --selftest     # validate judge on reference pairs
  python benchmarks/judge.py --run results/<stamp>  # score a completed run

Uses opencode's Zen Go endpoint (subscription, not metered) — two judge models
(deepseek-v4-pro, qwen3.7-max), scores averaged per Hebbia's "multiple grading
passes reduce judge non-determinism" approach. Key from OPENCODE_GO_API_KEY env
var or ~/.hermes/.env.
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from benchmarks.opencode_client import load_key, chat

RUNS_DIR = Path(__file__).resolve().parent / "results"
JUDGE_MODELS = ("deepseek-v4-pro", "qwen3.7-max")


# =============================================================================
# Rubrics
# =============================================================================

RUBRICS = {
    "communication-clarity": (
        "You are evaluating an AI engineering response for COMMUNICATION CLARITY. "
        "The target audience includes non-engineers (PMs, architects) as well as AI engineers. "
        "Score 0-3:\n"
        "0 = Jargony, assumes deep expertise, inaccessible to non-engineers\n"
        "1 = Mostly clear but occasional jargon without definition\n"
        "2 = Clear, defines terms, accessible to the stated audience\n"
        "3 = Exceptionally clear, uses analogies, anticipates confusion\n\n"
        "Respond with ONLY this JSON: {\"score\": <0-3 int>, \"why\": \"<one line>\"}"
    ),
    "reasoning-depth": (
        "You are evaluating an AI engineering response for REASONING DEPTH. "
        "Does the response show first-principles reasoning, or does it just name patterns "
        "without explaining why? Score 0-3:\n"
        "0 = Names a pattern/technique without any justification\n"
        "1 = Minimal justification ('because it's best practice')\n"
        "2 = Explains the 'why' behind the recommendation\n"
        "3 = Traces back to first principles (axioms, fundamentals) AND explains trade-offs\n\n"
        "Respond with ONLY this JSON: {\"score\": <0-3 int>, \"why\": \"<one line>\"}"
    ),
    "simplicity-bias": (
        "You are evaluating an AI engineering response for SIMPLICITY BIAS. "
        "Does the response default to the simplest solution, or does it over-engineer? "
        "Score 0-3:\n"
        "0 = Over-engineered: proposes complex architecture for a simple problem\n"
        "1 = Acceptable complexity but could be simpler\n"
        "2 = Appropriately simple — matches the problem's complexity\n"
        "3 = Elegantly minimal — the simplest thing that could possibly work\n\n"
        "Respond with ONLY this JSON: {\"score\": <0-3 int>, \"why\": \"<one line>\"}"
    ),
}


# =============================================================================
# Judge infrastructure
# =============================================================================

def judge_call(response_text: str, system_prompt: str, key: str) -> dict[str, str]:
    """Ask every judge model to score the response. Returns {model: raw_text}."""
    user_prompt = f"RESPONSE TO EVALUATE:\n\n{response_text}"
    return {model: chat(model, system_prompt, user_prompt, key, temp=0)["text"] for model in JUDGE_MODELS}


def parse_score(text: str) -> int | None:
    """Extract numeric score from a judge response."""
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
        return int(obj.get("score", -1))
    except (json.JSONDecodeError, ValueError, KeyError):
        return None


def score_response(response_text: str, rubric_name: str, key: str) -> dict:
    """Score a response against a rubric using all judge models, averaged."""
    if rubric_name not in RUBRICS:
        return {"error": f"Unknown rubric: {rubric_name}"}

    raw = judge_call(response_text, RUBRICS[rubric_name], key)
    per_model = {model: parse_score(text) for model, text in raw.items()}
    valid = [s for s in per_model.values() if s is not None]
    avg = sum(valid) / len(valid) if valid else None

    return {"rubric": rubric_name, "score": avg, "scores_by_model": per_model, "raw_by_model": raw}


# =============================================================================
# Selftest
# =============================================================================

def selftest(key: str | None = None):
    """Validate the judge: it must rank known good responses above known bad ones
    on the rubric each pair is meant to exercise. Free — uses the opencode subscription.
    """
    if not key:
        key = load_key()
    if not key:
        print("No API key found. Set OPENCODE_GO_API_KEY env var or ensure ~/.hermes/.env has it.")
        sys.exit(1)

    tests = {
        "clarity": {
            "rubric": "communication-clarity",
            "good": (
                "Think of an LLM like a very eager intern who's read every book in the library "
                "but has never actually done anything. They don't know what's true — they know "
                "what their books say is true. When you write a prompt, you're writing the first "
                "page of a document and asking them to complete it. So make your document look "
                "like the kind of document that would naturally contain the answer you want.\n\n"
                "That's the core idea. Everything else — system messages, few-shot examples, "
                "chain-of-thought — is just scaffolding to make that document look more like "
                "the thing you want completed."
            ),
            "bad": (
                "LLMs are autoregressive transformer architectures with causal attention masks. "
                "The key paradigms are zero-shot, few-shot, CoT, ReAct, and RAG. For structured "
                "output, use constrained decoding with JSON schema enforcement. Ensure your "
                "temperature and top_p parameters are calibrated to the task's entropy "
                "requirements. Meta-prompting can bootstrap recursive self-improvement loops."
            ),
        },
        "reasoning": {
            "rubric": "reasoning-depth",
            "good": (
                "The reason RAG fails here is axiom 3 of prompt engineering: the model assumes "
                "every token in its prompt is true (truth bias). When your retriever returns "
                "a wrong chunk, the model treats it as ground truth — it doesn't know to "
                "distrust retrieved content. This is why a bad retriever is WORSE than no "
                "retriever: you're actively injecting false premises that the model can't "
                "detect. The fix isn't a better prompt — it's a better retriever, or a "
                "reranker that filters chunks before they reach the model."
            ),
            "bad": (
                "For RAG, use LangChain with ChromaDB. It's the most popular framework and "
                "database. Set chunk_size=512 and chunk_overlap=128. Those are the standard "
                "values. Use OpenAI embeddings because they're the best. This is what most "
                "production RAG systems use."
            ),
        },
        "simplicity": {
            "rubric": "simplicity-bias",
            "good": (
                "Use Python's built-in @lru_cache on the lookup function. That's it — at "
                "this volume (a few hundred lookups a day) there's no case for Redis, a "
                "cache-warming job, or a custom eviction policy. Add a real cache only if "
                "you measure @lru_cache falling short."
            ),
            "bad": (
                "Stand up a Redis Cluster for caching, with a cache-warming cron job, a "
                "pub/sub invalidation system, and a custom LRU eviction policy layered on "
                "top, to cache roughly fifty lookups a day."
            ),
        },
    }

    passed = 0
    failed = 0

    for test_name, pair in tests.items():
        good = score_response(pair["good"], pair["rubric"], key)
        bad = score_response(pair["bad"], pair["rubric"], key)
        good_score, bad_score = good["score"], bad["score"]

        if good_score is not None and bad_score is not None and good_score > bad_score:
            print(f"ok  {test_name:12} [{pair['rubric']}] good={good_score} > bad={bad_score}")
            passed += 1
        else:
            print(f"XX  {test_name:12} [{pair['rubric']}] good={good_score} bad={bad_score} (good should be > bad)")
            failed += 1

    print(f"\n---")
    print(f"passed: {passed}  failed: {failed}")
    if failed:
        print(f"\n❌ Judge selftest failed. Fix rubrics before evaluating real runs.")
        sys.exit(1)
    else:
        print(f"\n✅ Judge validated. Rubrics produce correct ordering.")
        sys.exit(0)


# =============================================================================
# Run scoring
# =============================================================================

def run_judge(run_dir: str, key: str | None = None):
    """Score every output in a completed run's results.json against all rubrics."""
    if not key:
        key = load_key()
    if not key:
        print("No API key found. Set OPENCODE_GO_API_KEY env var or ensure ~/.hermes/.env has it.")
        sys.exit(1)

    results_path = Path(run_dir) / "results.json"
    if not results_path.exists():
        print(f"No results.json in {run_dir} — run benchmarks/runner.py first.")
        sys.exit(1)

    records = json.loads(results_path.read_text())
    for r in records:
        r["rubrics"] = {name: score_response(r["output"], name, key) for name in RUBRICS}
        scores = ", ".join(f"{name}={r['rubrics'][name]['score']}" for name in RUBRICS)
        print(f"{r['task']:15} [{r['arm']:8}] {scores}")

    out_path = Path(run_dir) / "judge_scores.json"
    out_path.write_text(json.dumps(records, indent=2))
    print(f"\nSaved: {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--selftest", action="store_true", help="Validate judge on reference pairs")
    parser.add_argument("--run", type=str, help="Path to completed run results")
    args = parser.parse_args()

    if args.selftest:
        selftest()
    elif args.run:
        run_judge(args.run)
    else:
        print("Usage: python benchmarks/judge.py --selftest")
        print("       python benchmarks/judge.py --run results/<stamp>")
