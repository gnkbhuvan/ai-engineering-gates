#!/usr/bin/env python3
"""AI Engineering Gates Benchmark Harness.

Runs each (task x skill-arm x model) cell and scores the output deterministically.
Inspired by ponytail's benchmarks/agentic/run.py — but adapted for SKILL evaluation
(measuring whether an agent with the skill loaded performs better than without).

  python benchmarks/selftest.py
      Validate every scorer (good passes, bad is caught). No API, no spend. Run first, always.

  python benchmarks/runner.py --skills prompt-engineering,agentic-ai --runs 3
      Live run (spends API). Results saved under benchmarks/results/<stamp>/.

  python benchmarks/runner.py --rescore results/<stamp>
      Recompute metrics from saved outputs. No API. Use after changing a scorer.

  python benchmarks/judge.py --run results/<stamp>
      LLM judge pass on subjective axes (rubric-scored). Validated by --selftest first.

Architecture:
  - tasks.py        → task definitions with good/bad refs + deterministic scorers
  - behavior.py     → behavioral gate probes per skill
  - judge.py        → LLM judge with rubric (validated by selftest)
  - rubrics/        → rubric JSON files per skill
  - results/        → timestamped output directories
"""

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = Path(__file__).resolve().parent / "results"


def load_skill(name: str) -> str:
    """Load a skill's SKILL.md (stripped of YAML frontmatter)."""
    p = ROOT / name / "SKILL.md"
    if not p.exists():
        raise FileNotFoundError(f"Skill not found: {p}")
    text = p.read_text(encoding="utf-8")
    # Strip YAML frontmatter
    if text.startswith("---"):
        parts = text.split("---", 2)
        text = parts[2] if len(parts) >= 3 else text
    return text.strip()


def build_prompt(task: dict, skill_text: str | None) -> str:
    """Build the full prompt: skill (if any) + task instruction."""
    parts = []
    if skill_text:
        parts.append(f"<skill>\n{skill_text}\n</skill>")
    parts.append(task["prompt"])
    return "\n\n".join(parts)


def main():
    parser = argparse.ArgumentParser(description="AI Engineering Gates Benchmark Harness")
    sub = parser.add_subparsers(dest="command")

    # Placeholder — full implementation follows ponytail's pattern
    # See benchmarks/runner.py for the full harness

    print("AI Engineering Gates Benchmark — see benchmarks/README.md for methodology")
    print("Run: python benchmarks/selftest.py  (validate instruments, no API)")
    print("Run: python benchmarks/runner.py --help  (full harness)")


if __name__ == "__main__":
    main()
