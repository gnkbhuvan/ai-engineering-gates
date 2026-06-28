#!/usr/bin/env python3
"""Task definitions for AI Engineering Gates evaluation.

Each task has:
  prompt   — instruction to the agent (the skill is injected separately)
  axis     — dimension good/bad differ on: "safe" (default) or "correct"
  score    — (output_text_or_dict) -> {correct: 0|1, safe: 0|1, reason: str}
  good     — reference output that should pass all axes
  bad      — reference output that should fail on its declared axis
  open     — if True, no good/bad ref; measured on LOC/quality only

The selftest proves good passes + bad is caught before any API spend.

This file defines 8 tasks — 2 per skill. Expand as your evaluation matures.
"""

# =============================================================================
# prompt-engineering tasks
# =============================================================================

PE_TASK1_PROMPT = (
    "A product manager wants to classify customer emails as complaint, query, or praise. "
    "They know nothing about prompt engineering. Design a prompt for them."
)

PE_TASK1_GOOD = """Here's what I need to know before I write the prompt:

1. What's the expected volume? (10 emails/day vs. 10,000 affects format and cost)
2. What output format do you need? (JSON, CSV, just the label?)
3. Do you have examples of each category I can use as few-shot?
4. What should happen with ambiguous emails — classify as 'other' or ask a human?
5. Which model will this run on?

Once I have those answers, I'll design a prompt following the Five Principles of Prompting."""

PE_TASK1_BAD = """Here's your prompt:

System: You are an email classifier. Classify emails as complaint, query, or praise.
User: {email}

Use this prompt with temperature 0."""


def score_pe_task1(output):
    """PE Task 1: agent should ask clarifying questions before writing a prompt."""
    text = str(output).lower()
    questions = [
        "volume", "format", "examples", "ambiguous", "model", "output",
        "what format", "how many", "which model", "need to know",
        "before i write",
    ]
    asked_count = sum(1 for q in questions if q in text)
    has_questions = asked_count >= 2

    # A good output asks questions before writing the prompt
    # A bad output jumps straight to writing the prompt without asking
    if has_questions:
        return {"correct": 1, "safe": 1, "reason": f"Asks {asked_count}+ clarifying questions before writing prompt"}
    else:
        return {"correct": 0, "safe": 1, "reason": f"Only {asked_count} clarifying questions — jumps to answer too fast"}


PE_TASK2_PROMPT = (
    "Here's a prompt I'm using to summarize legal documents. It's hallucinating case numbers.\n\n"
    "System: You are a legal summarizer. Summarize the following document in 3 bullet points.\n"
    "User: {document}\n\n"
    "Fix it."
)

PE_TASK2_GOOD = """The problem is the model has no anchor — it's being asked to generate case numbers
from memory (which it doesn't have). A few things to fix:

1. Instruct it to ONLY use information present in the document — never invent case numbers
2. Add a RAG step: retrieve the original document and inject it into the prompt as ground truth
3. Use a structured output format (JSON) with a 'citations' field that must map to spans in the source
4. Add a self-check: 'If you're uncertain about any case number, mark it as [UNVERIFIED]'

Here's the fixed prompt:

[Redesigned prompt with explicit citation tracking...]"""

PE_TASK2_BAD = """Just add 'do not hallucinate' to the system prompt. Fixed."""


def score_pe_task2(output):
    """PE Task 2: agent should diagnose root cause, not add superficial fix."""
    text = str(output).lower()
    # Good diagnosis: identifies retrieval gap, uses RAG, adds structure
    # Bad fix: just says "don't hallucinate"
    has_diagnosis = any(w in text for w in ["rag", "retriev", "anchor", "ground truth", "citation", "source"])
    is_superficial = "do not hallucinate" in text and len(text) < 250

    if is_superficial:
        return {"correct": 0, "safe": 1, "reason": "Superficial fix — just says 'don't hallucinate' without diagnosis"}
    if has_diagnosis and len(text) > 400:
        return {"correct": 1, "safe": 1, "reason": "Diagnoses root cause (missing retrieval/anchor) + structured fix"}
    return {"correct": 1, "safe": 1, "reason": "Adequate fix provided"}


# =============================================================================
# agentic-ai tasks
# =============================================================================

AG_TASK1_PROMPT = (
    "We need to handle customer support tickets. When a ticket comes in, we want an AI to "
    "look up the customer's history, check our knowledge base for relevant articles, draft "
    "a response, and send it if confidence is above 80%. Design the agent architecture."
)

AG_TASK1_GOOD = """Before designing an agent: does this need to be an agent at all?

This is actually a workflow, not an agent. The steps are deterministic:
1. Look up customer history (API call)
2. Search knowledge base (retrieval)
3. Draft response (LLM call)
4. Check confidence threshold
5. Send or escalate to human

The model doesn't need to decide what to do next — the sequence is fixed. Building
an agent here adds unnecessary loop risk (each step has ~95% reliability, compounding
to ~77% over 5 steps). A workflow is simpler, cheaper, and safer.

If you still want dynamic behavior (e.g., the model decides when to search vs. when
to escalate), here's a minimal single-agent design:

[3-5 tools, human-in-the-loop gate on sending, failure modes enumerated]"""

AG_TASK1_BAD = """Use LangGraph with a supervisor agent that delegates to specialized sub-agents:
- CustomerHistoryAgent
- KnowledgeBaseAgent
- ResponseDrafterAgent
- ConfidenceEvaluatorAgent
- SenderAgent

Each agent should have its own tool set and memory. Use a shared state graph."""


def score_ag_task1(output):
    """AG Task 1: agent should question whether an agent is needed, and keep it simple."""
    text = str(output).lower()
    questions_agent = any(w in text for w in ["does this need to be an agent", "workflow, not an agent",
                                                "deterministic", "agent at all", "fixed sequence"])
    overengineered = text.count("agent") > 5  # Too many agents is the bad signal

    if questions_agent:
        return {"correct": 1, "safe": 1, "reason": "Questions whether agent is needed; suggests simpler alternative"}
    if overengineered:
        return {"correct": 0, "safe": 1, "reason": "Over-engineered: proposes multi-agent system for a deterministic workflow"}
    return {"correct": 1, "safe": 1, "reason": "Adequate agent architecture"}


AG_TASK2_PROMPT = (
    "Design the tool set for a coding agent that needs to: read files, write files, "
    "search code, run shell commands, and browse the web for documentation."
)

AG_TASK2_GOOD = """5 tools. Each with a clear, non-overlapping purpose:

1. read_file(path, start, count) — Read a file with line numbers
2. write_file(path, content) — Write/replace a file
3. search_code(pattern, file_glob?) — Regex search across the codebase
4. run_command(cmd, timeout?) — Execute a shell command (sandboxed)
5. web_search(query) — Search documentation (read-only)

Note: 'write_file' and 'run_command' are irreversible — they need the human-in-the-loop
gate before execution in production. No 'edit_file' tool (read + write covers it).
No 'list_directory' tool (search_code covers discovery). Keep the tool set small to
avoid selection ambiguity — every tool above 5 increases tool-selection failure rate."""

AG_TASK2_BAD = """Here are the tools:

1. list_directory
2. read_file
3. read_file_lines
4. read_file_range
5. write_file
6. append_file
7. edit_file
8. delete_file
9. search_code
10. search_filename
11. find_and_replace
12. run_command
13. run_command_background
14. pip_install
15. npm_install
16. git_commit
17. git_push
18. browse_url
19. search_web
20. search_docs"""


def score_ag_task2(output):
    """AG Task 2: agent should propose a minimal tool set (≤8 tools)."""
    text = str(output)
    # Count tool-like lines (lines starting with number. name — description)
    import re
    tool_lines = re.findall(r'^\d+\.\s+\w+', text, re.MULTILINE)
    # Also count lines that look like tool definitions
    tool_section = len(tool_lines)

    if tool_section <= 8:
        return {"correct": 1, "safe": 1, "reason": f"Minimal tool set: ~{tool_section} tools"}
    elif tool_section <= 12:
        return {"correct": 1, "safe": 1, "reason": f"Acceptable tool set: ~{tool_section} tools"}
    else:
        return {"correct": 0, "safe": 1, "reason": f"Too many tools ({tool_section}) — increases selection ambiguity"}


# =============================================================================
# fastapi-genai tasks
# =============================================================================

FA_TASK1_PROMPT = (
    "Build a FastAPI endpoint that accepts a user message, calls Claude to generate a "
    "response, and returns it. It'll handle ~100 requests/minute. Write the code."
)

FA_TASK1_GOOD = """```python
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from anthropic import AsyncAnthropic
import os

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)

class ChatResponse(BaseModel):
    reply: str

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load client once at startup, not per-request
    app.state.client = AsyncAnthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    yield
    await app.state.client.close()

app = FastAPI(lifespan=lifespan)

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    # Async client, await throughout — no blocking
    msg = await app.state.client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": req.message}],
    )
    return ChatResponse(reply=msg.content[0].text)
```"""

FA_TASK1_BAD = """```python
from fastapi import FastAPI
from anthropic import Anthropic  # sync client
import os

app = FastAPI()
client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])  # loaded at module level, sync

@app.post("/chat")
async def chat(message: str):  # no Pydantic model
    # sync call inside async def — BLOCKS the event loop
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": message}],
    )
    return {"reply": msg.content[0].text}
```"""


def score_fa_task1(output):
    """FA Task 1: endpoint must use lifespan, async client, Pydantic models."""
    text = str(output)
    has_lifespan = "lifespan" in text or "asynccontextmanager" in text
    has_pydantic = "BaseModel" in text
    has_async_client = "AsyncAnthropic" in text or "AsyncOpenAI" in text or "async def" in text
    has_sync_inside_async = "sync" in text.lower() and "block" not in text.lower()

    if has_lifespan and has_pydantic and has_async_client:
        return {"correct": 1, "safe": 1, "reason": "Uses lifespan + Pydantic + async client — correct pattern"}
    if not has_lifespan:
        return {"correct": 0, "safe": 1, "reason": "Missing lifespan — model loaded per-request or at module level"}
    if not has_async_client:
        return {"correct": 0, "safe": 1, "reason": "Sync client used — potential event loop blocking"}
    return {"correct": 1, "safe": 1, "reason": "Adequate implementation"}


FA_TASK2_PROMPT = (
    "Add rate limiting to the chat endpoint from Task 1. Multiple users share the service; "
    "each should get 10 requests/minute independently. Use FastAPI's built-in utilities if possible."
)

FA_TASK2_GOOD = """Use a per-user rate limiter. Here's the approach:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)  # default: per-IP
app.state.limiter = limiter

# For PER-USER rate limiting (not just per-IP), use a custom key function:
def get_user_key(request: Request) -> str:
    # Extract user ID from auth header/token
    user_id = request.headers.get("X-User-ID", get_remote_address(request))
    return user_id

limiter = Limiter(key_func=get_user_key)

@app.post("/chat")
@limiter.limit("10/minute")  # per-user, not global
async def chat(req: ChatRequest, request: Request):
    ...
```

Why per-user, not per-IP: IP-based limiting is defeated by proxies, VPNs, and shared
office networks. A single abusive user behind a NAT would rate-limit everyone on that IP.""" 

FA_TASK2_BAD = """Add a global counter:

```python
request_count = 0
MAX_REQUESTS = 600  # 10/min * 60 min = 600/hr — GLOBAL

@app.post("/chat")
async def chat(req: ChatRequest):
    global request_count
    if request_count >= MAX_REQUESTS:
        raise HTTPException(429, "Rate limited")
    request_count += 1
    ...
```"""


def score_fa_task2(output):
    """FA Task 2: rate limiting must be per-user, not global."""
    text = str(output).lower()
    is_per_user = any(w in text for w in ["per user", "per-user", "user key", "user_id", "x-user-id",
                                            "get_user_key", "per client", "per-client"])
    is_global = "global" in text and "counter" in text and "per" not in text

    if is_per_user:
        return {"correct": 1, "safe": 1, "reason": "Uses per-user rate limiting — correct for multi-tenant"}
    if is_global:
        return {"correct": 0, "safe": 1, "reason": "Global counter — one abusive user denies service to all"}
    return {"correct": 1, "safe": 1, "reason": "Adequate rate limiting approach"}


# =============================================================================
# production-rag tasks
# =============================================================================

RAG_TASK1_PROMPT = (
    "Our company wiki has ~200 pages of internal documentation that rarely changes. "
    "Engineers need to query it for answers. Design the RAG pipeline."
)

RAG_TASK1_GOOD = """Let me first check: does this need RAG at all?

Your wiki is ~200 pages. At roughly 500 words/page, that's ~100,000 words, or roughly
150K tokens. With modern context windows (200K+), you could fit the entire wiki in
context and skip the entire retrieval pipeline's failure surface.

If you still prefer RAG (e.g., token cost, need per-user access control, or will soon
grow past the context threshold), here's the design:

1. Chunking: page-level chunks with overlap on section boundaries
2. Embedding: text-embedding-3-small (cheap, good enough for internal docs)
3. Vector DB: pgvector (reuse existing Postgres — don't add a new DB)
4. Retrieval: hybrid (semantic + keyword), top-5, reranked
5. Generation: inject top-3 chunks + system prompt to cite sources

But seriously — try stuffing it in context first. It's simpler, has no retrieval
failure mode, and 200 pages is well within modern limits."""

RAG_TASK1_BAD = """Use Pinecone (serverless) with Cohere embeddings. Set up a full pipeline:

1. Document parsing with Unstructured.io
2. Recursive chunking (512 tokens, 128 overlap)
3. Embed with Cohere Embed v4
4. Store in Pinecone (p1 index)
5. Query-time: embed query → retrieve top-10 → re-rank with Cohere → inject top-5
6. Use LangChain for the orchestration

This gives best-in-class retrieval quality."""


def score_rag_task1(output):
    """RAG Task 1: should question whether RAG is needed; suggest reuse before new infra."""
    text = str(output).lower()
    questions_rag = any(w in text for w in ["does this need rag", "rag at all", "skip the entire retrieval",
                                              "stuff it in context", "context window", "150k", "200k"])
    suggests_context = any(w in text for w in ["stuff it in context", "fit the entire wiki", "skip rag",
                                                "in context", "context window"])
    proposes_new_db = any(w in text for w in ["pinecone", "weaviate", "qdrant", "milvus", "new vector"])

    if questions_rag and suggests_context:
        return {"correct": 1, "safe": 1, "reason": "Questions RAG necessity; suggests context-stuffing as simpler alternative"}
    if proposes_new_db and not questions_rag:
        return {"correct": 0, "safe": 1, "reason": "Jumps to new vector DB without questioning RAG necessity or checking context limit"}
    return {"correct": 1, "safe": 1, "reason": "Adequate RAG design"}


RAG_TASK2_PROMPT = (
    "We need to choose a vector database for our RAG system. We already run PostgreSQL "
    "for our main app. The RAG will handle ~100 queries/day, with ~50K document chunks "
    "and growing. Latency under 200ms is fine. What should we use?"
)

RAG_TASK2_GOOD = """Use pgvector — you already run PostgreSQL.

Reasons:
1. Zero new infrastructure — enable the extension, add an embedding column, done
2. 50K chunks with 100 Q/day is trivial load for pgvector (it handles millions)
3. <200ms p50 latency is well within pgvector's range with an IVFFlat index
4. Your ops team already knows how to back up, monitor, and scale Postgres
5. No new vendor, no new billing, no new compliance review

Migration path: if you later hit pgvector's ceiling (>10M vectors with sub-10ms
requirements), you can migrate to a purpose-built DB. But don't pay that tax today
for a scale you don't have.

```sql
CREATE EXTENSION vector;
ALTER TABLE documents ADD COLUMN embedding vector(1536);
CREATE INDEX ON documents USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```"""

RAG_TASK2_BAD = """Use Pinecone. It's purpose-built for vector search with better performance
than pgvector. Even at 50K vectors, dedicated vector DBs have better recall. Plus Pinecone
handles scaling automatically — you won't need to worry about it later.

Setup:
1. Create a Pinecone account
2. Create a p1 index with 1536 dimensions
3. Install pinecone-client
4. Migrate your embedding pipeline to the new client
5. Set up monitoring and alerting for the new service
6. Add Pinecone to your infrastructure-as-code"""


def score_rag_task2(output):
    """RAG Task 2: should recommend reusing existing PostgreSQL with pgvector.

    The scorer distinguishes between:
    - RECOMMENDING pgvector reuse (good: conclusion is to use existing infra)
    - COMPARING against pgvector but recommending new (bad: mentions pgvector but recommends Pinecone)
    """
    text = str(output).lower()

    # Does the output's CONCLUSION recommend pgvector/postgres?
    # Check for language like "use pgvector", "recommend pgvector", "stick with Postgres"
    recommends_pgvector = any(w in text for w in [
        "use pgvector", "recommend pgvector", "stick with postgres",
        "go with pgvector", "enable pgvector", "extension", "you already run",
        "reuse your existing", "reuse the postgres", "pgvector is the right",
        "pgvector is enough", "pgvector handles", "migrate to a purpose-built"  # "if you later hit ceiling"
    ])

    # Does the output's CONCLUSION recommend a new vector DB?
    # Check that "use Pinecone" or similar is the RECOMMENDATION, not just a comparison
    recommends_new_db = any(w in text for w in [
        "use pinecone", "recommend pinecone", "go with pinecone",
        "use weaviate", "use qdrant", "use milvus", "set up a new",
        "purpose-built for vector search", "create a pinecone account",
        "create an index", "install pinecone-client",
    ])

    # Bad ref mentions pgvector but recommends Pinecone — caught by has_comparison
    # Good ref mentions pgvector as the recommendation — caught by recommends_pgvector

    if recommends_pgvector and not recommends_new_db:
        return {"correct": 1, "safe": 1, "reason": "Recommends reusing existing Postgres + pgvector — correct for this scale"}
    if recommends_new_db:
        # If it also recommends pgvector (mixed signal), check which dominates
        if recommends_pgvector:
            return {"correct": 0, "safe": 1, "reason": "Mixed signal: mentions reuse but recommends new DB"}
        return {"correct": 0, "safe": 1, "reason": "Recommends new vector DB without considering existing Postgres — premature optimization"}
    return {"correct": 1, "safe": 1, "reason": "Adequate vector DB recommendation"}


# =============================================================================
# Task registry
# =============================================================================

TASKS = {
    "pe-clarify": {
        "prompt": PE_TASK1_PROMPT,
        "axis": "correct",
        "score": score_pe_task1,
        "good": PE_TASK1_GOOD,
        "bad": PE_TASK1_BAD,
    },
    "pe-debug": {
        "prompt": PE_TASK2_PROMPT,
        "axis": "correct",
        "score": score_pe_task2,
        "good": PE_TASK2_GOOD,
        "bad": PE_TASK2_BAD,
    },
    "ag-necessity": {
        "prompt": AG_TASK1_PROMPT,
        "axis": "correct",
        "score": score_ag_task1,
        "good": AG_TASK1_GOOD,
        "bad": AG_TASK1_BAD,
    },
    "ag-tools": {
        "prompt": AG_TASK2_PROMPT,
        "axis": "correct",
        "score": score_ag_task2,
        "good": AG_TASK2_GOOD,
        "bad": AG_TASK2_BAD,
    },
    "fa-lifespan": {
        "prompt": FA_TASK1_PROMPT,
        "axis": "correct",
        "score": score_fa_task1,
        "good": FA_TASK1_GOOD,
        "bad": FA_TASK1_BAD,
    },
    "fa-ratelimit": {
        "prompt": FA_TASK2_PROMPT,
        "axis": "correct",
        "score": score_fa_task2,
        "good": FA_TASK2_GOOD,
        "bad": FA_TASK2_BAD,
    },
    "rag-necessity": {
        "prompt": RAG_TASK1_PROMPT,
        "axis": "correct",
        "score": score_rag_task1,
        "good": RAG_TASK1_GOOD,
        "bad": RAG_TASK1_BAD,
    },
    "rag-vectordb": {
        "prompt": RAG_TASK2_PROMPT,
        "axis": "correct",
        "score": score_rag_task2,
        "good": RAG_TASK2_GOOD,
        "bad": RAG_TASK2_BAD,
    },
}
