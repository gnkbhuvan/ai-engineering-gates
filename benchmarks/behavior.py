#!/usr/bin/env python3
"""Behavioral gate probes for AI Engineering Gates.

Verifies each skill actually changes agent BEHAVIOR, not just carries text.
Each probe targets a specific skill rule that matters. A skill that scores
well on LOC/cost but fails a behavioral gate is a regression, not a victory.

Run: python benchmarks/behavior.py --selftest
"""

import sys
from pathlib import Path


# =============================================================================
# Probe definitions — one per key skill behavior
# =============================================================================

PROBES = {
    # --- prompt-engineering ---
    "pe-asks-before-writing": {
        "skill": "prompt-engineering",
        "description": "When given an ambiguous prompt design task, agent asks clarifying "
                       "questions before writing the prompt (per the Information Missing gate).",
        "check": lambda output: _contains_questions(output) and _not_jumps_to_prompt(output),
    },
    "pe-diagnoses-not-patches": {
        "skill": "prompt-engineering",
        "description": "When debugging a failing prompt, agent identifies root cause "
                       "(first principles) before suggesting a fix.",
        "check": lambda output: _diagnoses_before_fixing(output),
    },

    # --- agentic-ai ---
    "ag-questions-agent-necessity": {
        "skill": "agentic-ai",
        "description": "When asked to build an agent, first questions whether an agent "
                       "is needed at all (per the Trigger Decision Tree step 1).",
        "check": lambda output: _questions_agent_necessity(output),
    },
    "ag-keeps-tools-minimal": {
        "skill": "agentic-ai",
        "description": "When designing tools, keeps the tool set small and descriptions "
                       "disjoint (per first-principles axiom 3).",
        "check": lambda output: _tool_count_is_small(output),
    },

    # --- fastapi-genai ---
    "fa-uses-lifespan": {
        "skill": "fastapi-genai",
        "description": "When building an endpoint, uses lifespan handler for model loading, "
                       "not per-request loading (per first-principles axiom 1).",
        "check": lambda output: _uses_lifespan(output),
    },
    "fa-per-user-rate-limit": {
        "skill": "fastapi-genai",
        "description": "When adding rate limiting, uses per-user limiting, not global "
                       "(per quick reference table).",
        "check": lambda output: _per_user_ratelimit(output),
    },
    "fa-no-premature-infra": {
        "skill": "fastapi-genai",
        "description": "Doesn't add infrastructure (queues, caches, worker fleets) "
                       "before measuring a need (per first-principles axiom 6).",
        "check": lambda output: _no_premature_infrastructure(output),
    },

    # --- production-rag ---
    "rag-questions-rag-necessity": {
        "skill": "production-rag",
        "description": "When asked to build RAG, first checks if RAG is needed at all "
                       "(per Trigger Decision Tree step 1).",
        "check": lambda output: _questions_rag_necessity(output),
    },
    "rag-reuses-existing-infra": {
        "skill": "production-rag",
        "description": "When choosing a vector DB, defaults to reusing existing infra "
                       "before proposing a new database.",
        "check": lambda output: _reuses_existing_db(output),
    },
}


# =============================================================================
# Check functions
# =============================================================================

def _contains_questions(output: str) -> bool:
    """Does the output contain clarifying questions (not just a prompt)?"""
    text = str(output)
    # Count question marks
    qmarks = text.count("?")
    # Check for question-like phrases
    q_phrases = ["what", "how many", "which model", "what format", "need to know",
                 "before i", "can you", "do you", "have you", "should i"]
    q_count = sum(1 for p in q_phrases if p in text.lower())
    return qmarks >= 2 or q_count >= 2


def _not_jumps_to_prompt(output: str) -> bool:
    """Output doesn't just write a prompt immediately without questions."""
    text = str(output).lower()
    # If the output starts directly with a prompt (system/user style) without questions first
    lines = text.strip().split("\n")
    first_10_lines = " ".join(lines[:10]).lower()
    if ("system:" in first_10_lines or "system message" in first_10_lines) and text.count("?") < 2:
        return False
    return True


def _diagnoses_before_fixing(output: str) -> bool:
    """Output contains diagnostic reasoning, not just a fix."""
    text = str(output).lower()
    diagnosis_signals = ["root cause", "diagnos", "first principles", "the problem is",
                         "underlying", "why", "the issue is", "this happens because"]
    superficial_signals = len(text) < 300 and any(w in text for w in ["just add", "just change", "simply add"])
    if superficial_signals:
        return False
    return any(s in text for s in diagnosis_signals)


def _questions_agent_necessity(output: str) -> bool:
    """Output questions whether an agent is necessary."""
    text = str(output).lower()
    signals = ["does this need to be an agent", "agent at all", "workflow, not an agent",
               "deterministic", "fixed sequence", "plain prompt would", "simpler",
               "do you actually need an agent"]
    return any(s in text for s in signals)


def _tool_count_is_small(output: str) -> bool:
    """Output proposes ≤ 8 tools (or explicitly justifies more)."""
    import re
    text = str(output)
    tool_lines = re.findall(r'^\d+\.\s+\w+', text, re.MULTILINE)
    return len(tool_lines) <= 8


def _uses_lifespan(output: str) -> bool:
    """Output uses lifespan/startup handler for model loading."""
    text = str(output)
    return "lifespan" in text or "asynccontextmanager" in text or "on_event" in text


def _per_user_ratelimit(output: str) -> bool:
    """Output uses per-user rate limiting, not global counter."""
    text = str(output).lower()
    per_user_signals = ["per user", "per-user", "per client", "user_id", "get_user_key",
                        "x-user-id", "per key", "key_func"]
    global_signals = "global" in text and any(w in text for w in ["counter", "request_count"])
    return any(s in text for s in per_user_signals) and not global_signals


def _no_premature_infrastructure(output: str) -> bool:
    """Output does NOT add infrastructure before measuring need."""
    text = str(output).lower()
    premature_signals = ["celery", "redis", "rabbitmq", "kafka", "task queue",
                         "worker fleet", "semantic cache", "kubernetes"]
    # Allow if justified by measured need
    has_justification = any(w in text for w in ["measured", "benchmark", "profiled", "bottleneck",
                                                  "if you need", "when you hit", "only if"])
    if any(s in text for s in premature_signals) and not has_justification:
        return False
    return True


def _questions_rag_necessity(output: str) -> bool:
    """Output questions whether RAG is needed."""
    text = str(output).lower()
    signals = ["does this need rag", "rag at all", "stuff it in context", "context window",
               "skip rag", "do you even need", "fit in context"]
    return any(s in text for s in signals)


def _reuses_existing_db(output: str) -> bool:
    """Output recommends reusing existing database before new one."""
    text = str(output).lower()
    reuse_signals = ["pgvector", "already run", "existing", "you already", "reuse",
                     "postgres", "extension"]
    new_db_signals = ["pinecone", "weaviate", "qdrant", "milvus", "new vector db",
                      "purpose-built"]
    has_reuse = any(s in text for s in reuse_signals)
    has_new_without_reuse = any(s in text for s in new_db_signals) and not has_reuse
    return has_reuse and not has_new_without_reuse


# =============================================================================
# Selftest
# =============================================================================

def selftest():
    """Run behavioral gate probes against known good/bad reference outputs."""
    # These reference pairs test the probes themselves
    tests = {
        "pe-asks-before-writing": {
            "good": "Before I write the prompt, can you tell me: what model? what format? how many examples?",
            "bad": "Here's your prompt: System: You are a classifier. User: {text}",
        },
        "pe-diagnoses-not-patches": {
            "good": "The root cause is the model has no retrieval anchor. You need RAG to ground the output in source text instead of relying on the model's memory.",
            "bad": "Just add 'do not hallucinate' to the system prompt. Fixed.",
        },
        "ag-questions-agent-necessity": {
            "good": "Before building an agent: is this actually an agent problem? These steps are deterministic — a workflow is simpler and cheaper.",
            "bad": "Use LangGraph with a supervisor agent and 5 specialized sub-agents. Here's the architecture:",
        },
        "ag-keeps-tools-minimal": {
            "good": "1. read_file\n2. write_file\n3. search_code\n4. run_command\n5. web_search\n\n5 tools. Each with a non-overlapping purpose.",
            "bad": "1. list_directory\n2. read_file\n3. read_file_lines\n4. read_file_range\n5. write_file\n6. append_file\n7. edit_file\n8. delete_file\n9. search_code\n10. search_filename\n11. find_and_replace\n12. run_command\n13. run_command_background\n14. pip_install\n15. npm_install",
        },
        "fa-uses-lifespan": {
            "good": "@asynccontextmanager\nasync def lifespan(app):\n    app.state.client = AsyncAnthropic()\n    yield\n    await app.state.client.close()",
            "bad": "client = Anthropic()\n\n@app.post('/chat')\nasync def chat(msg: str):\n    return client.messages.create(model='claude', messages=[...])",
        },
        "fa-per-user-rate-limit": {
            "good": "limiter = Limiter(key_func=get_user_key)  # per-user, not per-IP\n@limiter.limit('10/minute')",
            "bad": "request_count = 0\nif request_count >= MAX:\n    raise HTTPException(429)",
        },
        "rag-questions-rag-necessity": {
            "good": "Wait — 200 pages is ~150K tokens. You can fit the entire wiki in context. Skip RAG entirely.",
            "bad": "Use Pinecone with Cohere embeddings. Chunk at 512 tokens with 128 overlap. Full pipeline:",
        },
        "rag-reuses-existing-infra": {
            "good": "Use pgvector — you already run PostgreSQL. Add the extension, done. Migrate later if you hit its ceiling.",
            "bad": "Use Pinecone. It's purpose-built for vector search. Create an account, set up a p1 index, and migrate your pipeline.",
        },
    }

    passed = 0
    failed = 0

    for probe_id, refs in tests.items():
        check_fn = PROBES[probe_id]["check"]
        good_result = check_fn(refs["good"])
        bad_result = check_fn(refs["bad"])

        if good_result and not bad_result:
            print(f"ok  {probe_id:35} good=✓ bad=✗")
            passed += 1
        elif not good_result:
            print(f"XX  {probe_id:35} good=✗ (should pass) bad={'✗' if not bad_result else '✓'}")
            failed += 1
        elif bad_result:
            print(f"XX  {probe_id:35} good=✓ bad=✓ (should fail)")
            failed += 1
        else:
            print(f"??  {probe_id:35} unexpected state")
            failed += 1

    print(f"\n---")
    print(f"passed: {passed}  failed: {failed}")
    if failed:
        print(f"\n❌ {failed} behavioral probe(s) failed selftest. Fix before evaluating skills.")
        sys.exit(1)
    else:
        print(f"\n✅ All behavioral probes validated.")
        sys.exit(0)


def evaluate(output: str, skill: str) -> dict:
    """Run all probes for a skill against an agent output.

    Returns {probe_id: {pass: bool, description: str}}.
    """
    results = {}
    for probe_id, probe in PROBES.items():
        if probe["skill"] == skill:
            try:
                passed = probe["check"](output)
            except Exception as e:
                passed = False
            results[probe_id] = {"pass": passed, "description": probe["description"]}
    return results


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    else:
        print("Usage: python benchmarks/behavior.py --selftest")
        print("       python benchmarks/behavior.py < output.txt [--skill prompt-engineering]")
