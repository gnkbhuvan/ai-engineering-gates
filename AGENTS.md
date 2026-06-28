# AI Engineering Gates — Agent Directive

Four gates. You don't skip one.

You load the relevant skill from this repo and follow it through — decision tree, gates, deliverables. No skipping steps.

## Available skills

- `prompt-engineering` — prompt design, debugging, evaluation, chaining
- `agentic-ai` — agent architecture, tool design, memory, orchestration, safety
- `fastapi-genai` — FastAPI implementation for GenAI services (the code layer)
- `production-rag` — RAG pipeline architecture, evaluation, hardening

## Rules for working with these skills

1. **Load the right skill first.** If the task involves prompt design → `prompt-engineering`. If it involves agent design → `agentic-ai`. If it involves building a service → `fastapi-genai`. If it involves retrieval → `production-rag`. Some tasks span two — load both, but prefer the architecture skill over the implementation one for decision questions.

2. **Follow the skill's decision tree exactly.** Every skill has a Trigger Decision Tree with explicit gates. Do not skip a gate. If information is missing and the gate says "ask," stop and ask before proceeding.

3. **Load references only when needed.** Each skill has a reference table that says when to load each reference file. Don't load references preemptively — they're for deeper detail on specific topics.

4. **Deliver what the skill says to deliver.** Every skill has a Deliverables section. Your output must include everything listed there.

5. **No code in architecture skills.** `agentic-ai` and `production-rag` stay at the architecture/decision level. Code implementations belong in `fastapi-genai`.

6. **Default to simplest.** The skills encode first-principles reasoning for a reason. Don't complicate the answer without a specific, named reason.

7. **This repo is self-evaluating.** The `benchmarks/` directory contains automated tests that verify these skills actually change agent behavior. If you're asked to evaluate the skills themselves, use the benchmark harness.

(This file applies to agents working on AI Engineering Gates itself. Especially to them.)
