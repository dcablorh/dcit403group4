# Lab 1 diagnostic: what this model actually does

Run: 2026-11-25T16:36:02+00:00 on this machine (`groq/qwen/qwen3.8-27b`).

Every number below was measured by `python diagnostic/run_diagnostic.py`; the commands are in `lab01/README.md`.

## 1. Environment

| Item | Value |
|---|---|
| Python | 3.13.3 |
| LiteLLM | 1.85.6 |
| `LLM_MODEL` | `groq/qwen/qwen3.8-27b` |
| `GROQ_API_KEY` | set (56 chars, value never written to disk) (masked at read time) |
| `facts.md` blocks | 2 (current, stale) |

## 2. Latency and token cost

Prompt: _Explain in one sentence why a thermometer is not an agent._

| Run | Wall clock | Prompt tokens | Completion tokens | Total |
|---|---|---|---|---|
| 1 | 937 ms | 36 | 25 | 61 |
| 2 | 1373 ms | 36 | 25 | 61 |
| 3 | 655 ms | 36 | 25 | 61 |

Median wall clock **937 ms** (min 655, max 1373); median **61 tokens** per call. 0 rate-limit retries during this step.

First reply, verbatim: A thermometer is not an agent because it passively measures temperature without possessing the capacity for autonomous decision-making or intentional action.

## 3. Determinism (same prompt, same temperature)

| Temperature | Runs | Distinct answers | Exact match |
|---|---|---|---|
| 0.0 | 3 | 1 | yes |
| 0.7 | 3 | 3 | no |

At temperature 0.0 the answer was identical across 3 calls; at temperature 0.7 it was different across 3. `finish_reason` was stop.

## 4. Instruction adherence

| Instruction | Reply | Words | Obeyed |
|---|---|---|---|
| exactly one word: READY | READY | 1 | yes |
| no more than ten words | Performance | 1 | yes |

The model obeyed both constraints.

## 5. Out-of-date beliefs: the same question, two facts blocks

Question: _Which room do I go to for an official transcript?_

| Facts block | Answer |
|---|---|
| current (2026-11-25) | Go to the Transcripts and Certificates office in Block A, Room A12. Bring your application form, student ID, and GHS 100.00. |
| stale (2025-01-15) | Go to the Transcripts and Certificates office in Block A, Room A03. |

The two answers differ even though the question and the model did not change: only the facts block changed. The reasoning step was the same in both runs, so the mistake in the stale run is a **belief** problem, not a reasoning problem — which is the answer to concept-check Q4.

## 6. Memory in a conversation

Turn 1 asked for the Wi-Fi password and the bot answered: The Wi-Fi password for the `ADC-STUDENT` network is `adc2026`.

Then three unrelated questions, then: _What was the Wi-Fi password you gave me earlier in this conversation?_

Answer: The Wi-Fi password for the `ADC-STUDENT` network is `adc2026`.

The bot recalled its own earlier answer after three unrelated turns: the message list really is its percept sequence.

System prompt + conversation for that run: 5 turns, 8009 tokens.

## 7. What I will do differently because of this

- The model answered in 655-1373 ms here, but the request travels over the internet, so any client timeout I set is several seconds, and rate limits are retried rather than treated as failures.
- Every turn re-sends the whole facts block: about 1602 tokens per turn in step 6. That is why the free tier's per-minute limit was hit during this run, and why a long-lived assistant trims or retrieves facts instead of pasting all of them into every request.
- Temperature 0.0 is *approximately* deterministic here, so my tests check for required substrings and forbidden ones rather than whole-string equality.
- Hard format limits (one word, ten words) are obeyed but not guaranteed, so any script that needs the format checks it in code.
- Wrong answers caused by an old facts block are a knowledge-maintenance problem: the fix is to update the block, not to blame the reasoning.
- Reliability: 0 of the calls in this run needed a retry (rate limit or dropped connection), so every helper call goes through the same retry-with-backoff instead of a bare `completion()`.
- Conversation memory works over a handful of turns; long sessions need a summary or a facts lookup instead of trusting the transcript.
