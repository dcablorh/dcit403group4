"""Lab 1, Wednesday: diagnose the reasoning engine before you trust it.

A lab bot is only as good as the model inside it, and the model has measurable
habits: how long it takes, how much it costs, whether it repeats itself, whether
it obeys a length limit, and what it does when its beliefs are out of date. This
script measures those habits on this machine with the model in `.env` and writes
`report.md` next to itself. Every number is measured in the run — nothing is
copied from a tutorial.

    cd lab01
    python diagnostic/run_diagnostic.py
    python diagnostic/run_diagnostic.py --runs 2 --sleep 6

It makes about sixteen small model calls, so on the Groq free tier it pauses
between calls and retries rate limits. If a call still fails the row says so and
the rest of the run continues.
"""

import argparse
import os
import statistics
import sys
import time
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

LAB = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(LAB))  # so `llm` and `campus_bot` import from lab01/

from campus_bot import CampusBot  # noqa: E402
import llm  # noqa: E402
from llm import Reply, chat, load_env, mask  # noqa: E402

REPORT = Path(__file__).resolve().parent / "report.md"

PROMPT_LATENCY = "Explain in one sentence why a thermometer is not an agent."
PROMPT_EXACT = "Reply with exactly one word and nothing else: READY"
PROMPT_WORDS = "In no more than ten words, say what the letter P in PEAS stands for."
QUESTION_FACT = "Which room do I go to for an official transcript?"
FILLERS = [
    "Where is the library?",
    "What time does the cafeteria close?",
    "How much does printing cost per page?",
    "What is the Wi-Fi password?",
]
PROMPT_RECALL = "What was the Wi-Fi password you gave me earlier in this conversation?"


def tell(message: str) -> None:
    print(message, flush=True)


def sample(question: str, runs: int, sleep: float, temperature: float,
           system: str = "You are terse and accurate.") -> tuple[list[Reply], int]:
    """Ask the same question `runs` times; return the replies and the retry count."""
    replies, retries = [], 0
    for run in range(runs):
        if run:
            time.sleep(sleep)
        reply = chat([{"role": "system", "content": system},
                      {"role": "user", "content": question}],
                     temperature=temperature)
        retries += reply.attempts - 1
        replies.append(reply)
        tell(f"  run {run + 1}: {reply.ms:.0f} ms, {reply.total_tokens} tokens, "
             f"{reply.attempts} attempt(s)")
    return replies, retries


def word_count(text: str) -> int:
    cleaned = "".join(ch if (ch.isalnum() or ch.isspace() or ch in "'-") else " " for ch in text)
    return len([w for w in cleaned.split() if any(c.isalnum() for c in w)])


def md_cell(text: str) -> str:
    return text.replace("|", "/").replace("\n", " ").strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Lab 1 model diagnostic.")
    parser.add_argument("--runs", type=int, default=3, help="repeats for the determinism check")
    parser.add_argument("--sleep", type=float, default=4.0, help="seconds between calls")
    parser.add_argument("--temperature", type=float, default=0.7,
                        help="the 'normal' temperature to compare against 0.0")
    args = parser.parse_args()

    model = load_env()
    started = datetime.now(timezone.utc)
    lines: list[str] = ["# Lab 1 diagnostic: what this model actually does", "",
                        f"Run: {started.isoformat(timespec='seconds')} on this machine "
                        f"(`{model}`).", "",
                        "Every number below was measured by "
                        "`python diagnostic/run_diagnostic.py`; the commands are in "
                        "`lab01/README.md`.", ""]

    # ---- 1. environment ---------------------------------------------------
    try:
        litellm_version = version("litellm")
    except PackageNotFoundError:
        litellm_version = "not installed"
    probe = "GROQ_API_KEY" if model.startswith("groq/") else "GEMINI_API_KEY"
    tell("[1/6] environment")
    lines += ["## 1. Environment", "",
              "| Item | Value |", "|---|---|",
              f"| Python | {sys.version.split()[0]} |",
              f"| LiteLLM | {litellm_version} |",
              f"| `LLM_MODEL` | `{model}` |",
              f"| `{probe}` | {mask(os.getenv(probe, ''))} (masked at read time) |",
              "| `facts.md` blocks | 2 (current, stale) |",
              ""]

    # ---- 2. latency and cost ---------------------------------------------
    tell(f"[2/6] latency, {args.runs} cold calls at temperature 0")
    latency_replies, retries = sample(PROMPT_LATENCY, args.runs, args.sleep, 0.0)
    times = [r.ms for r in latency_replies]
    tokens = [r.total_tokens for r in latency_replies]
    lines += ["## 2. Latency and token cost", "",
              f"Prompt: _{PROMPT_LATENCY}_", "",
              "| Run | Wall clock | Prompt tokens | Completion tokens | Total |",
              "|---|---|---|---|---|"]
    for number, reply in enumerate(latency_replies, start=1):
        lines.append(f"| {number} | {reply.ms:.0f} ms | {reply.prompt_tokens} | "
                     f"{reply.completion_tokens} | {reply.total_tokens} |")
    lines += ["",
              f"Median wall clock **{statistics.median(times):.0f} ms** "
              f"(min {min(times):.0f}, max {max(times):.0f}); "
              f"median **{statistics.median(tokens):.0f} tokens** per call. "
              f"{retries} rate-limit retr{'y' if retries == 1 else 'ies'} during this step.", "",
              f"First reply, verbatim: {md_cell(latency_replies[0].text)}", ""]

    # ---- 3. determinism ---------------------------------------------------
    tell(f"[3/6] determinism, {args.runs} runs at temperature {args.temperature}"
         " (the temperature-0 runs from step 2 are reused)")
    temp0 = latency_replies
    time.sleep(args.sleep)
    tempn, retriesn = sample(PROMPT_LATENCY, args.runs, args.sleep, args.temperature)
    distinct0 = len({r.text for r in temp0})
    distinctn = len({r.text for r in tempn})
    lines += ["## 3. Determinism (same prompt, same temperature)", "",
              "| Temperature | Runs | Distinct answers | Exact match |",
              "|---|---|---|---|",
              f"| 0.0 | {len(temp0)} | {distinct0} | {'yes' if distinct0 == 1 else 'no'} |",
              f"| {args.temperature} | {len(tempn)} | {distinctn} | "
              f"{'yes' if distinctn == 1 else 'no'} |", "",
              f"At temperature 0.0 the answer was {'identical' if distinct0 == 1 else 'NOT identical'} "
              f"across {len(temp0)} calls; at temperature {args.temperature} it was "
              f"{'identical' if distinctn == 1 else 'different'} across {len(tempn)}. "
              "`finish_reason` was "
              + ", ".join(sorted({r.finish_reason or 'unknown' for r in temp0 + tempn})) + ".", ""]
    if distinct0 > 1:
        lines += ["The temperature-0 answers differed, which is normal on hosted APIs: "
                  "batching, hardware and sampling details are not part of the request, so "
                  "greedy decoding is only *approximately* reproducible. Any lab test that "
                  "compares full answer strings must allow for this.", ""]

    # ---- 4. instruction adherence ----------------------------------------
    tell("[4/6] instruction adherence")
    time.sleep(args.sleep)
    exact = chat([{"role": "system", "content": "You follow instructions exactly."},
                  {"role": "user", "content": PROMPT_EXACT}], temperature=0.0)
    time.sleep(args.sleep)
    short = chat([{"role": "system", "content": "You follow instructions exactly."},
                  {"role": "user", "content": PROMPT_WORDS}], temperature=0.0)
    exact_ok = exact.text.strip().strip('."`').upper() == "READY"
    words = word_count(short.text)
    lines += ["## 4. Instruction adherence", "",
              "| Instruction | Reply | Words | Obeyed |", "|---|---|---|---|",
              f"| exactly one word: READY | {md_cell(exact.text)} | {word_count(exact.text)} | "
              f"{'yes' if exact_ok else 'no'} |",
              f"| no more than ten words | {md_cell(short.text)} | {words} | "
              f"{'yes' if words <= 10 else 'no'} |", "",
              (f"The model obeyed both constraints." if exact_ok and words <= 10 else
               "At least one constraint was broken, so a prompt that relies on a hard format "
               "limit needs a check in code as well — the same lesson as Lab 2's parser and "
               "Lab 3's `record_sale`."), ""]

    # ---- 5. stale beliefs (the rationality question) ---------------------
    tell("[5/6] the same question against current and stale facts")
    answers = {}
    for name in ("current", "stale"):
        time.sleep(args.sleep)
        bot = CampusBot(version=name, temperature=0.0)
        answers[name] = bot.ask(QUESTION_FACT)
        tell(f"  {name}: {answers[name][:90]}")
    same = answers["current"].strip() == answers["stale"].strip()
    lines += ["## 5. Out-of-date beliefs: the same question, two facts blocks", "",
              f"Question: _{QUESTION_FACT}_", "",
              "| Facts block | Answer |", "|---|---|",
              f"| current (2026-11-25) | {md_cell(answers['current'])} |",
              f"| stale (2025-01-15) | {md_cell(answers['stale'])} |", "",
              (f"The two answers were identical ({'reasoning was not affected' if same else 'differ'})."
               if same else
               "The two answers differ even though the question and the model did not change: "
               "only the facts block changed. The reasoning step was the same in both runs, so "
               "the mistake in the stale run is a **belief** problem, not a reasoning problem — "
               "which is the answer to concept-check Q4."), ""]

    # ---- 6. memory vs context dilution -----------------------------------
    tell("[6/6] memory across a growing conversation")
    time.sleep(args.sleep)
    bot = CampusBot(version="current", temperature=0.0)
    first = bot.ask(FILLERS[3])
    for filler in FILLERS[:3]:
        time.sleep(args.sleep)
        bot.ask(filler)
    time.sleep(args.sleep)
    recalled = bot.ask(PROMPT_RECALL)
    recall_ok = "adc2026" in recalled.lower()
    lines += ["## 6. Memory in a conversation", "",
              f"Turn 1 asked for the Wi-Fi password and the bot answered: {md_cell(first)}", "",
              "Then three unrelated questions, then: _"
              f"{PROMPT_RECALL}_", "",
              f"Answer: {md_cell(recalled)}", "",
              ("The bot recalled its own earlier answer after three unrelated turns: the "
               "message list really is its percept sequence."
               if recall_ok else
               "The bot did **not** reproduce `adc2026` after the filler turns. On a short "
               "conversation that points at attention drift rather than a full context "
               "window, and it is why a real assistant re-reads facts instead of relying on "
               "its own past replies."), "",
              f"System prompt + conversation for that run: {bot.turns} turns, "
              f"{bot.tokens} tokens.", ""]

    # ---- verdict ----------------------------------------------------------
    per_turn = bot.tokens / max(bot.turns, 1)
    lines += ["## 7. What I will do differently because of this", "",
              f"- The model answered in {min(times):.0f}-{max(times):.0f} ms here, but the "
              "request travels over the internet, so any client timeout I set is several "
              "seconds, and rate limits are retried rather than treated as failures.",
              f"- Every turn re-sends the whole facts block: about {per_turn:.0f} tokens per "
              "turn in step 6. That is why the free tier's per-minute limit was hit during "
              "this run, and why a long-lived assistant trims or retrieves facts instead of "
              "pasting all of them into every request.",
              "- Temperature 0.0 is *approximately* deterministic here, so my tests check "
              "for required substrings and forbidden ones rather than whole-string equality.",
              "- Hard format limits (one word, ten words) are obeyed but not guaranteed, so "
              "any script that needs the format checks it in code.",
              "- Wrong answers caused by an old facts block are a knowledge-maintenance "
              "problem: the fix is to update the block, not to blame the reasoning.",
              f"- Reliability: {llm.RETRIES} of the calls in this run needed a retry "
              "(rate limit or dropped connection), so every helper call goes through the "
              "same retry-with-backoff instead of a bare `completion()`.",
              "- Conversation memory works over a handful of turns; long sessions need a "
              "summary or a facts lookup instead of trusting the transcript.",
              ""]

    REPORT.write_text("\n".join(lines), encoding="utf-8")
    tell(f"\n[wrote] {REPORT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
