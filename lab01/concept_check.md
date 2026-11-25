# Lab 1: Agents Then and Now: PEAS and Your First LLM Call: Concept Check

Answer in your own words before the Wednesday session (independent work). Your answers feed Section 2 of your lab report (Concept and classical root).

## Q1. Give the PEAS description of a self-checkout machine at a supermarket.

**Performance measure.** Value of goods paid for before the customer leaves; items
billed correctly; false theft alarms per hundred customers; average checkout time;
abandonments; losses from items that leave unpaid.

**Environment.** The till lane — goods and their barcodes, the bagging area and
its scale, the customer, the card/mobile-money network, the store's price
database, and the attendant on duty.

**Actuators.** Screen prompts and menus, the scanner, the speaker (beeps and
spoken prompts), the bill itself (lines and prices added), the payment request,
the receipt printer, and the lane lock / "wait for attendant" light.

**Sensors.** Barcode scanner, weight scale under the bagging area, card reader and
PIN pad, touch screen, cash acceptor where fitted, the age-verification flag for
restricted goods, and the attendant's override key.

The full version, with the environment properties, is the first table in
`peas.md`. The thing I had to get right was that the performance measure contains
two goals that fight each other — "nothing leaves unpaid" and "the queue moves" —
which is why the machine escalates to a human instead of deciding everything.

## Q2. Is the Campus Info Bot's environment episodic or sequential? Justify your answer using what the bot needs to remember.

**Sequential.** The quality of the answer to a question depends on the questions
already answered, so the agent's experience is not a series of independent
episodes.

The concrete evidence is question 9 in `tests.md`. Asked on its own, "What time
does it close?" has nothing to attach "it" to — the bot would have to refuse or
guess. Asked straight after "Where is the Department of Computer Science office?",
the bot answered *"The Department of Computer Science office closes at 16:30 on
weekdays."* To do that it needed the earlier question (to resolve "it"), its own
earlier answer (to know the office is in Block B, Room B11), and the facts block
(to get the closing time) — three things, two of which only exist because of the
previous turn. My bot keeps them by never clearing `messages`, which is why
`campus_bot.py --ask "q1" "q2"` behaves differently from two separate runs of
`--ask "q2"`.

A qualification: the *facts block* being static does not make the environment
episodic. The environment is sequential because of the conversation, and the
facts block is best described as the agent's built-in knowledge rather than a
percept.

## Q3. Which part of an LLM agent plays the role of the percept sequence?

The **message list that is re-sent on every call** — the conversation turns plus
any tool output, sitting in the context window. In a classical agent the percept
sequence is everything the sensors have delivered so far and the agent program
keeps its own state; an LLM agent has no state between calls. Whatever is not in
the messages at the moment of the call does not exist for the model. So the
"percept sequence" is literally the prompt: in `campus_bot.py`, the user turns
plus the assistant replies, in `lab02`'s ReAct loop the `Observation:` lines my
code wrote, and in Lab 3 the `tool` messages.

Two things that are *not* the percept sequence, and are easy to confuse with it:

- **The weights.** They are the agent's prior/built-in knowledge ("what a
  transcript usually is"), not this run's experience — closer to the classical
  agent program than to its percepts.
- **`facts.md` in the system prompt.** It is knowledge the agent starts with,
  fixed for the run. It shapes every answer but it is not sensed, so it behaves
  like the built-in knowledge in Russell & Norvig's table-based agent.

The practical consequence: "memory" for an LLM agent is just text that is still
in the window. When the conversation is trimmed, the agent's memory of it is gone
— there is no separate store to consult.

## Q4. An agent gives a wrong office location because its facts block was out of date. Was it irrational? Explain.

**No — not irrational, but wrong.** Rationality is doing the right thing *given
the percept sequence and the built-in knowledge available*. The bot answered the
way any careful reader of the 2025-01-15 block would have: it quoted the block
exactly, refused where the block was silent, and invented nothing. The
information it needed (that transcripts moved from A03 to A12) was never in its
percepts, so no amount of better reasoning could have produced it.

I ran the experiment rather than asserting it (`tests.md`, extra experiment A).
Same model, same question, same prompt structure, same temperature — I only
swapped the facts block:

| Facts block | Answer for the transcript office |
|---|---|
| current (2026-11-25) | Block A, Room **A12** |
| stale (2025-01-15) | Block A, Room **A03** |

The step-by-step reasoning was identical in both runs; only the premise differed.
That makes it a **belief** failure, and it belongs to whoever owns the facts block,
not to the model. Since the answer was wrong only because the belief was wrong,
the agent was rational and misinformed.

Where the answer would change: if the agent had evidence that its knowledge was
old and still asserted it, that *would* be irrational. My bot has two weak
defences against exactly that and neither is a real check — the facts block now
carries a version stamp, and a user rumour that contradicts the block loses
(`tests.md` question 12: "No, that is incorrect … Room A12"). If the block
carried an expiry date and the agent ignored it, or if it preferred a rumour over
its own block, the charge of irrationality would stick. The right fix for the
case above is still mundane: update the block, and stamp its date so the next
person can see how old it is.
