"""Check the environment before running the lab: keys, model name, one real call.

Run this first. It never prints a key, only its prefix and length.

    python check_env.py            # checks only
    python check_env.py --call     # also makes one small model call (a few tokens)
"""

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
load_dotenv(Path(__file__).resolve().parent / ".env")  # either location works

OK, WARN, BAD = "OK  ", "WARN", "FAIL"


def line(status, name, detail):
    print(f"[{status}] {name}: {detail}")


def mask(value):
    if not value:
        return "missing"
    return f"present (starts '{value[:4]}...', length {len(value)})"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--call", action="store_true", help="also make one model call")
    args = ap.parse_args()

    problems = 0
    model = os.getenv("LLM_MODEL", "")
    if model:
        line(OK, "LLM_MODEL", model)
    else:
        line(BAD, "LLM_MODEL", "not set - copy .env.example to .env")
        problems += 1

    groq = os.getenv("GROQ_API_KEY", "").strip()
    if groq:
        line(OK if groq.startswith("gsk_") else WARN, "GROQ_API_KEY", mask(groq))
        if not groq.startswith("gsk_"):
            print("       Groq keys start with gsk_. Check you pasted the whole key.")
    else:
        line(WARN, "GROQ_API_KEY", "missing - needed if LLM_MODEL is groq/...")

    gemini = os.getenv("GEMINI_API_KEY", "").strip()
    if gemini:
        line(OK, "GEMINI_API_KEY", mask(gemini))
    else:
        line(WARN, "GEMINI_API_KEY", "missing - only needed for the backup model")

    needed = model.split("/")[0] if model else ""
    key_for_model = {"groq": groq, "gemini": gemini}.get(needed, "")
    if model and not key_for_model:
        line(BAD, "key for LLM_MODEL", f"LLM_MODEL is '{model}' but no {needed} key is set")
        problems += 1

    if args.call and model and key_for_model:
        print("\nMaking one small call (a few tokens)...")
        try:
            from litellm import completion
            # max_tokens must leave room for a reasoning model's thoughts:
            # tiny limits return an empty content field, not an error.
            resp = completion(model=model, messages=[
                {"role": "user", "content": "Reply with the single word: ready"}],
                temperature=0, max_tokens=300, timeout=60)
            content = resp.choices[0].message.content or ""
            tokens = getattr(resp, "usage", None)
            if content.strip():
                print(f"[{OK}] model reply: {content.strip()!r} "
                      f"(tokens used: {getattr(tokens, 'total_tokens', '?')})")
            else:
                print(f"[{WARN}] call succeeded but content was empty - "
                      f"give the model more max_tokens")
        except Exception as e:
            print(f"[{BAD}] call failed: {type(e).__name__}: {e}")
            problems += 1

    print()
    if problems:
        print(f"Not ready: {problems} problem(s). Fix them, then run this again.")
        return 1
    print("Environment ready. Next: python baseline.py && python react_agent.py --suite")
    return 0


if __name__ == "__main__":
    sys.exit(main())
