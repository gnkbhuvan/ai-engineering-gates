#!/usr/bin/env python3
"""Capability eval: test each skill via opencode (deepseek-v4-pro), n trials, persist results.json.

This is the CAPABILITY suite (Anthropic's vocabulary: low pass rate expected,
real model calls). The REGRESSION suite is selftest.py + behavior.py (near-100%,
no API, run those first).

  python benchmarks/runner.py
      Runs all 8 tasks x 2 arms (no-skill, skill) x N_TRIALS trials each.
      Writes benchmarks/results/<stamp>/results.json for judge.py --run / analyze.py.

Multiple trials per cell because single runs are unreliable (model output varies
run to run) — see Anthropic's pass@k / pass^k: pass@k = at least one of k trials
succeeded, pass^k = all k trials succeeded. analyze.py computes both from this file.
"""
import json, sys, time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from benchmarks.tasks import TASKS
from benchmarks.opencode_client import load_key, chat

API_KEY = load_key()
if not API_KEY:
    print("No API key. Set OPENCODE_GO_API_KEY or ensure ~/.hermes/.env has it.")
    sys.exit(1)

MODEL = "deepseek-v4-pro"
N_TRIALS = 3
SKILLS_DIR = Path(__file__).resolve().parent.parent
RESULTS_DIR = Path(__file__).resolve().parent / "results"

def load_skill(name):
    p = SKILLS_DIR / name / "SKILL.md"
    if not p.exists():
        return None
    text = p.read_text()
    if text.startswith("---"):
        parts = text.split("---", 2)
        text = parts[2] if len(parts) >= 3 else text
    return text.strip()

TASK_SKILL = {
    "pe-clarify": "prompt-engineering", "pe-debug": "prompt-engineering",
    "ag-necessity": "agentic-ai", "ag-tools": "agentic-ai",
    "fa-lifespan": "fastapi-genai", "fa-ratelimit": "fastapi-genai",
    "rag-necessity": "production-rag", "rag-vectordb": "production-rag",
}

results = []
SYSTEM_BASE = "You are an AI engineer. Be concise."

for task_id, task in TASKS.items():
    skill_name = TASK_SKILL.get(task_id)
    if not skill_name:
        continue
    skill_text = load_skill(skill_name)

    print(f"\n{'='*60}")
    print(f"TASK: {task_id} ({skill_name})")
    print(f"{'='*60}")

    for arm, sys_prompt in (
        ("no-skill", SYSTEM_BASE),
        ("skill", f"{SYSTEM_BASE}\n\nFollow this skill:\n\n{skill_text}"),
    ):
        trial_corrects = []
        for trial in range(N_TRIALS):
            print(f"→ {arm} trial {trial+1}/{N_TRIALS}...", end=" ", flush=True)
            t0 = time.perf_counter()
            r = chat(MODEL, sys_prompt, task["prompt"], API_KEY)
            latency_s = time.perf_counter() - t0
            out, usage = r["text"], r["usage"]
            print(f"{len(out)} chars, {latency_s:.1f}s")

            score = task["score"](out)
            trial_corrects.append(score["correct"])
            results.append({
                "task": task_id,
                "skill": skill_name,
                "arm": arm,
                "trial": trial,
                "score": {"correct": score["correct"], "safe": score["safe"], "reason": score["reason"]},
                # ponytail: subscription-billed, not metered — cost is always 0, tokens/latency kept for reference.
                "metadata": {"cost": 0.0, "tokens": {"total": usage.get("total_tokens", 0)}, "latency_s": round(latency_s, 2)},
                "output": out,
            })
            time.sleep(0.5)

        pass_at_k = max(trial_corrects)
        pass_pow_k = min(trial_corrects)
        print(f"   {arm:10} {sum(trial_corrects)}/{N_TRIALS} correct | pass@{N_TRIALS}={pass_at_k} pass^{N_TRIALS}={pass_pow_k}")

# Persist
stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
out_dir = RESULTS_DIR / stamp
out_dir.mkdir(parents=True, exist_ok=True)
(out_dir / "results.json").write_text(json.dumps(results, indent=2))
print(f"\nSaved: {out_dir / 'results.json'}")
print(f"\nNext: python benchmarks/judge.py --run {out_dir}")
print(f"      python benchmarks/analyze.py {out_dir / 'results.json'}")
