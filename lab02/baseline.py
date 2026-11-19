"""Step 1 baseline: the same model, the same questions, no tools.

This is the control for the ReAct experiment. The model is asked the budget
question three times and two factual questions once each. Answers are saved to
evidence/baseline.md and the arithmetic is auto-marked by looking for the
correct value (175) in the reply; the factual ones are marked by hand because
a wrong fact can look confident.

    python baseline.py            # needs a real key
"""

import argparse
import os
import re
import sys
from pathlib import Path

# Windows consoles are cp1252 by default; model replies contain narrow and
# non-breaking spaces that would crash print(). Never fail on output encoding.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv

EVIDENCE_DIR = Path(__file__).resolve().parent / "evidence"
EVIDENCE_DIR.mkdir(exist_ok=True)
OUT = EVIDENCE_DIR / "baseline.md"

BUDGET_Q = ("I have GHS 1,200. I want 4 bags of rice at GHS 185 each and "
            "3 gallons of oil at GHS 95 each. How much will I have left?")
FACT_Q = [
    ("What is the capital town of the Bono East Region of Ghana?", "Techiman"),
    ("In what year was the Ghana cedi redenominated (1 new cedi = 10,000 old cedis)?", "2007"),
]

SYSTEM = "You are a helpful market assistant. Answer in one or two sentences."


def ask(question, temperature):
    from litellm import completion

    resp = completion(
        model=os.getenv("LLM_MODEL", "groq/openai/gpt-oss-20b"),
        messages=[{"role": "system", "content": SYSTEM},
                  {"role": "user", "content": question}],
        temperature=temperature,
    )
    usage = getattr(resp, "usage", None)
    return clean(resp.choices[0].message.content.strip()), getattr(usage, "total_tokens", 0)


def clean(text):
    """Normalise exotic spaces so console output and the markdown file are safe."""
    for bad, good in ((" ", " "), (" ", " "), (" ", " "),
                      (" ", " "), ("‑", "-"), ("–", "-"),
                      ("—", "-"), ("‘", "'"), ("’", "'"),
                      ("“", '"'), ("”", '"')):
        text = text.replace(bad, good)
    return text


def looks_right_budget(text):
    """The right answer contains 175 (and must not contain 1,380 + 175 confusion)."""
    numbers = {int(n) for n in re.findall(r"\d[\d,]*", text.replace(",", ""))}
    return 175 in numbers and 1380 not in numbers


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--temperature", type=float, default=0.7)
    args = ap.parse_args()
    load_dotenv()
    OUT.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    tokens = 0
    jobs = [("budget", BUDGET_Q, 175)] * 3 + [("factual", q, None) for q, _ in FACT_Q]

    for attempt, (kind, question, expected) in enumerate(jobs, start=1):
        try:
            answer, used = ask(question, args.temperature)
        except Exception as e:
            answer, used = f"[call failed: {type(e).__name__}: {e}]", 0
        tokens += used
        if kind == "budget":
            verdict = "arithmetic correct" if looks_right_budget(answer) else "arithmetic WRONG"
        else:
            verdict = "check the fact by hand"
        rows.append((attempt, kind, question, answer, verdict))

    lines = ["# Baseline: the model on its own, no tools", "",
              f"Model: `{os.getenv('LLM_MODEL', 'groq/openai/gpt-oss-20b')}`  "
              f"Temperature: {args.temperature}  Total tokens: {tokens}", "",
              "| # | Question | Answer | Mark |", "|---|---|---|---|"]
    for n, kind, q, a, verdict in rows:
        q2 = q.replace("|", "/")
        a2 = a.replace("\n", " ").replace("|", "/")
        lines.append(f"| {n} | {q2} | {a2} | {verdict} |")
    lines += ["", "## What this shows", "",
              "The budget question is asked three times. Count the rows marked",
              "'arithmetic WRONG': that is the baseline error rate that the ReAct",
              "loop has to beat. The two factual questions show how confident a",
              "wrong answer can sound; mark them by hand using a reliable source.", ""]
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"\n[saved] {OUT}")


if __name__ == "__main__":
    main()
