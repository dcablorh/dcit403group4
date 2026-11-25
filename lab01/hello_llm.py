"""Lab 1, step 1: the smallest thing that is still an agent loop.

One message in, one message out. This file adds nothing to the model call on
purpose: it prints the request, the reply and what the call cost, so that step 3
(`campus_bot.py`) can add memory and a facts block on top of a thing you have
already seen work.

    python hello_llm.py
    python hello_llm.py --prompt "Explain PEAS in one sentence."
    python hello_llm.py --temperature 0.7 --runs 3 --save evidence/hello_llm.txt
"""

import argparse
import sys
from pathlib import Path

from llm import chat, env_summary

DEFAULT_PROMPT = "In two sentences, what is an agent in artificial intelligence?"
DEFAULT_SYSTEM = "You are a helpful teaching assistant for a first AI course. Be brief."


def main() -> int:
    parser = argparse.ArgumentParser(description="Your first LLM call.")
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    parser.add_argument("--system", default=DEFAULT_SYSTEM)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--max-tokens", type=int, default=None)
    parser.add_argument("--runs", type=int, default=1,
                        help="ask the same question N times to see what temperature changes")
    parser.add_argument("--save", type=Path, default=None,
                        help="also write the transcript to this file")
    args = parser.parse_args()

    lines = env_summary() + [
        f"# temperature: {args.temperature}   runs: {args.runs}"
        f"   max_tokens: {args.max_tokens}",
        "",
        f"SYSTEM: {args.system}",
        f"USER  : {args.prompt}",
        "",
    ]
    print("\n".join(lines))

    total = 0
    for run in range(1, args.runs + 1):
        reply = chat(
            [{"role": "system", "content": args.system},
             {"role": "user", "content": args.prompt}],
            temperature=args.temperature,
            max_tokens=args.max_tokens,
        )
        total += reply.total_tokens
        block = [f"--- run {run} " + "-" * 60,
                 f"ASSISTANT: {reply.text}",
                 reply.as_row() + f"  finish={reply.finish_reason}"
                 + (f"  retries={reply.attempts - 1}" if reply.attempts > 1 else ""),
                 ""]
        print("\n".join(block))
        lines += block

    summary = [f"# total tokens for {args.runs} run(s): {total}"]
    print("\n".join(summary))
    lines += summary

    if args.save:
        args.save.parent.mkdir(parents=True, exist_ok=True)
        args.save.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"\n[saved] {args.save}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
