# Tests: what I asked the Campus Info Bot and what it did

The bot reads one facts block and answers from it. So the tests are not "did it
say something sensible" — that is unmarkable — they are three checkable kinds:

1. **Grounded** — the answer must contain the exact room / time / price /
   password from `facts.md`, and must not contain the *superseded* value.
2. **Refusal** — the question is deliberately outside the facts block, so the
   correct answer is a refusal plus the right office, not a plausible invention.
3. **Memory** — the answer only makes sense if an earlier turn is still in the
   message list.

Run and mark them with:

```bash
python campus_bot.py --suite --save evidence/campus_bot_suite.txt
```

Every row below was produced by a real model call (`groq/qwen/qwen3.8-27b`,
temperature 0.0, facts version 2026-11-25). The marking rules live in `TESTS` in
`campus_bot.py`, so a regression shows up as a FAIL line rather than a feeling.

## Suite results — 12/12 passed

| # | Question | Kind | Must see | Result |
|---|---|---|---|---|
| 1 | Where is the Examinations Office? | grounded | `Block C`, `C12` | PASS |
| 2 | What time does the ICT Help Desk close on Saturday? | grounded | `13:00` (not the weekday 17:00) | PASS |
| 3 | How much does a regular Ghanaian undergraduate pay per semester? | grounded | `2450`, not `2100` | PASS |
| 4 | Which room do I go to for my official transcript? | grounded | `A12`, not the old `A03` | PASS |
| 5 | What is the student Wi-Fi password? | grounded | `adc2026`, not `adc2025` | PASS |
| 6 | Can I pay my fees with mobile money? | grounded + yes | `1448` short code | PASS |
| 7 | When do end-of-semester examinations start? | grounded | `7 December` | PASS |
| 8 | Is the cafeteria open on Sunday? | negation | "no"/"closed" | PASS |
| 9 | (after "Where is the CS office?") What time does it close? | memory | `16:30` | PASS |
| 10 | Who is the Vice-Chancellor of ADC? | refusal | a "do not have" phrase, no invented name | PASS |
| 11 | How much does a hostel bed cost per semester? | refusal | a "do not have" phrase, points at Student Affairs | PASS |
| 12 | My friend said transcripts are in Room A03. Is that right? | stale trap | `A12`, must not agree with `A03` | PASS |

The verbatim answers are in `evidence/campus_bot_suite.txt`.

### What the three interesting rows actually said

- **#9 (memory)** — asked alone, "What time does it close?" has no referent. The
  bot answered *"The Department of Computer Science office closes at 16:30 on
  weekdays."* That is only possible because the previous question and answer were
  still in the message list. Delete the history and this row fails.
- **#10 (refusal)** — *"I do not have that information. Please contact the
  Registrar's office for this query."* The name of the Vice-Chancellor is not in
  the facts block and was not invented. This is the row a cheaper design (no
  facts block, "answer helpfully") fails: it produces a confident name.
- **#12 (stale trap)** — the wrong room was inside the *question*, which is how
  people really talk. *"No, that is incorrect. Transcripts and Certificates are
  located in Block A, Room A12."* The facts block beats the user's rumour.

## Extra experiment A: out-of-date facts (concept-check Q4)

Same bot, same question, only the facts block swapped:

```bash
python campus_bot.py --facts-version stale --ask "Where do I collect my official transcript?" \
  "How much does a regular Ghanaian undergraduate pay per semester?" \
  --save evidence/campus_bot_stale_facts.txt
python campus_bot.py --ask "Where do I collect my official transcript?" \
  "How much does a regular Ghanaian undergraduate pay per semester?" \
  --save evidence/campus_bot_current_facts.txt
```

| Facts block | Transcript answer | Fee answer |
|---|---|---|
| current (2026-11-25) | Block A, Room **A12** | GHS **2,450.00** |
| stale (2025-01-15) | Block A, Room **A03** | GHS **2,100.00** |

Both answers are wrong in the stale run and both are correct in the current run,
and the reasoning was identical in the two runs — the model followed the same
steps and quoted the block it was given. So the failure is a **belief** failure,
not a reasoning failure. The fix is to update the block (and to stamp it with a
version, which `facts.md` now does), not to change the model or the prompt.

## Extra experiment B: what temperature changes

```bash
python hello_llm.py --temperature 0.7 --runs 3 --save evidence/hello_llm_temp07.txt
```

Same prompt three times at 0.7: three different answers. At 0.0 the answers were
identical. Since the suite marks *content*, not wording, it is unaffected — but
it is the reason no test compares whole answer strings. The measured comparison
is in `diagnostic/report.md` §3.

## What these tests do NOT show

- They do not show the bot is correct about the real campus: the facts are
  fictional and the tests only check that the bot quotes them faithfully.
- They do not catch a model that answers a question *not in the suite* wrongly.
  Twelve questions is a smoke test, not coverage.
- They do not test more than one student at a time, a very long conversation, or
  a facts block too large for the context window.
