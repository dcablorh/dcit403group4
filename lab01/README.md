# Lab 1: Agents Then and Now: PEAS and Your First LLM Call

**Topic:** Agent definitions, PEAS, environment types, the LLM as reasoning engine

**Style:** Standalone, code

Instructions are in the DCIT 403 Laboratory Manual (version 2), Lab 1.

## Deliverables

- `hello_llm.py`, `peas.md`, `facts.md`, `campus_bot.py`, `tests.md`
- `concept_check.md`
- `evidence/` with at least one screenshot of a conversation
- `diagnostic/` (Wednesday)

Put outputs, traces, logs and screenshots in `evidence/`. Answer `concept_check.md` before the Wednesday session. Steps marked Independent in the manual are done on your own between the Thursday and Wednesday labs.

---

## What I built this week

The smallest agent that still deserves the name: one model call, one facts block,
one growing message list. No tools, no framework, no retrieval — those are Lab 2
and Lab 5.

| File | What it does | Lab step |
|---|---|---|
| `llm.py` | The one model call every script shares: LiteLLM, `clean()` for exotic spaces, retry-with-backoff on 429/connection errors, and a `Reply` with latency + token counts. Keys come from the environment, and `mask()` proves a key exists without printing it | setup |
| `hello_llm.py` | One message in, one message out: prints the request, the reply, milliseconds and prompt/completion/total tokens. `--runs` asks the same question N times so temperature has something to change | 1 |
| `facts.md` | The Campus Info Bot's whole world, as a fictional Accra Digital Campus: offices and rooms, hours, phones, fees, key dates, services. Two marked blocks — `CURRENT` (2026-11-25) and deliberately `STALE` (2025-01-15) — plus a changelog | 2 |
| `campus_bot.py` | The bot: facts block into the system prompt, message list kept across questions, `--ask`, `--chat`, `--suite`, `--facts-version stale`, `--show-prompt` | 3, 4 |
| `peas.md` | PEAS for the self-checkout machine (Q1), this bot and the Lab 3 pharmacy agent, then the environment-property table with a justification per cell | 2 |
| `tests.md` | Twelve questions in three kinds (grounded, refusal, memory), what each one is allowed to say, and the results of the real run — plus the stale-facts experiment and the temperature experiment | 5 |
| `diagnostic/run_diagnostic.py` | Wednesday: measures the reasoning engine instead of trusting it — environment, latency/tokens, determinism, instruction adherence, out-of-date beliefs, memory across a growing conversation. Writes `diagnostic/report.md` | Wednesday |
| `concept_check.md` | Part A answers | Part A |

### Run it

```bash
cd lab01
python hello_llm.py                                                     # step 1
python hello_llm.py --temperature 0.7 --runs 3                          # what temperature changes
python campus_bot.py --ask "Where is the Examinations Office?"          # step 3
python campus_bot.py --ask "Where is the CS office?" "What time does it close?"   # step 4, memory
python campus_bot.py --suite --save evidence/campus_bot_suite.txt       # step 5, 12 marked questions
python campus_bot.py --chat                                             # free conversation, type quit
python campus_bot.py --facts-version stale \
  --ask "Where do I collect my official transcript?"                    # Q4 experiment
python diagnostic/run_diagnostic.py --runs 3 --sleep 6                  # Wednesday
```

`LLM_MODEL` and `GROQ_API_KEY` come from `.env` at the repository root (Codespaces
secrets in the Codespace). Nothing in this folder reads a key from a file.

### How the bot is put together

```
system prompt  =  role + rules + the facts block   (built once, in CampusBot.__init__)
messages       =  [system] + every user question and every answer, in order
one turn       =  append the question -> completion(messages) -> append the reply
```

That is the whole agent. Two consequences worth stating because the lab asks for
them:

- The **facts block is built-in knowledge**, not a percept. It arrives at start-up
  and never changes during the run, so it behaves like the row of Russell &
  Norvig's table that says "what the world is like".
- The **message list is the percept sequence**. The model keeps no state between
  calls; anything dropped from `messages` is forgotten. `tests.md` question 9 only
  passes because the earlier turn is still there.

### Evidence

| File | From |
|---|---|
| `evidence/hello_llm.txt` | step 1: one call, with the request, the reply and the token counts |
| `evidence/hello_llm_temp07.txt` | extra experiment B: same question three times at temperature 0.7 — three different texts |
| `evidence/campus_bot_suite.txt` | step 5: the twelve questions in `tests.md`, each marked PASS/FAIL by the runner (12/12) |
| `evidence/campus_bot_conversation.txt` | a four-turn conversation, including a follow-up that only works if the previous turn is remembered |
| `evidence/conversation.html` | the same conversation rendered as a chat window (this is what the screenshot is taken from) |
| `evidence/first_conversation.png` | the screenshot the manual asks for: `conversation.html` rendered in a browser at 620 px wide, 2× scale |
| `evidence/campus_bot_current_facts.txt` | the transcript/fee questions against the current facts block (Room A12, GHS 2,450.00) |
| `evidence/campus_bot_stale_facts.txt` | the same questions against the stale block (Room A03, GHS 2,100.00) — the Q4 experiment |
| `diagnostic/report.md` | Wednesday: measured numbers for this model on this machine |

**Screenshot note.** `evidence/first_conversation.png` is `conversation.html`
rendered in a real browser (Chrome, headless, 620 px window at 2× scale). The
transcript it shows is the saved run in `campus_bot_conversation.txt`, which is a
real model run, not an illustration. If you re-run the conversation, regenerate
the page from the new transcript before taking a new screenshot.

### What the diagnostic measured

Median **~0.7–1.4 s** and **~61 tokens** for a one-sentence answer; temperature
0.0 gave the *same* text three times, temperature 0.7 gave three different texts;
both hard format limits (one word, ten words) were obeyed; the same question
against `current` and `stale` gave A12 and A03 with identical reasoning; and the
bot recalled its own Wi-Fi answer after three unrelated turns. The full tables
and the conclusions are in `diagnostic/report.md`.

The facts block is re-sent on every turn — about **1,600 tokens per turn** in the
five-turn memory run — so a long conversation is expensive and the Groq free tier
limits tokens per minute. That is why every script pauses between calls and
retries a 429 instead of losing the run.

### What I would fix next

- The bot answers from the whole facts block at once. Lab 5's retrieval is the
  answer for a block that no longer fits, and the diagnostic shows the cost of
  pasting it every turn.
- Nothing checks that `facts.md` is current. The version stamp and changelog are
  there for a human to read; an expiry check with a "last verified" date would
  have caught the A03 answer the experiment produced.
- `--chat` has no history limit: a long session grows until the context window
  ends it. A max-turns trim (and a visible notice when it trims) would be honest
  about forgetting.
