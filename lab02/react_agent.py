"""Lab 2: a ReAct agent from scratch, in plain Python, with no framework.

The loop is the classical sense-think-act cycle:

    Thought       deliberation  (the model plans)
    Action        decision      (the model names a tool)
    Observation   perception    (our code runs the tool and reports the result)

Run it with a real model:
    python react_agent.py --question "I have GHS 1,200 ..."
    python react_agent.py --suite              # all six lab questions

"""

import argparse
import os
import re
import sys
import time
from pathlib import Path

# Windows consoles are cp1252 by default; model replies contain narrow and
# non-breaking spaces that would crash print(). Never fail on output encoding.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv

from tools import TOOL_DESCRIPTIONS, TOOL_NAMES, TOOLS

EVIDENCE_DIR = Path(__file__).resolve().parent / "evidence"

SYSTEM_PROMPT = f"""You are a careful assistant to a trader at Makola Market in Accra, Ghana.
You answer costing questions and quick factual questions.

You have these tools:
{TOOL_DESCRIPTIONS}

Work in steps. On every step write exactly this, and nothing else:

Thought: <one or two sentences of reasoning>
Action: {TOOL_NAMES}
Action Input: <the tool input, or the final answer when Action is finish>

Rules:
1. Use the calculator for every arithmetic step. Never do arithmetic in your head.
2. Use wiki_lookup for facts about people, places and history. If the lookup
   finds nothing, say so instead of inventing an answer.
3. One tool per step.
4. Never write an Observation line: the system writes it and sends it back.
5. When you have the final answer, use Action: finish and put the whole answer
   in Action Input.
6. Before you finish, check that every number in your final answer came from a
   calculator Observation in this conversation. If it did not, call the
   calculator first. Never state a result you worked out in your head.
"""


# --- Parsing -------------------------------------------------------------
# The format the prompt asks for: "Action: name" then "Action Input: ..." on
# the next line. This is the parser from the lab manual.
ACTION_RE = re.compile(r"Action:\s*(\w+)\s*\n\s*Action Input:\s*(.*)", re.DOTALL | re.IGNORECASE)

# Real models sometimes put both fields on one line, add spaces, or label the
# input differently. This fallback looks for the two fields independently.
ACTION_NAME_RE = re.compile(r"Action(?!\s*Input)\s*:\s*([A-Za-z_]\w*)", re.IGNORECASE)
ACTION_INPUT_RE = re.compile(r"Action\s*Input\s*:\s*(.*)", re.IGNORECASE | re.DOTALL)
FINAL_ANSWER_RE = re.compile(r"Final\s*Answer\s*:\s*(.*)", re.IGNORECASE | re.DOTALL)


# A result that was reached without the calculator: an expression in the answer.
ARITHMETIC_RE = re.compile(r"\d[\d,]*\s*(?:[-+*/^x×])\s*\d")


def clean(text):
    """Normalise exotic spaces and quotes from the model so output is portable."""
    for bad, good in ((" ", " "), (" ", " "), (" ", " "),
                      (" ", " "), ("‑", "-"), ("–", "-"),
                      ("—", "-"), ("‘", "'"), ("’", "'"),
                      ("“", '"'), ("”", '"')):
        text = text.replace(bad, good)
    return text


def _clean_input(text):
    """Keep only the current step: drop leaked Observations and future steps.

    gpt-oss-20b tends to answer with the whole ReAct transcript at once (three
    Thought/Action blocks in one reply). Taking everything after "Action Input:"
    would hand the tool a paragraph instead of an expression, so the input stops
    at the first line that starts a new step.
    """
    for marker in (r"\n\s*Observation\s*:", r"\n\s*Thought\s*:",
                   r"\n\s*Action\s*(?:Input)?\s*:"):
        text = re.split(marker, text, maxsplit=1)[0]
    return text.strip().strip("`").strip()


def parse(text):
    """Return (action, action_input) or (None, None) if the reply is unusable."""
    m = ACTION_RE.search(text)
    if m:
        return m.group(1).strip().lower(), _clean_input(m.group(2))

    name = ACTION_NAME_RE.search(text)
    inp = ACTION_INPUT_RE.search(text)
    if name and inp:
        return name.group(1).strip().lower(), _clean_input(inp.group(1))
    if name and name.group(1).lower() == "finish":
        # "Action: finish" with the answer on a separate line.
        rest = text[name.end():]
        return "finish", _clean_input(rest) or "No answer given."

    final = FINAL_ANSWER_RE.search(text)
    if final:
        return "finish", _clean_input(final.group(1))
    return None, None


# Sent when a provider rejects the model's native tool-call output: the text
# protocol is enforced by the prompt, not by the API (that is Lab 3's job).
TOOL_PROTOCOL_NUDGE = (
    "Your previous reply was rejected because it used a JSON / tool-call "
    "format. Do not call tools through any API. Reply only with the three "
    "plain text lines:\nThought: <reasoning>\nAction: <tool or finish>\n"
    "Action Input: <input>"
)


# --- Model call ----------------------------------------------------------
def call_model(messages, model, temperature=0, max_retries=4):
    """One model call, retrying rate limits and dropped connections."""
    from litellm import completion
    from litellm.exceptions import (
        APIConnectionError,
        InternalServerError,
        RateLimitError,
        Timeout,
    )

    from litellm.exceptions import BadRequestError

    retryable = (RateLimitError, APIConnectionError, InternalServerError, Timeout)
    pause = 2
    for attempt in range(max_retries):
        try:
            resp = completion(
                model=model,
                messages=messages,
                temperature=temperature,
                stop=["Observation:"],  # the model must not invent percepts
                timeout=60,
                # gpt-oss counts reasoning tokens as completion tokens; keep it low
                **({"reasoning_effort": "low"} if "gpt-oss" in model else {}),
            )
            text = clean(resp.choices[0].message.content or "")
            usage = getattr(resp, "usage", None)
            tokens = {
                "prompt_tokens": getattr(usage, "prompt_tokens", 0) if usage else 0,
                "completion_tokens": getattr(usage, "completion_tokens", 0) if usage else 0,
                "total_tokens": getattr(usage, "total_tokens", 0) if usage else 0,
            }
            return text, tokens
        except BadRequestError as e:
            # Groq/OpenAI return this when the model emits a native tool call
            # while no tools were supplied: "Tool choice is none, but model
            # called a tool". That is a protocol failure, not a broken request.
            if "tool" not in str(e).lower():
                raise
            print("  [tool_use_failed] model used tool-call syntax; "
                  "adding a corrective instruction and retrying", file=sys.stderr)
            messages.append({"role": "user", "content": TOOL_PROTOCOL_NUDGE})
            if attempt == max_retries - 1:
                raise
            time.sleep(1)
        except retryable as e:
            if attempt == max_retries - 1:
                raise
            kind = "rate limit" if isinstance(e, RateLimitError) else type(e).__name__
            print(f"  [{kind}] waiting {pause}s and retrying", file=sys.stderr)
            time.sleep(pause)
            pause *= 2


# --- The loop ------------------------------------------------------------
def run_agent(question, max_steps=6, model=None, temperature=0,
              verbose=True, save=True, tag=None):
    """Run the ReAct loop. Returns a dict describing the run."""
    model = model or os.getenv("LLM_MODEL", "groq/openai/gpt-oss-20b")
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]
    lines = [
        f"QUESTION: {question}",
        f"MODEL: {model}",
        f"MODE: live",
        f"MAX_STEPS: {max_steps}   TEMPERATURE: {temperature}",
        "-" * 70,
        "SYSTEM PROMPT (abridged): ReAct format, tools = " + TOOL_NAMES,
        "-" * 70,
    ]

    steps = 0
    tokens = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    answer = None
    outcome = "max_steps"
    tools_used = set()
    finish_checked = False

    while steps < max_steps:
        steps += 1
        started = time.time()
        try:
            reply, used = call_model(messages, model, temperature)
            elapsed = time.time() - started
        except Exception as e:  # a dead API must not look like a reasoning bug
            lines.append(f"\nSTEP {steps}: model call failed: {type(e).__name__}: {e}")
            outcome = "model_error"
            break

        for key in ("prompt_tokens", "completion_tokens"):
            tokens[key] += used.get(key, 0)
        # Some providers report only prompt/completion tokens; others only total.
        tokens["total_tokens"] += used.get("total_tokens") or (
            used.get("prompt_tokens", 0) + used.get("completion_tokens", 0))

        messages.append({"role": "assistant", "content": reply})
        lines.append(f"\nSTEP {steps}  ({elapsed:.2f}s)\n{reply.strip()}")

        action, action_input = parse(reply)

        # --- reactive error handling, one branch per failure we have seen ---
        if action is None:
            observation = (
                "Could not parse your reply. Reply using exactly this format:\n"
                "Thought: <reasoning>\n"
                f"Action: {TOOL_NAMES}\n"
                "Action Input: <tool input or final answer>"
            )
            lines.append("  [parser] no Action/Action Input found -> corrective Observation")
        elif action == "finish":
            # Guardrail: the model may not stop with an arithmetic result that
            # no calculator Observation produced. A prompt rule alone was not
            # enough (see trace_9), so the loop enforces it once.
            if ("calculator" not in tools_used and not finish_checked
                    and ARITHMETIC_RE.search(action_input or "")):
                finish_checked = True
                observation = (
                    "Your answer contains an arithmetic result but no calculator "
                    "Observation. Run the calculation with the calculator, then "
                    "finish using the returned value."
                )
                lines.append("  [guardrail] finish rejected: arithmetic without a calculator call")
                lines.append(f"Observation: {observation}")
                messages.append({"role": "user", "content": f"Observation: {observation}"})
                continue
            answer = action_input or "No answer given."
            outcome = "finish"
            lines.append(f"  [finish] {answer}")
            break
        elif action not in TOOLS:
            observation = (
                f"Unknown action '{action}'. Valid actions are: {TOOL_NAMES}. "
                "Call one of them, or finish."
            )
            lines.append(f"  [unknown tool] '{action}' -> corrective Observation")
        else:
            observation = TOOLS[action](action_input)
            tools_used.add(action)
            lines.append(f"  [tool] {action}({action_input!r}) -> {observation}")

        if len(observation) > 1200:
            observation = observation[:1200] + " ...[truncated]"
        lines.append(f"Observation: {observation}")
        messages.append({"role": "user", "content": f"Observation: {observation}"})

    if outcome == "max_steps":
        answer = (
            f"Stopped after {max_steps} steps without a finish action. "
            "The agent did not reach an answer."
        )
        lines.append(f"\n[MAX_STEPS] limit of {max_steps} reached.")

    lines.append("\n" + "=" * 70)
    lines.append(f"OUTCOME: {outcome}   STEPS: {steps}   TOKENS: {tokens['total_tokens']} "
                 f"(prompt {tokens['prompt_tokens']}, completion {tokens['completion_tokens']})")
    lines.append(f"ANSWER: {answer}")
    trace = "\n".join(lines)

    if verbose:
        print(trace)

    path = None
    if save:
        path = save_trace(trace, tag)
        if verbose:
            print(f"\n[saved] {path}")
    return {"answer": answer, "steps": steps, "tokens": tokens,
            "outcome": outcome, "trace": trace, "path": path}


def next_trace_number():
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    used = [int(p.stem.split("_")[1]) for p in EVIDENCE_DIR.glob("trace_*.txt")
            if p.stem.split("_")[1].isdigit()]
    return max(used, default=0) + 1


def save_trace(trace, tag=None):
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    n = next_trace_number()
    suffix = f"_{tag}" if tag else ""
    path = EVIDENCE_DIR / f"trace_{n}{suffix}.txt"
    path.write_text(trace + "\n", encoding="utf-8")
    return path


# --- The six lab questions (steps 4 and 5) -------------------------------
QUESTIONS = [
    ("budget", "I have GHS 1,200. I want 4 bags of rice at GHS 185 each and "
               "3 gallons of oil at GHS 95 each. How much will I have left?"),
    ("both_tools_1", "Give me a one-sentence summary of Makola Market from "
                     "Wikipedia, and tell me what 7 bags of tomatoes at GHS 140 "
                     "each will cost."),
    ("both_tools_2", "Summarise the Ghana cedi from Wikipedia in one sentence, "
                     "and work out 2500 - 3*450."),
    ("missing_page", "What does Wikipedia say about the 'Kwame Nkrumah "
                     "University of dcit403'?"),
    ("no_tool", "In one sentence, what is a reactive agent?"),
    ("badly_worded", "bag rice 185 4x plus oil 95 3x minus 1200?? leftover"),
    ("runaway", "Keep improving the answer to 4*185 + 3*95 forever."),
]


def run_suite(model=None, max_steps=6, temperature=0):
    load_dotenv()
    results = []
    for qid, question in QUESTIONS:
        print("\n" + "#" * 70 + f"\n# {qid}\n" + "#" * 70)
        steps = 3 if qid == "runaway" else max_steps
        r = run_agent(question, max_steps=steps, model=model,
                      temperature=temperature, tag=qid)
        results.append((qid, r))
        time.sleep(3)  # stay inside the free-tier requests-per-minute limit
    print("\n\nSUMMARY")
    for qid, r in results:
        print(f"{qid:14s} outcome={r['outcome']:11s} steps={r['steps']} "
              f"tokens={r['tokens']['total_tokens']:5d} "
              f"answer={(r['answer'] or '')[:60]}")
    return results


def main():
    ap = argparse.ArgumentParser(description="Lab 2 ReAct agent")
    ap.add_argument("--question", help="one question to run")
    ap.add_argument("--suite", action="store_true", help="run the six lab questions")
    ap.add_argument("--max-steps", type=int, default=6)
    ap.add_argument("--temperature", type=float, default=0)
    ap.add_argument("--model", help="override LLM_MODEL")
    ap.add_argument("--no-save", action="store_true")
    args = ap.parse_args()

    load_dotenv()

    if args.suite:
        run_suite(model=args.model, max_steps=args.max_steps,
                  temperature=args.temperature)
        return

    if not args.question:
        ap.error("give --question '...' or --suite")

    run_agent(args.question, max_steps=args.max_steps, model=args.model,
              temperature=args.temperature, save=not args.no_save)


if __name__ == "__main__":
    main()
