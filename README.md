<p align="center">
  <img src="assets/banner.png" width="900" alt="AI Engineering Gates">
</p>

# AI Engineering Gates

*Four gates between you and shipping AI the wrong way.*

---

An AI agent is a text completion engine. It doesn't know what's true. It can't backtrack. It commits to every token. Without structure, it gives you a plausible answer — not a correct one.

These four skills give it that structure. Not by adding more tokens. By making it stop and think before it builds.

## What's inside

Four skills. Each one is a decision tree, not a tutorial. It gates you before you act.

| Skill | What it forces the agent to do |
|-------|-------------------------------|
| **prompt-engineering** | Ask clarifying questions before writing a prompt. Diagnose root cause before debugging. Apply the Five Principles in order. Ship nothing unevaluated. |
| **agentic-ai** | Question whether an agent is even needed. Default to a workflow. Keep tools minimal. Never let a model verify its own work. |
| **fastapi-genai** | Load models once at startup. Go async end-to-end or don't go async at all. Type everything with Pydantic. Don't add infrastructure before measuring. |
| **production-rag** | Check if RAG is even the right tool. Reuse existing infrastructure before adding new. Cost storage + embedding + query, not just generation. |

Every skill has first-principles axioms, a trigger decision tree, a mandatory deliverables checklist, and deep-dive references loaded only when needed.

## Evaluated, not just written

These skills aren't blog posts. They're tested.

```bash
python benchmarks/selftest.py    # Validates scorers — 16/16 passing
python benchmarks/behavior.py --selftest  # Behavioral probes — 8/8 passing
python benchmarks/judge.py --selftest     # LLM judge — validated
python benchmarks/runner.py      # Full benchmark: with/without skill
```

| Gate | What it proves |
|------|---------------|
| Scorer selftest (16/16) | Every scorer correctly distinguishes good from bad. The instruments are trustworthy. |
| Behavioral probes (8/8) | Each skill changes actual agent behavior — not just adds text to the prompt. |
| LLM judge | Subjective axes (clarity, reasoning depth) scored against a validated rubric. |
| Comparative baselines | Same task, same model — with the skill vs. without. Measured, not claimed. |

The methodology: 8 tasks × 2 skill arms = 16 scored cells. Each task has a good reference (correct + safe) and a bad reference (wrong on the axis that matters). The selftest runs before any API spend. If an instrument is broken, every number that follows is noise.

## See the difference

Same model. Same task. One has the skill loaded. One doesn't.

### "Design a prompt for email classification."

**Without skill:** Jumps straight to writing the prompt.

```
System: You are a customer support classifier. Classify each email
as complaint, query, or praise. Output JSON with category and confidence.

User: {email}
```

**With prompt-engineering:** Asks clarifying questions first — model, format, examples, edge cases — before writing anything. The prompt that follows has few-shot examples, an evaluation plan, and known limitations.

---

### "Design the agent architecture for support ticket handling."

**Without skill:** Proposes a multi-agent system — supervisor, sub-agents, shared state graph.

**With agentic-ai:** Questions whether this needs to be an agent at all. The steps are deterministic — it's a workflow, not an agent. A single LLM call at the draft step is simpler, cheaper, and has no compounding failure rate.

---

### "Add rate limiting to this FastAPI endpoint."

**Without skill:**

```python
limiter = Limiter(key_func=get_remote_address)
@limiter.limit("10/minute")
```

**With fastapi-genai:**

```python
def get_user_key(request: Request) -> str:
    return request.headers.get("X-User-ID", get_remote_address(request))

limiter = Limiter(key_func=get_user_key)
@limiter.limit("10/minute")
```

Same number of lines. One prevents a single abusive user behind a VPN from denying service to everyone on that IP. The other doesn't.

---

## The philosophy

> *"The model completes the prompt as if it were a document from its training set."*

That's axiom one of prompt engineering. Everything else follows:

- **Don't build what doesn't need to exist.** Before writing a prompt, ask what the task actually requires. Before building an agent, ask if a workflow would do. Before deploying RAG, ask if the data fits in context.
- **Default to what's already there.** Reuse the stdlib. Reuse the existing database. Reuse the installed dependency. Adding things is easy. Removing them is not.
- **Measure, don't assume.** The skills don't say "use a task queue." They say "use `BackgroundTasks` first. Escalate only when you've measured a bottleneck."

These aren't opinions. They're consequences of how LLMs actually work — single-pass, left-to-right, one token at a time.

## How to use

Clone the repo. When your agent needs one of these skills, point it at the SKILL.md file. The agent follows the decision tree inside.

```
# In AGENTS.md or Claude Code:
Load skill from: prompt-engineering/SKILL.md
```

The skill takes over from there — it asks its own clarifying questions, follows its own gated workflow, and produces its own mandatory deliverables.

Each skill has deep-dive references loaded only when a specific topic needs them. The agent doesn't read all 26 reference files. It reads the decision tree, follows the gate at each step, and loads the reference that matches the current branch.

## Install

### skills.sh (all agents)

```bash
npx skills add gnkbhuvan/ai-engineering-gates
```

One command. Works across Claude Code, Codex, Cursor, Windsurf, Gemini CLI, VS Code, Zed, and 20+ other agents. The skill is installed and auto-loaded on session start.

### Claude Code

```
/plugin marketplace add gnkbhuvan/ai-engineering-gates
/plugin install ai-engineering-gates@ai-engineering-gates
```

Send as two separate messages.

### Manual

```bash
git clone https://github.com/gnkbhuvan/ai-engineering-gates.git ~/.claude/skills/ai-engineering-gates
```

Point your agent at the SKILL.md for the skill you need. The root `AGENTS.md` is auto-loaded by most agents.

## Usage

```bash
# Verify the evals pass (no API required)
python benchmarks/selftest.py
python benchmarks/behavior.py --selftest

# Run the full benchmark
python benchmarks/runner.py --all --runs 3
```

## Repo

```
ai-engineering-gates/
├── banner.png                    # Four gates, one per skill
├── AGENTS.md                     # Agent directive
├── README.md
├── prompt-engineering/           # Prompt design, debugging, evaluation
│   ├── SKILL.md
│   └── references/ (6)
├── agentic-ai/                   # Agent architecture, tools, safety
│   ├── SKILL.md
│   └── references/ (6)
├── fastapi-genai/                # FastAPI for GenAI services
│   ├── SKILL.md
│   └── references/ (8)
├── production-rag/               # RAG pipeline design, hardening
│   ├── SKILL.md
│   └── references/ (6)
└── benchmarks/                   # The proof
    ├── selftest.py               # ✅ 16/16
    ├── behavior.py               # ✅ 8/8
    ├── tasks.py
    ├── runner.py
    └── judge.py
```
