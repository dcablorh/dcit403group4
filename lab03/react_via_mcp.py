"""Lab 3, Wednesday: the Lab 2 ReAct agent with its tools served by MCP.

Lab 2's agent imported its tools and described them by hand. This one starts
server.py, reads the tool list from the server at run time, and writes those
descriptions into the ReAct prompt. The loop is still the text protocol, so
the trace shows exactly what changed:

  * the tool list and the argument schemas now come from the MCP server;
  * "Action Input" must be a JSON object, because MCP tools take named
    arguments, not one free-text string;
  * the parser from Lab 2 is unchanged: it still splits Action and Action
    Input, and the JSON is decoded after parsing.

    python react_via_mcp.py --question "Do we have amoxicillin 500mg?"
    python react_via_mcp.py --question "Record a sale of 2 packs of amoxicillin 500mg."
"""

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
load_dotenv(ROOT / ".env")

# Reuse Lab 2's parser rather than writing a second one.
sys.path.insert(0, str(ROOT / "lab02"))
from react_agent import parse  # noqa: E402

from litellm import acompletion  # noqa: E402
from mcp import ClientSession, StdioServerParameters  # noqa: E402
from mcp.client.stdio import stdio_client  # noqa: E402

MODEL = os.environ.get("LLM_MODEL", "groq/qwen/qwen3.8-27b")
EVIDENCE = HERE / "evidence"
MAX_STEPS = 6
RETRY_WAITS = (5, 10, 20)

SERVER = StdioServerParameters(command=sys.executable,
                               args=[str(HERE / "server.py")], cwd=str(HERE))

PROMPT = """You are the stock assistant of a community pharmacy in Accra, Ghana.

Your tools are provided by an MCP server. You do not know their code, only
this list:

{tools}

Work in steps. On every step reply with exactly this, and nothing else:

Thought: <one or two sentences of reasoning>
Action: <one tool name from the list, or finish>
Action Input: <a JSON object of arguments, or the final answer for finish>

Rules:
1. Arguments must be a JSON object, e.g. {{"item": "amoxicillin", "strength": "500mg"}}.
   Use only the argument names shown for that tool.
2. Never invent stock, prices or dates: call a tool and use what it returns.
3. Never write an Observation line; the system runs the tool and sends it back.
4. If a sale is refused, relay the refusal exactly and do not retry with a
   different quantity.
5. Finish with Action: finish and put the whole answer in Action Input.
"""


def render_tools(tools) -> str:
    """Turn MCP tool definitions into prompt text the model can read."""
    blocks = []
    for t in tools:
        schema = t.inputSchema or {}
        params = schema.get("properties", {})
        required = set(schema.get("required", []))
        args = []
        for name, spec in params.items():
            kind = spec.get("type", "string")
            default = f", default {spec['default']!r}" if "default" in spec else ""
            mark = "" if name in required else " (optional)"
            args.append(f"      - {name}: {kind}{default}{mark}")
        blocks.append(
            f"  {t.name}\n"
            f"    {t.description or ''}\n"
            f"    arguments:\n" + ("\n".join(args) if args else "      (none)")
        )
    return "\n\n".join(blocks)


def content_text(result) -> str:
    return "\n".join(getattr(b, "text", str(b)) for b in result.content or [])


async def model_call(messages: list[dict]) -> str:
    """One completion, retried on rate limits. No tools argument: this is
    Lab 2's text protocol, not native function calling."""
    for wait in (*RETRY_WAITS, None):
        try:
            resp = await acompletion(model=MODEL, messages=messages,
                                     temperature=0, stop=["Observation:"])
            return (resp.choices[0].message.content or "").strip()
        except Exception as exc:
            retryable = any(w in str(exc).lower()
                            for w in ("rate limit", "ratelimit", "429", "connection"))
            if not retryable or wait is None:
                raise
            print(f"  (retrying in {wait}s: {type(exc).__name__})")
            await asyncio.sleep(wait)


async def run(question: str) -> None:
    EVIDENCE.mkdir(exist_ok=True)
    lines = ["# Lab 2 ReAct agent, tools discovered from the MCP server",
             f"# model: {MODEL}",
             f"# run: {datetime.now().isoformat(timespec='seconds')}",
             f"# question: {question}", ""]

    async with stdio_client(SERVER) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = (await session.list_tools()).tools
            names = [t.name for t in tools]
            print("Discovered over MCP:", ", ".join(names))

            lines.append("DISCOVERED TOOLS (from the server, not imported):")
            lines.append(render_tools(tools))
            lines.append("")

            messages = [{"role": "system", "content": PROMPT.format(tools=render_tools(tools))},
                        {"role": "user", "content": question}]
            lines.append(f"QUESTION: {question}")
            lines.append("-" * 70)

            answer, outcome = None, "max_steps"
            for step in range(1, MAX_STEPS + 1):
                started = time.perf_counter()
                reply = await model_call(messages)
                elapsed = time.perf_counter() - started
                messages.append({"role": "assistant", "content": reply})
                lines.append(f"\nSTEP {step}  ({elapsed:.2f}s)\n{reply}")

                action, action_input = parse(reply)
                if action is None:
                    observation = ("Could not parse your reply. Use exactly:\n"
                                   "Thought: ...\n"
                                   f"Action: {names} or finish\n"
                                   'Action Input: {"..."} or the final answer')
                    lines.append("  [parser] unparseable reply -> corrective Observation")
                elif action == "finish":
                    answer, outcome = action_input or "No answer given.", "finish"
                    break
                elif action not in names:
                    observation = (f"Unknown action '{action}'. Valid actions are "
                                   f"{names}, or finish.")
                    lines.append("  [unknown tool] corrective Observation")
                else:
                    try:
                        args = json.loads(action_input or "{}")
                        if not isinstance(args, dict):
                            raise ValueError("arguments must be a JSON object")
                    except (json.JSONDecodeError, ValueError) as exc:
                        observation = (f"Action Input for {action} must be a JSON "
                                       f"object of named arguments ({exc}).")
                        lines.append("  [bad arguments] corrective Observation")
                    else:
                        result = await session.call_tool(action, args)
                        observation = content_text(result)
                        lines.append(f"  [mcp] {action}({args}) -> "
                                     f"{' '.join(observation.split())[:200]}")
                        if result.isError:
                            observation = f"Tool error: {observation}"

                if len(observation) > 1500:
                    observation = observation[:1500] + " ...[truncated]"
                lines.append(f"Observation: {observation}")
                messages.append({"role": "user", "content": f"Observation: {observation}"})

                if step == MAX_STEPS:
                    lines.append("\nOUTCOME: max_steps")

            lines.append("\n" + "=" * 70)
            lines.append(f"OUTCOME: {outcome}")
            lines.append(f"FINAL ANSWER: {answer}")
            print(f"\n{answer}")

    out = EVIDENCE / "react_via_mcp.txt"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nTrace: {out}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--question", default="Do we have amoxicillin 500mg?")
    args = ap.parse_args()
    asyncio.run(run(args.question))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
