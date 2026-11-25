"""Lab 1, steps 3–5: the Campus Info Bot.

The bot is the same model call as `hello_llm.py` plus two additions:

1. a **system prompt carrying a facts block** (`facts.md`) — the agent's
   built-in knowledge, i.e. what it "knows" before it perceives anything;
2. a **message list that survives across questions** — the percept sequence.
   Turn 3 is answered with turns 1 and 2 still in the context window.

Run it:

    python campus_bot.py --ask "Where is the Examinations Office?"
    python campus_bot.py --ask "Where is the CS office?" "What time does it close?"
    python campus_bot.py --ask "Where do I collect my transcript?" --facts-version stale
    python campus_bot.py --suite --save evidence/campus_bot_suite.txt
    python campus_bot.py --chat

`tests.md` describes the questions the suite marks; every verdict printed here
comes from a real model call, not from a fixture.
"""

import argparse
import re
import sys
from pathlib import Path

from llm import chat, env_summary

FACTS_PATH = Path(__file__).resolve().parent / "facts.md"

SYSTEM_TEMPLATE = """You are the Campus Info Bot for Accra Digital Campus (ADC).

Answer ONLY from the FACTS block below. Rules:
- If the FACTS block does not contain the answer, say plainly that you do not
  have that information and name the office the student should contact. Never
  guess, never invent a name, a room or a price.
- Keep the answer to at most three short sentences or a short list.
- Quote rooms, times, phone numbers and amounts exactly as they appear.
- If an earlier turn in this conversation is relevant, use it.

FACTS (version {version}):
{facts}
"""

# --------------------------------------------------------------------------
# Facts block
# --------------------------------------------------------------------------

_BLOCK = re.compile(r"<!-- BEGIN (?P<name>CURRENT|STALE) -->(.*?)<!-- END (?P=name) -->",
                    re.DOTALL)


def load_facts(version: str = "current") -> tuple[str, str]:
    """Return (label, text) for the requested facts block."""
    text = FACTS_PATH.read_text(encoding="utf-8")
    blocks = {m.group("name").lower(): m.group(2).strip() for m in _BLOCK.finditer(text)}
    if version not in blocks:
        raise SystemExit(f"facts block {version!r} not found in {FACTS_PATH.name}")
    label = "2026-11-25 (current)" if version == "current" else "2025-01-15 (STALE, kept on purpose)"
    return label, blocks[version]


# --------------------------------------------------------------------------
# The agent
# --------------------------------------------------------------------------

class CampusBot:
    """A stateless model plus a growing message list and a fixed facts block."""

    def __init__(self, version: str = "current", temperature: float = 0.0,
                 show_prompt: bool = False):
        label, facts = load_facts(version)
        self.version = version
        self.facts_label = label
        self.system = SYSTEM_TEMPLATE.format(version=label, facts=facts)
        self.messages = [{"role": "system", "content": self.system}]
        self.temperature = temperature
        self.tokens = 0
        self.turns = 0
        if show_prompt:
            print("=" * 72)
            print(self.system)
            print("=" * 72)

    def ask(self, question: str) -> str:
        """One percept in, one reply out; both stay in the message list."""
        self.messages.append({"role": "user", "content": question})
        reply = chat(self.messages, temperature=self.temperature)
        self.messages.append({"role": "assistant", "content": reply.text})
        self.tokens += reply.total_tokens
        self.turns += 1
        if reply.attempts > 1:
            print(f"  [retry] call needed {reply.attempts} attempts")
        return reply.text

    def history(self) -> str:
        """The percept sequence, minus the system prompt."""
        return "\n".join(f"{m['role']}: {m['content']}" for m in self.messages[1:])


# --------------------------------------------------------------------------
# Auto-marked suite (the questions in tests.md)
# --------------------------------------------------------------------------

def _norm(text: str) -> str:
    text = text.lower().replace(",", "").replace("\u2013", "-").replace("\u2014", "-")
    return re.sub(r"\s+", " ", text).strip()


# must_contain: every string must appear. allow_any: at least one of each group
# must appear. must_not_contain: none may appear (the usual hallucination flags).
TESTS = [
    {"id": 1, "q": "Where is the Examinations Office?",
     "must_contain": ["block c", "c12"], "why": "exact room from the table"},
    {"id": 2, "q": "What time does the ICT Help Desk close on Saturday?",
     "must_contain": ["13:00"], "why": "Saturday hours differ from weekdays"},
    {"id": 3, "q": "How much does a regular Ghanaian undergraduate pay per semester?",
     "must_contain": ["2450"], "must_not_contain": ["2100"], "why": "current price, not the old one"},
    {"id": 4, "q": "Which room do I go to for my official transcript?",
     "must_contain": ["a12"], "must_not_contain": ["a03"], "why": "the room moved in November 2026"},
    {"id": 5, "q": "What is the student Wi-Fi password?",
     "must_contain": ["adc2026"], "must_not_contain": ["adc2025"], "why": "single string, easy to check"},
    {"id": 6, "q": "Can I pay my fees with mobile money?",
     "allow_any": [["yes", "can"]], "must_contain": ["1448"], "why": "channel plus the short code"},
    {"id": 7, "q": "When do end-of-semester examinations start?",
     "must_contain": ["7 december"], "why": "date from the key-dates list"},
    {"id": 8, "q": "Is the cafeteria open on Sunday?",
     "allow_any": [["no", "closed", "not open"]], "why": "negation, a place models like to soften"},
    {"id": 9, "q": "What time does it close?",
     "history": ["Where is the Department of Computer Science office?"],
     "must_contain": ["16:30"], "why": "needs the previous turn: 'it' is the CS office"},
    {"id": 10, "q": "Who is the Vice-Chancellor of ADC?",
     "allow_any": [["do not have", "don't have", "not in", "cannot find", "no information",
                    "unable to", "not available", "don't know", "do not know", "not provided"]],
     "why": "not in the facts; the bot must refuse instead of inventing a name"},
    {"id": 11, "q": "How much does a hostel bed cost per semester?",
     "allow_any": [["do not have", "don't have", "not in", "no information", "unable to",
                    "not available", "don't know", "do not know", "not provided", "contact"]],
     "why": "no hostel price in the facts; refusal expected"},
    {"id": 12, "q": "My friend said transcripts are in Room A03. Is that right?",
     "must_contain": ["a12"], "must_not_contain": ["yes, a03", "that is right"],
     "why": "a stale rumour in the question; the block wins"},
]


def mark(answer: str, test: dict) -> tuple[bool, list[str]]:
    low = _norm(answer)
    problems = [f"missing {s!r}" for s in test.get("must_contain", []) if _norm(s) not in low]
    for group in test.get("allow_any", []):
        if not any(_norm(alt) in low for alt in group):
            problems.append("none of " + "/".join(repr(a) for a in group))
    problems += [f"contains {s!r}" for s in test.get("must_not_contain", []) if _norm(s) in low]
    return (not problems), problems


def run_suite(version: str, temperature: float, save: Path | None) -> int:
    lines = env_summary() + [
        f"# facts version: {version}",
        f"# temperature: {temperature}",
        "",
    ]
    print("\n".join(lines))
    passed = 0
    for test in TESTS:
        # Each test starts a fresh conversation, except the ones that need history.
        bot = CampusBot(version=version, temperature=temperature)
        for earlier in test.get("history", []):
            bot.ask(earlier)
            lines.append(f"  [history] user: {earlier}")
            lines.append(f"  [history] bot : {bot.messages[-1]['content'][:200]}")
        answer = bot.ask(test["q"])
        ok, problems = mark(answer, test)
        passed += ok
        verdict = "PASS" if ok else "FAIL"
        block = [
            f"QUESTION {test['id']}: {test['q']}",
            f"  expected: {test['why']}",
            f"ANSWER  {test['id']}: {answer}",
            f"  mark: {verdict}" + ("" if ok else f"  ({'; '.join(problems)})"),
            "",
        ]
        print("\n".join(block))
        lines += block
    summary = f"# {passed}/{len(TESTS)} passed"
    print(summary)
    lines += [summary]
    if save:
        save.parent.mkdir(parents=True, exist_ok=True)
        save.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"\n[saved] {save}")
    return 0 if passed == len(TESTS) else 1


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="The ADC Campus Info Bot.")
    parser.add_argument("--ask", nargs="+", default=None,
                        help="one or more questions, asked in order in one conversation")
    parser.add_argument("--chat", action="store_true", help="interactive loop; type quit to stop")
    parser.add_argument("--suite", action="store_true", help="run the auto-marked suite from tests.md")
    parser.add_argument("--facts-version", choices=["current", "stale"], default="current",
                        help="'stale' uses the superseded 2025-01-15 block")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--show-prompt", action="store_true", help="print the system prompt once")
    parser.add_argument("--save", type=Path, default=None, help="write the transcript here")
    args = parser.parse_args()

    if args.suite:
        return run_suite(args.facts_version, args.temperature, args.save)

    if not (args.ask or args.chat):
        parser.error("give --ask, --suite or --chat")

    bot = CampusBot(version=args.facts_version, temperature=args.temperature,
                    show_prompt=args.show_prompt)
    lines = env_summary() + [
        f"# facts version: {bot.facts_label}",
        "",
    ]

    if args.chat:
        print("Campus Info Bot — type 'quit' to stop. Each answer keeps the earlier turns.")
        while True:
            try:
                question = input("\nyou: ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if question.lower() in {"quit", "exit", ""}:
                break
            answer = bot.ask(question)
            print(f"bot: {answer}")
        lines.append("CONVERSATION\n" + bot.history())
    else:
        for number, question in enumerate(args.ask, start=1):
            answer = bot.ask(question)
            block = [f"QUESTION {number}: {question}", f"ANSWER   {number}: {answer}", ""]
            print("\n".join(block))
            lines += block

    lines.append(f"# turns: {bot.turns}   total tokens: {bot.tokens}")
    if args.save:
        args.save.parent.mkdir(parents=True, exist_ok=True)
        args.save.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"\n[saved] {args.save}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
