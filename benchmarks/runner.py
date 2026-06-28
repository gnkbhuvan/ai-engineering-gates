#!/usr/bin/env python3
"""Real benchmark: test each skill via opencode (deepseek-v4-pro), persist results.json.

  python benchmarks/runner.py
      Runs all 8 tasks (no-skill vs. with-skill), writes
      benchmarks/results/<stamp>/results.json for judge.py --run / analyze.py.
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
        print(f"→ {arm}...", end=" ", flush=True)
        r = chat(MODEL, sys_prompt, task["prompt"], API_KEY)
        out, usage = r["text"], r["usage"]
        print(f"{len(out)} chars")

        score = task["score"](out)
        results.append({
            "task": task_id,
            "skill": skill_name,
            "arm": arm,
            "score": {"correct": score["correct"], "safe": score["safe"], "reason": score["reason"]},
            # ponytail: subscription-billed, not metered — cost is always 0, tokens kept for reference.
            "metadata": {"cost": 0.0, "tokens": {"total": usage.get("total_tokens", 0)}},
            "output": out,
        })
        print(f"   corr={score['correct']} safe={score['safe']} | {score['reason'][:80]}")
        time.sleep(0.5)

# Persist
stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
out_dir = RESULTS_DIR / stamp
out_dir.mkdir(parents=True, exist_ok=True)
(out_dir / "results.json").write_text(json.dumps(results, indent=2))
print(f"\nSaved: {out_dir / 'results.json'}")

# Summary
by_task = {}
for r in results:
    by_task.setdefault(r["task"], {})[r["arm"]] = r["score"]["correct"]
nc = sum(1 for v in by_task.values() if v.get("no-skill"))
wc = sum(1 for v in by_task.values() if v.get("skill"))
print(f"\n{'='*60}")
print(f"FINAL: No-skill correct={nc}/{len(by_task)} | With-skill correct={wc}/{len(by_task)}")
print(f"{'='*60}")
for task_id, v in by_task.items():
    d = v.get("skill", 0) - v.get("no-skill", 0)
    a = "↑" if d > 0 else ("↓" if d < 0 else "→")
    print(f"  {task_id:20} no={v.get('no-skill')} with={v.get('skill')} {a}")

print(f"\nNext: python benchmarks/judge.py --run {out_dir}")
print(f"      python benchmarks/analyze.py {out_dir / 'results.json'}")
