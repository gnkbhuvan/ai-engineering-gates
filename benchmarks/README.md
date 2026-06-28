# AI Engineering Gates Benchmarks

*Automated evaluation of the 4 AI skills: prompt-engineering, agentic-ai, fastapi-genai, production-rag.*

## Quickstart

```bash
# 1. Validate instruments (no API, no spend) — ALWAYS RUN FIRST
python benchmarks/selftest.py

# 2. Validate behavioral probes (no API)
python benchmarks/behavior.py --selftest

# 3. Validate LLM judge (opencode subscription, OPENCODE_GO_API_KEY)
python benchmarks/judge.py --selftest

# 4. Run the full evaluation
python benchmarks/runner.py

# 5. Score the run's outputs against the rubrics + compare arms
python benchmarks/judge.py --run benchmarks/results/<stamp>
python benchmarks/analyze.py benchmarks/results/<stamp>/results.json
```

## How it works

Two suites, in Anthropic's eval vocabulary ([Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)):

- **Regression suite** (`selftest.py` + `behavior.py`) — deterministic, no API, should stay near 100%. Catches the instruments themselves breaking, or a skill edit silently undoing a behavior it used to guarantee.
- **Capability suite** (`tasks.py` + `runner.py`) — real model calls, lower pass rate expected. Each (task × arm) cell runs **3 trials**, not 1 — single runs are unreliable (output varies run to run). We report `pass@3` (at least one of 3 trials correct) and `pass^3` (all 3 correct), per Anthropic's `pass@k`/`pass^k` metrics.
- **LLM judge** (`judge.py`) scores subjective axes (clarity, reasoning depth, simplicity bias) on the capability run's outputs, averaged across two judge models (deepseek-v4-pro, qwen3.7-max) to dampen single-judge non-determinism.

**Known gaps, documented rather than faked:**
- *Transcript/process grading* — Anthropic's framework grades tool calls and state changes, not just final output. We have no tool-calling agent harness here; the skills are injected as system prompts into single-turn chat completions. `behavior.py`'s text-pattern probes are the closest analog (they check what the model *said* about its reasoning, not what it *did*) — real transcript grading would require building an actual agentic loop with tools, which is a bigger project, not done here.
- *Human calibration* — `judge.py`'s rubrics are validated against known good/bad reference pairs (selftest), not against actual human-assigned scores. No human-in-the-loop calibration step exists yet.

## Architecture

```
benchmarks/
├── selftest.py         ← Regression: validates scorers, no API
├── behavior.py          ← Regression: behavioral gate probes, no API
├── tasks.py              ← Capability: 8 task definitions (2 per skill)
├── runner.py            ← Capability: runs tasks via opencode, n=3 trials, writes results.json
├── opencode_client.py  ← Shared opencode Zen Go endpoint client (used by runner.py + judge.py)
├── judge.py               ← LLM-as-judge rubric scoring (--selftest validates it; --run scores a completed run)
├── analyze.py             ← Aggregates results.json into pass@k/pass^k comparison tables
└── results/              ← Timestamped output directories (results.json, judge_scores.json)
```

## Tasks

| ID | Skill | What it tests |
|----|-------|---------------|
| pe-clarify | prompt-engineering | Asks clarifying questions before writing prompts |
| pe-debug | prompt-engineering | Diagnoses root cause, not superficial patch |
| ag-necessity | agentic-ai | Questions whether an agent is needed |
| ag-tools | agentic-ai | Proposes minimal, non-overlapping tool set |
| fa-lifespan | fastapi-genai | Uses lifespan for model loading |
| fa-ratelimit | fastapi-genai | Uses per-user rate limiting |
| rag-necessity | production-rag | Questions whether RAG is needed |
| rag-vectordb | production-rag | Recommends reusing existing infra |

## References

- [Ponytail benchmarks](https://github.com/DietrichGebert/ponytail/tree/main/benchmarks) — The inspiration
- [Hebbia's evaluation framework](https://www.hebbia.com/blog/evaluating-ai-agents-a-hybrid-deterministic-and-rubric-based-framework)
- [arXiv:2507.21504](https://arxiv.org/abs/2507.21504) — Survey on LLM Agent Evaluation
