"""Lab 3, Step 1: native function calling, without MCP.

The step-1 point is that we no longer ask the model to write "Action: ..."
text. We give it a JSON schema, the API enforces the shape, and the reply
arrives as a structured ``tool_calls`` field. Our code runs the function and
sends the result back as a ``tool`` message.

    python function_calling.py --question "Do we have amoxicillin 500mg?"
    python function_calling.py --questions-file questions_step1.txt

Every round trip is printed and appended to evidence/function_calling.txt.
"""

import argparse
import csv
import json
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

import os  # noqa: E402  (must come after load_dotenv)

from litellm import completion  # noqa: E402

DATA = Path(__file__).resolve().parent / "data" / "pharmacy_stock.csv"
EVIDENCE = Path(__file__).resolve().parent / "evidence"
MODEL = os.environ.get("LLM_MODEL", "groq/qwen/qwen3.8-27b")


# --- The plain Python function (no MCP yet) ------------------------------
def check_stock(item: str, strength: str = "") -> list[dict]:
    """Return the stock rows whose item name contains `item`.

    If `strength` is given, rows must also contain it. An empty list means
    the pharmacy does not stock that item.
    """
    with open(DATA, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    hits = [r for r in rows if item.lower() in r["item"].lower()]
    if strength:
        hits = [r for r in hits if strength.lower() in r["strength"].lower()]
    return hits


TOOLS = {"check_stock": check_stock}

# The description is part of the prompt: the model picks tools by reading it.
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "check_stock",
            "description": (
                "Look up a medicine in the pharmacy stock list. Returns rows "
                "with item, strength, form, quantity in stock, unit price in "
                "GHS and expiry date. Use it before answering any question "
                "about availability, price or expiry."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "item": {
                        "type": "string",
                        "description": "Medicine name, e.g. 'amoxicillin'",
                    },
                    "strength": {
                        "type": "string",
                        "description": "Strength, e.g. '500mg'. Omit to return all strengths.",
                    },
                },
                "required": ["item"],
            },
        },
    }
]

SYSTEM_PROMPT = (
    "You are the stock assistant of a community pharmacy in Accra, Ghana. "
    "Always call check_stock before you answer a stock, price or expiry "
    "question. Never invent a quantity, price or date. Quote the data the "
    "tool returns; if the tool returns no rows, say the item is not stocked."
)


# --- One round trip ------------------------------------------------------
def ask(question: str) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]

    # Call 1: the model decides to call a tool.
    resp = completion(model=MODEL, messages=messages, tools=TOOL_SCHEMAS,
                      temperature=0)
    msg = resp.choices[0].message
    print("\n-- assistant message 1 --")
    print(f"content: {msg.content!r}")
    if not msg.tool_calls:
        print("No tool call. Answer taken as-is.")
        return msg.content or ""

    messages.append(msg.model_dump(exclude_none=True))
    for tc in msg.tool_calls:
        print(f"tool_call: id={tc.id} name={tc.function.name} "
              f"arguments={tc.function.arguments}")
        args = json.loads(tc.function.arguments)
        result = TOOLS[tc.function.name](**args)
        print(f"tool result: {json.dumps(result)[:400]}")
        messages.append({
            "role": "tool",
            "tool_call_id": tc.id,
            "content": json.dumps(result),
        })

    # Call 2: the final answer must now use the tool result.
    resp = completion(model=MODEL, messages=messages, tools=TOOL_SCHEMAS,
                      temperature=0)
    answer = resp.choices[0].message.content or ""
    print("\n-- assistant message 2 --")
    print(answer)
    return answer


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--question", action="append", default=[],
                    help="question to ask (repeatable)")
    ap.add_argument("--questions-file",
                    help="text file with one question per line")
    args = ap.parse_args()

    questions = list(args.question)
    if args.questions_file:
        questions += [ln.strip() for ln in
                      Path(args.questions_file).read_text(encoding="utf-8").splitlines()
                      if ln.strip() and not ln.startswith("#")]
    if not questions:
        questions = ["Do we have amoxicillin 500mg?"]

    EVIDENCE.mkdir(exist_ok=True)
    out = EVIDENCE / "function_calling.txt"
    buf: list[str] = [f"# Step 1: native function calling on {MODEL}",
                      f"# tools: {[t['function']['name'] for t in TOOL_SCHEMAS]}", ""]
    for i, q in enumerate(questions, 1):
        if i > 1:
            time.sleep(8)  # Groq free tier limits input tokens per minute
        buf.append("=" * 72)
        buf.append(f"QUESTION: {q}")
        try:
            answer = ask(q)
            buf.append(f"\nFINAL ANSWER: {answer}")
        except Exception as exc:  # keep going: one bad call must not stop the run
            buf.append(f"\nERROR: {type(exc).__name__}: {exc}")
        buf.append("")
        print("\n" + "=" * 72)

    out.write_text("\n".join(buf), encoding="utf-8")
    print(f"\nEvidence appended to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
