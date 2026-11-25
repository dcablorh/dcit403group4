"""Lab 3, Step 3 + 5: an agent that discovers its tools from the MCP server.

This file never imports the tool functions. It starts server.py over stdio,
asks the server for its tool list, turns that list into JSON schemas for the
model, and runs each tool call through `session.call_tool`. That is the whole
point of MCP: the tools live outside the agent.

Every tool call is appended to evidence/tool_calls.jsonl with its timestamp,
arguments, a short result summary and the duration in milliseconds.

    python client_agent.py --question "Do we have amoxicillin 500mg?"
    python client_agent.py --suite          # six questions incl. one sale
"""

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
load_dotenv(HERE.parent / ".env")

from litellm import acompletion  # noqa: E402
from mcp import ClientSession, StdioServerParameters  # noqa: E402
from mcp.client.stdio import stdio_client  # noqa: E402

MODEL = os.environ.get("LLM_MODEL", "groq/qwen/qwen3.8-27b")
LOG = HERE / "evidence" / "tool_calls.jsonl"
EVIDENCE = HERE / "evidence"
MAX_STEPS = 6
# Groq's free tier limits input tokens per minute. Space the questions out and
# retry with backoff instead of losing a run to a 429.
PAUSE_SECONDS = 8
RETRY_WAITS = (5, 10, 20, 30)

SERVER = StdioServerParameters(command=sys.executable, args=[str(HERE / "server.py")],
                               cwd=str(HERE))

SYSTEM_PROMPT = """You are the stock assistant of a community pharmacy in Accra, Ghana.
You can only learn about the stock by calling the tools you are given. Never
invent a quantity, price or expiry date, and never guess whether an item is in
stock: call a tool first.

Use check_stock for a named medicine and strength, search_items when you only
have part of a name or want to know which forms exist, and list_expiring for
"what expires soon" questions. Use record_sale only when the user asks you to
sell or remove stock; pass the strength whenever more than one strength exists.

If record_sale refuses a sale, tell the user exactly why (for example an
oversale or an expired batch) and do not retry with a different number.
Answer in the user's own terms, quoting the figures the tools returned.
"""

SIX_QUESTIONS = [
    "Do we have amoxicillin 500mg?",
    "Which items expire within 60 days?",
    "Do you have any paracetamol syrup, and what does it cost?",
    "How much paracetamol do we have?",
    "Record a sale of 3 packs of amoxicillin 500mg.",
    "Sell 500 packs of paracetamol 500mg to a customer.",
]


# --- Helpers -------------------------------------------------------------
def tool_schemas(tools) -> list[dict]:
    """Turn MCP tool definitions into the OpenAI/LiteLLM function schema."""
    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description or "",
                "parameters": t.inputSchema or {"type": "object", "properties": {}},
            },
        }
        for t in tools
    ]


def result_text(result) -> str:
    """Flatten an MCP CallToolResult into one string."""
    parts = []
    for block in result.content or []:
        parts.append(getattr(block, "text", str(block)))
    return "\n".join(parts)


def summarise(result, limit: int = 300) -> str:
    """Short, single-line summary for the log and the transcript.

    FastMCP sends one content block per returned row, each block a JSON
    document. Parse them one by one: joining the blocks first would give
    invalid JSON and a summary of raw text.
    """
    parsed = []
    for block in result.content or []:
        text = getattr(block, "text", None)
        if text is None:
            continue
        try:
            parsed.append(json.loads(text))
        except json.JSONDecodeError:
            parsed.append(" ".join(text.split()))

    if not parsed:
        return "no rows (empty result)"
    data = parsed[0] if len(parsed) == 1 else parsed
    if isinstance(data, dict):
        if "message" in data:
            return str(data["message"])[:limit]
        if "item" in data:
            return (f"1 row: {data['item']} {data['strength']} {data['form']}, "
                    f"qty {data['quantity']}, GHS {data['unit_price_ghs']}, "
                    f"expires {data['expiry_date']}")[:limit]
        return "object: " + ", ".join(data)[:limit]
    if isinstance(data, list):
        if not data:
            return "no rows"
        rows = [r for r in data if isinstance(r, dict) and "item" in r]
        if len(rows) == len(data):
            names = ", ".join(f"{r['item']} {r['strength']}" for r in rows[:5])
            more = f" (+{len(rows) - 5} more)" if len(rows) > 5 else ""
            return f"{len(rows)} row(s): {names}{more}"[:limit]
        return f"{len(data)} row(s)"
    return str(data)[:limit]


def assistant_message(msg) -> dict:
    """Convert a LiteLLM response message to a dict we can send back."""
    out = {"role": "assistant", "content": msg.content or ""}
    if msg.tool_calls:
        out["tool_calls"] = [
            {
                "id": tc.id,
                "type": "function",
                "function": {"name": tc.function.name,
                             "arguments": tc.function.arguments},
            }
            for tc in msg.tool_calls
        ]
    return out


def log_call(question_id: int, question: str, name: str, args: dict,
             summary: str, duration_ms: int, ok: bool) -> None:
    LOG.parent.mkdir(exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        "question_id": question_id,
        "question": question,
        "tool": name,
        "arguments": args,
        "result_summary": summary,
        "duration_ms": duration_ms,
        "ok": ok,
    }
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# --- The agent loop ------------------------------------------------------
async def chat(messages: list[dict], schemas: list[dict]):
    """One model call, retried with backoff on a 429 or a dropped connection."""
    for wait in (*RETRY_WAITS, None):
        try:
            return await acompletion(model=MODEL, messages=messages,
                                     tools=schemas, temperature=0)
        except Exception as exc:
            text = f"{type(exc).__name__}: {exc}".lower()
            retryable = ("rate limit" in text or "ratelimit" in text
                         or "connection" in text or "429" in text)
            if not retryable or wait is None:
                raise
            print(f"  (retrying in {wait}s: {type(exc).__name__})")
            await asyncio.sleep(wait)


async def answer(session: ClientSession, schemas: list[dict], question: str,
                 question_id: int, transcript: list[str]) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]
    transcript.append("=" * 72)
    transcript.append(f"QUESTION {question_id}: {question}")

    for step in range(1, MAX_STEPS + 1):
        resp = await chat(messages, schemas)
        msg = resp.choices[0].message
        messages.append(assistant_message(msg))
        transcript.append(f"\n[step {step}] assistant content: {msg.content!r}")

        if not msg.tool_calls:
            text = msg.content or "(no answer)"
            transcript.append(f"FINAL: {text}")
            return text

        for tc in msg.tool_calls:
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            transcript.append(f"[step {step}] tool_call: {name}({args})")

            started = time.perf_counter()
            try:
                result = await session.call_tool(name, args)
                text = result_text(result)
                ok = not result.isError
            except Exception as exc:  # a broken tool call must not end the run
                text = f"Tool error: {type(exc).__name__}: {exc}"
                ok = False
                result = None
            duration_ms = int((time.perf_counter() - started) * 1000)
            summary = (summarise(result) if result is not None
                       else " ".join(text.split()))
            log_call(question_id, question, name, args, summary, duration_ms, ok)
            transcript.append(f"          -> {summary} ({duration_ms} ms)")

            messages.append({"role": "tool", "tool_call_id": tc.id,
                             "content": text})

    transcript.append(f"OUTCOME: max_steps ({MAX_STEPS}) reached")
    return "Stopped: the agent did not finish within the step limit."


async def run(questions: list[str], tag: str) -> None:
    EVIDENCE.mkdir(exist_ok=True)
    transcript: list[str] = [f"# client_agent.py on {MODEL}",
                             f"# server: python {HERE / 'server.py'}",
                             f"# run: {datetime.now().isoformat(timespec='seconds')}", ""]

    async with stdio_client(SERVER) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = (await session.list_tools()).tools
            schemas = tool_schemas(tools)
            transcript.append("DISCOVERED TOOLS: " + ", ".join(t.name for t in tools))
            print("Discovered tools:", ", ".join(t.name for t in tools))

            for i, q in enumerate(questions, 1):
                print(f"\n[{i}/{len(questions)}] {q}")
                if i > 1:
                    await asyncio.sleep(PAUSE_SECONDS)
                try:
                    final = await answer(session, schemas, q, i, transcript)
                except Exception as exc:
                    final = f"ERROR: {type(exc).__name__}: {exc}"
                    transcript.append(f"ERROR: {final}")
                print(f"  -> {final}")

    out = EVIDENCE / f"client_agent_{tag}.txt"
    out.write_text("\n".join(transcript), encoding="utf-8")
    print(f"\nTranscript: {out}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--question", action="append", default=[])
    ap.add_argument("--suite", action="store_true",
                    help="run the six lab questions, including one sale")
    ap.add_argument("--tag", default="run", help="name for the transcript file")
    args = ap.parse_args()

    questions = list(args.question)
    if args.suite:
        questions += SIX_QUESTIONS
    if not questions:
        questions = SIX_QUESTIONS[:1]

    asyncio.run(run(questions, args.tag))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
