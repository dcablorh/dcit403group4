"""Tests for parse(). Run: python test_parser.py  (no API key needed).

Every case here is a reply shape that a real model has produced, or a shape the
manual's single regex cannot handle. The output is saved to
evidence/parser_tests.txt so the failure analysis in the report has evidence.
"""

from pathlib import Path

from react_agent import ACTION_RE, parse

CASES = [
    ("exact format from the prompt",
     "Thought: compute the total.\nAction: calculator\nAction Input: 4*185 + 3*95",
     ("calculator", "4*185 + 3*95")),

    ("Windows line endings and extra spaces",
     "Thought: compute.\r\nAction:  calculator \r\n  Action Input:   1200 - 1025  ",
     ("calculator", "1200 - 1025")),

    ("both fields on one line (manual regex fails)",
     "Thought: compute.\nAction: calculator Action Input: 1200 - 1025",
     ("calculator", "1200 - 1025")),

    ("model leaks its own Observation (stop= did not hold)",
     "Thought: compute.\nAction: calculator\nAction Input: 4*185\nObservation: 740",
     ("calculator", "4*185")),

    ("tool name capitalised by the model",
     "Thought: look it up.\nAction: Wiki_Lookup\nAction Input: Makola Market",
     ("wiki_lookup", "Makola Market")),

    ("answer wrapped in backticks",
     "Thought: look it up.\nAction: wiki_lookup\nAction Input: `Makola Market`",
     ("wiki_lookup", "Makola Market")),

    ("final answer label instead of finish",
     "Thought: done.\nFinal Answer: You will have GHS 175 left.",
     ("finish", "You will have GHS 175 left.")),

    ("finish with a newline before the answer",
     "Thought: done.\nAction: finish\nYou will have GHS 175 left.",
     ("finish", "You will have GHS 175 left.")),

    ("whole ReAct transcript in one reply (gpt-oss-20b does this)",
     "Thought: Compute the total.\nAction: calculator\nAction Input: 4*185 + 3*95\n"
     "\nThought: Subtract from the budget.\nAction: calculator\n"
     "Action Input: 1200 - 1025\n\nThought: Answer.\nAction: finish\n"
     "Action Input: GHS 175",
     ("calculator", "4*185 + 3*95")),

    ("future steps leaked, tool input is text not a number",
     "Thought: Look it up.\nAction: wiki_lookup\nAction Input: Makola Market  \n"
     "\nThought: Then cost it.\nAction: calculator\nAction Input: 7*140",
     ("wiki_lookup", "Makola Market")),

    ("prose, no Action line at all (must return None)",
     "I think the answer is 175 but I am not certain.",
     (None, None)),

    ("empty reply (must return None)",
     "",
     (None, None)),
]


def main():
    out = ["Parser tests: manual regex vs the tolerant parser", "=" * 60]
    failures = 0
    for name, text, expected in CASES:
        got = parse(text)
        ok = got == expected
        failures += 0 if ok else 1
        # what the lab manual's single regex does with the same reply
        m = ACTION_RE.search(text)
        manual = (m.group(1).strip(), m.group(2).strip()) if m else (None, None)
        out.append(f"[{'PASS' if ok else 'FAIL'}] {name}")
        out.append(f"        input        : {text!r}")
        out.append(f"        manual regex : {manual}")
        out.append(f"        expected     : {expected}")
        out.append(f"        got          : {got}")
    out.append("=" * 60)
    out.append(f"{len(CASES) - failures}/{len(CASES)} passed")
    report = "\n".join(out)
    print(report)
    path = Path(__file__).resolve().parent / "evidence" / "parser_tests.txt"
    path.parent.mkdir(exist_ok=True)
    path.write_text(report + "\n", encoding="utf-8")
    print(f"\n[saved] {path}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
