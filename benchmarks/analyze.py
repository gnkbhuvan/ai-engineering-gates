#!/usr/bin/env python3
"""Analyze benchmark results — produces comparison tables.

Aggregates over trials per (task, arm): pass@k (at least one trial correct)
and pass^k (all trials correct) — see Anthropic's eval vocabulary. With
N_TRIALS=1 (older results.json files) pass@k == pass^k == that single trial.

Usage:
  python benchmarks/analyze.py results/<stamp>/results.json
"""

import json
import sys
from pathlib import Path

SKILL_MAP = {
    "pe-clarify": "prompt-engineering",
    "pe-debug": "prompt-engineering",
    "ag-necessity": "agentic-ai",
    "ag-tools": "agentic-ai",
    "fa-lifespan": "fastapi-genai",
    "fa-ratelimit": "fastapi-genai",
    "rag-necessity": "production-rag",
    "rag-vectordb": "production-rag",
}


def group_trials(data, task_id, arm):
    return [r for r in data if r["task"] == task_id and r["arm"] == arm]


def analyze(results_path: str):
    data = json.loads(Path(results_path).read_text())

    print("=" * 95)
    print(" PER-TASK COMPARISON (pass@k = at least one trial correct, pass^k = all trials correct)")
    print("=" * 95)
    print(f"{'Task':<16} {'Skill':<18} {'No-Skill':<16} {'Skill':<16} {'Winner':<14}")
    print("-" * 95)

    by_skill = {}
    for task_id in SKILL_MAP:
        skill = SKILL_MAP[task_id]
        no_skill = group_trials(data, task_id, "no-skill")
        skill_trials = group_trials(data, task_id, "skill")
        k = len(no_skill) or len(skill_trials) or 1

        ns_correct = [r["score"]["correct"] for r in no_skill]
        ws_correct = [r["score"]["correct"] for r in skill_trials]
        ns_rate = f"{sum(ns_correct)}/{len(ns_correct)}" if ns_correct else "?"
        ws_rate = f"{sum(ws_correct)}/{len(ws_correct)}" if ws_correct else "?"
        ns_pass_at_k = max(ns_correct) if ns_correct else 0
        ws_pass_at_k = max(ws_correct) if ws_correct else 0

        if ns_pass_at_k and ws_pass_at_k:
            winner = "tie ✓✓"
        elif ns_pass_at_k:
            winner = "regression ⚠"
        elif ws_pass_at_k:
            winner = "SKILL WINS ✅"
        else:
            winner = "both fail ❌"

        print(f"{task_id:<16} {skill:<18} {ns_rate:<16} {ws_rate:<16} {winner:<14}")

        agg = by_skill.setdefault(skill, {"no_skill_trials": 0, "no_skill_correct": 0,
                                           "skill_trials": 0, "skill_correct": 0})
        agg["no_skill_trials"] += len(ns_correct)
        agg["no_skill_correct"] += sum(ns_correct)
        agg["skill_trials"] += len(ws_correct)
        agg["skill_correct"] += sum(ws_correct)

    print(f"\n{'=' * 80}")
    print(" PER-SKILL AGGREGATE (trial-level success rate, not just pass@k)")
    print(f"{'=' * 80}")
    print(f"{'Skill':<22} {'No-Skill':<16} {'With Skill':<16} {'Delta':<10}")
    print("-" * 64)
    for skill, scores in by_skill.items():
        ns_rate = scores["no_skill_correct"] / scores["no_skill_trials"] * 100 if scores["no_skill_trials"] else 0
        ws_rate = scores["skill_correct"] / scores["skill_trials"] * 100 if scores["skill_trials"] else 0
        delta = ws_rate - ns_rate
        delta_str = f"+{delta:.0f}%" if delta > 0 else f"{delta:.0f}%" if delta < 0 else "—"
        print(f"{skill:<22} {ns_rate:.0f}% ({scores['no_skill_correct']}/{scores['no_skill_trials']})     "
              f"{ws_rate:.0f}% ({scores['skill_correct']}/{scores['skill_trials']})     {delta_str}")

    total_ns_t = sum(s["no_skill_trials"] for s in by_skill.values())
    total_ns_c = sum(s["no_skill_correct"] for s in by_skill.values())
    total_ws_t = sum(s["skill_trials"] for s in by_skill.values())
    total_ws_c = sum(s["skill_correct"] for s in by_skill.values())
    print(f"\n{'─' * 64}")
    print(f"{'OVERALL':<22} {total_ns_c/total_ns_t*100:.0f}% ({total_ns_c}/{total_ns_t})     "
          f"{total_ws_c/total_ws_t*100:.0f}% ({total_ws_c}/{total_ws_t})")

    total_cost = sum(r.get("metadata", {}).get("cost", 0) for r in data)
    total_tokens = sum(r.get("metadata", {}).get("tokens", {}).get("total", 0) for r in data)
    total_latency = sum(r.get("metadata", {}).get("latency_s", 0) for r in data)
    print(f"\n  Total cost: ${total_cost:.4f} (subscription, not metered)")
    print(f"  Total tokens: {total_tokens}")
    print(f"  Total latency: {total_latency:.1f}s across {len(data)} trials")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        results_dir = Path(__file__).resolve().parent / "results"
        runs = sorted([d for d in results_dir.iterdir() if d.is_dir() and (d / "results.json").exists()])
        if runs:
            results_path = runs[-1] / "results.json"
            print(f"Analyzing latest: {results_path}\n")
        else:
            print("No results found. Run benchmark first.")
            sys.exit(1)
    else:
        results_path = sys.argv[1]

    analyze(results_path)
