# DCIT403 Lab 02 — Report

**Student name:** David Abban
**Student ID:** `<your ID>`
**Lab number and title:** Lab 2 — Architectures: A ReAct Agent From Scratch
**Lab repository link:** https://github.com/dcablorh/dcit403group4
**Date submitted:** `<date>`

## 1. Objective

The lab set out to build a ReAct agent in plain Python, with no framework, for a
fictional Makola Market trader who needs shopping costs worked out and quick
facts answered. The agent reasons in text, chooses between a safe calculator and
a Wikipedia lookup, and has to survive unparseable replies, unknown tools and
loops that never end.

## 2. Concept and Classical Root

The classical sense–think–act cycle separates perceiving, deciding and acting.
ReAct is a *hybrid* of the two older architectures. Its reactive half is the
rule "the next Action depends on the newest Observation": when a Wikipedia
lookup returns no page, the agent's next move changes immediately, so it is not
executing a plan fixed in advance. Its deliberative half is the `Thought` line,
which states a plan ("get the total cost, then subtract it from the budget")
that spans several steps.

In BDI terms the message list is the belief set (the question plus every
Observation so far), the trader's need is the desire, and the stated plan is the
intention, executed one tool call at a time and revised when an Observation
contradicts it. `Action: finish` discharges the intention; `max_steps` is the
guard when the agent never discharges it.

The point that separates this from a chatbot: **the model never executes
anything.** It writes text naming a tool; my code parses that text, runs the
Python function and feeds the result back as a new percept. The model decides
*what* to compute, the code computes. That is also why the call uses
`stop=["Observation:"]`: otherwise the model continues the transcript and
answers from a number that was never computed — a hallucinated percept.

## 3. Implementation

Four files in `lab02/`:

- `tools.py` — `calculator` walks the AST with an operator table, so no `eval`
  and no attribute access: `__import__('os')` returns `Error: Unsupported
  expression`. `wiki_lookup` calls the Wikipedia summary endpoint with a 10 s
  timeout, a User-Agent and an 800-character cut.
- `react_agent.py` — the system prompt (it contains the tool descriptions,
  because the tool list *is* part of the prompt), the parser and the loop.
- `baseline.py` — the same questions with no tools, for comparison.
- `test_parser.py` — reply shapes turned into regression tests.

Key decisions:

1. **Observations are appended as `user` messages**, so the model reads them as
   input from the world rather than as its own text.
2. **Every failure becomes an Observation.** The loop never raises because of
   model output; a bad reply earns a corrective message and still costs a step,
   so a confused model cannot loop for free.
3. **The parser keeps only the current step** (Section 5).
4. **`max_steps=6`**, and the run records `OUTCOME: max_steps` rather than
   pretending to have an answer.

The centre of the loop, abridged:

```python
while steps < max_steps:
    steps += 1
    reply, used = call_model(messages, model, temperature)
    messages.append({"role": "assistant", "content": reply})
    action, action_input = parse(reply)
    if action is None:          observation = CORRECTIVE_FORMAT
    elif action == "finish":    answer, outcome = action_input, "finish"; break
    elif action not in TOOLS:   observation = f"Unknown action '{action}'..."
    else:                       observation = TOOLS[action](action_input)
    messages.append({"role": "user", "content": f"Observation: {observation}"})
```

## 4. Evidence

**Baseline, no tools (`evidence/baseline.md`, model `groq/qwen/qwen3.8-27b`).**
The budget question was asked three times and answered wrongly every time: GHS
15, GHS 205 and GHS 65, against the correct GHS 175. The factual question "what
is the capital town of the Bono East Region?" was answered confidently and
wrongly as **Kintampo** (it is Techiman). Total 463 tokens.

**ReAct, same questions (`evidence/trace_1..8`).**

| Trace | Question type | Outcome | Steps | Tokens | Result |
|---|---|---|---|---|---|
| `trace_1_budget` | needs calculator | finish | 3 | 1,588 | GHS 175 — correct, calculator called twice |
| `trace_2_both_tools_1` | needs both tools | finish | 3 | 1,780 | Makola summary + GHS 980 |
| `trace_3_both_tools_2` | needs both tools | finish | 3 | 1,581 | cedi summary + 1,150 |
| `trace_4_missing_page` | unanswerable | finish | 2 | 1,076 | found KNUST and answered anyway (see Section 5) |
| `trace_5_no_tool` | needs no tool | finish | 6 | 4,061 | five wasted lookups, stopped at the limit |
| `trace_6_badly_worded` | malformed input | finish | 2 | 957 | GHS 175 — correct |
| `trace_7_runaway` | asked to loop forever | finish | 2 | 849 | answered and stopped |
| `trace_8_max_steps` | budget, limit set to 1 | max_steps | 1 | 428 | `OUTCOME: max_steps`, no fake answer |

So on this model ReAct turned 0/3 correct arithmetic into 3/3, and each number
in the answer can be traced to a calculator Observation. Excerpt:

```
Thought: Calculate the total cost of rice and oil.
Action: calculator
Action Input: 4*185 + 3*95
Observation: 1025
...
Action: finish
Action Input: You will have GHS 175 left. (4 bags of rice at GHS 185 = GHS 740; ...)
```

**Parser tests (`evidence/parser_tests.txt`).** 12 of 12 shapes parse, and the
manual's single regex is printed beside each case, so the two failures in
Section 5 are visible side by side.

*Caption:* the traces show the model deciding what to compute and the code doing
the computing; the baseline shows the same model getting the same sums wrong
when it has to compute them itself.

## 5. Failure and Fix

**What happened.** On the third step of the first real run, the calculator was
called with a paragraph instead of an expression:

```
Action: calculator
Action Input: 4*185 + 3*95  \n\n Thought: Subtract total cost ... \n
Action: calculator \n Action Input: 1200 - 1025 ...
```

The tool returned `Error: invalid syntax` and the run stalled.

**Why it happened.** The model wrote the *entire* ReAct transcript in one reply
— three Thought/Action blocks — instead of one step. The manual's regex,
`Action:\s*(\w+)\s*\nAction Input:\s*(.*)` with `DOTALL`, lets `(.*)` run to the
end of the reply, so the first tool input swallowed the next two steps. This is
the structural cost of a text protocol: the format is enforced by the prompt,
not by the API (contrast Lab 3, where the schema is enforced server-side), so
the parser is part of the agent function and must bound each field itself.

**The fix.** `_clean_input()` now cuts the tool input at the first line that
starts a new step — `Observation:`, `Thought:`, or `Action:` — so only the
current step can reach a tool. The captured reply became a regression test.

**The result.** `python test_parser.py` passes 12/12, and shows the difference
directly:

```
[PASS] whole ReAct transcript in one reply (gpt-oss-20b does this)
        manual regex : ('calculator', '4*185 + 3*95\n\nThought: Subtract ...')
        got          : ('calculator', '4*185 + 3*95')
```

After the fix, `trace_1_budget` calls the calculator twice with clean
expressions and returns the correct GHS 175. Two related failures were found the
same way and are recorded with their evidence: gpt-oss-20b refused the text
protocol entirely (`tool_use_failed`, `evidence/attempt_gptoss_tool_use_failed
.txt`), which is why this lab runs on `qwen3.8-27b`; and the model twice tried
to finish with arithmetic it had done in its head, so the loop now rejects such
a `finish` once and demands a calculator Observation.

What the fixes do **not** solve: in `trace_4_missing_page` the model silently
replaced the fictional "Kwame Nkrumah University of dcit403" with KNUST and
answered the corrected question, and in `trace_5_no_tool` it spent five lookups
on a definition it could answer directly. Both are judgement failures rather
than parse failures, and neither is fixed by the parser: the first needs a rule
(and a check) that an unanswerable question is reported as unanswerable, the
second needs a cheaper stopping test.

## 6. AI-Use Log

| Date | Lab | Tool | What I asked | What I used | What I changed or checked |
|---|---|---|---|---|---|
| 19 Nov 2026 | Lab 2 | free-pi (coding agent) | Read the Lab 2 manual and template and set up `lab02/` | A starting structure for `tools.py`, `react_agent.py`, `baseline.py`, `test_parser.py` | Read every file; wrote the parser fallback and the corrective-Observation branches myself; ran the tool checks and `test_parser.py` (12/12) |
| 19 Nov 2026 | Lab 2 | free-pi (coding agent) | "Why does my regex miss the Action line when both fields are on one line?" | The idea of searching the two fields independently | Wrote the fallback and proved with `test_parser.py` that the manual regex returns `(None, None)` while mine returns the action and input |
| 19 Nov 2026 | Lab 2 | free-pi (coding agent) | Why the calculator received a paragraph instead of an expression | The explanation that `DOTALL` let the input run past the field into the next steps | Bounded the input at the next `Thought:/Action:/Observation:` myself and added two regression tests |
| 19 Nov 2026 | Lab 2 | free-pi (coding agent) | Why Groq returned `tool_use_failed` | That gpt-oss-20b emits native tool calls even with no tools supplied | Confirmed the error on 7/7 questions, tried a corrective instruction, then switched the lab model to `qwen3.8-27b` and re-ran everything |
| 19 Nov 2026 | Lab 2 | free-pi (coding agent) | How to stop the model finishing with mental arithmetic | The suggestion to reject that `finish` in the loop rather than only in the prompt | Added the guardrail myself, then observed it fire and recorded the trace |

## 7. Project Link

**Team repository:** `<team repo URL>`
**My contribution this week:** `<one line; teams are formed in this week's Wednesday session>`
